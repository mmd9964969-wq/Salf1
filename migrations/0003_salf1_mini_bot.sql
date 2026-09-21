create table if not exists salf1_bot_users (
  telegram_user_id bigint primary key,
  username text,
  first_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  trial_expires_at timestamptz not null,
  tron_balance bigint not null default 0,
  salf_enabled boolean not null default false,
  account_connected boolean not null default false,
  referrer_user_id bigint references salf1_bot_users(telegram_user_id),
  referral_rewarded boolean not null default false,
  referral_count integer not null default 0
);

create index if not exists salf1_bot_users_referrer_idx
  on salf1_bot_users (referrer_user_id);

create index if not exists salf1_bot_users_enabled_idx
  on salf1_bot_users (salf_enabled, account_connected);

create table if not exists salf1_bot_referral_rewards (
  referred_user_id bigint primary key references salf1_bot_users(telegram_user_id) on delete cascade,
  referrer_user_id bigint not null references salf1_bot_users(telegram_user_id) on delete cascade,
  reward_tron bigint not null default 300,
  rewarded_at timestamptz not null default now()
);

create index if not exists salf1_bot_referral_rewards_referrer_idx
  on salf1_bot_referral_rewards (referrer_user_id);
