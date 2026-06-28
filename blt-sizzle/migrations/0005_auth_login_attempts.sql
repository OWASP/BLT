-- Migration number: 0005    2026-06-28
-- Track credential-login attempts for basic password brute-force throttling.

CREATE TABLE IF NOT EXISTS auth_login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_email_created
ON auth_login_attempts(email, created_at);
