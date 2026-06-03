"""Admin operations — manage pods, traders, capital. Admins only.

All calls hit the backend's /admin endpoints, which re-check is_admin server-side.
"""
from ._session import Session


class Admin:
    def __init__(self, session: Session):
        self._s = session
        me = self._s.get("/me")
        if not me.get("is_admin"):
            raise PermissionError("This account does not have admin access.")

    # ── Pods ─────────────────────────────────────────────────────────────────

    def create_pod(self, name, asset_class, *, benchmark_symbol="SPY", description=None,
                   capital=0, alpaca_api_key=None, alpaca_api_secret=None,
                   alpaca_account_id=None) -> dict:
        """Create a pod, optionally attaching its Alpaca paper-account keys."""
        return self._s.post("/admin/pods", {
            "name": name,
            "asset_class": asset_class,
            "benchmark_symbol": benchmark_symbol,
            "description": description,
            "allocated_capital": capital,
            "alpaca_api_key": alpaca_api_key,
            "alpaca_api_secret": alpaca_api_secret,
            "alpaca_account_id": alpaca_account_id,
        })

    def set_alpaca(self, pod_id, *, api_key=None, api_secret=None, account_id=None) -> dict:
        """Attach or update a pod's Alpaca credentials."""
        return self._s.post(f"/admin/pods/{pod_id}/alpaca", {
            "alpaca_api_key": api_key,
            "alpaca_api_secret": api_secret,
            "alpaca_account_id": account_id,
        })

    def allocate_capital(self, pod_id, amount, note=None) -> dict:
        """Set a pod's allocated capital (logged to the audit trail)."""
        return self._s.post(f"/admin/pods/{pod_id}/capital", {"amount": amount, "note": note})

    # ── Memberships ──────────────────────────────────────────────────────────

    def list_traders(self) -> list:
        """All registered traders (id, display_name, is_admin)."""
        return self._s.get("/admin/traders")

    def add_trader(self, pod_id, trader_id, role="trader") -> dict:
        """Assign a trader to a pod. role: 'trader' or 'pm'."""
        return self._s.post("/admin/memberships",
                            {"pod_id": pod_id, "trader_id": trader_id, "role": role})

    def remove_trader(self, pod_id, trader_id) -> dict:
        """Remove a trader from a pod."""
        return self._s.delete("/admin/memberships",
                             {"pod_id": pod_id, "trader_id": trader_id, "role": "trader"})
