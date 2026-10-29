-- Soft delete for traders, so an admin can recover them. Deleting sets
-- deleted_at; the backend then refuses that trader's logins, sessions and API
-- keys. Pod assignments, API keys and trade history are kept, so clearing
-- deleted_at restores the account as it was.

alter table traders add column if not exists deleted_at timestamptz;

-- Same view as 001_schema.sql, minus deleted traders, so they drop off the
-- public pod rosters.
create or replace view members
  with (security_invoker = true) as
select
  t.id                       as id,
  m.pod_id                   as pod_id,
  t.display_name             as name,
  m.role                     as role,
  null::text                 as avatar_url,
  m.assigned_at::date        as joined_at,
  t.is_admin                 as is_admin
from pod_memberships m
join traders t on t.id = m.trader_id
where t.deleted_at is null;

grant select on members to anon, authenticated;
