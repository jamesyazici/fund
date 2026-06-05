"""Admin portal authentication.

The portal signs in with Google Identity Services, sends the Google ID token to
the backend, and receives a short-lived portal token if the verified email is in
the configured admin allowlist. Admin endpoints accept EITHER that portal token
OR any supported trader bearer token whose trader has is_admin = true, so both
the web portal and the Python admin client work.
"""
import time

import jwt
from fastapi import Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .config import get_settings
from .auth import _bearer, trader_from_token

_ALG = "HS256"
_TTL_SECONDS = 60 * 60 * 8  # 8 hours

PORTAL_ACTOR = {"id": None, "display_name": "Admin Portal", "is_admin": True, "portal": True}


def verify_google_admin(credential: str) -> dict:
    """Verify a Google ID token and require an allowlisted admin email."""
    s = get_settings()
    if not s.google_oauth_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_OAUTH_CLIENT_ID is not configured.")
    if not credential:
        raise HTTPException(status_code=400, detail="Missing Google credential.")

    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            s.google_oauth_client_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google credential: {e}")

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email is not verified.")
    if email not in s.admin_google_emails:
        raise HTTPException(status_code=403, detail="This Google account is not an admin.")

    return {
        "email": email,
        "name": info.get("name") or email,
        "picture": info.get("picture"),
    }


def issue_portal_token(email: str = None) -> str:
    s = get_settings()
    payload = {
        "typ": "portal",
        "role": "admin",
        "email": email,
        "exp": int(time.time()) + _TTL_SECONDS,
    }
    return jwt.encode(payload, s.admin_portal_secret, algorithm=_ALG)


def _is_portal_token(token: str) -> bool:
    try:
        payload = jwt.decode(token, get_settings().admin_portal_secret, algorithms=[_ALG])
    except jwt.PyJWTError:
        return False
    return payload.get("typ") == "portal"


def get_admin_actor(authorization: str = Header(default=None)) -> dict:
    """Admin gate: portal token, or a trader bearer whose trader is_admin."""
    token = _bearer(authorization)
    if _is_portal_token(token):
        return dict(PORTAL_ACTOR)
    trader = trader_from_token(token)
    if not trader.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return trader
