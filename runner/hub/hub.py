"""Market-data hub: one Alpaca websocket -> local NATS bus.

One process per VM. Subscribes to the symbols in ``HUB_SYMBOLS`` and republishes
every trade / quote / 1-minute bar as JSON:

    md.trade.<SYMBOL>   {"symbol", "price", "size", "timestamp"}
    md.quote.<SYMBOL>   {"symbol", "bid_price", "bid_size", "ask_price", "ask_size", "timestamp"}
    md.bar.<SYMBOL>     {"symbol", "open", "high", "low", "close", "volume", "timestamp"}

Dynamic subscription over the ``hub.control`` subject arrives with the supervisor
in a later phase. For now, set ``HUB_SYMBOLS`` to the union of every symbol your
deployed strategies need.

Environment
-----------
HUB_ALPACA_KEY, HUB_ALPACA_SECRET   Alpaca market-data credentials (free tier = IEX)
HUB_FEED                            "iex" (default) or "sip"
HUB_SYMBOLS                         comma-separated, e.g. "AAPL,MSFT,SPY"
NATS_URL                            nats://nats:4222 (default)
"""
from __future__ import annotations

import asyncio
import json
import os

import nats
from alpaca.data.enums import DataFeed
from alpaca.data.live import StockDataStream

NATS_URL = os.environ.get("NATS_URL", "nats://nats:4222")
FEED = DataFeed.SIP if os.environ.get("HUB_FEED", "iex").lower() == "sip" else DataFeed.IEX
SYMBOLS = sorted({s.strip().upper() for s in os.environ.get("HUB_SYMBOLS", "").split(",") if s.strip()})
KEY = os.environ.get("HUB_ALPACA_KEY", "")
SECRET = os.environ.get("HUB_ALPACA_SECRET", "")


async def main() -> None:
    if not KEY or not SECRET:
        raise SystemExit("HUB_ALPACA_KEY / HUB_ALPACA_SECRET are required")

    nc = await nats.connect(NATS_URL, name="marketdata-hub", max_reconnect_attempts=-1)
    print(f"[hub] NATS {NATS_URL} | feed={FEED.value} | symbols={SYMBOLS or '(none)'}", flush=True)

    async def publish(subject: str, obj: dict) -> None:
        try:
            await nc.publish(subject, json.dumps(obj).encode())
        except Exception as exc:  # a publish error must never kill the stream
            print(f"[hub] publish failed {subject}: {exc}", flush=True)

    async def on_trade(t) -> None:
        await publish(f"md.trade.{t.symbol}", {
            "symbol": t.symbol,
            "price": float(t.price),
            "size": float(getattr(t, "size", 0) or 0),
            "timestamp": t.timestamp.isoformat(),
        })

    async def on_quote(q) -> None:
        await publish(f"md.quote.{q.symbol}", {
            "symbol": q.symbol,
            "bid_price": float(getattr(q, "bid_price", 0) or 0),
            "bid_size": float(getattr(q, "bid_size", 0) or 0),
            "ask_price": float(getattr(q, "ask_price", 0) or 0),
            "ask_size": float(getattr(q, "ask_size", 0) or 0),
            "timestamp": q.timestamp.isoformat(),
        })

    async def on_bar(b) -> None:
        await publish(f"md.bar.{b.symbol}", {
            "symbol": b.symbol,
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(getattr(b, "volume", 0) or 0),
            "timestamp": b.timestamp.isoformat(),
        })

    stream = StockDataStream(KEY, SECRET, feed=FEED)
    if SYMBOLS:
        stream.subscribe_trades(on_trade, *SYMBOLS)
        stream.subscribe_quotes(on_quote, *SYMBOLS)
        stream.subscribe_bars(on_bar, *SYMBOLS)
    else:
        print("[hub] HUB_SYMBOLS is empty — nothing to stream", flush=True)

    # `_run_forever()` is alpaca-py's coroutine entrypoint for running the
    # websocket inside an existing event loop (StockDataStream.run() just wraps
    # asyncio.run around it). It reconnects internally on disconnect.
    while True:
        try:
            await stream._run_forever()
        except Exception as exc:
            print(f"[hub] stream error, reconnecting in 5s: {exc}", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
