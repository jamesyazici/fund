"""
rqfc daily backtester.

Strategy files must expose one function:

    def run(date: str, acct) -> None:
        ...

    date  — 'YYYY-MM-DD' string for the current simulation day
    acct  — a BacktestAccount that mirrors the real rqfc Account API:
              acct.bars(symbol, days=30)   -> list of OHLCV dicts
              acct.price(symbol)           -> {"symbol": ..., "price": ...}
              acct.positions()             -> list of position dicts
              acct.account()               -> {"portfolio_value", "cash", ...}
              acct.buy(symbol, qty)        -> queued, executes at next-day open
              acct.sell(symbol, qty)       -> queued, executes at next-day open
              acct.short(symbol, qty)      -> queued, executes at next-day open
              acct.cover(symbol, qty)      -> queued, executes at next-day open
              acct.dollar_buy(symbol, $)   -> queued, executes at next-day open
              acct.dollar_sell(symbol, $)  -> queued, executes at next-day open

Code written for live trading with the rqfc package runs unchanged here.
Orders placed inside run() execute at the next trading day's open (no lookahead).

Requires: pandas  (pip install pandas)
Data:     Alpaca free tier — daily OHLCV back to ~2016 for US equities.
"""

import importlib.util
import random
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Default universe: ~200 large-cap US equities with history back to 2016 ──────

_DEFAULT_UNIVERSE = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "CSCO", "ADBE", "CRM", "ORCL",
    "IBM", "TXN", "QCOM", "AMD", "INTC", "AMAT", "LRCX", "KLAC", "ADI", "MCHP",
    "NOW", "INTU", "CDNS", "SNPS", "FTNT", "PANW",
    # Consumer / Retail / E-commerce
    "AMZN", "TSLA", "NFLX", "BKNG", "EBAY", "ROST", "TJX", "COST", "WMT", "TGT",
    "HD", "LOW", "MCD", "SBUX", "YUM", "CMG", "DLTR", "ORLY", "FAST", "CPRT",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "ABT", "TMO", "DHR", "ISRG",
    "BSX", "SYK", "EW", "ZTS", "GILD", "AMGN", "VRTX", "REGN", "BIIB", "IDXX",
    "IQV", "ELV", "HUM", "CI", "CVS", "MCK",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "V", "MA",
    "COF", "USB", "PNC", "CME", "ICE", "SPGI", "MSCI", "AON", "MMC",
    "AIG", "MET", "PRU", "ALL", "TRV", "CB",
    # Industrials
    "GE", "HON", "CAT", "DE", "UNP", "CSX", "NSC", "FDX", "UPS", "RTX",
    "LHX", "ETN", "EMR", "PH", "ITW", "ROP", "GWW", "PCAR", "ODFL", "CTAS",
    "RSG", "WM",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "VLO", "PSX", "OXY", "KMI",
    "WMB", "HES",
    # Consumer Staples
    "PG", "KO", "PEP", "PM", "MO", "CL", "KMB", "GIS", "STZ", "MNST",
    # Utilities / Real Estate
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "XEL", "PEG", "SRE", "ED",
    "O", "PLD", "SPG", "CCI", "WELL", "DLR", "PSA", "AVB",
    # Materials
    "LIN", "APD", "ECL", "SHW", "PPG", "DOW", "FCX",
    # Telecom
    "T", "VZ",
    # Other large caps
    "ACN", "TDG", "MAR", "HLT", "HCA", "F", "GM", "VRSK", "EFX", "DXCM",
]

_DATA_EARLIEST = date(2016, 1, 1)


# ── BacktestAccount — mirrors the real rqfc Account API ──────────────────────────

