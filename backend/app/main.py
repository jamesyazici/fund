"""RQFC trading backend.

Holds Alpaca credentials, enforces trader/pod permissions, submits orders, and
writes everything to Supabase. Traders authenticate with a Supabase JWT.
"""
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import alpaca_client as alp
from . import db, metrics
from .auth import get_current_trader
from .portal_auth import get_admin_actor, verify_credentials, issue_portal_token
from .config import get_settings
from .schemas import (
    OrderRequest, CancelRequest, CreatePodRequest,
    SetAlpacaRequest, CapitalRequest, MembershipRequest,
    PortalLogin, CreateTraderRequest,
)

PORTAL_HTML = Path(__file__).parent / "portal" / "index.html"

app = FastAPI(title="RQFC Trading Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Permission helper ─────────────────────────────────────────────────────────

def _require_pod_access(trader: dict, pod_id: str) -> None:
    if trader.get("is_admin"):
        return
    if not db.get_membership(pod_id, trader["id"]):
        raise HTTPException(status_code=403, detail="You are not assigned to this pod.")


# ── Health & identity ─────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/me")
def me(trader: dict = Depends(get_current_trader)):
    return {
        "trader_id": trader["id"],
        "display_name": trader["display_name"],
        "is_admin": trader["is_admin"],
        "pods": db.list_trader_pods(trader["id"]),
    }


@app.get("/pods")
def list_pods(trader: dict = Depends(get_current_trader)):
    """All pods (id, name, asset_class) — used by the client to resolve names."""
    res = db.sb().table("pods").select("id, name, asset_class, allocated_capital").execute()
    return res.data or []


# ── Trading ───────────────────────────────────────────────────────────────────

@app.post("/orders")
def place_order(req: OrderRequest, trader: dict = Depends(get_current_trader)):
    _require_pod_access(trader, req.pod_id)
    pod = db.get_pod(req.pod_id)
    if not pod:
        raise HTTPException(404, "Pod not found.")
    if not req.qty and not req.notional:
        raise HTTPException(400, "Provide either qty or notional.")

    order = alp.submit_order(
        req.pod_id, symbol=req.symbol, side=req.side, qty=req.qty,
        notional=req.notional, order_type=req.order_type,
        limit_price=req.limit_price, time_in_force=req.time_in_force,
    )
    row = alp.to_trade_row(order, req.order_label, pod["asset_class"])
    db.log_trade(req.pod_id, trader["id"], row)
    return {"order_id": row["alpaca_order_id"], "status": row["status"], "trade": row}


@app.post("/orders/cancel")
def cancel_order(req: CancelRequest, trader: dict = Depends(get_current_trader)):
    _require_pod_access(trader, req.pod_id)
    alp.cancel_order(req.pod_id, req.order_id)
    return {"cancelled": req.order_id}


# ── Pod live data ─────────────────────────────────────────────────────────────

@app.get("/pods/{pod_id}/account")
def pod_account(pod_id: str, trader: dict = Depends(get_current_trader)):
    _require_pod_access(trader, pod_id)
    return alp.get_account(pod_id)


@app.get("/pods/{pod_id}/positions")
def pod_positions(pod_id: str, trader: dict = Depends(get_current_trader)):
    _require_pod_access(trader, pod_id)
    return alp.get_positions(pod_id)


# ── Market data (any authenticated trader) ────────────────────────────────────

@app.get("/market/price")
def market_price(symbol: str, pod_id: str, trader: dict = Depends(get_current_trader)):
    _require_pod_access(trader, pod_id)
    return {"symbol": symbol.upper(), "price": alp.get_price(pod_id, symbol)}


@app.get("/market/bars")
def market_bars(symbol: str, pod_id: str, days: int = 30,
                trader: dict = Depends(get_current_trader)):
    _require_pod_access(trader, pod_id)
    return alp.get_bars(pod_id, symbol, days)


# ── Sync: pull Alpaca → Supabase (dashboard data) ─────────────────────────────

@app.post("/sync/{pod_id}")
def sync_pod(pod_id: str, trader: dict = Depends(get_current_trader)):
    _require_pod_access(trader, pod_id)
    positions = alp.get_positions(pod_id)
    db.replace_positions(pod_id, positions)

    nav_rows = alp.get_nav_history(pod_id)
    db.upsert_nav(pod_id, nav_rows)

    m = metrics.compute(nav_rows, trade_count=db.count_trades(pod_id))
    if m:
        db.upsert_metrics(pod_id, m)

    return {"positions": len(positions), "nav_days": len(nav_rows), "metrics": bool(m)}


# ── Admin portal ──────────────────────────────────────────────────────────────
# Admin endpoints accept a portal token (POST /admin/login) OR a Supabase admin
# JWT — both resolve via get_admin_actor.

@app.get("/portal", include_in_schema=False)
def portal_page():
    return FileResponse(PORTAL_HTML)


@app.post("/admin/login")
def admin_login(req: PortalLogin):
    if not verify_credentials(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid portal credentials.")
    return {"token": issue_portal_token()}


@app.get("/admin/pods")
def admin_list_pods(actor: dict = Depends(get_admin_actor)):
    return db.list_pods_admin()


@app.post("/admin/pods")
def admin_create_pod(req: CreatePodRequest, actor: dict = Depends(get_admin_actor)):
    pod = db.create_pod(
        req.name, req.asset_class, benchmark_symbol=req.benchmark_symbol,
        description=req.description, allocated_capital=req.allocated_capital,
    )
    if req.alpaca_api_key or req.alpaca_account_id:
        db.set_pod_alpaca(pod["id"], alpaca_account_id=req.alpaca_account_id,
                          api_key=req.alpaca_api_key, api_secret=req.alpaca_api_secret)
    if req.allocated_capital:
        db.log_capital_allocation(pod["id"], req.allocated_capital, None, actor.get("id"), "initial")
    return pod


@app.post("/admin/pods/{pod_id}/alpaca")
def admin_set_alpaca(pod_id: str, req: SetAlpacaRequest, actor: dict = Depends(get_admin_actor)):
    if not db.get_pod(pod_id):
        raise HTTPException(404, "Pod not found.")
    db.set_pod_alpaca(pod_id, alpaca_account_id=req.alpaca_account_id,
                      api_key=req.alpaca_api_key, api_secret=req.alpaca_api_secret)
    return {"ok": True}


@app.post("/admin/pods/{pod_id}/capital")
def admin_allocate_capital(pod_id: str, req: CapitalRequest, actor: dict = Depends(get_admin_actor)):
    pod = db.get_pod(pod_id)
    if not pod:
        raise HTTPException(404, "Pod not found.")
    previous = pod.get("allocated_capital")
    db.set_allocated_capital(pod_id, req.amount)
    db.log_capital_allocation(pod_id, req.amount, previous, actor.get("id"), req.note)
    # NOTE: with the Trading API, Alpaca's paper balance is reset in the
    # dashboard, not via API. Broker API enables true programmatic funding here.
    return {"pod_id": pod_id, "allocated_capital": req.amount, "previous": previous}


@app.get("/admin/traders")
def admin_list_traders(actor: dict = Depends(get_admin_actor)):
    return db.list_traders()


@app.post("/admin/traders")
def admin_create_trader(req: CreateTraderRequest, actor: dict = Depends(get_admin_actor)):
    """Create an rqfc account: a Supabase Auth login + a linked trader row."""
    try:
        auth_user_id = db.create_auth_user(req.email, req.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not create login: {e}")
    trader = db.create_trader(req.display_name, req.is_admin, auth_user_id)
    return {"trader_id": trader["id"], "display_name": trader["display_name"],
            "is_admin": trader["is_admin"], "email": req.email}


@app.get("/admin/memberships")
def admin_list_memberships(pod_id: str = None, actor: dict = Depends(get_admin_actor)):
    return db.list_memberships(pod_id)


@app.post("/admin/memberships")
def admin_add_membership(req: MembershipRequest, actor: dict = Depends(get_admin_actor)):
    db.add_membership(req.pod_id, req.trader_id, req.role)
    return {"ok": True}


@app.delete("/admin/memberships")
def admin_remove_membership(req: MembershipRequest, actor: dict = Depends(get_admin_actor)):
    db.remove_membership(req.pod_id, req.trader_id)
    return {"ok": True}
