import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient

from . import db
from . import trading as _trading
from . import account as _account
from . import market_data as _market_data
from . import metrics as _metrics
from . import utils as _utils


class Account:
    """
    A student's trading account. All trading, portfolio, market data,
    and metrics operations are methods on this object.

    Obtain one via rqfc.init():
        account = rqfc.init("PKXXX...", "secret...")
    """

    def __init__(self, api_key: str, secret_key: str,
                 paper: bool = True, name: str = None):
        self._tc = TradingClient(api_key, secret_key, paper=paper)
        self._dc = StockHistoricalDataClient(api_key, secret_key)

        alpaca_acct = self._tc.get_account()
        self.account_id: str = alpaca_acct.id
        self.paper = paper

        # Link this Alpaca account to its pod/member row. Admins register
        # members with admin.add_member(...); until then nothing is logged.
        self._member = db.resolve_member(self.account_id)

        mode = "PAPER" if paper else "LIVE"
        if self._member:
            self.log_snapshot()
            label = f" ({self._member.get('name') or name})" if (self._member.get("name") or name) else ""
            print(f"rqfc initialized — {mode} | account: {self.account_id}{label} | pod linked ✓")
        else:
            print(f"rqfc initialized — {mode} | account: {self.account_id}")
            print(f"[rqfc] This account isn't registered to a pod yet — trades won't appear "
                  f"on the dashboard. Ask an admin to run:\n"
                  f"        admin.add_member(pod_id, 'Your Name', alpaca_account_id='{self.account_id}')")

    # -------------------------------------------------------------------------
    # Trading
    # -------------------------------------------------------------------------

    def buy(self, symbol: str, qty: float, order_type: str = "market",
            limit_price: float = None, time_in_force: str = "day"):
        """
        Buy shares of a stock.
            symbol:         Ticker, e.g. "AAPL"
            qty:            Number of shares
            order_type:     "market" (default) or "limit"
            limit_price:    Required when order_type="limit"
            time_in_force:  "day" (default), "gtc", "ioc", "fok"
        """
        return _trading.buy(self._tc, self._member, symbol, qty,
                            order_type, limit_price, time_in_force)

    def sell(self, symbol: str, qty: float, order_type: str = "market",
             limit_price: float = None, time_in_force: str = "day"):
        """Sell shares you own."""
        return _trading.sell(self._tc, self._member, symbol, qty,
                             order_type, limit_price, time_in_force)

    def short(self, symbol: str, qty: float, time_in_force: str = "day"):
        """Short sell — bet the price will drop. Close with cover()."""
        return _trading.short(self._tc, self._member, symbol, qty, time_in_force)

    def cover(self, symbol: str, qty: float, time_in_force: str = "day"):
        """Cover a short position — buy back the shorted shares."""
        return _trading.cover(self._tc, self._member, symbol, qty, time_in_force)

    def dollar_buy(self, symbol: str, amount: float, time_in_force: str = "day"):
        """Buy by dollar amount instead of share count. e.g. dollar_buy("AAPL", 5000)"""
        return _trading.dollar_buy(self._tc, self._member, symbol, amount, time_in_force)

    def dollar_sell(self, symbol: str, amount: float, time_in_force: str = "day"):
        """Sell by dollar amount instead of share count."""
        return _trading.dollar_sell(self._tc, self._member, symbol, amount, time_in_force)

    def bracket_order(self, symbol: str, qty: float, side: str,
                      take_profit: float, stop_loss: float,
                      time_in_force: str = "day"):
        """
        Enter a position with automatic take-profit and stop-loss attached.
            side:        "buy" or "sell"
            take_profit: Limit price to exit with a gain
            stop_loss:   Stop price to cap the loss
        """
        return _trading.bracket_order(self._tc, self._member, symbol, qty,
                                      side, take_profit, stop_loss, time_in_force)

    def trailing_stop(self, symbol: str, qty: float,
                      trail_percent: float, side: str = "sell"):
        """
        Trailing stop that follows the price automatically.
            trail_percent: How far (%) below peak to set the stop, e.g. 5.0 = 5%
        """
        return _trading.trailing_stop(self._tc, self._member, symbol, qty,
                                      trail_percent, side)

    def get_open_orders(self):
        """All pending (not yet filled) orders."""
        return _trading.get_open_orders(self._tc)

    def cancel_order(self, order_id: str):
        """Cancel a specific order by its Alpaca order ID."""
        return _trading.cancel_order(self._tc, order_id)

    def cancel_all_orders(self):
        """Cancel every open/pending order."""
        return _trading.cancel_all_orders(self._tc)

    def get_order_history(self, limit: int = 100):
        """Past filled and cancelled orders."""
        return _trading.get_order_history(self._tc, limit)

    # -------------------------------------------------------------------------
    # Account & positions
    # -------------------------------------------------------------------------

    def get_account(self):
        """Raw Alpaca account object: equity, buying power, margin, status."""
        return _account.get_account(self._tc)

    def get_portfolio_value(self) -> float:
        """Total current portfolio value in dollars."""
        return _account.get_portfolio_value(self._tc)

    def get_buying_power(self) -> float:
        """Cash currently available to trade."""
        return _account.get_buying_power(self._tc)

    def get_pnl(self) -> dict:
        """Unrealized P&L, realized P&L (today), and their sum."""
        return _account.get_pnl(self._tc)

    def get_position(self, symbol: str):
        """Current position for one stock: qty, avg entry, current price, P&L."""
        return _account.get_position(self._tc, symbol)

    def get_all_positions(self):
        """All open positions as a list of Alpaca Position objects."""
        return _account.get_all_positions(self._tc)

    def get_portfolio_summary(self) -> pd.DataFrame:
        """Full positions table as a DataFrame."""
        return _account.get_portfolio_summary(self._tc)

    def close_position(self, symbol: str):
        """Market-sell the entire position in one stock."""
        return _account.close_position(self._tc, symbol)

    def close_all_positions(self):
        """Liquidate the entire portfolio and cancel all open orders."""
        return _account.close_all_positions(self._tc)

    def get_concentration(self) -> pd.DataFrame:
        """Each position as a % of total portfolio — quick risk snapshot."""
        return _account.get_concentration(self._tc)

    def get_portfolio_history(self, days: int = None,
                              start: str = None, end: str = None) -> pd.DataFrame:
        """
        Equity curve over time as a DataFrame.
            days:  Number of calendar days to look back
            start: Start date "YYYY-MM-DD"
            end:   End date "YYYY-MM-DD" (defaults to today)
        """
        return _account.get_portfolio_history(self._tc, days=days, start=start, end=end)

    def get_portfolio_returns(self, days: int = None,
                              start: str = None, end: str = None) -> pd.Series:
        """Daily return series for the portfolio."""
        return _account.get_portfolio_returns(self._tc, days=days, start=start, end=end)

    def get_win_rate(self) -> dict:
        """% of completed round-trip trades that were profitable (FIFO matching)."""
        return _account.get_win_rate(self._tc)

    def rebalance(self, target_weights: dict):
        """
        Rebalance to target % weights. Positions not in target_weights are closed.
            target_weights: {"AAPL": 0.30, "TSLA": 0.20, "NVDA": 0.50}
        """
        return _account.rebalance(self._tc, self._member, target_weights)

    def log_snapshot(self):
        """
        Save current equity and cash to Supabase. Called automatically on init.
        Call this manually at the start of each trading session to keep the
        equity curve up to date for admin analytics.
        """
        try:
            acct = self._tc.get_account()
            db.log_snapshot(self._member, float(acct.equity), float(acct.cash))
        except Exception as e:
            print(f"[rqfc] Warning: could not log snapshot: {e}")

    def sync(self):
        """
        Push your current equity, cash, and open positions to Supabase so the
        Fund dashboard reflects your live portfolio.

        Call this at least once per trading session (and after big changes).
        Equity history drives your pod's NAV chart and risk metrics; positions
        feed the holdings table. Individual trades are logged automatically as
        you place them.
        """
        if not self._member:
            print("[rqfc] sync skipped — account not registered to a pod yet.")
            return
        self.log_snapshot()
        try:
            positions = self._tc.get_all_positions()
            rows = [{
                "symbol":          p.symbol,
                "quantity":        float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price":   float(p.current_price) if p.current_price else None,
                "market_value":    float(p.market_value) if p.market_value else None,
                "unrealized_pnl":  float(p.unrealized_pl) if p.unrealized_pl else None,
            } for p in positions]
            db.sync_positions(self._member, rows)
            print(f"[rqfc] Synced {len(rows)} position(s) and equity snapshot to the dashboard.")
        except Exception as e:
            print(f"[rqfc] Warning: could not sync positions: {e}")

    # -------------------------------------------------------------------------
    # Market data
    # -------------------------------------------------------------------------

    def get_price(self, symbol: str) -> float:
        """Latest trade price for a stock."""
        return _market_data.get_price(self._dc, symbol)

    def get_quote(self, symbol: str) -> dict:
        """Current bid/ask quote, sizes, and spread."""
        return _market_data.get_quote(self._dc, symbol)

    def get_bars(self, symbol: str, timeframe: str = "1D",
                 days: int = None, start: str = None,
                 end: str = None) -> pd.DataFrame:
        """
        OHLCV price history as a DataFrame.
            timeframe: "1D", "1H", "5Min", "15Min", "1W", etc.
        """
        return _market_data.get_bars(self._dc, symbol, timeframe, days, start, end)

    def get_snapshot(self, symbol: str) -> dict:
        """Full snapshot: price, bid/ask, daily OHLCV, and % change."""
        return _market_data.get_snapshot(self._dc, symbol)

    def get_snapshots(self, symbols: list) -> pd.DataFrame:
        """Snapshots for a list of tickers at once — much faster than looping."""
        return _market_data.get_snapshots(self._dc, symbols)

    def get_news(self, symbol: str, limit: int = 10) -> pd.DataFrame:
        """Recent news headlines for a stock."""
        return _market_data.get_news(self._dc, symbol, limit)

    def get_top_movers(self, n: int = 10) -> dict:
        """Biggest % gainers and losers today from a broad universe of liquid stocks."""
        return _market_data.get_top_movers(self._dc, n)

    def get_assets(self, asset_class: str = "us_equity") -> list:
        """All active tradeable assets."""
        return _market_data.get_assets(self._tc, asset_class)

    def is_tradeable(self, symbol: str) -> bool:
        """Quick check: is this symbol currently tradeable on Alpaca?"""
        return _market_data.is_tradeable(self._tc, symbol)

    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    def get_sharpe(self, days: int = 252, risk_free_rate: float = 0.05) -> float:
        """Annualized Sharpe ratio for the portfolio over the last N calendar days."""
        returns = _account.get_portfolio_returns(self._tc, days=days)
        return _metrics.get_sharpe(returns, risk_free_rate)

    def get_sortino(self, days: int = 252, risk_free_rate: float = 0.05) -> float:
        """Annualized Sortino ratio (penalizes only downside volatility)."""
        returns = _account.get_portfolio_returns(self._tc, days=days)
        return _metrics.get_sortino(returns, risk_free_rate)

    def get_max_drawdown(self, days: int = 252) -> float:
        """Max peak-to-trough drawdown. Returns a negative decimal: -0.23 = -23%."""
        returns = _account.get_portfolio_returns(self._tc, days=days)
        return _metrics.get_max_drawdown(returns)

    def get_beta(self, symbol: str, benchmark: str = "SPY",
                 days: int = 252) -> float:
        """Beta of a stock vs a benchmark (default SPY)."""
        stock_r = (_market_data
                   .get_bars(self._dc, symbol, timeframe="1D", days=days)["close"]
                   .pct_change().dropna())
        bench_r = (_market_data
                   .get_bars(self._dc, benchmark, timeframe="1D", days=days)["close"]
                   .pct_change().dropna())
        return _metrics.get_beta(stock_r, bench_r)

    def get_volatility(self, symbol: str, days: int = 30) -> float:
        """Annualized realized volatility for a stock. Returns a decimal: 0.25 = 25%."""
        bars = _market_data.get_bars(self._dc, symbol, timeframe="1D", days=days)
        returns = bars["close"].pct_change().dropna()
        return _metrics.get_volatility(returns)

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

    def is_market_open(self) -> bool:
        """Returns True if the US stock market is currently open."""
        return _utils.is_market_open(self._tc)

    def get_market_clock(self) -> dict:
        """Current market status and time to next open/close."""
        return _utils.get_market_clock(self._tc)


def init(api_key: str, secret_key: str,
         paper: bool = True, name: str = None) -> Account:
    """
    Initialize rqfc. Returns an Account object.

    Args:
        api_key:    Alpaca API key (found in Alpaca dashboard under API Keys)
        secret_key: Alpaca secret key
        paper:      True = paper trading (default), False = live trading
        name:       Optional display name stored in Supabase (e.g. "Alice")

    Requires SUPABASE_URL and SUPABASE_KEY environment variables to be set.
    """
    return Account(api_key, secret_key, paper=paper, name=name)
