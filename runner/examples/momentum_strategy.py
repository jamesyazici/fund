"""Example: 1-minute momentum, event-driven.

Deploy (later phase):
    rqfc deploy runner/examples/momentum_strategy.py --pod "Your Pod"

Run locally against the hub:
    RQFC_BACKEND_URL=http://localhost:8000 \
    RQFC_STRATEGY_TOKEN=rqfc_your_api_key \
    RQFC_POD_ID=<pod-uuid> \
    RQFC_STRATEGY_FILE=runner/examples/momentum_strategy.py \
    NATS_URL=nats://localhost:4222 \
    python -m rqfc._runtime

Logic: each minute, once every symbol has `lookback` bars, rank by return over
that window, hold the top N in equal dollar amounts, exit anything that drops
out. Orders are placed through the normal backend; fills arrive later via
`on_fill` (no fill is assumed here).
"""
from rqfc import Strategy


class Momentum(Strategy):
    symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "META",
               "AMZN", "TSLA", "JPM", "V", "MA"]
    top_n = 3
    lookback = 6  # bars

    def on_start(self):
        self._closes: dict[str, list[float]] = {s: [] for s in self.symbols}
        self._last_minute: str | None = None
        print(f"[momentum] watching {len(self.symbols)} symbols", flush=True)

    def on_bar(self, bar):
        sym = bar["symbol"]
        series = self._closes.setdefault(sym, [])
        series.append(bar["close"])
        self._closes[sym] = series[-self.lookback:]

        # Rebalance at most once per bar minute, and only once warmed up.
        minute = str(bar["timestamp"])[:16]
        if minute == self._last_minute:
            return
        if any(len(self._closes[s]) < self.lookback for s in self.symbols):
            return
        self._last_minute = minute

        momentum = {
            s: c[-1] / c[0] - 1
            for s, c in self._closes.items()
            if len(c) >= self.lookback and c[0] > 0
        }
        target = set(sorted(momentum, key=momentum.get, reverse=True)[: self.top_n])

        held = {p["symbol"]: p["quantity"] for p in self.acct.positions()}
        for s, qty in held.items():
            if s not in target and qty:
                self.acct.sell(s, qty)

        to_buy = [s for s in target if s not in held]
        if not to_buy:
            return
        cash = self.acct.account().get("cash", 0) or 0
        if cash <= 0:
            return
        per_name = cash / len(to_buy)
        for s in to_buy:
            self.acct.dollar_buy(s, per_name)

    def on_fill(self, fill):
        print(f"[momentum] fill {fill.get('side')} {fill.get('filled_qty')} "
              f"{fill.get('symbol')} @ {fill.get('price')}", flush=True)
