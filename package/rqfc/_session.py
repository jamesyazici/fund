"""Authenticated HTTP session against the RQFC backend.

Login goes to Supabase Auth (email + password → JWT); every backend call carries
that JWT as a bearer token. No Alpaca keys ever touch the client.
"""
import re

import requests

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def looks_like_uuid(value: str) -> bool:
    return bool(value and _UUID_RE.match(str(value)))


class Session:
    def __init__(self, backend_url: str, supabase_url: str, anon_key: str):
        self.backend_url = backend_url.rstrip("/")
        self.supabase_url = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self.access_token = None

    def login(self, email: str, password: str) -> None:
        r = requests.post(
            f"{self.supabase_url}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": self.anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Login failed [{r.status_code}]: {r.text}")
        self.access_token = r.json()["access_token"]

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        if not self.access_token:
            raise RuntimeError("Not logged in. Call rqfc.login(email, password) first.")
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
