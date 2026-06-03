# Fund Transparency Portal — Architecture & Build Plan

A **public, read-only** web portal that exposes the live state of a multi-pod
quantitative fund. Anyone on the internet can view each pod's current value,
the trades being executed (with timestamps and attribution), open positions,
and risk/performance metrics (alpha, beta, Sharpe, and more).

This document is the single source of truth for **another agent to build the
stack end to end.** It specifies the architecture, data model, write contract,
metric definitions, frontend structure, and deployment pipeline.

---

## 1. Concept

The fund is organized into **pods**. Each pod trades a single asset class:

- **Equities**
- **Options**
- **Fixed Income**
- (extensible — Crypto, FX, Futures, etc.)

Each pod has **one Portfolio Manager (PM)** and **2–3 traders**. Traders execute
trades through a separate backend trading engine (see §4). This portal does
**not** execute trades and has **no admin/login UI** — it only *displays* what
the engine writes to the database.

### Design principles

1. **Fully public & transparent** — no authentication required to view anything.
2. **Read-only frontend** — the SPA never writes. All writes come from the
   trading engine using a privileged key the browser never sees.
3. **Static-deployable** — runs as a pure SPA on GitHub Pages (no server).
4. **Live** — new trades appear in real time; valuations refresh on a schedule.
5. **Precomputed metrics** — heavy math runs in Supabase, not per-visitor.

---

## 2. High-Level Architecture

```
┌──────────────────────────┐
│   Trading Engine (you)   │   Python package wrapping Alpaca Markets.
│   - executes trades      │   Runs off-platform (trader machines / a server).
│   - wraps Alpaca API     │   Holds the Supabase SERVICE-ROLE key.
└────────────┬─────────────┘
             │  insert trades, upsert positions  (service role — bypasses RLS)
             ▼
┌──────────────────────────────────────────────────────────────────┐
│                          SUPABASE                                  │
│                                                                    │
│  Postgres            Edge Functions (scheduled via pg_cron)        │
│  ─────────           ───────────────────────────────────          │
│  pods                sync-prices    → pull Alpaca market data,     │
│  members                              mark positions to market     │
│  trades              compute-nav     → roll positions+cash → NAV   │
│  positions           compute-metrics → alpha/beta/sharpe/etc.      │
│  price_history                                                     │
│  nav_history         Realtime: broadcast INSERTs on `trades`,      │
│  benchmark_prices               `positions`, `nav_history`         │
│  metrics                                                           │
│  config              Row Level Security: anon = SELECT only        │
└────────────┬─────────────────────────────────────────────────────┘
             │  anon key + RLS (read-only)        ▲ realtime subscribe
             ▼                                     │
┌──────────────────────────────────────────────────────────────────┐
│              FRONTEND SPA  (Vite + React + TS)                     │
│              deployed to GitHub Pages                              │
│  - Fund overview, pod detail, trade blotter, metrics, charts       │
│  - @supabase/supabase-js (anon key, public-safe)                   │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
        Public viewers (no login)
```

**Trust boundary:** the `service_role` key lives **only** in the trading engine.
The frontend ships with the `anon` key, which is safe to expose because RLS
restricts the `anon` role to `SELECT`.

---

## 3. Backend — Supabase

### 3.1 Tech

- **Postgres** (Supabase managed) — primary store.
- **Row Level Security (RLS)** — public read, no public write.
- **Edge Functions** (Deno/TypeScript) — scheduled price sync + metric computation.
- **`pg_cron`** — schedules the Edge Functions / SQL jobs.
- **Realtime** — pushes new trades/positions/NAV to connected browsers.

### 3.2 Data model

> Use UUID primary keys (`gen_random_uuid()`), `timestamptz` for all times
> (store UTC), and `numeric` for money/quantities (never floats for money).

