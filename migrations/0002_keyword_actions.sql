create table if not exists keyword_actions (
  id bigserial primary key,
  owner_id text not null,
  name text not null,
  trigger_type text not null default 'contains',
  trigger_value text not null,
  scope text not null default 'all',
  conditions jsonb not null default '{}'::jsonb,
  actions jsonb not null default '[]'::jsonb,
  delay_min integer not null default 0,
  delay_max integer not null default 0,
  cooldown_seconds integer not null default 0,
  enabled boolean not null default true,
  execution_count integer not null default 0,
  last_executed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists keyword_actions_owner_idx
  on keyword_actions (owner_id);

create index if not exists keyword_actions_enabled_idx
  on keyword_actions (owner_id, enabled);

create index if not exists keyword_actions_trigger_idx
  on keyword_actions (owner_id, trigger_type, trigger_value);
