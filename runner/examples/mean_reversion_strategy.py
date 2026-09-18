"""Example: mean reversion via z-score, event-driven, ~S&P 100 universe.

Deploy:
    rqfc deploy runner/examples/mean_reversion_strategy.py --pod "Your Pod"

Logic: every `decision_interval_minutes` (default 15), for every symbol, look
at its z-score over the last `window` one-minute closes — how many standard
deviations the latest close sits from its own rolling average. Buy when a
symbol looks unusually cheap relative to its recent average (z-score below
entry_z); sell once it reverts back toward the mean (z-score above exit_z).
Long-only, one position per symbol, fixed dollar size per entry.

Bars still update the rolling window every minute — only the buy/sell
decision itself is throttled to once per interval, across the whole universe
at once. (There's no separate timer hook in the runtime; this just skips the
decision pass until enough wall-clock time has passed since the last one,
using whichever bar happens to arrive next as the trigger.)

Mirror image of the momentum example: momentum bets a move continues, mean
reversion bets it snaps back. Same Strategy API, same Account, same
"no assumed fills" — on_fill just logs what the broker actually reports.
"""
from rqfc import Strategy

# Approximately the S&P 100 (OEX) by sector — large, liquid names so IEX
# prints frequently enough to be useful. Constituents drift over time; this
# is a snapshot, not a live index feed.
SNP100_APPROX = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL", "CRM", "ADBE",
    "CSCO", "ACN", "IBM", "TXN", "QCOM", "AMD", "INTC", "AMAT", "LRCX",
    "ADI", "INTU", "NOW", "MU",
    # Consumer Discretionary
    "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG", "SBUX", "TJX",
    # Communication Services
    "NFLX", "CMCSA", "VZ", "T", "DIS", "TMUS",
    # Financials
    "BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK",
    "AXP", "SCHW", "C", "CB", "PGR", "CME", "USB", "PNC", "MMC", "AON",
    # Health Care
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "AMGN",
    "ISRG", "ELV", "MDT", "GILD", "VRTX", "SYK", "BSX", "CI", "REGN", "ZTS",
    # Industrials
    "RTX", "HON", "UNP", "CAT", "GE", "BA", "DE", "ADP", "ETN", "UPS",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB",
    # Consumer Staples
    "PG", "KO", "PEP", "COST", "WMT", "PM", "MO",
    # Utilities / Materials / Real Estate
    "NEE", "SO", "DUK", "LIN", "PLD",
]


class MeanReversion(Strategy):
    symbols = SNP100_APPROX
    window = 20                     # bars in the rolling mean/std
    entry_z = -1.5                   # buy when this far below the rolling mean
    exit_z = 0.0                      # sell once back to (or above) the rolling mean
    dollars_per_position = 2000
    decision_interval_minutes = 15

    def on_start(self):
        self._closes: dict[str, list[float]] = {s: [] for s in self.symbols}
        self._last_bucket: str | None = None
        print(
            f"[mean_reversion] watching {len(self.symbols)} symbols, "
            f"window={self.window}, deciding every {self.decision_interval_minutes}m",
            flush=True,
        )

    @staticmethod
    def _zscore(closes: list[float], window: int) -> float | None:
        if len(closes) < window:
            return None
        mean = sum(closes) / len(closes)
        variance = sum((c - mean) ** 2 for c in closes) / len(closes)
        std = variance ** 0.5
        if std == 0:
            return None
        return (closes[-1] - mean) / std

    def _bucket(self, timestamp: str) -> str:
        """Round an ISO timestamp down to the current decision_interval_minutes bucket."""
        minute = int(timestamp[14:16])
        rounded = (minute // self.decision_interval_minutes) * self.decision_interval_minutes
        return f"{timestamp[:14]}{rounded:02d}"

    def on_bar(self, bar):
        sym = bar["symbol"]
        series = self._closes.setdefault(sym, [])
        series.append(bar["close"])
        self._closes[sym] = series[-self.window:]

        bucket = self._bucket(str(bar["timestamp"]))
        if bucket == self._last_bucket:
            return  # already made a decision for this window
        self._last_bucket = bucket
        self._decide()

    def _decide(self) -> None:
        held = {p["symbol"]: p["quantity"] for p in self.acct.positions()}
        for sym, closes in self._closes.items():
            z = self._zscore(closes, self.window)
            if z is None:
                continue
            holding = bool(held.get(sym))
            if not holding and z <= self.entry_z:
                self.acct.dollar_buy(sym, self.dollars_per_position)
            elif holding and z >= self.exit_z:
                self.acct.sell(sym, held[sym])

    def on_fill(self, fill):
        print(f"[mean_reversion] fill {fill.get('side')} {fill.get('filled_qty')} "
              f"{fill.get('symbol')} @ {fill.get('price')}", flush=True)