```sql
-- A pod = one asset-class trading team
create table pods (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,                 -- "Volatility Arb", "Rates"
  asset_class      text not null,                 -- 'equities'|'options'|'fixed_income'|...
  description      text,
  benchmark_symbol text not null default 'SPY',   -- per-pod benchmark (see §6)
  inception_date   date not null,
  starting_capital numeric not null,              -- AUM allocated at inception
  created_at       timestamptz not null default now()
);

-- PM and traders belonging to a pod
create table members (
  id         uuid primary key default gen_random_uuid(),
  pod_id     uuid not null references pods(id) on delete cascade,
  name       text not null,
  role       text not null check (role in ('pm','trader')),
  avatar_url text,
  joined_at  date not null default current_date
);

-- Every executed trade (the live blotter)
create table trades (
  id              uuid primary key default gen_random_uuid(),
  pod_id          uuid not null references pods(id) on delete cascade,
  member_id       uuid references members(id),      -- who executed it
  symbol          text not null,
  side            text not null check (side in ('buy','sell')),
  quantity        numeric not null,
  price           numeric not null,                 -- fill price
  notional        numeric not null,                 -- quantity * price (signed by side optional)
  asset_class     text not null,
  alpaca_order_id text unique,                       -- idempotency from the engine
  executed_at     timestamptz not null,             -- fill time from Alpaca
  created_at      timestamptz not null default now()
);
create index on trades (pod_id, executed_at desc);

-- Current open positions, marked to market by sync-prices
create table positions (
  id               uuid primary key default gen_random_uuid(),
  pod_id           uuid not null references pods(id) on delete cascade,
  symbol           text not null,
  quantity         numeric not null,                -- net; 0 rows may be pruned
  avg_entry_price  numeric not null,
  current_price    numeric,                         -- last mark
  market_value     numeric,                         -- quantity * current_price
  unrealized_pnl   numeric,
  updated_at       timestamptz not null default now(),
  unique (pod_id, symbol)
);

-- Daily close prices for everything we hold or benchmark against
create table price_history (
  symbol text not null,
  date   date not null,
  close  numeric not null,
  primary key (symbol, date)
);

-- Benchmark series (kept separate for clarity; same shape)
create table benchmark_prices (
  symbol text not null,
  date   date not null,
  close  numeric not null,
  primary key (symbol, date)
);

-- Daily fund value per pod (the NAV time series powering value + returns)
create table nav_history (
  pod_id       uuid not null references pods(id) on delete cascade,
  date         date not null,
  nav          numeric not null,                    -- positions market value + cash
  cash         numeric not null default 0,
  daily_return numeric,                             -- (nav_t / nav_{t-1}) - 1
  primary key (pod_id, date)
);

-- Precomputed risk/performance metrics per pod (latest + history)
create table metrics (
  pod_id            uuid not null references pods(id) on delete cascade,
  as_of_date        date not null,
  cumulative_return numeric,   -- since inception
  annualized_return numeric,
  volatility        numeric,   -- annualized stdev of daily returns
  sharpe            numeric,
  sortino           numeric,
  beta              numeric,   -- vs pod benchmark
  alpha             numeric,   -- Jensen's alpha, annualized
  max_drawdown      numeric,   -- most negative peak-to-trough
  calmar            numeric,   -- annualized_return / |max_drawdown|
  var_95            numeric,   -- 1-day historical VaR, 95%
  win_rate          numeric,   -- fraction of positive-return days
  trade_count       integer,
  primary key (pod_id, as_of_date)
);

-- Global tunables (risk-free rate, etc.)
create table config (
  key   text primary key,
  value jsonb not null
);
-- seed: ('risk_free_rate', '0.05'), ('trading_days_per_year', '252')
```

### 3.3 Row Level Security

```sql
-- Enable RLS on every table, then grant anon read-only.
alter table pods             enable row level security;
alter table members          enable row level security;
alter table trades           enable row level security;
alter table positions        enable row level security;
alter table price_history    enable row level security;
alter table benchmark_prices enable row level security;
alter table nav_history      enable row level security;
alter table metrics          enable row level security;
alter table config           enable row level security;

-- Public read policy (repeat per table)
create policy "public read" on pods for select to anon using (true);
-- ... identical policy on each table ...

-- No insert/update/delete policies for anon ⇒ writes are denied.
-- The trading engine uses the service_role key, which BYPASSES RLS.
```

### 3.4 Realtime

Enable Realtime on `trades`, `positions`, and `nav_history` (add them to the
`supabase_realtime` publication). The frontend subscribes to `INSERT`/`UPDATE`
events to live-update the blotter, position table, and value tickers.

### 3.5 Scheduled jobs (Edge Functions + pg_cron)

| Function          | Schedule                  | Responsibility                                                                 |
|-------------------|---------------------------|--------------------------------------------------------------------------------|
| `sync-prices`     | every 5–15 min, market hrs | Pull latest prices (Alpaca market-data API) for held + benchmark symbols → `price_history` / `benchmark_prices`; update `positions.current_price`, `market_value`, `unrealized_pnl`. |
| `compute-nav`     | daily after close (or end of `sync-prices`) | For each pod: NAV = Σ position market values + cash → upsert `nav_history`, compute `daily_return`. |
| `compute-metrics` | daily after `compute-nav` | From `nav_history` + `benchmark_prices` + `config.risk_free_rate`, compute all metrics (§6) → upsert `metrics`. |

`pg_cron` schedules these via `cron.schedule(...)` calling the function over HTTP
(`net.http_post`) or running SQL directly. Market data comes from the **same
Alpaca account** the trading engine uses (data API), so no extra vendor needed.

---

## 4. Write Contract (Trading Engine ↔ Supabase)

