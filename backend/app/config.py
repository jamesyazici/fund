import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        # Supabase
        self.supabase_url = _require("SUPABASE_URL")
        self.supabase_service_key = _require("SUPABASE_SERVICE_ROLE_KEY")
        # Used to verify trader JWTs. Find it in Supabase:
        # Settings → API → JWT Settings → JWT Secret.
        self.supabase_jwt_secret = _require("SUPABASE_JWT_SECRET")
        self.supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

        # Alpaca — paper trading by default.
        self.alpaca_paper = os.environ.get("ALPACA_PAPER", "true").lower() != "false"
        # Optional single-account fallback: if a pod has no row in
        # pod_alpaca_credentials, the backend uses these env keys. Lets you
        # validate one pod end-to-end without storing secrets in the DB.
        self.alpaca_api_key = os.environ.get("ALPACA_API_KEY")
        self.alpaca_api_secret = os.environ.get("ALPACA_API_SECRET")

        self.cors_origins = [
            o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()
        ]

        # Admin portal login. Defaults to the requested elbow/grease; override
        # in production via env. Portal tokens are signed with this secret.
        self.admin_portal_username = os.environ.get("ADMIN_PORTAL_USERNAME", "elbow")
        self.admin_portal_password = os.environ.get("ADMIN_PORTAL_PASSWORD", "grease")
        self.admin_portal_secret = os.environ.get("ADMIN_PORTAL_SECRET") or self.supabase_jwt_secret


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


@lru_cache
def get_settings() -> Settings:
    return Settings()
