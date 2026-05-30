-- Migration number: 0011   2026-05-30T00:00:00.000Z
-- User-owned API keys for programmatic access.

CREATE TABLE IF NOT EXISTS user_api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK(LENGTH(name) >= 1 AND LENGTH(name) <= 80),
    key_prefix TEXT NOT NULL CHECK(LENGTH(key_prefix) >= 8 AND LENGTH(key_prefix) <= 32),
    key_hash TEXT NOT NULL UNIQUE,
    scopes TEXT DEFAULT '[]',
    is_active BOOLEAN DEFAULT 1,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    revoked_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_id
    ON user_api_keys(user_id);

CREATE INDEX IF NOT EXISTS idx_user_api_keys_key_hash
    ON user_api_keys(key_hash);

CREATE INDEX IF NOT EXISTS idx_user_api_keys_active_user
    ON user_api_keys(user_id, is_active);