> This section is the **interface** between your Alpaca-wrapper package and this
> system. The frontend depends on these tables being populated as described.
> Build the engine to honor it; the building agent should NOT build the engine,
> only ensure the schema matches.

On each fill, the engine (using the `service_role` key) must:

1. **Insert a `trades` row** with `alpaca_order_id` set (unique → idempotent
   retries), `member_id` of the executing trader, `executed_at` = Alpaca fill
   time, and correct `pod_id`/`asset_class`.
2. **Upsert the affected `positions` row** (`on conflict (pod_id, symbol)`):
   recompute net `quantity` and `avg_entry_price`; prune rows that net to 0.
3. Leave price marks, NAV, and metrics to the scheduled jobs (§3.5).

Minimal engine-side write (pseudo-SQL):

```sql
insert into trades (pod_id, member_id, symbol, side, quantity, price, notional,
                    asset_class, alpaca_order_id, executed_at)
values (:pod, :member, :sym, :side, :qty, :px, :qty*:px, :ac, :order_id, :filled_at)
on conflict (alpaca_order_id) do nothing;
```

The engine never touches `metrics`, `nav_history`, or `price_history` for
benchmarks — those are derived.

---

## 5. Frontend — Vite + React + TypeScript

### 5.1 Stack

| Concern         | Choice                                              |
|-----------------|-----------------------------------------------------|
| Build / SPA     | **Vite + React 18 + TypeScript**                    |
| Routing         | **react-router-dom** with `HashRouter` (GH Pages safe) |
| Data layer      | **@supabase/supabase-js** + **@tanstack/react-query** |
| Realtime        | Supabase channels → invalidate React Query caches   |
| Styling         | **Tailwind CSS** + **shadcn/ui**                    |
| Charts          | **Recharts** (metrics/NAV) and/or **lightweight-charts** (TradingView) for price/NAV time series |
| Tables          | **@tanstack/react-table**                           |
| Dates           | **date-fns**                                        |
| Validation      | **zod** schemas for every Supabase row type         |
| Numbers         | a small `formatCurrency` / `formatPct` util         |

### 5.2 Routes / pages

| Route        | Page              | Contents                                                                                  |
|--------------|-------------------|-------------------------------------------------------------------------------------------|
| `/`          | **Fund Overview** | Total AUM, fund-wide aggregate metrics, pod cards (value, day P&L, sparkline), global recent-trades feed (live). |
| `/pod/:id`   | **Pod Detail**    | Header (name, asset class, PM + traders), NAV chart, current positions table (live marks), trade blotter (live), metrics panel, benchmark overlay. |
| `/trades`    | **Trade Blotter** | All trades, filterable by pod / member / symbol / date; live-appending.                    |
| `/about`     | **Methodology**   | How metrics are computed, benchmark/risk-free choices, data freshness, transparency note.  |

### 5.3 Suggested structure

```
src/
  lib/
    supabase.ts        // createClient(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)
    formatters.ts
    metrics.ts         // shared metric labels/descriptions (definitions in §6)
  types/
    db.ts              // zod schemas + inferred TS types per table
  hooks/
    usePods.ts         // react-query queries
    usePodTrades.ts
    useRealtimeTrades.ts   // subscribe → queryClient.invalidate / optimistic prepend
    useMetrics.ts
  components/
    PodCard.tsx
    TradeBlotter.tsx
    PositionsTable.tsx
    NavChart.tsx
    MetricsPanel.tsx
    MetricTile.tsx
    MemberList.tsx
  pages/
    Overview.tsx
    PodDetail.tsx
    Trades.tsx
    About.tsx
  App.tsx              // HashRouter + routes + layout
  main.tsx
```

### 5.4 Realtime pattern

```ts
// useRealtimeTrades.ts (sketch)
useEffect(() => {
  const ch = supabase
    .channel('trades')
    .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'trades' },
        (payload) => queryClient.invalidateQueries({ queryKey: ['trades'] }))
    .subscribe();
  return () => { supabase.removeChannel(ch); };
}, []);
```

### 5.5 Environment

```
# .env (local) / GitHub Actions secrets (CI)
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-public-key>   # safe to ship; RLS enforces read-only
```

The **anon key is meant to be public**; never put the `service_role` key in the
frontend or in any committed file.

---

## 6. Metric Definitions

Let `r_t` = daily pod return (from `nav_history.daily_return`), `b_t` =
benchmark daily return, `rf` = daily risk-free rate (`config.risk_free_rate / 252`),
and `N = 252` trading days/year.

