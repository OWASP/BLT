CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slack_user_id TEXT NOT NULL UNIQUE,
    team_id TEXT DEFAULT '',
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    access_token TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    workspace_id INTEGER NOT NULL,
    role TEXT DEFAULT 'owner',
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    UNIQUE(user_id, workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_user_workspaces_user
ON user_workspaces(user_id);

CREATE INDEX IF NOT EXISTS idx_user_workspaces_workspace
ON user_workspaces(workspace_id);
