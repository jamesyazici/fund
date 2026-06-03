"""Create sample traders end-to-end.

For each entry below this:
  1. creates a Supabase Auth user (email + password),
  2. inserts/links a `traders` row (with is_admin),
  3. optionally assigns them to a pod.

Run from the backend dir with your .env loaded:
    python -m scripts.seed_users

Idempotent: re-running updates the linked trader rather than duplicating.
"""
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ── Edit these ────────────────────────────────────────────────────────────────
SAMPLE_USERS = [
    {"email": "admin@rqfc.club",  "password": "changeme-admin", "name": "Club Admin", "is_admin": True},
    {"email": "alice@rqfc.club",  "password": "changeme-alice", "name": "Alice",       "is_admin": False},
    {"email": "bob@rqfc.club",    "password": "changeme-bob",   "name": "Bob",         "is_admin": False},
]
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    sb = create_client(url, service_key)

    for u in SAMPLE_USERS:
        # 1. Create (or find) the auth user.
        auth_user_id = _ensure_auth_user(sb, u["email"], u["password"])

        # 2. Upsert the trader row linked to that auth user.
        existing = (
            sb.table("traders").select("id").eq("auth_user_id", auth_user_id).limit(1).execute()
        )
        if existing.data:
            sb.table("traders").update({
                "display_name": u["name"], "is_admin": u["is_admin"],
            }).eq("id", existing.data[0]["id"]).execute()
            trader_id = existing.data[0]["id"]
        else:
            row = sb.table("traders").insert({
                "auth_user_id": auth_user_id,
                "display_name": u["name"],
                "is_admin": u["is_admin"],
            }).execute().data[0]
            trader_id = row["id"]

        print(f"✓ {u['email']:24s} trader_id={trader_id} admin={u['is_admin']}")


def _ensure_auth_user(sb, email: str, password: str) -> str:
    """Create a confirmed auth user, or return the existing one's id."""
    try:
        res = sb.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        return res.user.id
    except Exception:
        # Likely already exists — find it.
        page = sb.auth.admin.list_users()
        users = page if isinstance(page, list) else getattr(page, "users", page)
        for user in users:
            if getattr(user, "email", None) == email:
                return user.id
        raise


if __name__ == "__main__":
    main()
