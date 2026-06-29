# rqfc — RQFC fund trading client
#
# A thin, authenticated client for the RQFC trading backend. Traders log in with
# credentials or an API key issued by an admin; the backend holds each pod's
# Alpaca keys and submits trades on their behalf. No Alpaca keys ever touch this
# client.
#
# Trader usage:
#   import rqfc
#   rqfc.login("alice@example.com", "password")
#   # or: rqfc.login(api_key="rqfc_...")
#   acct = rqfc.pod("Alpha Equities")   # a pod you're assigned to
#   acct.buy("AAPL", 10)
#   acct.positions()
#   acct.sync()                          # refresh the dashboard
#
# Admin usage:
#   rqfc.login("admin@example.com", "password")
#   admin = rqfc.admin()
#   pod = admin.create_pod("Vol Arb", "options", capital=100000,
#                          alpaca_api_key="PK...", alpaca_api_secret="...")
#   admin.add_trader(pod["id"], trader_id, role="trader")
#   admin.allocate_capital(pod["id"], 150000)
from __future__ import annotations

import os

from ._session import Session
from .client import Account
from .admin import Admin

__version__ = "1.0.0"
DEFAULT_BACKEND_URL = "https://fund-tkb1.onrender.com"

_session: Session | None = None


def configure(backend_url: str = None) -> Session:
    """Set backend connection details.

    Defaults to RQFC_BACKEND_URL, then the production RQFC API. Local dev can
    pass backend_url="http://localhost:8000".
    """
    global _session
    backend_url = backend_url or os.environ.get("RQFC_BACKEND_URL", DEFAULT_BACKEND_URL)
    _session = Session(backend_url)
    return _session


def _print_login_summary(sess: Session, pods: list) -> None:
    """Print a compact per-pod dashboard after login."""
    if not pods:
        return

    def pct(v):
        if v is None:
            return "    —"
        sign = "+" if v >= 0 else ""
        return f"{sign}{v * 100:.2f}%"

    for membership in pods:
        pod_info = membership.get("pods", {})
        pod_id   = membership.get("pod_id")
        pod_name = pod_info.get("name", "?")
        if not pod_id:
            continue

        try:
            a = sess.get(f"/pods/{pod_id}/account")
            if not a:
                continue

            pv     = a.get("portfolio_value") or 0
            cash   = a.get("cash") or 0
            bp     = a.get("buying_power") or 0
            day_r  = a.get("session_return")
            r5d    = a.get("return_5d")
            sharpe = a.get("sharpe_30d")

            width = max(len(pod_name) + 2, 36)
            bar   = "─" * width

            print(f"\n  {pod_name}")
            print(f"  {bar}")
            print(f"  {'Portfolio Value':<20} ${pv:>12,.2f}")
            print(f"  {'Cash':<20} ${cash:>12,.2f}")
            print(f"  {'Buying Power':<20} ${bp:>12,.2f}")
            print(f"  {'Day Return':<20} {pct(day_r):>13}")
            print(f"  {'5-Day Return':<20} {pct(r5d):>13}")
            if sharpe is not None:
                print(f"  {'Sharpe (30d)':<20} {sharpe:>13.4f}")
        except Exception:
            continue


def login(email: str = None, password: str = None, *, api_key: str = None,
          backend_url: str = None, summary: bool = True) -> dict:
    """Authenticate and start a session. Returns your profile.

    Pass summary=False to skip the post-login dashboard.
    """
    global _session
    if backend_url is not None or _session is None:
        sess = configure(backend_url)
    else:
        sess = _session
    if api_key:
        if email or password:
            raise ValueError("Use either email/password or api_key, not both.")
        sess.use_api_key(api_key)
        me = sess.get("/me")
    else:
        if not email or not password:
            raise ValueError("Call rqfc.login(email, password) or rqfc.login(api_key='rqfc_...').")
        me = sess.login(email, password) or sess.get("/me")

    tag  = " (admin)" if me.get("is_admin") else ""
    pods = me.get("pods", [])
    pod_names = [p["pods"]["name"] for p in pods] or "none assigned"
    print(f"Logged in as {me['display_name']}{tag}.  Pods: {pod_names}")

    if summary and not me.get("is_admin"):
        _print_login_summary(sess, pods)

    return me


def _require_session() -> Session:
    if _session is None or not _session.access_token:
        raise RuntimeError(
            "Not logged in. Call rqfc.login(email, password) or "
            "rqfc.login(api_key='rqfc_...') first."
        )
    return _session


def pod(name_or_id: str) -> Account:
    """Select a pod to trade, by name or id."""
    return Account(_require_session(), name_or_id)


def admin() -> Admin:
    """Get the admin interface (requires an admin account)."""
    return Admin(_require_session())


def whoami() -> dict:
    """Your profile and pod assignments."""
    return _require_session().get("/me")


__all__ = [
    "DEFAULT_BACKEND_URL",
    "configure",
    "login",
    "pod",
    "admin",
    "whoami",
    "Account",
    "Admin",
]