class BacktestAccount:
    """
    Drop-in replacement for rqfc.Account during a backtest.
    Order calls are queued and executed at the next trading day's open price.
    All read methods (bars, positions, account, price) reflect state as of `current_date`.
    """

    def __init__(self, dfs: dict, current_date: str, positions: dict, cash: float):
        self._dfs      = dfs            # {symbol: DataFrame}
        self._date     = current_date   # 'YYYY-MM-DD'
        self._pos      = positions      # {symbol: {"qty": float, "avg_entry": float}}
        self._cash     = cash
        self._pending  = []             # orders queued this day

    # ── Read methods ─────────────────────────────────────────────────────────────

    def bars(self, symbol: str, days: int = 30) -> list:
        df = self._dfs.get(symbol.upper())
        if df is None:
            return []
        sliced = df[df.index <= self._date].tail(days)
        return [
            {
                "date":   idx,
                "open":   float(row["open"]),
                "high":   float(row["high"]),
                "low":    float(row["low"]),
                "close":  float(row["close"]),
                "volume": float(row["volume"]),
            }
            for idx, row in sliced.iterrows()
        ]

    def price(self, symbol: str) -> dict:
        df = self._dfs.get(symbol.upper())
        if df is None or self._date not in df.index:
            return None
        return {"symbol": symbol.upper(), "price": float(df.loc[self._date, "close"])}

    def positions(self) -> list:
        result = []
        for sym, pos in self._pos.items():
            qty = pos.get("qty", 0)
            if qty <= 1e-6:
                continue
            df = self._dfs.get(sym)
            if df is not None and self._date in df.index:
                cur_px = float(df.loc[self._date, "close"])
            else:
                cur_px = pos["avg_entry"]
            mv = qty * cur_px
            result.append({
                "symbol":            sym,
                "instrument_type":   "equity",
                "underlying_symbol": None,
                "quantity":          qty,
                "avg_entry_price":   pos["avg_entry"],
                "current_price":     cur_px,
                "market_value":      mv,
                "cost_basis":        qty * pos["avg_entry"],
                "multiplier":        1.0,
                "unrealized_pnl":    mv - qty * pos["avg_entry"],
            })
        return result

    def account(self) -> dict:
        pos_value = sum(p["market_value"] for p in self.positions())
        nav = self._cash + pos_value
        return {
            "portfolio_value": nav,
            "cash":            self._cash,
            "buying_power":    self._cash,
            "equity":          nav,
        }

    # ── Order methods (queued, execute at next open) ──────────────────────────────

    def buy(self, symbol: str, qty, order_type=None, limit_price=None,
            time_in_force=None, override_risk=False):
        self._pending.append({"side": "buy", "symbol": symbol.upper(),
                              "qty": float(qty), "notional": None})

    def sell(self, symbol: str, qty, order_type=None, limit_price=None,
             time_in_force=None, override_risk=False):
        self._pending.append({"side": "sell", "symbol": symbol.upper(),
                              "qty": float(qty), "notional": None})

    def short(self, symbol: str, qty, time_in_force=None, override_risk=False):
        self._pending.append({"side": "short", "symbol": symbol.upper(),
                              "qty": float(qty), "notional": None})

    def cover(self, symbol: str, qty, time_in_force=None, override_risk=False):
        self._pending.append({"side": "cover", "symbol": symbol.upper(),
                              "qty": float(qty), "notional": None})

    def dollar_buy(self, symbol: str, amount, time_in_force=None, override_risk=False):
        self._pending.append({"side": "buy", "symbol": symbol.upper(),
                              "qty": None, "notional": float(amount)})

    def dollar_sell(self, symbol: str, amount, time_in_force=None, override_risk=False):
        self._pending.append({"side": "sell", "symbol": symbol.upper(),
                              "qty": None, "notional": float(amount)})

    # ── No-ops (not meaningful in backtest) ──────────────────────────────────────

    def cancel(self, *a, **k):      return None
    def sync(self, *a, **k):        return {}
    def history(self, *a, **k):     return []
    def orders(self, *a, **k):      return []
    def show_account(self):         print(self.account())
    def show_positions(self):       print(self.positions())
    def show_orders(self, *a, **k): pass
    def show_history(self, *a, **k): pass


# ── Strategy loader ──────────────────────────────────────────────────────────────

def _load_strategy(file_path: str):
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {path}")
    spec   = importlib.util.spec_from_file_location("_rqfc_strategy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        raise AttributeError(
            f"{path.name} must define:  run(date, acct) -> None"
        )
    return module.run


# ── Date helpers ─────────────────────────────────────────────────────────────────

def _random_year_window():
    today = date.today()
    latest_start = today - timedelta(days=400)
    delta_days = (latest_start - _DATA_EARLIEST).days
    if delta_days <= 0:
        raise RuntimeError("System date appears to be before 2017.")
    start = _DATA_EARLIEST + timedelta(days=random.randint(0, delta_days))
    end   = start + timedelta(days=365)
    return start.isoformat(), end.isoformat()


# ── Data fetching ────────────────────────────────────────────────────────────────

def _fetch_bulk_bars(sess, pod_id: str, universe: list, start: str, end: str) -> dict:
    return sess.get("/market/bulk-bars", {
        "pod_id":  pod_id,
        "symbols": ",".join(universe),
        "start":   start,
        "end":     end,
    })


