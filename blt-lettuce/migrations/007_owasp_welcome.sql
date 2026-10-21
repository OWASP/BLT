-- OWASP welcome bot (src/lettuce/welcome_bot.py). New, empty tables, so the indexes cost
-- nothing to build; no existing table is touched.
--
-- team_joins: one row per team_join in a welcome workspace: the join history and that
-- join's welcome outcome. The INSERT is also the Slack event claim: the partial unique
-- index on event_id makes a retried delivery insert nothing, so it is welcomed once.
-- welcome_status: pending -> sent | failed, or skipped (bot, deleted, already welcomed)
-- or disabled (WELCOME_ENABLED off: recorded, not DMed).
-- tracking_id is the unguessable id in the welcome's footer logo URL (/welcome-logo?tid=).
CREATE TABLE IF NOT EXISTS team_joins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_id TEXT NOT NULL DEFAULT '',
    joined_at TEXT NOT NULL,
    welcome_status TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    tracking_id TEXT NOT NULL DEFAULT '',
    dm_channel TEXT NOT NULL DEFAULT '',
    message_ts TEXT NOT NULL DEFAULT '',
    attempts INTEGER NOT NULL DEFAULT 0,
    sent_at TEXT NOT NULL DEFAULT '',
    delivered_at TEXT NOT NULL DEFAULT '',
    opened_at TEXT NOT NULL DEFAULT '',
    opened_via TEXT NOT NULL DEFAULT ''
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_joins_event
ON team_joins(event_id) WHERE event_id != '';

-- Health, report and history: one team's joins in a time window.
CREATE INDEX IF NOT EXISTS idx_team_joins_team_joined
ON team_joins(team_id, joined_at);

-- "Already welcomed in the last 30 days?" before each DM.
CREATE INDEX IF NOT EXISTS idx_team_joins_team_user
ON team_joins(team_id, user_id);

-- Delivery and logo-hit updates find the row by its tracking id.
CREATE INDEX IF NOT EXISTS idx_team_joins_tracking
ON team_joins(tracking_id) WHERE tracking_id != '';

-- welcome_state: a few small JSON values the cron writes and /health/welcome reads:
--   auth:<team_id>      the last auth.test result (hourly)
--   channels:<team_id>  public channels with the most members (daily)
CREATE TABLE IF NOT EXISTS welcome_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
) WITHOUT ROWID;
