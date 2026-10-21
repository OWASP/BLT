-- Slack event ids already accepted, so a retried delivery is handled once. team_join used to
-- send a second (or third) welcome DM when Slack retried while the first was still running;
-- the dedupe read the events table, which the first delivery had not written yet.
-- Ids only (no payload); prune_event_log deletes rows older than 48 hours on the hourly cron.
CREATE TABLE IF NOT EXISTS slack_event_claims (
    event_id TEXT PRIMARY KEY,
    team_id TEXT DEFAULT '',
    event_type TEXT DEFAULT '',
    created_at TEXT NOT NULL
) WITHOUT ROWID;
