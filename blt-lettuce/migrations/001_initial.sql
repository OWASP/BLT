-- BLT-Lettuce D1 initial migration
-- Note: user/auth tables were intentionally removed.

CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    icon_url TEXT DEFAULT '',
    app_id TEXT DEFAULT '',
    app_name TEXT DEFAULT '',
    app_icon_url TEXT DEFAULT '',
    manifest_yaml TEXT DEFAULT '',
    installer_slack_user_id TEXT DEFAULT '',
    installer_name TEXT DEFAULT '',
    channel_count INTEGER DEFAULT 0,
    member_count INTEGER DEFAULT 0,
    access_token TEXT NOT NULL,
    bot_user_id TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_team_app
ON workspaces(team_id, app_id);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    member_count INTEGER DEFAULT 0,
    topic TEXT DEFAULT '',
    purpose TEXT DEFAULT '',
    is_private INTEGER DEFAULT 0,
    send_join_message INTEGER DEFAULT 0,
    join_message_id INTEGER DEFAULT NULL,
    join_delivery_mode TEXT DEFAULT 'dm',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    UNIQUE(workspace_id, channel_id)
);

CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    repo_url TEXT NOT NULL,
    repo_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    language TEXT DEFAULT '',
    stars INTEGER DEFAULT 0,
    source_type TEXT DEFAULT 'repo',
    metadata_json TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    UNIQUE(workspace_id, repo_url)
);

CREATE TABLE IF NOT EXISTS github_organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    org_login TEXT NOT NULL,
    org_type TEXT DEFAULT 'org',
    metadata_json TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    UNIQUE(workspace_id, org_login)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    event_type TEXT NOT NULL,
    user_slack_id TEXT DEFAULT '',
    channel_name TEXT DEFAULT '',
    channel_id TEXT DEFAULT '',
    request_data TEXT DEFAULT '',
    verified INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS join_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    message_text TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
);

CREATE INDEX IF NOT EXISTS idx_events_workspace_created
ON events(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_channels_workspace
ON channels(workspace_id, member_count DESC);

CREATE INDEX IF NOT EXISTS idx_join_messages_workspace
ON join_messages(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_github_orgs_workspace
ON github_organizations(workspace_id, org_login);
