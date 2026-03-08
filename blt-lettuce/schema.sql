-- BLT-Lettuce D1 Database Schema
-- Run locally:  wrangler d1 execute BLT_DB --local --file=schema.sql
-- Run remote:   wrangler d1 execute BLT_DB --file=schema.sql

-- Users authenticated via "Sign in with Slack"
-- A single user can manage multiple workspaces
-- SECURITY NOTE: access_token stores the Slack user OAuth token. Consider
-- encrypting at-rest using a Worker secret key if your threat model requires
-- it. Restrict D1 read access to the Worker service binding only.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slack_user_id TEXT UNIQUE NOT NULL,
    team_id TEXT NOT NULL,
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    access_token TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Active login sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Slack workspaces that have had the bot installed
-- SECURITY NOTE: access_token stores the bot OAuth token in plaintext.
-- A compromised D1 read would allow full bot impersonation for that workspace.
-- Restrict D1 access to the Worker service binding and apply least-privilege
-- IAM policies. Consider application-layer encryption for high-security
-- deployments.
-- NOTE: Multiple bot/app installations per team are supported via composite key (team_id, app_id)
CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    app_id TEXT DEFAULT '',
    app_name TEXT DEFAULT '',
    app_icon_url TEXT DEFAULT '',
    manifest_yaml TEXT DEFAULT '',
    access_token TEXT NOT NULL,
    bot_user_id TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_team_app 
ON workspaces(team_id, app_id);

-- Junction table: which users manage which workspaces (many-to-many)
-- role: 'owner' (installed the bot) or 'admin'
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

-- Channels discovered per workspace (populated during scan)
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    member_count INTEGER DEFAULT 0,
    topic TEXT DEFAULT '',
    purpose TEXT DEFAULT '',
    is_private INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    UNIQUE(workspace_id, channel_id)
);

-- GitHub repositories attached to a workspace for user matching
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    repo_url TEXT NOT NULL,
    repo_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    language TEXT DEFAULT '',
    stars INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    UNIQUE(workspace_id, repo_url)
);

-- Bot activity events (team_join, command, etc.)
-- workspace_id is nullable to allow logging events from webhooks that arrive
-- before a workspace has been registered via the OAuth flow.
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    event_type TEXT NOT NULL,
    user_slack_id TEXT DEFAULT '',
    status TEXT DEFAULT 'success',
    created_at TEXT NOT NULL
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_events_workspace_created ON events(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_channels_workspace ON channels(workspace_id, member_count DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_workspaces_user ON user_workspaces(user_id);
CREATE INDEX IF NOT EXISTS idx_user_workspaces_workspace ON user_workspaces(workspace_id);
