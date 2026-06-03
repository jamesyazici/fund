# RQFC Fund — Architecture

How the trading package, backend, database, Alpaca, and dashboard fit together.

## Core model

| Concept | Maps to | Notes |
|---|---|---|
| **Pod** | one Alpaca account (1:1) | A strategy team. Holds the capital and the positions. |
| **Trader** | one rqfc account = one Supabase Auth user | A person. Assigned to one or more pods. |
| **Admin** | a trader with `is_admin = true` | Can trade any pod, assign/remove traders, allocate capital. |

3–4 traders share a pod's single Alpaca account. Because the account is shared,
**Alpaca only knows pod-level positions and P&L** — performance is reported per
pod. Trades still record *which trader* placed them (for audit and activity feeds).

## The trust boundary (why there's a backend)

Traders must authenticate, must **not** hold the pod's Alpaca keys, and must be
restricted to pods they're assigned to. None of that can be enforced by code
running on a trader's laptop. So three things live behind a trusted backend:

1. **Alpaca credentials** — never sent to traders.
2. **Permission checks** — "can this trader trade this pod?"
3. **All database writes** — via the Supabase service-role key.

```
 Trader's machine            Backend (FastAPI, holds secrets)         External
 ────────────────            ────────────────────────────────        ──────────
 import rqfc
 rqfc.login(email, pw) ─────► (Supabase Auth verifies password) ◄───► Supabase Auth
        ◄───────────────────  returns JWT (identity token)
 account = rqfc.pod(id)
 account.buy("AAPL", 10) ───► POST /orders  (Authorization: Bearer JWT)
                              1. verify JWT → trader
                              2. check membership / is_admin for pod
                              3. load pod's Alpaca keys
                              4. submit order ──────────────────────► Alpaca
                              5. log trade (service role) ──────────► Supabase
        ◄───────────────────  return fill

 React dashboard ───────────────────────────────────────────────► Supabase (public read)
```

The package is a **thin client**: authenticate, then make HTTP calls. All the
Alpaca logic (the current `trading.py` / `account.py` / `market_data.py`) moves
**server-side** into the backend, where it can run with the pod's keys.

## Components

### 1. Supabase (database + auth)
- **Auth**: each trader is a Supabase Auth user (email + password). Login returns
  a JWT the backend verifies.
- **Postgres**: schema in `app/supabase/migrations/001_schema.sql`. Public read on
  display tables; **all writes are service-role** (from the backend). The
  `pod_alpaca_credentials` table has *no* RLS policy, so only the backend can read it.

Key tables:
- `pods` — public pod info + `allocated_capital`. No Alpaca secrets.
- `traders` — rqfc accounts, linked to auth via `auth_user_id`, `is_admin` flag.
- `pod_memberships` — which traders may trade which pods, with `role`.
- `pod_alpaca_credentials` — **backend-only** Alpaca account id / keys per pod.
- `trades` — every order, tagged with `pod_id` + `trader_id`.
- `positions`, `nav_history`, `metrics` — pod-level, synced from Alpaca.
- `capital_allocations` — audit log of funding changes.
- `members` (view) — `pod_memberships ⋈ traders`, so the dashboard has a stable roster API.

### 2. Backend (FastAPI — recommended)
A small Python service. FastAPI because the existing Alpaca logic is already
Python (`alpaca-py`) and moves over almost verbatim.

Responsibilities:
- Verify Supabase JWTs (HS256 with the project JWT secret, or JWKS).
- Enforce permissions (membership / admin).
- Hold Alpaca credentials and submit orders.
- Write trades and sync positions / NAV / metrics into Supabase (service role).

Proposed endpoints:

| Method | Path | Who | Does |
|---|---|---|---|
| POST | `/orders` | trader (for their pods) / admin (any) | place an order, log the trade |
| POST | `/orders/cancel` | same | cancel an open order |
| GET | `/pods/{id}/account` | members / admin | live equity, buying power |
| GET | `/pods/{id}/positions` | members / admin | live positions |
| GET | `/market/price`, `/market/bars` | any trader | market data (read-only) |
| POST | `/admin/pods` | admin | create a pod + its Alpaca account |
| POST | `/admin/pods/{id}/capital` | admin | fund/reset the pod's balance, log it |
| POST | `/admin/memberships` | admin | assign / remove a trader |
| POST | `/sync/{pod_id}` | admin / cron | pull positions + NAV from Alpaca → Supabase |

