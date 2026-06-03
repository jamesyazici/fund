import os
from collections import deque
from datetime import datetime, timedelta

import pandas as pd

from . import metrics as _metrics


class Admin:
    """
    Admin interface — read all students' trades and portfolio analytics
    from Supabase without needing access to anyone's Alpaca credentials.

    Requires the service role key (bypasses RLS) rather than the anon key.

    Usage:
        import rqfc
        admin = rqfc.Admin()   # reads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from env
    """

    def __init__(self, supabase_url: str = None, service_role_key: str = None):
        url = supabase_url or os.environ.get("SUPABASE_URL")
        key = service_role_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "Admin requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.\n"
                "Set them as environment variables or pass them directly:\n"
                "  admin = rqfc.Admin(supabase_url='...', service_role_key='...')"
            )
        try:
            from supabase import create_client
        except ImportError:
            raise RuntimeError("Run: pip install supabase")
        self._sb = create_client(url, key)

    # -------------------------------------------------------------------------
    # Trades
    # -------------------------------------------------------------------------

    def get_all_trades(self, account_id: str = None, symbol: str = None,
                       limit: int = 500) -> pd.DataFrame:
        """
        All trades across all students, newest first.

        Args:
            account_id: Filter to one student's Alpaca account ID
            symbol:     Filter to one ticker, e.g. "AAPL"
            limit:      Max rows to return (default 500)
        """
        query = (
            self._sb.table("trades")
            .select("*, accounts(display_name)")
            .order("created_at", desc=True)
        )
        if account_id:
            query = query.eq("account_id", account_id)
        if symbol:
            query = query.eq("symbol", symbol.upper())
        result = query.limit(limit).execute()
        if not result.data:
            return pd.DataFrame()
        df = pd.json_normalize(result.data)
        if "accounts.display_name" in df.columns:
            df = df.rename(columns={"accounts.display_name": "display_name"})
        return df

    # -------------------------------------------------------------------------
    # Per-student analytics
    # -------------------------------------------------------------------------

    def get_pnl(self, account_id: str) -> dict:
        """
        PnL for one student computed from stored portfolio snapshots.
        Returns starting equity, latest equity, and total return %.
        """
        snaps = (
            self._sb.table("portfolio_snapshots")
            .select("equity, recorded_at")
            .eq("account_id", account_id)
            .order("recorded_at")
            .execute()
        )
        if not snaps.data or len(snaps.data) < 2:
            return {"error": "Not enough snapshot data. Student needs to run log_snapshot() more."}
        start_equity = float(snaps.data[0]["equity"])
        latest_equity = float(snaps.data[-1]["equity"])
        pnl = latest_equity - start_equity
        return {
            "account_id":       account_id,
            "start_equity":     round(start_equity, 2),
            "latest_equity":    round(latest_equity, 2),
            "total_pnl":        round(pnl, 2),
            "total_return_pct": round(pnl / start_equity * 100, 2) if start_equity else 0.0,
        }

    def get_sharpe(self, account_id: str, days: int = 30,
                   risk_free_rate: float = 0.05) -> float:
        """
        Annualized Sharpe ratio for one student, computed from stored snapshots.

        Args:
            account_id:      Student's Alpaca account ID
            days:            Lookback window in calendar days (default 30)
            risk_free_rate:  Annual risk-free rate as a decimal (default 5%)
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        snaps = (
            self._sb.table("portfolio_snapshots")
            .select("equity, recorded_at")
            .eq("account_id", account_id)
            .gte("recorded_at", cutoff)
            .order("recorded_at")
            .execute()
        )
        if not snaps.data or len(snaps.data) < 3:
            return 0.0
        equity = pd.Series([float(r["equity"]) for r in snaps.data])
        returns = equity.pct_change().dropna()
        return _metrics.get_sharpe(returns, risk_free_rate)

    def get_sortino(self, account_id: str, days: int = 30,
                    risk_free_rate: float = 0.05) -> float:
        """Sortino ratio for one student from stored snapshots."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        snaps = (
            self._sb.table("portfolio_snapshots")
            .select("equity")
            .eq("account_id", account_id)
            .gte("recorded_at", cutoff)
            .order("recorded_at")
            .execute()
        )
        if not snaps.data or len(snaps.data) < 3:
            return 0.0
        equity = pd.Series([float(r["equity"]) for r in snaps.data])
        returns = equity.pct_change().dropna()
        return _metrics.get_sortino(returns, risk_free_rate)

    def get_max_drawdown(self, account_id: str, days: int = 30) -> float:
        """Max drawdown for one student from stored snapshots."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        snaps = (
            self._sb.table("portfolio_snapshots")
            .select("equity")
            .eq("account_id", account_id)
            .gte("recorded_at", cutoff)
            .order("recorded_at")
            .execute()
        )
        if not snaps.data or len(snaps.data) < 3:
            return 0.0
        equity = pd.Series([float(r["equity"]) for r in snaps.data])
        returns = equity.pct_change().dropna()
        return _metrics.get_max_drawdown(returns)

    def get_equity_curve(self, account_id: str) -> pd.DataFrame:
        """Full equity curve for one student as a time-indexed DataFrame."""
        snaps = (
            self._sb.table("portfolio_snapshots")
            .select("equity, cash, recorded_at")
            .eq("account_id", account_id)
            .order("recorded_at")
            .execute()
        )
        if not snaps.data:
            return pd.DataFrame()
        df = pd.DataFrame(snaps.data)
        df["recorded_at"] = pd.to_datetime(df["recorded_at"])
        return df.set_index("recorded_at")

    def get_win_rate(self, account_id: str) -> dict:
        """Win rate for one student computed from their trade history in Supabase."""
        trades = (
            self._sb.table("trades")
            .select("side, filled_avg_price, qty, symbol")
            .eq("account_id", account_id)
            .execute()
        )
        return self._win_rate_from_trades(trades.data or [])

    # -------------------------------------------------------------------------
    # Cross-student views
    # -------------------------------------------------------------------------

    def get_student_summary(self) -> pd.DataFrame:
        """
        One row per student: trade count, win rate, and join date.
        For PnL and Sharpe per student, use get_leaderboard().
        """
        accounts = (
            self._sb.table("accounts")
            .select("id, display_name, created_at")
            .execute()
        )
        if not accounts.data:
            print("No accounts found.")
            return pd.DataFrame()

        rows = []
        for acct in accounts.data:
            aid = acct["id"]
            trades_res = (
                self._sb.table("trades")
                .select("side, filled_avg_price, qty, symbol, order_type")
                .eq("account_id", aid)
                .execute()
            )
            trades = trades_res.data or []
            win_data = self._win_rate_from_trades(trades)
            rows.append({
                "account_id":   aid,
                "display_name": acct.get("display_name") or "",
                "joined":       (acct.get("created_at") or "")[:10],
                "trade_count":  len(trades),
                "win_rate":     win_data["win_rate"],
                "wins":         win_data["wins"],
                "losses":       win_data["losses"],
            })

        return (
            pd.DataFrame(rows)
            .sort_values("trade_count", ascending=False)
            .reset_index(drop=True)
        )

    def get_leaderboard(self, days: int = 30) -> pd.DataFrame:
        """
        All students ranked by total PnL.
        Includes total return %, Sharpe ratio, and win rate.

        Args:
            days: Lookback window for Sharpe calculation (default 30)
        """
        accounts = self._sb.table("accounts").select("id, display_name").execute()
        if not accounts.data:
            return pd.DataFrame()

        rows = []
        for acct in accounts.data:
            aid = acct["id"]
            pnl_data = self.get_pnl(aid)
            sharpe = self.get_sharpe(aid, days=days)
            trades_res = (
                self._sb.table("trades")
                .select("side, filled_avg_price, qty, symbol")
                .eq("account_id", aid)
                .execute()
            )
            win_data = self._win_rate_from_trades(trades_res.data or [])
            rows.append({
                "account_id":       aid,
                "name":             acct.get("display_name") or aid[:14],
                "total_pnl":        pnl_data.get("total_pnl", 0),
                "total_return_pct": pnl_data.get("total_return_pct", 0),
                "latest_equity":    pnl_data.get("latest_equity", 0),
                "sharpe":           sharpe,
                "win_rate":         win_data["win_rate"],
                "trade_count":      win_data["wins"] + win_data["losses"],
            })

        return (
            pd.DataFrame(rows)
            .sort_values("total_pnl", ascending=False)
            .reset_index(drop=True)
        )

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _win_rate_from_trades(self, trades: list) -> dict:
        by_symbol: dict = {}
        for t in trades:
            sym = t.get("symbol", "")
            if sym not in by_symbol:
                by_symbol[sym] = {"buys": deque(), "sells": deque()}
            price = t.get("filled_avg_price")
            if price is None:
                continue
            if t.get("side") == "buy":
                by_symbol[sym]["buys"].append(float(price))
            else:
                by_symbol[sym]["sells"].append(float(price))
        wins, losses = 0, 0
        for s in by_symbol.values():
            buys, sells = s["buys"], s["sells"]
            while buys and sells:
                if sells.popleft() > buys.popleft():
                    wins += 1
                else:
                    losses += 1
        total = wins + losses
        return {
            "wins":     wins,
            "losses":   losses,
            "win_rate": round(wins / total * 100, 2) if total > 0 else 0.0,
        }
