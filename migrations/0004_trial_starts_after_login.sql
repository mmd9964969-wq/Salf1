-- Trial must begin only after the customer successfully logs in an account.
-- Existing unconnected users should not have a running trial.
alter table salf1_bot_users
  alter column trial_expires_at drop not null;

update salf1_bot_users
set trial_expires_at = null,
    salf_enabled = false
where account_connected = false;