Hosting: Render / Railway / Fly.io (any container host). Secrets (Supabase
service-role key, Supabase JWT secret, Alpaca keys) live in the backend env.

### 3. rqfc package (thin client)
```python
import rqfc

rqfc.login("alice@rqfc.club", "password")   # → Supabase Auth, caches JWT
account = rqfc.pod("Alpha Equities")         # pick a pod you're allowed to trade
account.buy("AAPL", 10)                       # → POST backend /orders
account.positions()                           # → GET backend /pods/{id}/positions

# admins only
admin = rqfc.admin()
admin.create_pod("Vol Arb", "options", capital=100_000)
admin.add_trader("bob@rqfc.club", pod="Vol Arb", role="trader")
admin.allocate_capital("Vol Arb", 150_000)
```
The client keeps the same friendly method names (`buy`, `sell`, `short`, …) but
each one is now an authenticated HTTP call, not a direct Alpaca call.

### 4. Admin portal
A self-contained web UI served by the backend at `GET /portal`
(`backend/app/portal/index.html`, vanilla JS — no build step). It logs in with a
shared username/password (`ADMIN_PORTAL_USERNAME`/`ADMIN_PORTAL_PASSWORD`,
default `elbow`/`grease`) → a portal token, and drives the `/admin/*` API to
create pods, create rqfc accounts (Supabase Auth user + trader), set Alpaca
credentials, allocate capital, and assign traders. It lives on the backend (not
the public GitHub Pages dashboard) because those actions need the service-role
key. `/admin/*` accepts the portal token **or** a Supabase admin JWT, so the
portal and the Python admin client are interchangeable.

### 5. React dashboard
Read-only, public. Already reads `pods`, `members` (view), `trades`,
`positions`, `nav_history`, `metrics` from Supabase. No changes needed beyond
the schema rename already applied.

## Connecting the Alpaca accounts — one open decision

You chose **actual Alpaca funding** for capital allocation. How that's wired
depends on which Alpaca product you use:

### Option A — Alpaca **Broker API** (recommended for this)
Purpose-built for "a firm with many funded sub-accounts."
- One Broker API credential for the whole club (lives in backend env).
- Create one Alpaca account **per pod** programmatically.
- **Fund/allocate capital via journals** — real, API-driven, exactly what you want.
- Trade on behalf of any pod account with the single firm credential.
- `pod_alpaca_credentials` only stores each pod's `alpaca_account_id` (no per-pod secrets).
- Sandbox is free for development.

### Option B — Alpaca **Trading API** + separate paper accounts
- Manually create N Alpaca paper accounts (one per pod), store each keypair
  (encrypted) in `pod_alpaca_credentials`.
- "Funding" = resetting each paper account's balance in the dashboard — **not
  truly programmatic**, so `admin.allocate_capital()` can't fully work.
- Simpler to start, but doesn't deliver real capital allocation.

**Recommendation:** Broker API (sandbox) — it's the only option that makes
"admin allocates capital to a pod" a real, programmatic feature, and it removes
per-pod secret storage entirely.

## Security notes
- Traders never receive Alpaca keys; the backend holds them.
- `pod_alpaca_credentials` is unreadable except by the service role. Use Supabase
  Vault / pgsodium to encrypt at rest in production.
- JWTs are short-lived; the client refreshes via Supabase.
- A trader can only act on pods in their `pod_memberships` (admins bypass).

## Build phases
1. **DB schema** — ✅ done (`001_schema.sql`, `002_seed.sql`).
2. **Confirm Alpaca product** — Broker API vs Trading API (above).
3. **Backend** — FastAPI skeleton: JWT verification, `/orders`, permission checks,
   Alpaca submission, trade logging. Move `trading.py`/`account.py`/`market_data.py`
   server-side.
4. **Package** — refactor `rqfc` into a thin authenticated client (`login`, `pod`,
   `admin`).
5. **Sync job** — scheduled `/sync` to refresh positions / NAV / metrics per pod.
6. **Auth setup** — create Supabase Auth users for traders; wire `auth_user_id`.
