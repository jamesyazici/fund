"""RQFC trading backend.

Holds Alpaca credentials, enforces trader/pod permissions, submits orders, and
writes everything to Supabase. Traders authenticate with backend sessions,
rqfc API keys, or legacy Supabase JWTs.
"""
from pathlib import Path
import json
import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from . import alpaca_client as alp
from . import db, metrics
from .auth import (
    api_key_prefix,
    authenticate_with_supabase,
    get_current_trader,
    hash_api_key,
)
from .portal_auth import get_admin_actor, verify_google_admin, issue_portal_token
from .config import get_settings
from .schemas import (
    OrderRequest, CancelRequest, CreatePodRequest,
    SetAlpacaRequest, CapitalRequest, MembershipRequest,
    PortalLogin, TraderLogin, CreateTraderRequest, CreateTraderApiKeyRequest,
)

PORTAL_HTML = Path(__file__).parent / "portal" / "index.html"

app = FastAPI(
    title="RQFC Trading Backend",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

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

@app.get("/", include_in_schema=False)
def root_page():
    return HTMLResponse("""
<!doctype html>
<html lang="en" data-theme="system">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>RQFC Fund API</title>
<style>
  :root, [data-theme="dark"] {
    --bg:#070a12; --panel:#101827; --panelSoft:rgba(16,24,39,.74); --line:#273449; --text:#f8fafc;
    --muted:#9aa8bc; --accent:#22c55e; --accent2:#38bdf8; --button:#f8fafc; --buttonText:#071014;
    --heroA:rgba(34,197,94,.20); --heroB:rgba(56,189,248,.18); --grid:#1e293b; --tile:#0f172a;
    color-scheme:dark;
  }
  [data-theme="light"] {
    --bg:#f6f8fb; --panel:#ffffff; --panelSoft:rgba(255,255,255,.82); --line:#d7e0ec; --text:#0f172a;
    --muted:#526276; --accent:#047857; --accent2:#2563eb; --button:#0f172a; --buttonText:#ffffff;
    --heroA:rgba(4,120,87,.14); --heroB:rgba(37,99,235,.13); --grid:#e7eef8; --tile:#ffffff;
    color-scheme:light;
  }
  @media (prefers-color-scheme: light) {
    [data-theme="system"] {
      --bg:#f6f8fb; --panel:#ffffff; --panelSoft:rgba(255,255,255,.82); --line:#d7e0ec; --text:#0f172a;
      --muted:#526276; --accent:#047857; --accent2:#2563eb; --button:#0f172a; --buttonText:#ffffff;
      --heroA:rgba(4,120,87,.14); --heroB:rgba(37,99,235,.13); --grid:#e7eef8; --tile:#ffffff;
      color-scheme:light;
    }
  }
  * { box-sizing:border-box; }
  body {
    margin:0; min-height:100vh; color:var(--text); background:
      radial-gradient(circle at 18% 14%, var(--heroB) 0, transparent 25rem),
      radial-gradient(circle at 86% 12%, var(--heroA) 0, transparent 22rem),
      linear-gradient(135deg, var(--bg), color-mix(in srgb, var(--bg) 86%, var(--panel)));
    font:16px/1.5 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  }
  body::before {
    content:""; position:fixed; inset:0; pointer-events:none; opacity:.34;
    background-image:linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px);
    background-size:44px 44px; mask-image:linear-gradient(to bottom, #000, transparent 72%);
  }
  main { min-height:100vh; display:grid; place-items:center; padding:5rem 1.25rem 2rem; }
  .hero { width:min(1080px, 100%); display:grid; grid-template-columns:minmax(0,1.05fr) minmax(320px,.95fr); gap:3rem; align-items:center; position:relative; }
  .eyebrow { display:inline-flex; align-items:center; gap:.45rem; color:var(--accent); font-size:.78rem; letter-spacing:.14em; text-transform:uppercase; font-weight:800; }
  .eyebrow::before { content:""; width:.5rem; height:.5rem; border-radius:999px; background:var(--accent); box-shadow:0 0 22px var(--accent); }
  h1 { font-size:clamp(3rem, 8vw, 6.4rem); line-height:.9; margin:.75rem 0 1.2rem; letter-spacing:0; max-width:10ch; }
  p { max-width:36rem; color:var(--muted); margin:0 0 1.5rem; font-size:1.05rem; }
  .ctaRow { display:flex; gap:.75rem; flex-wrap:wrap; align-items:center; }
  a {
    display:inline-flex; align-items:center; justify-content:center; min-height:2.8rem;
    padding:0 1rem; border-radius:8px; background:var(--button); color:var(--buttonText);
    text-decoration:none; font-weight:750;
  }
  .ghost { background:transparent; color:var(--text); border:1px solid var(--line); }
  .theme {
    position:fixed; top:1rem; right:1rem; display:flex; gap:.25rem; padding:.25rem;
    border:1px solid var(--line); border-radius:999px; background:var(--panelSoft); backdrop-filter:blur(14px);
  }
  .theme button {
    width:2.05rem; height:2.05rem; display:grid; place-items:center; border:0; border-radius:999px; padding:0; background:transparent;
    color:var(--muted); cursor:pointer;
  }
  .theme svg { width:1rem; height:1rem; }
  .theme button.active { background:var(--button); color:var(--buttonText); font-weight:750; }
  .visual {
    border:1px solid var(--line); background:var(--panelSoft); border-radius:18px;
    padding:1rem; box-shadow:0 24px 80px rgba(0,0,0,.24); overflow:hidden; backdrop-filter:blur(18px);
  }
  .bar { display:flex; gap:.4rem; margin-bottom:1rem; }
  .dot { width:.7rem; height:.7rem; border-radius:999px; background:#334155; }
  .dot:nth-child(1) { background:#ef4444; } .dot:nth-child(2) { background:#f59e0b; } .dot:nth-child(3) { background:#22c55e; }
  .terminal { border:1px solid var(--line); border-radius:12px; overflow:hidden; background:var(--tile); }
  .line { display:grid; grid-template-columns:5rem 1fr auto; gap:.6rem; padding:.7rem .8rem; border-top:1px solid var(--line); align-items:center; }
  .line:first-child { border-top:0; }
  .sym { font-weight:800; }
  .spark { height:.45rem; border-radius:999px; background:linear-gradient(90deg, var(--accent), var(--accent2)); }
  .gain { color:var(--accent); font-weight:800; font-variant-numeric:tabular-nums; }
  .metric { margin-top:1rem; display:grid; grid-template-columns:1fr 1fr; gap:.6rem; }
  .tile { border:1px solid var(--line); border-radius:10px; padding:.85rem; background:var(--tile); }
  .label { color:var(--muted); font-size:.75rem; }
  .value { font-size:1.35rem; font-weight:800; margin-top:.2rem; }
  @media (max-width:760px) {
    main { padding-top:4.5rem; }
    .hero { grid-template-columns:1fr; gap:2rem; }
    .visual { order:-1; }
    h1 { max-width:11ch; }
  }
</style>
</head>
<body>
<div class="theme" aria-label="Theme">
  <button data-theme-choice="system" onclick="setTheme('system')" title="System theme" aria-label="System theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg></button>
  <button data-theme-choice="light" onclick="setTheme('light')" title="Light theme" aria-label="Light theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg></button>
  <button data-theme-choice="dark" onclick="setTheme('dark')" title="Dark theme" aria-label="Dark theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.99 13.2A8.5 8.5 0 1 1 10.8 3.01 6.5 6.5 0 0 0 20.99 13.2Z"/></svg></button>
</div>
<main>
  <section class="hero" aria-label="RQFC Fund API">
    <div>
      <div class="eyebrow">RQFC Fund Infrastructure</div>
      <h1>Trading backend online.</h1>
      <p>
        This service powers authenticated pod trading, portfolio sync, and the
        private admin control plane. API documentation is not exposed publicly.
      </p>
      <div class="ctaRow">
        <a href="/portal">Open Admin Portal</a>
        <a class="ghost" href="/portal">Manage pods</a>
      </div>
    </div>
    <div class="visual" aria-hidden="true">
      <div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
      <div class="terminal">
        <div class="line"><span class="sym">AAPL</span><span class="spark" style="width:88%"></span><span class="gain">+1.8%</span></div>
        <div class="line"><span class="sym">NVDA</span><span class="spark" style="width:96%"></span><span class="gain">+3.4%</span></div>
        <div class="line"><span class="sym">SPY</span><span class="spark" style="width:72%"></span><span class="gain">+0.7%</span></div>
        <div class="line"><span class="sym">BTC</span><span class="spark" style="width:81%"></span><span class="gain">+2.1%</span></div>
      </div>
      <div class="metric">
        <div class="tile"><div class="label">Auth</div><div class="value">Locked</div></div>
        <div class="tile"><div class="label">Execution</div><div class="value">API</div></div>
      </div>
    </div>
  </section>
</main>
<script>
const THEME_KEY = 'rqfc_public_theme';
function setTheme(theme) {
  localStorage.setItem(THEME_KEY, theme);
  document.documentElement.dataset.theme = theme;
  document.querySelectorAll('[data-theme-choice]').forEach(button => {
    button.classList.toggle('active', button.dataset.themeChoice === theme);
  });
}
setTheme(localStorage.getItem(THEME_KEY) || 'system');
</script>
</body>
</html>
    """)


@app.post("/auth/login")
def trader_login(req: TraderLogin):
    return authenticate_with_supabase(req.email, req.password)


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


# ── Public transparency data ─────────────────────────────────────────────────

def _live_pod_snapshot(pod: dict) -> dict:
    """Read-only public pod snapshot with live Alpaca marks when available."""
    snapshot = {
        "id": pod["id"],
        "name": pod["name"],
        "asset_class": pod["asset_class"],
        "description": pod.get("description"),
        "benchmark_symbol": pod.get("benchmark_symbol"),
        "inception_date": pod.get("inception_date"),
        "allocated_capital": float(pod.get("allocated_capital") or 0),
        "live": False,
        "source": "supabase",
        "account": None,
        "positions": [],
        "nav": float(pod.get("allocated_capital") or 0),
        "cash": None,
        "gross_notional": 0.0,
        "net_notional": 0.0,
        "unrealized_pnl": 0.0,
        "live_gain": 0.0,
        "daily_return": None,
        "session_return": None,
        "total_return": None,
        "error": None,
    }
    try:
        account = alp.get_account(pod["id"])
        positions = alp.get_positions(pod["id"])
        gross = 0.0
        net = 0.0
        pnl = 0.0
        for position in positions:
            quantity = float(position.get("quantity") or 0)
            price = position.get("current_price")
            market_value = position.get("market_value")
            if market_value is None and price is not None:
                market_value = quantity * float(price)
                position["market_value"] = round(market_value, 2)
            value = float(market_value or 0)
            gross += abs(value)
            net += value
            pnl += float(position.get("unrealized_pnl") or 0)

        nav = float(account.get("portfolio_value") or account.get("equity") or snapshot["nav"])
        allocated = snapshot["allocated_capital"]
        snapshot.update({
            "live": True,
            "source": "alpaca",
            "account": account,
            "positions": positions,
            "nav": nav,
            "cash": float(account.get("cash") or 0),
            "gross_notional": round(gross, 2),
            "net_notional": round(net, 2),
            "unrealized_pnl": round(pnl, 2),
            "live_gain": round(nav - allocated, 2),
            "daily_return": account.get("session_return"),
            "session_return": account.get("session_return"),
            "total_return": ((nav / allocated) - 1) if allocated else None,
        })
    except Exception as e:
        snapshot["error"] = str(getattr(e, "detail", e))
    return snapshot


@app.get("/public/live")
def public_live_snapshots():
    """Public transparency feed. Never returns credentials or trader identities."""
    pods = db.sb().table("pods").select("*").order("created_at").execute().data or []
    snapshots = [_live_pod_snapshot(p) for p in pods]
    return {"pods": snapshots}


@app.get("/public/pods/{pod_id}/live")
def public_live_pod_snapshot(pod_id: str):
    pod = db.get_pod(pod_id)
    if not pod:
        raise HTTPException(404, "Pod not found.")
    return _live_pod_snapshot(pod)


@app.get("/public/pods/{pod_id}/intraday-nav")
def public_intraday_nav(pod_id: str, minutes: int = 390):
    if not db.get_pod(pod_id):
        raise HTTPException(404, "Pod not found.")
    try:
        return {"pod_id": pod_id, "timeframe": "1Min", "rows": alp.get_intraday_nav_history(pod_id, minutes)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(getattr(e, "detail", e)))


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
# Admin endpoints accept a portal token (POST /admin/login) OR any supported
# trader bearer whose linked trader has is_admin=true.

@app.get("/portal", include_in_schema=False)
def portal_page():
    html = PORTAL_HTML.read_text(encoding="utf-8").replace(
        "__GOOGLE_OAUTH_CLIENT_ID__",
        json.dumps(get_settings().google_oauth_client_id),
    )
    response = HTMLResponse(html)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    return response


@app.post("/admin/login")
def admin_login(req: PortalLogin):
    admin = verify_google_admin(req.credential)
    return {"token": issue_portal_token(admin["email"]), "admin": admin}


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


@app.get("/admin/trades")
def admin_list_trade_activity(
    trader_id: str = None,
    pod_id: str = None,
    limit: int = 100,
    actor: dict = Depends(get_admin_actor),
):
    return db.list_trade_activity(trader_id=trader_id, pod_id=pod_id, limit=limit)


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


@app.get("/admin/traders/{trader_id}/api-keys")
def admin_list_trader_api_keys(trader_id: str, actor: dict = Depends(get_admin_actor)):
    if not db.get_trader_by_id(trader_id):
        raise HTTPException(404, "Trader not found.")
    return db.list_trader_api_keys(trader_id)


@app.post("/admin/traders/{trader_id}/api-keys")
def admin_create_trader_api_key(
    trader_id: str,
    req: CreateTraderApiKeyRequest,
    actor: dict = Depends(get_admin_actor),
):
    if not db.get_trader_by_id(trader_id):
        raise HTTPException(404, "Trader not found.")
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "API key name is required.")

    plaintext = "rqfc_" + secrets.token_urlsafe(32)
    row = db.create_trader_api_key(
        trader_id,
        name=name,
        key_prefix=api_key_prefix(plaintext),
        key_hash=hash_api_key(plaintext),
    )
    return {
        "id": row["id"],
        "trader_id": row["trader_id"],
        "name": row["name"],
        "key_prefix": row["key_prefix"],
        "created_at": row["created_at"],
        "api_key": plaintext,
    }


@app.delete("/admin/api-keys/{key_id}")
def admin_revoke_trader_api_key(key_id: str, actor: dict = Depends(get_admin_actor)):
    if not db.revoke_trader_api_key(key_id):
        raise HTTPException(404, "Active API key not found.")
    return {"ok": True}


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
