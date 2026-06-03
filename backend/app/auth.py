"""Trader identity from a Supabase JWT.

The rqfc client logs in against Supabase Auth and receives a JWT. It sends that
JWT as `Authorization: Bearer <token>`. We verify the signature with the project
JWT secret, then map the auth user id to a `traders` row.
"""
import jwt
from fastapi import Header, HTTPException

from .config import get_settings
from . import db


def _bearer(authorization: str) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


def trader_from_token(token: str) -> dict:
    """Verify a Supabase JWT and return the linked trader row."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
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


def get_current_trader(authorization: str = Header(default=None)) -> dict:
    return trader_from_token(_bearer(authorization))


def require_admin(trader: dict) -> None:
    if not trader.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
