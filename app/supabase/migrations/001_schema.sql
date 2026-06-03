-- ============================================================
-- Fund Transparency Portal — Schema
-- Run in Supabase SQL editor (or supabase db push)
-- ============================================================

create extension if not exists "pgcrypto";

-- ── Tables ───────────────────────────────────────────────────

create table pods (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,
  asset_class      text not null,
  description      text,
  benchmark_symbol text not null default 'SPY',
  inception_date   date not null,
  starting_capital numeric not null,
  created_at       timestamptz not null default now()
);

create table members (
  id         uuid primary key default gen_random_uuid(),
  pod_id     uuid not null references pods(id) on delete cascade,
  name       text not null,
  role       text not null check (role in ('pm','trader')),
  avatar_url text,
  joined_at  date not null default current_date
);

create table trades (
  id              uuid primary key default gen_random_uuid(),
  pod_id          uuid not null references pods(id) on delete cascade,
  member_id       uuid references members(id),
  symbol          text not null,
  side            text not null check (side in ('buy','sell')),
  quantity        numeric not null,
  price           numeric not null,
  notional        numeric not null,
  asset_class     text not null,
  alpaca_order_id text unique,
  executed_at     timestamptz not null,
  created_at      timestamptz not null default now()
);
create index on trades (pod_id, executed_at desc);
create index on trades (executed_at desc);

create table positions (
  id               uuid primary key default gen_random_uuid(),
  pod_id           uuid not null references pods(id) on delete cascade,
  symbol           text not null,
  quantity         numeric not null,
  avg_entry_price  numeric not null,
  current_price    numeric,
  market_value     numeric,
  unrealized_pnl   numeric,
  updated_at       timestamptz not null default now(),
  unique (pod_id, symbol)
);

create table price_history (
  symbol text not null,
  date   date not null,
  close  numeric not null,
  primary key (symbol, date)
);

create table benchmark_prices (
  symbol text not null,
  date   date not null,
  close  numeric not null,
  primary key (symbol, date)
);

create table nav_history (
  pod_id       uuid not null references pods(id) on delete cascade,
  date         date not null,
  nav          numeric not null,
  cash         numeric not null default 0,
  daily_return numeric,
  primary key (pod_id, date)
);

create table metrics (
  pod_id            uuid not null references pods(id) on delete cascade,
  as_of_date        date not null,
  cumulative_return numeric,
  annualized_return numeric,
  volatility        numeric,
  sharpe            numeric,
  sortino           numeric,
  beta              numeric,
  alpha             numeric,
  max_drawdown      numeric,
  calmar            numeric,
  var_95            numeric,
  win_rate          numeric,
  trade_count       integer,
  primary key (pod_id, as_of_date)
);

create table config (
  key   text primary key,
  value jsonb not null
);

-- ── Row Level Security ────────────────────────────────────────

alter table pods             enable row level security;
alter table members          enable row level security;
alter table trades           enable row level security;
alter table positions        enable row level security;
alter table price_history    enable row level security;
alter table benchmark_prices enable row level security;
alter table nav_history      enable row level security;
alter table metrics          enable row level security;
alter table config           enable row level security;

create policy "public read" on pods             for select to anon using (true);
create policy "public read" on members          for select to anon using (true);
create policy "public read" on trades           for select to anon using (true);
create policy "public read" on positions        for select to anon using (true);
create policy "public read" on price_history    for select to anon using (true);
create policy "public read" on benchmark_prices for select to anon using (true);
create policy "public read" on nav_history      for select to anon using (true);
create policy "public read" on metrics          for select to anon using (true);
create policy "public read" on config           for select to anon using (true);

-- ── Config seed ───────────────────────────────────────────────

insert into config (key, value) values
  ('risk_free_rate',        '0.05'),
  ('trading_days_per_year', '252');

-- ── Realtime ─────────────────────────────────────────────────
-- In Supabase dashboard: Database → Replication → enable for trades, positions, nav_history
-- Or run:
-- alter publication supabase_realtime add table trades;
-- alter publication supabase_realtime add table positions;
-- alter publication supabase_realtime add table nav_history;
