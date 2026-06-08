-- Portfolio accounting for live transparency.
-- Alpaca fills are authoritative; trades remain the public order log.

alter table trades
  add column if not exists filled_at timestamptz,
  add column if not exists realized_pnl numeric,
  add column if not exists fees numeric,
  add column if not exists multiplier numeric not null default 1,
  add column if not exists instrument_type text not null default 'equity',
  add column if not exists underlying_symbol text,
  add column if not exists option_expiration date,
  add column if not exists option_type text,
  add column if not exists option_strike numeric;

create table if not exists order_fills (
  id                 uuid primary key default gen_random_uuid(),
  pod_id             uuid not null references pods(id) on delete cascade,
  trader_id          uuid references traders(id) on delete set null,
  trade_id           uuid references trades(id) on delete set null,
  alpaca_order_id    text not null,
  fill_id            text,
  symbol             text not null,
  side               text not null check (side in ('buy','sell')),
  instrument_type    text not null default 'equity',
  underlying_symbol  text,
  quantity           numeric not null,
  price              numeric not null,
  multiplier         numeric not null default 1,
  notional           numeric not null,
  fees               numeric not null default 0,
  realized_pnl       numeric,
  filled_at          timestamptz not null,
  raw                jsonb,
  created_at         timestamptz not null default now(),
  unique (pod_id, alpaca_order_id, fill_id)
);

create index if not exists order_fills_pod_time_idx
  on order_fills (pod_id, filled_at desc);

create index if not exists order_fills_symbol_idx
  on order_fills (symbol, filled_at desc);

create table if not exists position_marks (
  pod_id             uuid not null references pods(id) on delete cascade,
  symbol             text not null,
  instrument_type    text not null default 'equity',
  underlying_symbol  text,
  quantity           numeric not null,
  avg_entry_price    numeric not null,
  current_price      numeric,
  multiplier         numeric not null default 1,
  market_value       numeric not null default 0,
  cost_basis         numeric not null default 0,
  realized_pnl       numeric not null default 0,
  unrealized_pnl     numeric not null default 0,
  total_pnl          numeric not null default 0,
  updated_at         timestamptz not null default now(),
  primary key (pod_id, symbol)
);

create index if not exists position_marks_pod_value_idx
  on position_marks (pod_id, market_value desc);

create table if not exists portfolio_marks (
  pod_id            uuid not null references pods(id) on delete cascade,
  marked_at         timestamptz not null default now(),
  cash              numeric,
  equity            numeric,
  portfolio_value   numeric,
  gross_notional    numeric not null default 0,
  net_notional      numeric not null default 0,
  realized_pnl      numeric not null default 0,
  unrealized_pnl    numeric not null default 0,
  total_pnl         numeric not null default 0,
  source            text not null default 'alpaca_and_market_data',
  primary key (pod_id, marked_at)
);

create index if not exists portfolio_marks_pod_time_idx
  on portfolio_marks (pod_id, marked_at desc);

alter table order_fills enable row level security;
alter table position_marks enable row level security;
alter table portfolio_marks enable row level security;

create policy "public read" on order_fills
  for select to anon, authenticated using (true);
create policy "public read" on position_marks
  for select to anon, authenticated using (true);
create policy "public read" on portfolio_marks
  for select to anon, authenticated using (true);

alter publication supabase_realtime add table order_fills;
alter publication supabase_realtime add table position_marks;
alter publication supabase_realtime add table portfolio_marks;
