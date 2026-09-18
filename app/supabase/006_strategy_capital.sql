-- Minimal per-strategy capital cap. Deliberately small: a hard dollar limit
-- on buy-side orders, enforced against a simple spend ledger (buy notional
-- minus sell notional for that strategy's own trades) — not mark-to-market,
-- not a strikes/escalation system. Broader risk management is a later pass.

alter table strategies add column if not exists allocated_capital numeric;

alter table trades add column if not exists strategy_id uuid references strategies(id) on delete set null;

create index if not exists trades_strategy_idx on trades (strategy_id) where strategy_id is not null;
