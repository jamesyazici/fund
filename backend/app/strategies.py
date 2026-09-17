"""Strategy deployment.

Traders upload a bundle (`rqfc deploy`); the VM supervisor polls
`/internal/strategies/pending`, requests a token, downloads the bundle, and
runs it in a sandbox. A running strategy trades through the ordinary
`/orders` etc. endpoints, using a normal trader session token — the sandbox
acts with exactly the authority the deploying trader already has, nothing
more, so no new auth mechanism was needed here.

Two auth models on this one file:
  * `/strategies/*`           — a trader bearer (same rule as /orders: your
                                 own pods, or any pod if you're admin).
  * `/internal/strategies/*`  — the VM's shared secret only. Never accepts a
                                 trader token, never issued to a browser.
"""
from __future__ import annotations

import base64
import re

from fastapi import APIRouter, Depends, Header, HTTPException

from . import db
from .auth import get_current_trader, issue_trader_session
from .config import get_settings
from .schemas import DeployStrategyRequest, StrategyLogLine, StrategyStatusUpdate

router = APIRouter()

_MAX_BUNDLE_BYTES = 2 * 1024 * 1024  # 2 MB
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _looks_like_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value or ""))


def _require_internal(x_internal_secret: str = Header(default=None)) -> None:
    secret = get_settings().internal_shared_secret
    if not secret or x_internal_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing internal secret.")


def _resolve_pod_for_trader(ref: str, trader: dict) -> dict:
    pod = db.get_pod(ref) if _looks_like_uuid(ref) else db.find_pod_by_name(ref)
    if not pod:
        raise HTTPException(404, f"No pod '{ref}'.")
    if not trader.get("is_admin") and not db.get_membership(pod["id"], trader["id"]):
        raise HTTPException(403, "You are not assigned to this pod.")
    return pod


# ── Trader-facing ────────────────────────────────────────────────────────────

@router.post("/strategies")
def deploy_strategy(req: DeployStrategyRequest, trader: dict = Depends(get_current_trader)):
    pod = _resolve_pod_for_trader(req.pod, trader)
    try:
        bundle = base64.b64decode(req.bundle_b64, validate=True)
    except Exception:
        raise HTTPException(400, "bundle_b64 is not valid base64.")
    if not bundle:
        raise HTTPException(400, "Bundle is empty.")
    if len(bundle) > _MAX_BUNDLE_BYTES:
        raise HTTPException(400, f"Bundle exceeds {_MAX_BUNDLE_BYTES // 1024} KB limit.")

    db.stop_pod_strategies(pod["id"])  # at most one active strategy per pod
    row = db.create_strategy(pod["id"], trader["id"], req.name, req.bundle_b64, len(bundle))
    db.write_audit_log(
        "strategy_deployed",
        f"Strategy '{req.name}' deployed to pod '{pod['name']}' ({len(bundle)} bytes)",
        actor=trader.get("display_name"), pod_id=pod["id"], trader_id=trader["id"],
    )
    return {"id": row["id"], "pod_id": pod["id"], "status": row["status"]}


@router.get("/strategies/current")
def current_strategy(pod: str, trader: dict = Depends(get_current_trader)):
    p = _resolve_pod_for_trader(pod, trader)
    row = db.get_current_strategy(p["id"])
    if not row:
        raise HTTPException(404, "No strategy deployed to this pod.")
    return row


@router.get("/strategies/logs")
def strategy_logs(pod: str, limit: int = 200, trader: dict = Depends(get_current_trader)):
    p = _resolve_pod_for_trader(pod, trader)
    row = db.get_current_strategy(p["id"])
    if not row:
        raise HTTPException(404, "No strategy deployed to this pod.")
    return db.list_strategy_logs(row["id"], limit=limit)


@router.post("/strategies/stop")
def stop_strategy(pod: str, trader: dict = Depends(get_current_trader)):
    p = _resolve_pod_for_trader(pod, trader)
    n = db.stop_pod_strategies(p["id"])
    if n:
        db.write_audit_log(
            "strategy_stopped", f"Strategy stopped for pod '{p['name']}'",
            actor=trader.get("display_name"), pod_id=p["id"], trader_id=trader["id"],
        )
    return {"stopped": n}


# ── VM supervisor only (shared secret) ───────────────────────────────────────

@router.get("/internal/strategies/pending")
def pending_strategies(_: None = Depends(_require_internal)):
    return db.list_pending_strategies()


@router.get("/internal/strategies/{strategy_id}/bundle")
def strategy_bundle(strategy_id: str, _: None = Depends(_require_internal)):
    row = db.get_strategy_bundle(strategy_id)
    if not row:
        raise HTTPException(404, "Strategy not found.")
    return row  # {"id", "pod_id", "bundle_b64"}


@router.post("/internal/strategies/{strategy_id}/token")
def strategy_token(strategy_id: str, _: None = Depends(_require_internal)):
    row = db.get_strategy(strategy_id)
    if not row:
        raise HTTPException(404, "Strategy not found.")
    return {"token": issue_trader_session(row["trader_id"]), "pod_id": row["pod_id"]}


@router.post("/internal/strategies/{strategy_id}/status")
def set_strategy_status(strategy_id: str, body: StrategyStatusUpdate, _: None = Depends(_require_internal)):
    if not db.get_strategy(strategy_id):
        raise HTTPException(404, "Strategy not found.")
    db.update_strategy_status(strategy_id, body.status, body.detail)
    return {"ok": True}


@router.post("/internal/strategies/{strategy_id}/logs")
def add_strategy_log(strategy_id: str, body: StrategyLogLine, _: None = Depends(_require_internal)):
    db.append_strategy_log(strategy_id, body.line)
    return {"ok": True}
