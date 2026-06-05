"""Authenticated HTTP session against the RQFC backend.

The backend owns auth, authorization, and Alpaca credentials. This client stores
only a backend-issued token or trader API key and sends it as bearer auth.
"""
import re

import requests

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def looks_like_uuid(value: str) -> bool:
    return bool(value and _UUID_RE.match(str(value)))


class Session:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.access_token = None
        self.profile = None

    def login(self, email: str, password: str) -> dict:
        r = requests.post(
            f"{self.backend_url}/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Login failed [{r.status_code}]: {r.text}")
        data = r.json()
        self.access_token = data["token"]
        self.profile = data.get("profile")
        return self.profile or {}

    def use_api_key(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("api_key is required.")
        self.access_token = api_key
        self.profile = None

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        if not self.access_token:
            raise RuntimeError(
                "Not logged in. Call rqfc.login(email, password) or "
                "rqfc.login(api_key='rqfc_...') first."
            )
        return {"Authorization": f"Bearer {self.access_token}"}

    def get(self, path: str, params: dict = None):
        return self._handle(requests.get(
            f"{self.backend_url}{path}", headers=self._headers(), params=params, timeout=60))

    def post(self, path: str, json: dict = None):
        return self._handle(requests.post(
            f"{self.backend_url}{path}", headers=self._headers(), json=json, timeout=60))

    def delete(self, path: str, json: dict = None):
        return self._handle(requests.delete(
            f"{self.backend_url}{path}", headers=self._headers(), json=json, timeout=60))

    @staticmethod
    def _handle(r: requests.Response):
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise RuntimeError(f"[{r.status_code}] {detail}")
        return r.json() if r.content else None
