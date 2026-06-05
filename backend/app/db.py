"""Supabase access for the backend, using the service-role key (bypasses RLS).

Everything that writes to the database goes through here. Traders never write
directly; the backend is the only writer.
"""
from __future__ import annotations

from datetime import datetime, timezone

from supabase import create_client, Client

from .config import get_settings

_sb: Client | None = None


def sb() -> Client:
    global _sb
    if _sb is None:
        s = get_settings()
        _sb = create_client(s.supabase_url, s.supabase_service_key)
    return _sb


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Traders & permissions ────────────────────────────────────────────────────

def get_trader_by_auth_id(auth_user_id: str):
    res = (
        sb().table("traders")
        .select("id, display_name, is_admin, auth_user_id")
        .eq("auth_user_id", auth_user_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_trader_by_id(trader_id: str):
    res = (
        sb().table("traders")
        .select("id, display_name, is_admin, auth_user_id")
        .eq("id", trader_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def list_traders():
    res = sb().table("traders").select("id, display_name, is_admin, auth_user_id, created_at").execute()
    return res.data or []


def create_auth_user(email: str, password: str) -> str:
    """Create a confirmed Supabase Auth user, return its id."""
    res = sb().auth.admin.create_user({
        "email": email, "password": password, "email_confirm": True,
    })
    return res.user.id


def create_trader(display_name: str, is_admin: bool = False, auth_user_id: str = None) -> dict:
    return sb().table("traders").insert({
        "display_name": display_name,
        "is_admin": is_admin,
        "auth_user_id": auth_user_id,
    }).execute().data[0]


def list_trader_api_keys(trader_id: str) -> list[dict]:
    res = (
        sb().table("trader_api_keys")
        .select("id, trader_id, name, key_prefix, revoked_at, last_used_at, created_at")
        .eq("trader_id", trader_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def create_trader_api_key(trader_id: str, *, name: str, key_prefix: str, key_hash: str) -> dict:
    return (
        sb().table("trader_api_keys")
        .insert({
            "trader_id": trader_id,
            "name": name,
            "key_prefix": key_prefix,
            "key_hash": key_hash,
        })
        .execute()
        .data[0]
    )


def revoke_trader_api_key(key_id: str) -> bool:
    res = (
        sb().table("trader_api_keys")
        .update({"revoked_at": _now()})
        .eq("id", key_id)
        .is_("revoked_at", "null")
        .execute()
    )
    return bool(res.data)


def get_active_api_key_by_hash(key_hash: str):
    res = (
        sb().table("trader_api_keys")
        .select("id, trader_id, traders(id, display_name, is_admin, auth_user_id)")
        .eq("key_hash", key_hash)
        .is_("revoked_at", "null")
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def mark_api_key_used(key_id: str) -> None:
    sb().table("trader_api_keys").update({"last_used_at": _now()}).eq("id", key_id).execute()


def get_membership(pod_id: str, trader_id: str):
    res = (
        sb().table("pod_memberships")
        .select("pod_id, trader_id, role")
        .eq("pod_id", pod_id)
        .eq("trader_id", trader_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def list_trader_pods(trader_id: str):
    res = (
        sb().table("pod_memberships")
        .select("pod_id, role, pods(name, asset_class)")
        .eq("trader_id", trader_id)
        .execute()
    )
    return res.data or []


def list_memberships(pod_id: str = None):
    q = sb().table("pod_memberships").select("pod_id, trader_id, role, traders(display_name)")
    if pod_id:
        q = q.eq("pod_id", pod_id)
    return q.execute().data or []


def list_pods_admin():
    """All pods plus whether Alpaca creds are configured."""
    pods = sb().table("pods").select("*").order("created_at").execute().data or []
    creds = sb().table("pod_alpaca_credentials").select("pod_id, alpaca_account_id, api_key_enc").execute().data or []
    has = {c["pod_id"]: bool(c.get("api_key_enc")) for c in creds}
    for p in pods:
        p["has_alpaca"] = has.get(p["id"], False)
    return pods


# ── Pods & credentials ───────────────────────────────────────────────────────

def get_pod(pod_id: str):
    res = sb().table("pods").select("*").eq("id", pod_id).limit(1).execute()
    return res.data[0] if res.data else None


def find_pod_by_name(name: str):
    res = sb().table("pods").select("*").eq("name", name).limit(1).execute()
    return res.data[0] if res.data else None


def get_pod_alpaca(pod_id: str):
    """Return {alpaca_account_id, api_key, api_secret} for a pod, or None."""
    res = (
        sb().table("pod_alpaca_credentials")
        .select("alpaca_account_id, api_key_enc, api_secret_enc")
        .eq("pod_id", pod_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    row = res.data[0]
    return {
        "alpaca_account_id": row.get("alpaca_account_id"),
        "api_key": row.get("api_key_enc"),
        "api_secret": row.get("api_secret_enc"),
    }


def create_pod(name, asset_class, *, benchmark_symbol="SPY", description=None,
               allocated_capital=0, inception_date=None) -> dict:
    payload = {
        "name": name,
        "asset_class": asset_class,
        "benchmark_symbol": benchmark_symbol,
        "description": description,
        "allocated_capital": allocated_capital,
    }
    if inception_date:
        payload["inception_date"] = inception_date
    return sb().table("pods").insert(payload).execute().data[0]


def set_pod_alpaca(pod_id, *, alpaca_account_id=None, api_key=None, api_secret=None) -> None:
    sb().table("pod_alpaca_credentials").upsert({
        "pod_id": pod_id,
        "alpaca_account_id": alpaca_account_id,
        "api_key_enc": api_key,
        "api_secret_enc": api_secret,
        "updated_at": _now(),
    }, on_conflict="pod_id").execute()


def add_membership(pod_id, trader_id, role="trader") -> None:
    sb().table("pod_memberships").upsert({
        "pod_id": pod_id, "trader_id": trader_id, "role": role,
    }, on_conflict="pod_id,trader_id").execute()


def remove_membership(pod_id, trader_id) -> None:
    sb().table("pod_memberships").delete().eq("pod_id", pod_id).eq("trader_id", trader_id).execute()


def set_allocated_capital(pod_id, amount) -> None:
    sb().table("pods").update({"allocated_capital": amount}).eq("id", pod_id).execute()


def log_capital_allocation(pod_id, new_capital, previous_capital, allocated_by, note=None) -> None:
    sb().table("capital_allocations").insert({
        "pod_id": pod_id,
        "new_capital": new_capital,
        "previous_capital": previous_capital,
        "allocated_by": allocated_by,
        "note": note,
    }).execute()


# ── Trades, positions, NAV, metrics ──────────────────────────────────────────

def log_trade(pod_id, trader_id, trade: dict) -> None:
    sb().table("trades").insert({
        "pod_id": pod_id,
        "trader_id": trader_id,
        **trade,
    }).execute()


def replace_positions(pod_id, rows: list) -> None:
    if rows:
        now = _now()
        sb().table("positions").upsert(
            [{"pod_id": pod_id, "updated_at": now, **r} for r in rows],
            on_conflict="pod_id,symbol",
        ).execute()
    held = [r["symbol"] for r in rows]
    q = sb().table("positions").delete().eq("pod_id", pod_id)
    if held:
        q = q.not_.in_("symbol", held)
    q.execute()


def upsert_nav(pod_id, rows: list) -> None:
    if not rows:
        return
    sb().table("nav_history").upsert(
        [{"pod_id": pod_id, **r} for r in rows], on_conflict="pod_id,date"
    ).execute()


def upsert_metrics(pod_id, row: dict) -> None:
    sb().table("metrics").upsert({"pod_id": pod_id, **row}, on_conflict="pod_id,as_of_date").execute()


def count_trades(pod_id) -> int:
    return sb().table("trades").select("id", count="exact").eq("pod_id", pod_id).execute().count or 0