def _build_dfs(raw_bars: dict) -> dict:
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for backtesting:  pip install pandas")

    dfs = {}
    for symbol, bars in raw_bars.items():
        if not bars:
            continue
        df = pd.DataFrame(bars)
        df["date"] = df["date"].astype(str)
        df = df.set_index("date").sort_index()
        for col in ("open", "high", "low", "close", "volume"):
            if col in df.columns:
                df[col] = df[col].astype(float)
        dfs[symbol] = df
    return dfs


# ── Simulation ───────────────────────────────────────────────────────────────────

def _execute_order(order: dict, next_day: str, dfs: dict, positions: dict, cash: float):
    sym = order["symbol"]
    df  = dfs.get(sym)
    if df is None or next_day not in df.index:
        return cash

    px = float(df.loc[next_day, "open"])
    if px <= 0:
        return cash

    side     = order["side"]
    qty      = order["qty"]
    notional = order["notional"]

    if qty is None and notional is not None:
        qty = notional / px

    if qty is None or qty <= 0:
        return cash

    if side in ("buy", "short"):
        affordable = cash * 0.999 / px
        qty = min(qty, affordable)
        if qty <= 1e-6:
            return cash
        old_pos    = positions.get(sym, {"qty": 0, "avg_entry": 0})
        old_qty    = old_pos["qty"]
        new_qty    = old_qty + qty
        avg_entry  = ((old_qty * old_pos["avg_entry"]) + (qty * px)) / new_qty
        positions[sym] = {"qty": new_qty, "avg_entry": avg_entry}
        cash -= qty * px

    elif side in ("sell", "cover"):
        held = positions.get(sym, {"qty": 0})["qty"]
        qty  = min(qty, held)
        if qty <= 1e-6:
            return cash
        cash += qty * px
        new_qty = positions[sym]["qty"] - qty
        if new_qty <= 1e-6:
            del positions[sym]
        else:
            positions[sym]["qty"] = new_qty

    return cash


def _simulate(strategy_fn, dfs: dict, win_start: str, win_end: str, capital: float) -> list:
    all_dates = sorted(set(
        d for df in dfs.values()
        for d in df.index
        if win_start <= d <= win_end
    ))
    if not all_dates:
        return []

    cash      = float(capital)
    positions = {}  # {symbol: {"qty": float, "avg_entry": float}}
    equity_curve = []

    for i, today in enumerate(all_dates):
        # Mark to market at today's close
        pos_value = 0.0
        for sym, pos in positions.items():
            df = dfs.get(sym)
            if df is not None and today in df.index:
                pos_value += pos["qty"] * float(df.loc[today, "close"])
        nav = cash + pos_value
        equity_curve.append({"date": today, "nav": round(nav, 2)})

        # Create account snapshot for today — strategy sees state as of today's close
        acct = BacktestAccount(dfs, today, {s: dict(p) for s, p in positions.items()}, cash)

        try:
            strategy_fn(today, acct)
        except Exception:
            pass

        # Execute queued orders at next day's open
        if i + 1 >= len(all_dates):
            break
        next_day = all_dates[i + 1]
        for order in acct._pending:
            cash = _execute_order(order, next_day, dfs, positions, cash)

    return equity_curve


# ── Metrics ──────────────────────────────────────────────────────────────────────

def _metrics(equity_curve: list, bench_curve: list) -> dict:
    if len(equity_curve) < 2:
        return {}

    navs = [e["nav"] for e in equity_curve]
    rets = [(navs[i] / navs[i - 1]) - 1 for i in range(1, len(navs)) if navs[i - 1] > 0]
    if not rets:
        return {}

    n      = len(rets)
    mean_r = sum(rets) / n
    var    = sum((r - mean_r) ** 2 for r in rets) / (n - 1) if n > 1 else 0
    vol    = var ** 0.5
    sharpe = ((mean_r - 0.05 / 252) / vol * (252 ** 0.5)) if vol > 0 else 0.0

    start_dt  = datetime.fromisoformat(equity_curve[0]["date"])
    end_dt    = datetime.fromisoformat(equity_curve[-1]["date"])
    days      = max((end_dt - start_dt).days, 1)
    total_ret = (navs[-1] / navs[0]) - 1
    cagr      = (navs[-1] / navs[0]) ** (365 / days) - 1

    peak, max_dd = navs[0], 0.0
    for nav in navs:
        peak   = max(peak, nav)
        max_dd = max(max_dd, (peak - nav) / peak)

    bench_navs = [e["nav"] for e in bench_curve] if bench_curve else []
    bench_ret  = (
        (bench_navs[-1] / bench_navs[0]) - 1
        if len(bench_navs) >= 2 and bench_navs[0] > 0 else None
    )

    return {
        "total_return":     round(total_ret, 4),
        "cagr":             round(cagr, 4),
        "sharpe":           round(sharpe, 4),
        "max_drawdown":     round(max_dd, 4),
        "benchmark_return": round(bench_ret, 4) if bench_ret is not None else None,
    }


