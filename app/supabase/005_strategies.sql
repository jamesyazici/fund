-- Strategy deployments: a bundle a trader submitted for a pod (`rqfc deploy`),
-- and its lifecycle as tracked by the VM supervisor.
--
-- The bundle is stored as base64 text rather than bytea to avoid PostgREST's
-- bytea-encoding edge cases from the Python client — simplest reliable path,
-- fine at the sizes these bundles are (capped at 2 MB by the backend).
--
-- Backend-owned only: no public policies, no trader/admin writes except
-- through the /strategies and /internal/strategies endpoints (service role).

create table if not exists strategies (
  id           uuid primary key default gen_random_uuid(),
  pod_id       uuid not null references pods(id) on delete cascade,
  trader_id    uuid not null references traders(id) on delete cascade,
  name         text not null,
  status       text not null default 'pending'
                 check (status in ('pending', 'running', 'stopped', 'failed')),
  status_detail text,
  bundle_b64   text not null,
  bundle_size  integer not null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists strategies_pod_status_idx on strategies (pod_id, status);
create index if not exists strategies_pending_idx on strategies (created_at) where status = 'pending';

create table if not exists strategy_logs (
  id           uuid primary key default gen_random_uuid(),
  strategy_id  uuid not null references strategies(id) on delete cascade,
  line         text not null,
  logged_at    timestamptz not null default now()
);

create index if not exists strategy_logs_strategy_time_idx on strategy_logs (strategy_id, logged_at desc);

alter table strategies enable row level security;
alter table strategy_logs enable row level security;
-- Intentionally no public policies — service role (the backend) only.
