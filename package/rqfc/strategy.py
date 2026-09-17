"""Event-driven strategy interface.

A strategy deployed to a pod is a single ``.py`` file that defines **either**:

1. a subclass of :class:`Strategy` that overrides any of the event hooks, or
2. a plain ``run(date, acct)`` function (the backtest / ``run_live.py`` signature)
   — it is wrapped automatically by :class:`DailyRunAdapter` and invoked once per
   trading day.

Every hook has access to ``self.acct`` — the ordinary ``rqfc`` :class:`~rqfc.client.Account`
object — so ``self.acct.buy(...)``, ``self.acct.positions()``, ``self.acct.account()``
behave exactly as they do in a manual session. Market-data events arrive as plain
dicts (see each hook's docstring for the shape).

The class is intentionally dependency-free so ``import rqfc`` stays lightweight;
the runtime that actually drives these hooks lives in :mod:`rqfc._runtime` and
needs the optional ``runtime`` extra.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class Strategy:
    """Base class for a deployed strategy.

    Override :attr:`symbols` and any of the ``on_*`` hooks. Unset hooks are
    simply never called.
    """

    #: Symbols this strategy wants streamed to it. Set at class level, e.g.
    #: ``symbols = ["AAPL", "MSFT"]``. Empty means "no market-data subscription";
    #: the runtime still drives a legacy ``run()`` via a clock symbol.
    symbols: list[str] = []

    def __init__(self, acct):
        self.acct = acct

    # ── lifecycle ───────────────────────────────────────────────────────────
    def on_start(self) -> None:
        """Called once, after the bus connects, before any market data."""

    def on_stop(self) -> None:
        """Called once during shutdown or redeploy. Best-effort."""

    # ── market data ─────────────────────────────────────────────────────────
    def on_trade(self, trade: dict) -> None:
        """A print. ``{"symbol", "price", "size", "timestamp"}``."""

    def on_quote(self, quote: dict) -> None:
        """Top of book.
        ``{"symbol", "bid_price", "bid_size", "ask_price", "ask_size", "timestamp"}``.
        """

    def on_bar(self, bar: dict) -> None:
        """A 1-minute bar.
        ``{"symbol", "open", "high", "low", "close", "volume", "timestamp"}``.
        """

    # ── execution ───────────────────────────────────────────────────────────
    def on_fill(self, fill: dict) -> None:
        """A real fill reported by the broker — never assume a fill before this.
        ``{"order_id", "symbol", "side", "qty", "price", "filled_qty", "status",
        "timestamp"}``.
        """


class DailyRunAdapter(Strategy):
    """Adapts a legacy ``run(date, acct)`` function to the :class:`Strategy` API.

    ``run`` is invoked once when the strategy starts, then again on the first bar
    of each new UTC day. A legacy strategy that declares no :attr:`symbols` is
    driven by the runtime's clock symbol (``SPY`` by default), so it still fires
    once per trading day.
    """

    symbols: list[str] = []

    def __init__(self, acct, run_fn):
        super().__init__(acct)
        self._run_fn = run_fn
        self._last_day: str | None = None

    def on_start(self) -> None:
        self._maybe_run(_utc_today())

    def on_bar(self, bar: dict) -> None:
        self._maybe_run(str(bar.get("timestamp", ""))[:10] or _utc_today())

    def _maybe_run(self, day: str) -> None:
        if not day or day == self._last_day:
            return
        self._last_day = day
        self._run_fn(day, self.acct)
