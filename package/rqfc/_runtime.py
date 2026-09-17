"""In-sandbox strategy runtime.

Runs inside a pod's sandbox container (``python -m rqfc._runtime``). It:

* loads the deployed strategy file,
* subscribes to that strategy's market-data subjects on the local NATS bus,
* dispatches ``on_bar`` / ``on_trade`` / ``on_quote`` / ``on_fill`` to the
  strategy in a worker thread with a per-hook wall-clock budget,
* lets the strategy trade through the ordinary ``rqfc`` Account, i.e. the
  existing backend ``/orders`` endpoint — nothing new server-side is required
  for order submission.

Fills arrive asynchronously on ``exec.fill.<pod_id>`` (published by the VM
fills-listener, added in a later phase). Until then ``on_fill`` simply never
fires and orders behave exactly as they do today.

Requires the optional extra:  ``pip install "rqfc[runtime]"``  (pulls ``nats-py``).

Environment
-----------
RQFC_BACKEND_URL       backend base URL (required)
RQFC_STRATEGY_TOKEN    pod-scoped bearer token or an ``rqfc_`` API key (required)
RQFC_POD_ID            pod UUID (required)
RQFC_STRATEGY_FILE     path to the strategy .py  (default: /strategy/strategy.py)
NATS_URL               e.g. nats://nats:4222     (default)
RQFC_EVENT_TIMEOUT_MS  per-hook wall-clock budget in ms (default: 30000)
RQFC_CLOCK_SYMBOL      bar symbol used as a daily clock for legacy run() (default: SPY)
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import signal
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from ._session import Session
from .client import Account
from .strategy import DailyRunAdapter, Strategy

_HEARTBEAT_SECONDS = 15
_QUEUE_MAX = 2000


def _env(key: str, default: str | None = None, *, required: bool = False) -> str:
    val = os.environ.get(key, default)
    if required and not val:
        print(f"[runtime] missing required env var {key}", file=sys.stderr, flush=True)
        raise SystemExit(2)
    return val or ""


def load_strategy(path: str, acct: Account) -> Strategy:
    """Import ``path`` and return an instantiated strategy.

    Prefers an explicit :class:`Strategy` subclass; falls back to a legacy
    ``run(date, acct)`` function wrapped in :class:`DailyRunAdapter`.
    """
    if not os.path.exists(path):
        raise SystemExit(f"[runtime] strategy file not found: {path}")
    spec = importlib.util.spec_from_file_location("rqfc_user_strategy", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[runtime] could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["rqfc_user_strategy"] = module
    spec.loader.exec_module(module)

    for obj in vars(module).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, Strategy)
            and obj not in (Strategy, DailyRunAdapter)
        ):
            return obj(acct)
    run_fn = getattr(module, "run", None)
    if callable(run_fn):
        return DailyRunAdapter(acct, run_fn)
    raise SystemExit(
        "[runtime] strategy file must define a Strategy subclass or a run(date, acct) function"
    )


class Runtime:
    def __init__(self) -> None:
        self.backend = _env("RQFC_BACKEND_URL", required=True)
        self.token = _env("RQFC_STRATEGY_TOKEN", required=True)
        self.pod_id = _env("RQFC_POD_ID", required=True)
        self.strategy_file = _env("RQFC_STRATEGY_FILE", "/strategy/strategy.py")
        self.nats_url = _env("NATS_URL", "nats://nats:4222")
        self.timeout = float(_env("RQFC_EVENT_TIMEOUT_MS", "30000")) / 1000.0
        self.clock_symbol = _env("RQFC_CLOCK_SYMBOL", "SPY").upper()

        session = Session(self.backend)
        # Any bearer string works here — a pod-scoped strategy token or an
        # rqfc_ API key. The backend already accepts both on /orders.
        session.use_api_key(self.token)
        self.acct = Account(session, self.pod_id)  # UUID -> no name-resolution call

        self.strategy = load_strategy(self.strategy_file, self.acct)
        self.symbols = sorted({s.upper() for s in (self.strategy.symbols or [])})

        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="strategy")
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAX)
        self._last_bar_ts: dict[str, str] = {}
        self._stopping = asyncio.Event()
        self._nc = None

    # ── subjects ────────────────────────────────────────────────────────────
    def _subjects(self) -> list[str]:
        subjects = [f"exec.fill.{self.pod_id}"]
        for sym in self.symbols or [self.clock_symbol]:
            subjects.append(f"md.bar.{sym}")
        for sym in self.symbols:
            subjects.append(f"md.trade.{sym}")
            subjects.append(f"md.quote.{sym}")
        return subjects

    # ── NATS -> queue ──────────────────────────────────────────────────────
    async def _on_msg(self, msg) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            return
        parts = msg.subject.split(".")
        kind = parts[1] if len(parts) > 1 else parts[0]  # md.<kind>.<sym> | exec.fill.<pod>

        if kind == "bar":
            sym = payload.get("symbol", "")
            ts = str(payload.get("timestamp", ""))
            if ts and self._last_bar_ts.get(sym) == ts:
                return  # this exact bar was already queued
            if ts:
                self._last_bar_ts[sym] = ts

        item = (kind, payload)
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            # Drop the oldest event and keep the newest — a slow strategy never
            # wedges the bus, it just misses stale data.
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                pass
            try:
                self._queue.put_nowait(item)
            except Exception:
                pass

    # ── queue -> strategy hooks ───────────────────────────────────────────
    async def _call(self, hook: str, *args) -> None:
        fn = getattr(self.strategy, hook, None)
        if fn is None:
            return
        loop = asyncio.get_running_loop()
        started = time.monotonic()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(self._pool, lambda: fn(*args)), self.timeout
            )
        except asyncio.TimeoutError:
            print(
                f"[runtime] WARN {hook} exceeded {self.timeout:.1f}s budget "
                f"(still running in background)",
                flush=True,
            )
        except Exception:
            print(f"[runtime] ERROR in {hook}:\n{traceback.format_exc()}", flush=True)
        else:
            dur = time.monotonic() - started
            if dur > self.timeout * 0.5:
                print(f"[runtime] {hook} took {dur:.2f}s", flush=True)

    async def _consume(self) -> None:
        hooks = {"bar": "on_bar", "trade": "on_trade", "quote": "on_quote", "fill": "on_fill"}
        while not self._stopping.is_set():
            try:
                kind, payload = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            try:
                await self._call(hooks.get(kind, ""), payload)
            finally:
                self._queue.task_done()

    async def _heartbeat(self) -> None:
        while not self._stopping.is_set():
            print(
                f"[runtime] heartbeat pod={self.pod_id[:8]} "
                f"strategy={type(self.strategy).__name__} qsize={self._queue.qsize()}",
                flush=True,
            )
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=_HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                pass

    # ── main loop ─────────────────────────────────────────────────────────
    async def run(self) -> None:
        import nats

        self._nc = await nats.connect(
            self.nats_url,
            name=f"strategy-{self.pod_id[:8]}",
            max_reconnect_attempts=-1,
        )

        want = self.symbols or [self.clock_symbol]
        # Ask the hub to make sure these symbols are on the upstream feed.
        # (No-op until the hub grows a control listener in a later phase.)
        await self._nc.publish(
            "hub.control", json.dumps({"action": "subscribe", "symbols": want}).encode()
        )
        for subject in self._subjects():
            await self._nc.subscribe(subject, cb=self._on_msg)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._stopping.set)
            except (NotImplementedError, RuntimeError):
                pass

        print(
            f"[runtime] started pod={self.pod_id} "
            f"strategy={type(self.strategy).__name__} symbols={want} "
            f"backend={self.backend}",
            flush=True,
        )
        await self._call("on_start")

        consumer = asyncio.create_task(self._consume())
        heartbeat = asyncio.create_task(self._heartbeat())
        await self._stopping.wait()

        print("[runtime] stopping…", flush=True)
        consumer.cancel()
        heartbeat.cancel()
        await self._call("on_stop")
        try:
            await self._nc.drain()
        except Exception:
            pass
        self._pool.shutdown(wait=False, cancel_futures=True)


def main() -> None:
    asyncio.run(Runtime().run())


if __name__ == "__main__":
    main()
