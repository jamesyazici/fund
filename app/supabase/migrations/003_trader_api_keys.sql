-- Backend-owned trader API keys.
-- Plaintext keys are shown once by the backend and never stored.

create table if not exists trader_api_keys (
  id           uuid primary key default gen_random_uuid(),
  trader_id    uuid not null references traders(id) on delete cascade,
  name         text not null,
  key_prefix   text not null,
  key_hash     text not null unique,
  revoked_at   timestamptz,
  last_used_at timestamptz,
  created_at   timestamptz not null default now()
);

create index if not exists trader_api_keys_trader_created_idx
  on trader_api_keys (trader_id, created_at desc);

create index if not exists trader_api_keys_active_hash_idx
  on trader_api_keys (key_hash)
  where revoked_at is null;

alter table trader_api_keys enable row level security;
-- Intentionally no public policies. The backend service role owns all access.
