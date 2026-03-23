CREATE TABLE IF NOT EXISTS slack_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_kind TEXT NOT NULL,
    slack_type TEXT,
    command_name TEXT,
    team_id TEXT,
    user_id TEXT,
    channel_id TEXT,
    payload_json TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_slack_activity_received_at
ON slack_activity(received_at);

CREATE TABLE IF NOT EXISTS workspace_installations (
    team_id TEXT PRIMARY KEY,
    installer_user_id TEXT NOT NULL,
    installed_at TEXT NOT NULL
);