# rqfc — RQFC fund trading client
#
# A thin, authenticated client for the RQFC trading backend. Traders log in with
# Supabase credentials (issued by an admin); the backend holds each pod's Alpaca
# keys and submits trades on their behalf. No Alpaca keys ever touch this client.
#
# Setup (once):
#   export RQFC_BACKEND_URL=https://your-backend
#   export RQFC_SUPABASE_URL=https://<project>.supabase.co
#   export RQFC_SUPABASE_ANON_KEY=<anon-key>
#
# Trader usage:
#   import rqfc
#   rqfc.login("alice@rqfc.club", "password")
#   acct = rqfc.pod("Alpha Equities")   # a pod you're assigned to
#   acct.buy("AAPL", 10)
#   acct.positions()
#   acct.sync()                          # refresh the dashboard
#
# Admin usage:
#   rqfc.login("admin@rqfc.club", "password")
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

_session: Session | None = None


def configure(backend_url: str = None, supabase_url: str = None, anon_key: str = None) -> Session:
    """Set connection details. Falls back to RQFC_* environment variables."""
    global _session
    backend_url = backend_url or os.environ.get("RQFC_BACKEND_URL", "http://localhost:8000")
    supabase_url = supabase_url or os.environ.get("RQFC_SUPABASE_URL")
    anon_key = anon_key or os.environ.get("RQFC_SUPABASE_ANON_KEY")
    if not supabase_url or not anon_key:
        raise RuntimeError(
            "Missing Supabase connection. Set RQFC_SUPABASE_URL and "
            "RQFC_SUPABASE_ANON_KEY, or pass them to rqfc.login(...)."
        )
    _session = Session(backend_url, supabase_url, anon_key)
    return _session


def login(email: str, password: str, *, backend_url: str = None,
          supabase_url: str = None, anon_key: str = None) -> dict:
    """Authenticate and start a session. Returns your profile."""
    sess = configure(backend_url, supabase_url, anon_key)
    sess.login(email, password)
    me = sess.get("/me")
    tag = " (admin)" if me.get("is_admin") else ""
    print(f"Logged in as {me['display_name']}{tag}. Pods: {[p['pods']['name'] for p in me['pods']] or 'none assigned'}")
    return me


def _require_session() -> Session:
    if _session is None or not _session.access_token:
        raise RuntimeError("Not logged in. Call rqfc.login(email, password) first.")
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


__all__ = ["configure", "login", "pod", "admin", "whoami", "Account", "Admin"]
