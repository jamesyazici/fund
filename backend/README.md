# RQFC Trading Backend

FastAPI service that holds Alpaca credentials, authenticates traders (Supabase
JWT), enforces pod permissions, submits orders, and writes everything to
Supabase. It is the only component that touches Alpaca keys or writes to the DB.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # fill in Supabase + Alpaca values
uvicorn app.main:app --reload --port 8000
```
Interactive docs at http://localhost:8000/docs.

## Endpoints
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | — | liveness |
| GET | `/portal` | — | serves the admin portal web UI |
| GET | `/me` | trader | profile + pod assignments |
| GET | `/pods` | trader | list pods (name resolution) |
| POST | `/orders` | trader (own pods) / admin | place an order, log the trade |
| POST | `/orders/cancel` | trader / admin | cancel an open order |
| GET | `/pods/{id}/account` | member / admin | live equity/cash |
| GET | `/pods/{id}/positions` | member / admin | live positions |
| GET | `/market/price`, `/market/bars` | trader | market data |
| POST | `/sync/{pod_id}` | member / admin | Alpaca → Supabase (positions, NAV, metrics) |
| POST | `/admin/login` | username/password | portal login → portal token |
| GET | `/admin/pods` | admin | pods + whether Alpaca is configured |
| POST | `/admin/pods` | admin | create pod (+ optional Alpaca creds) |
| POST | `/admin/pods/{id}/alpaca` | admin | set pod Alpaca creds |
| POST | `/admin/pods/{id}/capital` | admin | allocate capital (audited) |
| GET | `/admin/traders` | admin | list traders |
| POST | `/admin/traders` | admin | create rqfc account (Auth user + trader) |
| GET | `/admin/memberships` | admin | list assignments |
| POST/DELETE | `/admin/memberships` | admin | assign / remove a trader |

### Admin portal
`GET /portal` serves a self-contained web UI (`app/portal/index.html`) for
creating pods, rqfc accounts, Alpaca credentials, capital, and assignments — no
CLI needed. It logs in with `ADMIN_PORTAL_USERNAME` / `ADMIN_PORTAL_PASSWORD`
(default `elbow` / `grease`) and receives a portal token. Admin endpoints accept
**either** that portal token **or** a Supabase JWT whose trader has `is_admin`
(see `app/portal_auth.py`), so the portal and the Python admin client both work.

## How auth works
The client logs into Supabase Auth (email+password) and gets a JWT. It sends the
JWT as `Authorization: Bearer …`. `app/auth.py` verifies the signature with
`SUPABASE_JWT_SECRET` and maps `sub` → a `traders` row. `is_admin` and
`pod_memberships` gate every action.

## Alpaca credentials
`app/alpaca_client.py` resolves a pod's keys from `pod_alpaca_credentials`, or
falls back to `ALPACA_API_KEY`/`ALPACA_API_SECRET` from the env (handy for
validating a single pod). Keys never leave the backend.

## Layout
```
app/
  config.py         env/settings
  auth.py           JWT verification → trader
  db.py             Supabase service-role client + all writes
  alpaca_client.py  per-pod Alpaca access (orders, positions, history, data)
  metrics.py        NAV → risk/return metrics
  schemas.py        request models
  main.py           routes
scripts/seed_users.py   create sample Supabase Auth users + traders
```