| Metric              | Formula                                                                          |
|---------------------|----------------------------------------------------------------------------------|
| Cumulative return   | `∏(1 + r_t) − 1` since inception                                                 |
| Annualized return   | `(1 + cumulative)^(N / days) − 1`                                                 |
| Volatility (ann.)   | `stdev(r_t) * √N`                                                                 |
| Sharpe              | `(mean(r_t) − rf) / stdev(r_t) * √N`                                              |
| Sortino             | `(mean(r_t) − rf) / stdev(min(r_t − rf, 0)) * √N`                                 |
| Beta                | `Cov(r_t, b_t) / Var(b_t)`                                                        |
| Alpha (Jensen, ann.)| `(mean(r_t) − [rf + β·(mean(b_t) − rf)]) * N`                                     |
| Max drawdown        | `min_t( NAV_t / running_max(NAV) − 1 )`                                           |
| Calmar              | `annualized_return / |max_drawdown|`                                             |
| VaR 95% (1-day)     | `−percentile(r_t, 5%)` (historical)                                              |
| Win rate            | `count(r_t > 0) / count(r_t)`                                                     |

### Benchmarks per asset class (`pods.benchmark_symbol`)

| Asset class    | Default benchmark            |
|----------------|------------------------------|
| Equities       | `SPY`                        |
| Options        | `SPY` (or a vol proxy)       |
| Fixed Income   | `AGG` (or `TLT`)             |
| Crypto         | `BTC`                        |

Risk-free rate is a single tunable in `config` (e.g. 5%); document the value and
date on `/about`. Compute with a minimum return history (e.g. ≥ 20 days) before
showing Sharpe/beta to avoid noise; otherwise display "accumulating history."

---

## 7. Deployment — GitHub Pages

GitHub Pages serves static files only, which fits a Vite SPA.

1. **Base path** — in `vite.config.ts` set `base: '/fund-frontend/'` (the repo
   name). If served from a custom domain or `<user>.github.io`, set `base: '/'`.
2. **Routing** — use `HashRouter` so deep links (`/#/pod/123`) work without
   server rewrites. (Alternative: `BrowserRouter` + a `404.html` redirect hack.)
3. **CI/CD** — GitHub Actions builds and deploys via the Pages action:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push: { branches: [main] }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm run build
        env:
          VITE_SUPABASE_URL: ${{ secrets.VITE_SUPABASE_URL }}
          VITE_SUPABASE_ANON_KEY: ${{ secrets.VITE_SUPABASE_ANON_KEY }}
      - uses: actions/upload-pages-artifact@v3
        with: { path: dist }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: ${{ steps.d.outputs.page_url }} }
    steps:
      - id: d
        uses: actions/deploy-pages@v4
```

Add `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` as repo **secrets**; they're
injected at build time.

---

## 8. Security Notes

- **Only** the `anon` key ships to the browser; RLS makes it read-only.
- The `service_role` key lives **only** in the trading engine's environment.
- No PII beyond display names/avatars of fund members.
- Treat all displayed numbers as derived/cached; the `/about` page states data
  freshness and methodology for genuine transparency.

---

## 9. Build Plan (phased — for the implementing agent)

**Phase 0 — Scaffold.** `npm create vite@latest` (react-ts); add Tailwind,
shadcn/ui, react-router, react-query, supabase-js, zod. Set `base` + `HashRouter`.

**Phase 1 — Supabase schema.** Create project; run the §3.2 DDL; enable RLS +
public-read policies (§3.3); enable Realtime (§3.4); seed `config`, a couple of
demo `pods` + `members`, and synthetic `trades`/`nav_history` for development.

**Phase 2 — Read-only frontend (static data).** Build types/zod (`types/db.ts`),
the supabase client, and all four pages against seeded data. Charts + tables
render real rows.

**Phase 3 — Realtime.** Wire `useRealtimeTrades` and live position/NAV updates.

**Phase 4 — Scheduled compute.** Implement `sync-prices`, `compute-nav`,
`compute-metrics` Edge Functions; schedule with `pg_cron`; verify metrics match
the §6 formulas against hand-computed values on seed data.

**Phase 5 — Deploy.** Add the Actions workflow + secrets; ship to GitHub Pages;
verify deep links and realtime over HTTPS.

**Out of scope (separate repo):** the Alpaca-wrapper trading engine. This portal
only consumes what that engine writes per the §4 contract.

---

## 10. Tech Stack Summary

| Layer            | Technology                                                        |
|------------------|-------------------------------------------------------------------|
| Frontend         | Vite, React 18, TypeScript, Tailwind, shadcn/ui                   |
| Data / charts    | @supabase/supabase-js, @tanstack/react-query, react-table, Recharts / lightweight-charts, zod, date-fns |
| Backend          | Supabase (Postgres, RLS, Edge Functions, Realtime, pg_cron)      |
| Market data      | Alpaca Markets data API                                           |
| Trade execution  | External Python Alpaca-wrapper engine (separate repo)            |
| Hosting / CI     | GitHub Pages + GitHub Actions                                    |
```
