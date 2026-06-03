"""Admin portal authentication.

The portal logs in with a single shared username/password (default elbow/grease)
and receives a short-lived portal token. Admin endpoints accept EITHER that
portal token OR a Supabase JWT for a trader with is_admin = true, so both the web
portal and the Python admin client work.
"""
import time

import jwt
from fastapi import Header, HTTPException

from .config import get_settings
from .auth import _bearer, trader_from_token

_ALG = "HS256"
_TTL_SECONDS = 60 * 60 * 8  # 8 hours

PORTAL_ACTOR = {"id": None, "display_name": "Admin Portal", "is_admin": True, "portal": True}


def verify_credentials(username: str, password: str) -> bool:
    s = get_settings()
    return username == s.admin_portal_username and password == s.admin_portal_password


def issue_portal_token() -> str:
    s = get_settings()
    payload = {"typ": "portal", "role": "admin", "exp": int(time.time()) + _TTL_SECONDS}
    return jwt.encode(payload, s.admin_portal_secret, algorithm=_ALG)


def _is_portal_token(token: str) -> bool:
    try:
        payload = jwt.decode(token, get_settings().admin_portal_secret, algorithms=[_ALG])
    except jwt.PyJWTError:
        return False
    return payload.get("typ") == "portal"


def get_admin_actor(authorization: str = Header(default=None)) -> dict:
    """Admin gate: portal token, or a Supabase JWT whose trader is_admin."""
    token = _bearer(authorization)
    if _is_portal_token(token):
        return dict(PORTAL_ACTOR)
    trader = trader_from_token(token)
    if not trader.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return trader
