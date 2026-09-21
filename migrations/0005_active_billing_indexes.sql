-- Performance indexes for the active-customer billing path.
-- Only active, connected accounts participate in the per-minute charge query.

create index if not exists idx_salf1_bot_users_active_billing
  on salf1_bot_users (telegram_user_id)
  where salf_enabled = true and account_connected = true;

create index if not exists idx_salf1_bot_users_active_trial
  on salf1_bot_users (trial_expires_at)
  where salf_enabled = true and account_connected = true;

create index if not exists idx_salf1_referral_rewards_referrer
  on salf1_bot_referral_rewards (referrer_user_id);
