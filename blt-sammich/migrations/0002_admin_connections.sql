CREATE TABLE IF NOT EXISTS connected_workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL UNIQUE,
    team_name TEXT NOT NULL,
    icon_url TEXT DEFAULT '',
    installer_user_id TEXT DEFAULT '',
    bot_user_id TEXT DEFAULT '',
    invite_link TEXT DEFAULT '',
    github_org_url TEXT DEFAULT '',
    repo_count INTEGER DEFAULT 0,
    channel_count INTEGER DEFAULT 0,
    member_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'connected',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS managed_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT DEFAULT 'online',
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_connected_workspaces_status
ON connected_workspaces(status);

CREATE INDEX IF NOT EXISTS idx_managed_servers_status
ON managed_servers(status);
