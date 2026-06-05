# Fund (to be named)

## Rahul Rajkumar & James Yazici

A transparent, multi-pod paper-trading fund for RQFC.

- **Pod** = one Alpaca account (a strategy team). **Trader** = one rqfc account.
  Several traders share a pod; admins manage pods, traders, and capital.
- Traders authenticate (Supabase Auth) and trade through a backend that holds
  the Alpaca keys — keys never reach a trader's machine.

### Repo layout
| Dir | What |
|---|---|
| `app/` | React + Vite dashboard (public, read-only). Deploys to GitHub Pages. |
| `backend/` | FastAPI service: auth, permissions, Alpaca order execution, DB writes. |
| `package/` | `rqfc` — thin Python client traders/admins use. |
| `app/supabase/migrations/` | Postgres schema + demo seed. |
| `docs/` | `ARCHITECTURE.md` (design), `RUNBOOK.md` (end-to-end setup). |
