"""Trader identity from backend sessions, rqfc API keys, or Supabase JWTs.

The preferred flow is backend-owned auth: the client logs in against this API,
receives a backend-issued trader session token, and sends it as
`Authorization: Bearer <token>`. For automation, traders can send an rqfc API
key in the same bearer slot. Supabase JWTs remain accepted for compatibility.
"""
import hashlib
import hmac
import time
import urllib.error
import urllib.request
import json

import jwt
from fastapi import Header, HTTPException

from .config import get_settings
from . import db

_ALG = "HS256"
_SESSION_TTL_SECONDS = 60 * 60 * 12
_API_KEY_PREFIX = "rqfc_"


def _bearer(authorization: str) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


def _profile(trader: dict) -> dict:
    return {
        "trader_id": trader["id"],
        "display_name": trader["display_name"],
        "is_admin": trader["is_admin"],
        "pods": db.list_trader_pods(trader["id"]),
    }


def issue_trader_session(trader_id: str) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "typ": "trader_session",
        "sub": trader_id,
        "iat": now,
        "exp": now + _SESSION_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.admin_portal_secret, algorithm=_ALG)


def _trader_from_session_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, get_settings().admin_portal_secret, algorithms=[_ALG])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")

    if payload.get("typ") != "trader_session":
        raise HTTPException(status_code=401, detail="Not a trader session token")

    trader_id = payload.get("sub")
    if not trader_id:
        raise HTTPException(status_code=401, detail="Session token missing subject")

    trader = db.get_trader_by_id(trader_id)
    if not trader:
        raise HTTPException(status_code=403, detail="Trader profile no longer exists.")
    return trader


def _trader_from_supabase_jwt(token: str) -> dict:
    """Verify a Supabase JWT and return the linked trader row."""
    try:
        payload = jwt.decode(
            token,
            get_settings().supabase_jwt_secret,
            algorithms=[_ALG],
            audience="authenticated",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    auth_user_id = payload.get("sub")
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    trader = db.get_trader_by_auth_id(auth_user_id)
    if not trader:
        raise HTTPException(
            status_code=403,
            detail="No trader profile is linked to this login. Ask an admin to register you.",
        )
    return trader


def _api_key_hash(api_key: str) -> str:
    secret = get_settings().admin_portal_secret
    return hmac.new(secret.encode("utf-8"), api_key.encode("utf-8"), hashlib.sha256).hexdigest()


def api_key_prefix(api_key: str) -> str:
    return api_key[:18]


def hash_api_key(api_key: str) -> str:
    return _api_key_hash(api_key)


def trader_from_api_key(api_key: str) -> dict:
    row = db.get_active_api_key_by_hash(_api_key_hash(api_key))
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    trader = row.get("traders") or db.get_trader_by_id(row["trader_id"])
    if not trader:
        raise HTTPException(status_code=403, detail="Trader profile no longer exists.")
    db.mark_api_key_used(row["id"])
    return trader


def trader_from_token(token: str) -> dict:
    """Resolve any supported bearer token to a trader row."""
    if token.startswith(_API_KEY_PREFIX):
        return trader_from_api_key(token)

    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    if unverified.get("typ") == "trader_session":
        return _trader_from_session_token(token)
    return _trader_from_supabase_jwt(token)


def get_current_trader(authorization: str = Header(default=None)) -> dict:
    return trader_from_token(_bearer(authorization))


def require_admin(trader: dict) -> None:
    if not trader.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")


def authenticate_with_supabase(email: str, password: str) -> dict:
    """Authenticate with Supabase Auth using the backend-held anon key."""
    settings = get_settings()
    if not settings.supabase_anon_key:
        raise HTTPException(status_code=500, detail="SUPABASE_ANON_KEY is required for /auth/login.")

    url = settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password"
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {settings.supabase_anon_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8") or "Invalid login credentials."
        raise HTTPException(status_code=401, detail=detail)
    except urllib.error.URLError as e:
        raise HTTPException(status_code=502, detail=f"Supabase Auth unavailable: {e}")

    auth_user_id = (data.get("user") or {}).get("id")
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Supabase Auth did not return a user.")

    trader = db.get_trader_by_auth_id(auth_user_id)
    if not trader:
        raise HTTPException(
            status_code=403,
            detail="No trader profile is linked to this login. Ask an admin to register you.",
        )

    return {
        "token": issue_trader_session(trader["id"]),
        "token_type": "bearer",
        "expires_in": _SESSION_TTL_SECONDS,
        "profile": _profile(trader),
    }
