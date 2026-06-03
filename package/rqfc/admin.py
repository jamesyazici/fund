import os
import re
from collections import deque
from datetime import datetime, timedelta, timezone

import pandas as pd

from . import metrics as _metrics

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


class Admin:
    """
    Admin interface — register pods/students, read everyone's trades and
    analytics, and roll per-student data up into the pod-level NAV history
    and metrics the Fund dashboard reads.

    Requires the service role key (bypasses RLS) rather than the anon key.

    Usage:
        import rqfc
        admin = rqfc.Admin()   # reads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from env

        pod = admin.create_pod("Alpha Equities", "equities", starting_capital=100000)
        admin.add_member(pod, "Alice", alpaca_account_id="PKXXXX", role="pm")
        ...
        admin.rebuild()        # refresh dashboard NAV + metrics
        admin.get_leaderboard()
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
    # Registration (pods & members)
    # -------------------------------------------------------------------------

    def create_pod(self, name: str, asset_class: str, *,
                   benchmark_symbol: str = "SPY", description: str = None,
                   starting_capital: float = 0, inception_date: str = None) -> str:
        """Create a pod (strategy team) and return its id."""
        payload = {
            "name": name,
            "asset_class": asset_class,
            "benchmark_symbol": benchmark_symbol,
            "description": description,
            "starting_capital": starting_capital,
        }
        if inception_date:
            payload["inception_date"] = inception_date
        res = self._sb.table("pods").insert(payload).execute()
        return res.data[0]["id"]

    def add_member(self, pod_id: str, name: str, alpaca_account_id: str, *,
                   role: str = "trader", starting_capital: float = 0) -> str:
        """
        Register a student in a pod and link their Alpaca account.

        alpaca_account_id is the id shown by Account.account_id (and printed
        on rqfc.init). Once linked, that student's trades and snapshots flow
        to the dashboard automatically. Idempotent on alpaca_account_id.
        """
        payload = {
            "pod_id": pod_id,
            "name": name,
            "role": role,
            "alpaca_account_id": alpaca_account_id,
            "starting_capital": starting_capital,
        }
        res = self._sb.table("members").upsert(
            payload, on_conflict="alpaca_account_id"
        ).execute()
        return res.data[0]["id"]

    def list_pods(self) -> pd.DataFrame:
        res = self._sb.table("pods").select("*").order("created_at").execute()
        return pd.DataFrame(res.data or [])

    def list_members(self, pod_id: str = None) -> pd.DataFrame:
        q = self._sb.table("members").select("id, pod_id, name, role, alpaca_account_id")
        if pod_id:
            q = q.eq("pod_id", pod_id)
        res = q.execute()
        return pd.DataFrame(res.data or [])

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _member_id(self, ident: str) -> str:
        """Accept a member uuid or an alpaca_account_id and return the member uuid."""
        if ident and _UUID_RE.match(ident):
            return ident
        res = (
            self._sb.table("members")
            .select("id")
            .eq("alpaca_account_id", ident)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise ValueError(f"No member found for '{ident}'. Register them with add_member().")
        return res.data[0]["id"]

    def _equity_series(self, member_id: str, days: int = None) -> pd.Series:
        q = (
            self._sb.table("member_snapshots")
            .select("equity, recorded_at")
            .eq("member_id", member_id)
            .order("recorded_at")
        )
        if days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            q = q.gte("recorded_at", cutoff)
        snaps = q.execute().data or []
        if not snaps:
            return pd.Series(dtype=float)
        s = pd.Series(
            [float(r["equity"]) for r in snaps],
            index=pd.to_datetime([r["recorded_at"] for r in snaps]),
        )
        return s

    # -------------------------------------------------------------------------
    # Trades
    # -------------------------------------------------------------------------

    def get_all_trades(self, member: str = None, symbol: str = None,
                       pod_id: str = None, limit: int = 500) -> pd.DataFrame:
        """
        All trades across all students, newest first.

        Args:
            member:  Filter to one student (member uuid or alpaca_account_id)
            symbol:  Filter to one ticker, e.g. "AAPL"
            pod_id:  Filter to one pod
            limit:   Max rows (default 500)
        """
        query = (
            self._sb.table("trades")
            .select("*, members(name)")
            .order("executed_at", desc=True)
        )
        if member:
            query = query.eq("member_id", self._member_id(member))
        if pod_id:
            query = query.eq("pod_id", pod_id)
        if symbol:
            query = query.eq("symbol", symbol.upper())
        result = query.limit(limit).execute()
        if not result.data:
            return pd.DataFrame()
        df = pd.json_normalize(result.data)
        if "members.name" in df.columns:
            df = df.rename(columns={"members.name": "trader"})
        return df

    # -------------------------------------------------------------------------
    # Per-student analytics (from member_snapshots)
    # -------------------------------------------------------------------------

    def get_pnl(self, member: str) -> dict:
        """Starting equity, latest equity, and total return % for one student."""
        mid = self._member_id(member)
        eq = self._equity_series(mid)
        if len(eq) < 2:
            return {"error": "Not enough snapshot data. Student needs to call account.sync() more."}
        start, latest = float(eq.iloc[0]), float(eq.iloc[-1])
        pnl = latest - start
        return {
            "member_id":        mid,
            "start_equity":     round(start, 2),
            "latest_equity":    round(latest, 2),
            "total_pnl":        round(pnl, 2),
            "total_return_pct": round(pnl / start * 100, 2) if start else 0.0,
        }

    def get_sharpe(self, member: str, days: int = 30, risk_free_rate: float = 0.05) -> float:
        eq = self._equity_series(self._member_id(member), days=days)
        if len(eq) < 3:
            return 0.0
        return _metrics.get_sharpe(eq.pct_change().dropna(), risk_free_rate)

    def get_sortino(self, member: str, days: int = 30, risk_free_rate: float = 0.05) -> float:
        eq = self._equity_series(self._member_id(member), days=days)
        if len(eq) < 3:
            return 0.0
        return _metrics.get_sortino(eq.pct_change().dropna(), risk_free_rate)

    def get_max_drawdown(self, member: str, days: int = 30) -> float:
        eq = self._equity_series(self._member_id(member), days=days)
        if len(eq) < 3:
            return 0.0
        return _metrics.get_max_drawdown(eq.pct_change().dropna())

    def get_equity_curve(self, member: str) -> pd.DataFrame:
        """Full equity/cash curve for one student as a time-indexed DataFrame."""
        mid = self._member_id(member)
        snaps = (
            self._sb.table("member_snapshots")
            .select("equity, cash, recorded_at")
            .eq("member_id", mid)
            .order("recorded_at")
            .execute()
        )
        if not snaps.data:
            return pd.DataFrame()
        df = pd.DataFrame(snaps.data)
        df["recorded_at"] = pd.to_datetime(df["recorded_at"])
        return df.set_index("recorded_at")

    def get_win_rate(self, member: str) -> dict:
        """Win rate for one student computed from their trade history."""
        mid = self._member_id(member)
        trades = (
            self._sb.table("trades")
            .select("side, price, quantity, symbol")
            .eq("member_id", mid)
            .execute()
        )
        return self._win_rate_from_trades(trades.data or [])

    # -------------------------------------------------------------------------
    # Pod-level rollup → dashboard (nav_history + metrics)
    # -------------------------------------------------------------------------

    def rebuild(self, pod_id: str = None, risk_free_rate: float = 0.05) -> None:
        """
        Roll per-student snapshots up into pod NAV history and metrics.

        Aggregates each pod's members' equity into a daily pod NAV, then
        computes the risk/return metrics the dashboard displays. Run this
        periodically (e.g. nightly or after a session). Pass pod_id to rebuild
        a single pod, or omit to rebuild all.
        """
        pods = self._sb.table("pods").select("id").execute().data or []
        if pod_id:
            pods = [p for p in pods if p["id"] == pod_id]
        for pod in pods:
            self._rebuild_pod(pod["id"], risk_free_rate)
        print(f"[rqfc] Rebuilt {len(pods)} pod(s).")

    def _rebuild_pod(self, pid: str, risk_free_rate: float) -> None:
        snaps = (
            self._sb.table("member_snapshots")
            .select("member_id, equity, cash, recorded_at")
            .eq("pod_id", pid)
            .order("recorded_at")
            .execute()
        ).data or []
        if not snaps:
            return

        df = pd.DataFrame(snaps)
        df["recorded_at"] = pd.to_datetime(df["recorded_at"])
        df["date"] = df["recorded_at"].dt.date
        df["equity"] = df["equity"].astype(float)
        df["cash"] = df["cash"].astype(float)

        # Last snapshot per member per day, then carry each member forward so
        # the pod NAV doesn't dip just because someone didn't sync that day.
        daily = df.sort_values("recorded_at").groupby(["member_id", "date"]).last().reset_index()
        eq = daily.pivot(index="date", columns="member_id", values="equity").sort_index().ffill()
        cash = daily.pivot(index="date", columns="member_id", values="cash").sort_index().ffill()

        pod_nav = eq.sum(axis=1)
        pod_cash = cash.sum(axis=1)
        returns = pod_nav.pct_change()

        nav_rows = []
        for d in pod_nav.index:
            dr = returns.loc[d]
            nav_rows.append({
                "pod_id":       pid,
                "date":         str(d),
                "nav":          round(float(pod_nav.loc[d]), 2),
                "cash":         round(float(pod_cash.loc[d]), 2),
                "daily_return": None if pd.isna(dr) else round(float(dr), 6),
            })
        self._sb.table("nav_history").upsert(nav_rows, on_conflict="pod_id,date").execute()

        metrics_row = self._compute_metrics(pid, pod_nav, returns.dropna(), risk_free_rate)
        self._sb.table("metrics").upsert(metrics_row, on_conflict="pod_id,as_of_date").execute()

    def _compute_metrics(self, pid: str, nav: pd.Series, ret: pd.Series,
                         risk_free_rate: float) -> dict:
        start, end = float(nav.iloc[0]), float(nav.iloc[-1])
        cum_return = (end / start - 1) if start else 0.0
        n = len(ret)
        ann_return = ((1 + cum_return) ** (252.0 / n) - 1) if n else 0.0
        max_dd = _metrics.get_max_drawdown(ret) if n else 0.0
        sortino = _metrics.get_sortino(ret, risk_free_rate) if n else 0.0
        calmar = (ann_return / abs(max_dd)) if max_dd else None
        var_95 = float(ret.quantile(0.05)) if n else None
        win_rate = float((ret > 0).mean()) if n else None

        trade_count = (
            self._sb.table("trades").select("id", count="exact")
            .eq("pod_id", pid).execute().count or 0
        )

        return {
            "pod_id":            pid,
            "as_of_date":        str(nav.index[-1]),
            "cumulative_return": round(cum_return, 6),
            "annualized_return": round(ann_return, 6),
            "volatility":        _metrics.get_volatility(ret) if n else 0.0,
            "sharpe":            _metrics.get_sharpe(ret, risk_free_rate) if n else 0.0,
            # inf (no downside days) isn't valid JSON/numeric — store null.
            "sortino":           None if sortino in (float("inf"), float("-inf")) else sortino,
            "beta":              None,   # needs benchmark_prices; left null for now
            "alpha":             None,
            "max_drawdown":      max_dd,
            "calmar":            round(calmar, 4) if calmar is not None else None,
            "var_95":            round(var_95, 6) if var_95 is not None else None,
            "win_rate":          round(win_rate, 4) if win_rate is not None else None,
            "trade_count":       int(trade_count),
        }

    # -------------------------------------------------------------------------
    # Cross-student / cross-pod views
    # -------------------------------------------------------------------------

    def get_student_summary(self) -> pd.DataFrame:
        """One row per student: pod, trade count, and win rate."""
        members = (
            self._sb.table("members")
            .select("id, name, pod_id, alpaca_account_id, joined_at")
            .execute()
        ).data or []
        if not members:
            print("No members found. Register students with add_member().")
            return pd.DataFrame()

        rows = []
        for m in members:
            trades = (
                self._sb.table("trades")
                .select("side, price, quantity, symbol")
                .eq("member_id", m["id"])
                .execute()
            ).data or []
            win = self._win_rate_from_trades(trades)
            rows.append({
                "member_id":   m["id"],
                "name":        m.get("name") or "",
                "pod_id":      m.get("pod_id"),
                "joined":      (m.get("joined_at") or "")[:10],
                "trade_count": len(trades),
                "win_rate":    win["win_rate"],
                "wins":        win["wins"],
                "losses":      win["losses"],
            })
        return pd.DataFrame(rows).sort_values("trade_count", ascending=False).reset_index(drop=True)

    def get_leaderboard(self, days: int = 30) -> pd.DataFrame:
        """
        Pods ranked by total PnL (aggregated from their members' equity).

        Uses the most recent member snapshots; run rebuild() first if you want
        these numbers to match the dashboard exactly.
        """
        pods = self._sb.table("pods").select("id, name, starting_capital").execute().data or []
        if not pods:
            return pd.DataFrame()

        rows = []
        for pod in pods:
            pid = pod["id"]
            snaps = (
                self._sb.table("member_snapshots")
                .select("member_id, equity, recorded_at")
                .eq("pod_id", pid)
                .order("recorded_at")
                .execute()
            ).data or []

            start_nav = latest_nav = 0.0
            if snaps:
                sdf = pd.DataFrame(snaps)
                sdf["recorded_at"] = pd.to_datetime(sdf["recorded_at"])
                sdf["equity"] = sdf["equity"].astype(float)
                sdf["date"] = sdf["recorded_at"].dt.date
                daily = sdf.sort_values("recorded_at").groupby(["member_id", "date"]).last().reset_index()
                eq = daily.pivot(index="date", columns="member_id", values="equity").sort_index().ffill()
                pod_nav = eq.sum(axis=1)
                start_nav = float(pod_nav.iloc[0])
                latest_nav = float(pod_nav.iloc[-1])

            pnl = latest_nav - start_nav
            trade_count = (
                self._sb.table("trades").select("id", count="exact")
                .eq("pod_id", pid).execute().count or 0
            )
            rows.append({
                "pod_id":           pid,
                "name":             pod.get("name") or pid[:8],
                "nav":              round(latest_nav, 2),
                "total_pnl":        round(pnl, 2),
                "total_return_pct": round(pnl / start_nav * 100, 2) if start_nav else 0.0,
                "trade_count":      int(trade_count),
            })
        return pd.DataFrame(rows).sort_values("total_pnl", ascending=False).reset_index(drop=True)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _win_rate_from_trades(self, trades: list) -> dict:
        by_symbol: dict = {}
        for t in trades:
            sym = t.get("symbol", "")
            if sym not in by_symbol:
                by_symbol[sym] = {"buys": deque(), "sells": deque()}
            price = t.get("price")
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