def _benchmark_curve(dfs: dict, all_dates: list, capital: float) -> list:
    spy = dfs.get("SPY")
    if spy is None or not all_dates:
        return []
    first_px = None
    curve    = []
    for d in all_dates:
        if d in spy.index:
            px = float(spy.loc[d, "close"])
            if first_px is None:
                first_px = px
            curve.append({"date": d, "nav": round(capital * px / first_px, 2)})
    return curve


# ── Results container ────────────────────────────────────────────────────────────

class BacktestResults(list):
    """
    List of result dicts, one per backtest window.
    Prints a clean summary table instead of raw data when passed to print().

    Each item has keys: start, end, capital, metrics, equity_curve, benchmark_curve.
    Access programmatically:
        results[0]["metrics"]["sharpe"]
        results[0]["equity_curve"]   # list of {"date", "nav"}
    """

    _strategy_name = ""

    def __str__(self):
        return _format_results(self, self._strategy_name)

    def __repr__(self):
        return _format_results(self, self._strategy_name)


# ── Output ───────────────────────────────────────────────────────────────────────

def _pct(v):
    if v is None:
        return "        —"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v * 100:.2f}%"


def _format_results(results, strategy_name: str) -> str:
    lines = []
    for r in results:
        m       = r["metrics"]
        curve   = r["equity_curve"]
        end_nav = curve[-1]["nav"] if curve else r["capital"]
        dd      = m.get("max_drawdown")

        lines.append("")
        lines.append("  ══════════════════════════════════════════════════")
        lines.append(f"  Strategy    {strategy_name}")
        lines.append(f"  Period      {r['start']}  →  {r['end']}")
        lines.append(f"  Capital     ${r['capital']:>12,.0f}")
        lines.append(f"  Final NAV   ${end_nav:>12,.0f}   ({_pct(m.get('total_return'))})")
        lines.append("  ──────────────────────────────────────────────────")
        lines.append(f"  CAGR                   {_pct(m.get('cagr')):>10}")
        lines.append(f"  Sharpe (annualised)    {m.get('sharpe', 0):>10.4f}")
        lines.append(f"  Max Drawdown           {_pct(-dd if dd else None):>10}")
        if m.get("benchmark_return") is not None:
            alpha = (m.get("total_return") or 0) - m["benchmark_return"]
            lines.append(f"  Benchmark SPY          {_pct(m['benchmark_return']):>10}")
            lines.append(f"  Alpha vs SPY           {_pct(alpha):>10}")
        lines.append("  ══════════════════════════════════════════════════")
        lines.append("")
    return "\n".join(lines)


def _print_results(results, strategy_name: str) -> None:
    print(_format_results(results, strategy_name))


# ── Public entry point ───────────────────────────────────────────────────────────

def run_daily_backtest(
    sess,
    pod_id: str,
    strategy_file: str,
    *,
    universe: list = None,
    start: str = None,
    end: str = None,
    capital: float = 100_000.0,
    draws: int = 1,
) -> list:
    strategy_fn   = _load_strategy(strategy_file)
    strategy_name = Path(strategy_file).stem
    universe = list(universe or _DEFAULT_UNIVERSE)
    if "SPY" not in universe:
        universe = ["SPY"] + universe

    windows = [(start, end)] if (start and end) else [_random_year_window() for _ in range(draws)]

    all_results = BacktestResults()
    all_results._strategy_name = strategy_name
    for win_start, win_end in windows:
        print(f"\n  Fetching {len(universe)} symbols  {win_start} → {win_end} …")
        raw   = _fetch_bulk_bars(sess, pod_id, universe, win_start, win_end)
        found = sum(1 for v in raw.values() if v)
        print(f"  Got data for {found}/{len(universe)} symbols. Simulating…")

        dfs = _build_dfs(raw)
        all_dates = sorted(set(
            d for df in dfs.values()
            for d in df.index
            if win_start <= d <= win_end
        ))

        equity_curve = _simulate(strategy_fn, dfs, win_start, win_end, capital)
        bench        = _benchmark_curve(dfs, all_dates, capital)
        m            = _metrics(equity_curve, bench)

        result = {
            "start": win_start, "end": win_end, "capital": capital,
            "equity_curve": equity_curve, "benchmark_curve": bench, "metrics": m,
        }
        all_results.append(result)

    _print_results(all_results, strategy_name)
    return all_results
