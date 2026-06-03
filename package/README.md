# rqfc

Thin Python client for the RQFC fund trading backend.

Traders log in with credentials issued by an admin (Supabase Auth). The backend
holds each pod's Alpaca keys and submits trades on the trader's behalf — **no
Alpaca keys ever touch this client**. A pod is one Alpaca account; several
traders share a pod; admins can trade any pod and manage capital/membership.

See `../docs/ARCHITECTURE.md` and `../docs/RUNBOOK.md` for the full system.

## Install
```bash
pip install -e .          # or: pip install rqfc
```

## Configure
Point the client at your backend + Supabase (env vars, or pass to `login`):
```bash
export RQFC_BACKEND_URL=https://your-backend
export RQFC_SUPABASE_URL=https://<project>.supabase.co
export RQFC_SUPABASE_ANON_KEY=<anon-key>
```

## Trader usage
```python
import rqfc
rqfc.login("alice@rqfc.club", "password")

rqfc.whoami()                 # your profile + assigned pods

acct = rqfc.pod("Alpha Equities")   # by name or id; must be assigned
acct.buy("AAPL", 10)
acct.sell("AAPL", 5)
acct.short("TSLA", 3)
acct.dollar_buy("NVDA", 5000)
acct.account()                # live equity / cash / buying power
acct.positions()              # live positions
acct.price("AAPL")
acct.sync()                   # refresh the dashboard (positions, NAV, metrics)
```

## Admin usage
```python
rqfc.login("admin@rqfc.club", "password")
admin = rqfc.admin()

pod = admin.create_pod("Vol Arb", "options", capital=100000,
                       alpaca_api_key="PK...", alpaca_api_secret="...")
admin.list_traders()
admin.add_trader(pod["id"], trader_id, role="trader")
admin.allocate_capital(pod["id"], 150000)
admin.remove_trader(pod["id"], trader_id)
```

## Method reference
**Account** (`rqfc.pod(...)`): `buy`, `sell`, `short`, `cover`, `dollar_buy`,
`dollar_sell`, `cancel`, `account`, `positions`, `price`, `bars`, `sync`.

**Admin** (`rqfc.admin()`): `create_pod`, `set_alpaca`, `allocate_capital`,
`list_traders`, `add_trader`, `remove_trader`.
