"""Example: mean reversion via z-score, event-driven.

Deploy:
    rqfc deploy runner/examples/mean_reversion_strategy.py --pod "Your Pod"

Logic: for each symbol, track a rolling window of 1-minute closes and compute
how many standard deviations the latest close sits from its own rolling
average (a z-score). Buy when a symbol looks unusually cheap relative to its
recent average (z-score below entry_z); sell once it reverts back toward the
mean (z-score above exit_z). Long-only, one position per symbol, fixed dollar
size per entry.

Mirror image of the momentum example: momentum bets a move continues, mean
reversion bets it snaps back. Same Strategy API, same Account, same
"no assumed fills" — on_fill just logs what the broker actually reports.
"""
from rqfc import Strategy


class MeanReversion(Strategy):
    symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "META",
               "AMZN", "TSLA", "JPM", "V", "MA"]
    window = 20                # bars in the rolling mean/std
    entry_z = -1.5              # buy when this far below the rolling mean
    exit_z = 0.0                 # sell once back to (or above) the rolling mean
    dollars_per_position = 2000

    def on_start(self):
        self._closes: dict[str, list[float]] = {s: [] for s in self.symbols}
        print(f"[mean_reversion] watching {len(self.symbols)} symbols, window={self.window}", flush=True)

    def _zscore(self, closes: list[float]) -> float | None:
        if len(closes) < self.window:
            return None
        mean = sum(closes) / len(closes)
        variance = sum((c - mean) ** 2 for c in closes) / len(closes)
        std = variance ** 0.5
        if std == 0:
            return None
        return (closes[-1] - mean) / std

    def on_bar(self, bar):
        sym = bar["symbol"]
        series = self._closes.setdefault(sym, [])
        series.append(bar["close"])
        self._closes[sym] = series[-self.window:]

        z = self._zscore(self._closes[sym])
        if z is None:
            return  # not enough history yet

        held = {p["symbol"]: p["quantity"] for p in self.acct.positions()}
        holding = bool(held.get(sym))

        if not holding and z <= self.entry_z:
            self.acct.dollar_buy(sym, self.dollars_per_position)
        elif holding and z >= self.exit_z:
            self.acct.sell(sym, held[sym])

    def on_fill(self, fill):
        print(f"[mean_reversion] fill {fill.get('side')} {fill.get('filled_qty')} "
              f"{fill.get('symbol')} @ {fill.get('price')}", flush=True)
