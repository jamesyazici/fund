"""The trader-facing Account object.

Every method is an authenticated call to the backend, which holds the pod's
Alpaca keys and submits on your behalf. You can only act on pods you're assigned
to (admins can act on any pod).
"""
from datetime import datetime, timezone

from ._session import Session, looks_like_uuid


def _fmt_ts(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%b %d, %Y  %H:%M:%S UTC")
    except Exception:
        return iso


_STATUS_LABELS = {
    "filled": "Order filled",
    "partially_filled": "Order partially filled",
    "accepted": "Order accepted (pending fill)",
    "pending_new": "Order accepted (pending fill)",
    "new": "Order accepted (pending fill)",
    "canceled": "Order canceled",
    "rejected": "Order rejected",
    "expired": "Order expired",
}


_PENDING_STATUSES = {"new", "accepted", "pending_new"}


class OrderResult(dict):
    """Order response dict that prints as a readable confirmation."""

    def __repr__(self) -> str:
        status = self.get("status", "unknown")
        trade = self.get("trade") or {}
        symbol = trade.get("symbol", "?")
        side = (trade.get("side") or "").upper()
        qty = trade.get("quantity") or trade.get("filled_qty")
        price = trade.get("price")
        filled_qty = trade.get("filled_qty") or 0
        notional = trade.get("notional")
        order_type = (trade.get("order_type") or "MARKET").upper()
        order_id = self.get("order_id") or trade.get("alpaca_order_id", "—")
        filled_at = _fmt_ts(trade.get("filled_at"))
        label = _STATUS_LABELS.get(status, f"Order {status}")

        # Why isn't it filled yet?
        if status in _PENDING_STATUSES and filled_qty == 0:
            if order_type == "LIMIT":
                pending_note = " (waiting for limit price)"
            else:
                pending_note = " (market is closed — will fill at open)"
        elif status == "partially_filled":
            pending_note = " (partial — remainder working)"
        else:
            pending_note = ""

        # headline
        price_str = f" @ ${price:,.4f}" if price is not None else ""
        notional_str = f"  (${notional:,.2f} notional)" if notional is not None else ""
        qty_str = f"{qty:g}" if qty is not None else "?"
        headline = f"  {label} — {side} {qty_str}x {symbol}{price_str}{notional_str}"

        rows = [
            "",
            headline,
            "  " + "-" * max(len(headline) - 2, 48),
            f"  {'Order ID':<14} {order_id}",
            f"  {'Type':<14} {order_type}",
        ]
        if qty is not None:
            filled_line = f"  {'Filled':<14} {filled_qty:g} / {qty:g} shares"
            if pending_note:
                filled_line += pending_note
            rows.append(filled_line)
        if trade.get("filled_at"):
            rows.append(f"  {'Filled at':<14} {filled_at}")
        elif trade.get("executed_at"):
            rows.append(f"  {'Submitted':<14} {_fmt_ts(trade.get('executed_at'))}")
        rows.append("")
        return "\n".join(rows)


class PositionList(list):
    """List of positions that prints as a clean table."""

    def __repr__(self) -> str:
        if not self:
            return "\n  (no open positions)\n"
        col = "  {:<8}  {:>10}  {:>11}  {:>11}  {:>13}  {:>13}"
        rows = [
            "",
            col.format("SYMBOL", "QTY", "ENTRY", "MARK", "MKT VALUE", "UNREAL P&L"),
            "  " + "-" * 74,
        ]
        for p in self:
            pnl = p.get("unrealized_pnl") or 0
            sign = "+" if pnl >= 0 else ""
            rows.append(col.format(
                p.get("symbol", "?"),
                f"{p.get('quantity', 0):.4f}",
                f"${p.get('avg_entry_price', 0):.4f}",
                f"${p.get('current_price') or 0:.4f}",
                f"${abs(p.get('market_value') or 0):,.2f}",
                f"{sign}${abs(pnl):,.2f}",
            ))
        rows.append("")
        return "\n".join(rows)


class AccountSummary(dict):
    """Account dict that prints as a clean summary."""

    def __repr__(self) -> str:
        pv  = self.get("portfolio_value", 0)
        cash = self.get("cash", 0)
        bp  = self.get("buying_power", 0)
        sr  = self.get("session_return")
        r5d = self.get("return_5d")
        sharpe = self.get("sharpe_30d")

        def pct(v): return f"{'+' if v >= 0 else ''}{v*100:.2f}%"

        rows = [
            "",
            f"  {'Portfolio Value':.<24} ${pv:>12,.2f}",
            f"  {'Cash':.<24} ${cash:>12,.2f}",
            f"  {'Buying Power':.<24} ${bp:>12,.2f}",
        ]
        if sr is not None:
            rows.append(f"  {'Day Return':.<24} {pct(sr):>13}")
        if r5d is not None:
            rows.append(f"  {'5-Day Return':.<24} {pct(r5d):>13}")
        if sharpe is not None:
            rows.append(f"  {'Sharpe (30d)':.<24} {sharpe:>13.4f}")

        recent = self.get("recent_days") or []
        if recent:
            rows.append("  " + "-" * 38)
            rows.append(f"  {'DATE':<14}  {'NAV':>12}  {'DAY RTN':>8}")
            for d in recent:
                dr = d.get("daily_return")
                dr_str = pct(dr) if dr is not None else "   —"
                rows.append(f"  {d['date']:<14}  ${d['nav']:>11,.2f}  {dr_str:>8}")

        rows.append("")
        return "\n".join(rows)


class OrderList(list):
    """List of orders that prints as a clean table."""

    def __repr__(self) -> str:
        if not self:
            return "\n  (no orders)\n"
        col = "  {:<8}  {:<6}  {:<8}  {:>8}  {:>8}  {:>10}  {:<12}  {}"
        rows = [
            "",
            col.format("SYMBOL", "SIDE", "TYPE", "QTY", "FILLED", "PRICE", "STATUS", "SUBMITTED"),
            "  " + "-" * 84,
        ]
        for o in self:
            qty = o.get("qty") or 0
            filled = o.get("filled_qty") or 0
            price = o.get("filled_price") or o.get("limit_price")
            submitted = o.get("submitted_at", "")[:16].replace("T", " ") if o.get("submitted_at") else "—"
            rows.append(col.format(
                o.get("symbol", "?"),
                (o.get("side") or "").upper(),
                (o.get("order_type") or "MKT").upper()[:8],
                f"{qty:g}",
                f"{filled:g}",
                f"${price:,.2f}" if price else "—",
                (o.get("status") or "").upper()[:12],
                submitted,
            ))
        rows.append("")
        return "\n".join(rows)


class TradeHistory(list):
    """List of historical trades that prints as a clean table."""

    def __repr__(self) -> str:
        if not self:
            return "\n  (no trade history)\n"
        col = "  {:<8}  {:<5}  {:>8}  {:>10}  {:>12}  {:<10}  {}"
        rows = [
            "",
            col.format("SYMBOL", "SIDE", "QTY", "PRICE", "REALIZED", "STATUS", "EXECUTED"),
            "  " + "-" * 74,
        ]
        for t in self:
            qty = t.get("filled_qty") or t.get("quantity") or 0
            price = t.get("price")
            realized = t.get("realized_pnl")
            executed = (t.get("executed_at") or "")[:16].replace("T", " ")
            sign = "+" if (realized or 0) >= 0 else ""
            rows.append(col.format(
                t.get("symbol", "?"),
                (t.get("side") or "").upper()[:5],
                f"{float(qty):g}" if qty else "—",
                f"${float(price):,.4f}" if price else "—",
                f"{sign}${abs(float(realized)):,.2f}" if realized is not None else "—",
                (t.get("status") or "filled").upper()[:10],
                executed or "—",
            ))
        rows.append(f"\n  {len(self)} trade(s) shown.\n")
        return "\n".join(rows)


class SyncResult(dict):
    """Sync response that prints as a short summary."""

    def __repr__(self) -> str:
        metrics = "updated" if self.get("metrics") else "insufficient history"
        return (
            f"\n  Synced: {self.get('positions', 0)} position(s), "
            f"{self.get('nav_days', 0)} NAV day(s), metrics {metrics}.\n"
        )


# Map common Alpaca rejection phrases to plain-language messages.
_ORDER_ERRORS = [
    (["insufficient", "buying power", "funds", "exceed"], "Insufficient funds."),
    (["not found", "no asset", "unknown symbol"], "Symbol not found or not tradeable."),
    (["market is closed", "outside", "not tradable"], "Market is closed or outside trading hours."),
    (["already exists", "duplicate"], "Duplicate order — this order was already placed."),
    (["qty", "quantity", "minimum"], "Invalid quantity (too small or fractional not supported)."),
]


class Account:
    """A pod you can trade. Obtain one via rqfc.pod(name_or_id)."""

    def __init__(self, session: Session, pod_ref: str):
        self._s = session
        self.pod_id = self._resolve_pod(pod_ref)

    def _resolve_pod(self, ref: str) -> str:
        if looks_like_uuid(ref):
            return ref
        for p in self._s.get("/pods"):
            if p["name"].lower() == str(ref).lower():
                return p["id"]
        raise ValueError(f"No pod named '{ref}'. Run rqfc.whoami() to see your pods.")

    # ── Orders ───────────────────────────────────────────────────────────────

    def _order(self, **kw):
        try:
            return OrderResult(self._s.post("/orders", {"pod_id": self.pod_id, **kw}))
        except RuntimeError as exc:
            raw = str(exc).lower()
            label = kw.get("symbol", "?").upper()
            for keywords, friendly in _ORDER_ERRORS:
                if any(k in raw for k in keywords):
                    print(f"  Order rejected ({label}): {friendly}")
                    return None
            # Unknown rejection — show the Alpaca detail but don't crash.
            print(f"  Order rejected ({label}): {exc}")
            return None

    def buy(self, symbol, qty, order_type="market", limit_price=None,
            time_in_force="day", override_risk=False):
        """Buy shares. order_type: 'market' (default) or 'limit'.
        Pass override_risk=True to bypass the pod's max-position-size limit."""
        return self._order(symbol=symbol, side="buy", qty=qty, order_type=order_type,
                           order_label=order_type, limit_price=limit_price,
                           time_in_force=time_in_force, override_risk=override_risk)

    def sell(self, symbol, qty, order_type="market", limit_price=None,
             time_in_force="day", override_risk=False):
        """Sell shares you hold in the pod."""
        return self._order(symbol=symbol, side="sell", qty=qty, order_type=order_type,
                           order_label=order_type, limit_price=limit_price,
                           time_in_force=time_in_force, override_risk=override_risk)

    def short(self, symbol, qty, time_in_force="day", override_risk=False):
        """Short sell. Close with cover()."""
        return self._order(symbol=symbol, side="sell", qty=qty, order_label="short",
                           time_in_force=time_in_force, override_risk=override_risk)

    def cover(self, symbol, qty, time_in_force="day", override_risk=False):
        """Buy back a short position."""
        return self._order(symbol=symbol, side="buy", qty=qty, order_label="cover",
                           time_in_force=time_in_force, override_risk=override_risk)

    def dollar_buy(self, symbol, amount, time_in_force="day", override_risk=False):
        """Buy by dollar amount, e.g. dollar_buy('AAPL', 5000).
        Pass override_risk=True to bypass the pod's max-position-size limit."""
        return self._order(symbol=symbol, side="buy", notional=amount, order_label="dollar_buy",
                           time_in_force=time_in_force, override_risk=override_risk)

    def dollar_sell(self, symbol, amount, time_in_force="day", override_risk=False):
        """Sell by dollar amount."""
        return self._order(symbol=symbol, side="sell", notional=amount, order_label="dollar_sell",
                           time_in_force=time_in_force, override_risk=override_risk)

    def cancel(self, order_id):
        """Cancel an open order by its Alpaca order id."""
        return self._s.post("/orders/cancel", {"pod_id": self.pod_id, "order_id": order_id})

    # ── Read ─────────────────────────────────────────────────────────────────

    def account(self) -> AccountSummary:
        """Live equity, cash, buying power, 5-day return, and 30-day Sharpe."""
        return AccountSummary(self._s.get(f"/pods/{self.pod_id}/account"))

    def positions(self) -> PositionList:
        """Live open positions. Behaves as a plain list — positions()[0] works fine."""
        return PositionList(self._s.get(f"/pods/{self.pod_id}/positions"))

    def orders(self, status: str = "open") -> OrderList:
        """Orders from Alpaca. status: 'open' (default) | 'closed' | 'all'"""
        return OrderList(self._s.get(f"/pods/{self.pod_id}/orders", {"status": status}))

    def history(self, limit: int = 100, my_trades_only: bool = False) -> TradeHistory:
        """Completed trades for this pod.

        my_trades_only=True filters to only your own orders within the pod.
        """
        return TradeHistory(self._s.get(
            f"/pods/{self.pod_id}/trades",
            {"limit": limit, "trader_only": "true" if my_trades_only else "false"},
        ))

    def price(self, symbol):
        """Latest trade price."""
        return self._s.get("/market/price", {"symbol": symbol, "pod_id": self.pod_id})

    def bars(self, symbol, days=30):
        """Daily OHLCV bars."""
        return self._s.get("/market/bars", {"symbol": symbol, "pod_id": self.pod_id, "days": days})

    def sync(self) -> SyncResult:
        """Pull the pod's positions + NAV from Alpaca into the dashboard."""
        return SyncResult(self._s.post(f"/sync/{self.pod_id}"))

    # ── Display helpers (explicit pretty-print without auto-firing on print) ──

    def show_account(self) -> None:
        """Print a formatted account summary."""
        print(self.account())

    def show_positions(self) -> None:
        """Print a formatted positions table."""
        print(self.positions())

    def show_orders(self, status: str = "open") -> None:
        """Print a formatted orders table."""
        print(self.orders(status))

    def show_history(self, limit: int = 50, my_trades_only: bool = False) -> None:
        """Print a formatted trade history table."""
        print(self.history(limit, my_trades_only))

    def log_run(self, strategy_name: str, orders_placed: int, note: str = "") -> None:
        """Write a strategy-run entry to the admin audit log (visible in portal Logs tab)."""
        try:
            self._s.post(f"/pods/{self.pod_id}/log-run", {
                "strategy": strategy_name,
                "orders_placed": orders_placed,
                "note": note,
            })
        except Exception:
            pass
