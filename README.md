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

**Start here:** [`docs/RUNBOOK.md`](docs/RUNBOOK.md) to stand it all up and place a test trade.

---

### Week 1 Deliverables

#### Backend
- Create a class for each pod
- Each class inherits a base class that has methods:
  - view portfolio
  - place trade
  - view stats (sharpe, beta, etc.)
  - requires local env with user and pass (white listed internally)
- Package surfaces market data
- Posts trades to google sheet

#### Frontend
- Reads data from google sheet (make schema)
- Looks clean and is for anyone to maneuver publicly
- Can see all trades, history, metrics (sharpe, beta, etc.)
- Can aggregate or segregate by pod (or trader?)
- Hosted on github pages entirely
