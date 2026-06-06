CREATE TABLE IF NOT EXISTS slack_apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT NOT NULL UNIQUE,
    app_name TEXT DEFAULT '',
    app_icon_url TEXT DEFAULT '',
    client_id TEXT DEFAULT '',
    client_secret TEXT DEFAULT '',
    signing_secret TEXT DEFAULT '',
    app_token TEXT DEFAULT '',
    manifest_yaml TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_slack_apps_app_id
ON slack_apps(app_id);
