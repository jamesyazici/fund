"""The trader-facing Account object.

Every method is an authenticated call to the backend, which holds the pod's
Alpaca keys and submits on your behalf. You can only act on pods you're assigned
to (admins can act on any pod).
"""
from ._session import Session, looks_like_uuid


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
        return self._s.post("/orders", {"pod_id": self.pod_id, **kw})

    def buy(self, symbol, qty, order_type="market", limit_price=None, time_in_force="day"):
        """Buy shares. order_type: 'market' (default) or 'limit'."""
        return self._order(symbol=symbol, side="buy", qty=qty, order_type=order_type,
                           order_label=order_type, limit_price=limit_price,
                           time_in_force=time_in_force)

    def sell(self, symbol, qty, order_type="market", limit_price=None, time_in_force="day"):
        """Sell shares you hold in the pod."""
        return self._order(symbol=symbol, side="sell", qty=qty, order_type=order_type,
                           order_label=order_type, limit_price=limit_price,
                           time_in_force=time_in_force)

    def short(self, symbol, qty, time_in_force="day"):
        """Short sell. Close with cover()."""
        return self._order(symbol=symbol, side="sell", qty=qty, order_label="short",
                           time_in_force=time_in_force)

    def cover(self, symbol, qty, time_in_force="day"):
        """Buy back a short position."""
        return self._order(symbol=symbol, side="buy", qty=qty, order_label="cover",
                           time_in_force=time_in_force)

    def dollar_buy(self, symbol, amount, time_in_force="day"):
        """Buy by dollar amount, e.g. dollar_buy('AAPL', 5000)."""
        return self._order(symbol=symbol, side="buy", notional=amount, order_label="dollar_buy",
                           time_in_force=time_in_force)

    def dollar_sell(self, symbol, amount, time_in_force="day"):
        """Sell by dollar amount."""
        return self._order(symbol=symbol, side="sell", notional=amount, order_label="dollar_sell",
                           time_in_force=time_in_force)

    def cancel(self, order_id):
        """Cancel an open order by its Alpaca order id."""
        return self._s.post("/orders/cancel", {"pod_id": self.pod_id, "order_id": order_id})

    # ── Read ─────────────────────────────────────────────────────────────────

    def account(self):
        """Live equity, cash, and buying power for the pod."""
        return self._s.get(f"/pods/{self.pod_id}/account")

    def positions(self):
        """Live open positions for the pod."""
        return self._s.get(f"/pods/{self.pod_id}/positions")

    def price(self, symbol):
        """Latest trade price."""
        return self._s.get("/market/price", {"symbol": symbol, "pod_id": self.pod_id})

    def bars(self, symbol, days=30):
        """Daily OHLCV bars."""
        return self._s.get("/market/bars", {"symbol": symbol, "pod_id": self.pod_id, "days": days})

    def sync(self):
        """Pull the pod's positions + NAV from Alpaca into the dashboard."""
        return self._s.post(f"/sync/{self.pod_id}")
