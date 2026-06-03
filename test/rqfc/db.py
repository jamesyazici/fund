import os
from datetime import datetime, timezone

_client = None


def _get():
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set.\n"
                "Find them in your Supabase project under Settings → API."
            )
        try:
            from supabase import create_client
        except ImportError:
            raise RuntimeError("supabase package not installed. Run: pip install supabase")
        _client = create_client(url, key)
    return _client


def configure(url: str, key: str) -> None:
    global _client
    from supabase import create_client
    _client = create_client(url, key)


def ensure_account(account_id: str, display_name: str = None) -> None:
    try:
        payload = {"id": account_id}
        if display_name:
            payload["display_name"] = display_name
        _get().table("accounts").upsert(payload).execute()
    except Exception as e:
        print(f"[rqfc] Warning: could not register account: {e}")


def log_trade(account_id: str, trade: dict) -> None:
    try:
        _get().table("trades").insert({"account_id": account_id, **trade}).execute()
    except Exception as e:
        print(f"[rqfc] Warning: could not log trade: {e}")


def log_snapshot(account_id: str, equity: float, cash: float) -> None:
    try:
        _get().table("portfolio_snapshots").insert({
            "account_id": account_id,
            "equity": equity,
            "cash": cash,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        print(f"[rqfc] Warning: could not log snapshot: {e}")
