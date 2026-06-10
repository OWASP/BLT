CREATE TABLE IF NOT EXISTS team_welcome_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL DEFAULT 'team_join',
    message_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_team_welcome_messages_team_id
ON team_welcome_messages(team_id, event_type);
