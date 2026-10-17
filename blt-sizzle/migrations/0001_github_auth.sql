-- Migration number: 0001    2026-03-21
-- Add GitHub OAuth support and encrypt all user PII columns

-- Rename plaintext PII columns to encrypted variants
ALTER TABLE users RENAME COLUMN email TO encrypted_email;
ALTER TABLE users RENAME COLUMN display_name TO encrypted_display_name;
ALTER TABLE users RENAME COLUMN slack_webhook_url TO encrypted_slack_webhook_url;

-- Add GitHub identity column
ALTER TABLE users ADD COLUMN github_id TEXT;

CREATE INDEX IF NOT EXISTS idx_users_github_id ON users(github_id);

-- Sessions table for GitHub OAuth tokens
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- OAuth CSRF state tokens
CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);