-- Migration number: 0010   2026-05-30T00:00:00.000Z
-- Phase-one auth foundation: email verification timestamp and provider identities.

ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS user_auth_identities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL CHECK(provider IN ('local', 'github')),
    provider_user_id TEXT NOT NULL,
    provider_username_encrypted TEXT,
    provider_email_encrypted TEXT,
    provider_email_hash TEXT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(provider, provider_user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_auth_identities_user_id
    ON user_auth_identities(user_id);

CREATE INDEX IF NOT EXISTS idx_user_auth_identities_provider
    ON user_auth_identities(provider);

CREATE INDEX IF NOT EXISTS idx_user_auth_identities_provider_email_hash
    ON user_auth_identities(provider, provider_email_hash);
