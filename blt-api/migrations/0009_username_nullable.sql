-- Migration number: 0009   2026-03-20T00:00:00.000Z
-- Make username nullable now that username_encrypted/username_hash are the
-- canonical identity columns. Existing rows keep their username value.
-- SQLite does not support ALTER COLUMN, so the table is rebuilt.

PRAGMA foreign_keys = OFF;

CREATE TABLE users_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    username_encrypted TEXT,
    username_hash TEXT,
    password TEXT NOT NULL CHECK(LENGTH(password) <= 128),
    title INTEGER CHECK(title IS NULL OR (title >= 1 AND title <= 5)),
    winnings REAL DEFAULT 0.0 CHECK(winnings >= 0),
    total_score INTEGER DEFAULT 0 CHECK(total_score >= 0),
    is_active BOOLEAN DEFAULT 1,
    is_staff BOOLEAN DEFAULT 0,
    is_superuser BOOLEAN DEFAULT 0,
    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_encrypted TEXT NOT NULL,
    email_hash TEXT NOT NULL UNIQUE,
    description_encrypted TEXT,
    user_avatar_encrypted TEXT,
    signup_ip_encrypted TEXT,
    signup_ip_hash TEXT,
    signup_ua_encrypted TEXT
);

INSERT INTO users_new (
    id, username, username_encrypted, username_hash,
    password, title, winnings, total_score,
    is_active, is_staff, is_superuser,
    date_joined, last_login, created, modified,
    email_encrypted, email_hash,
    description_encrypted, user_avatar_encrypted,
    signup_ip_encrypted, signup_ip_hash, signup_ua_encrypted
)
SELECT
    id, username, username_encrypted, username_hash,
    password, title, winnings, total_score,
    is_active, is_staff, is_superuser,
    date_joined, last_login, created, modified,
    email_encrypted, email_hash,
    description_encrypted, user_avatar_encrypted,
    signup_ip_encrypted, signup_ip_hash, signup_ua_encrypted
FROM users;

DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_username_hash ON users(username_hash);
CREATE INDEX IF NOT EXISTS idx_users_email_hash_unique ON users(email_hash);
CREATE INDEX IF NOT EXISTS idx_users_signup_ip_hash ON users(signup_ip_hash);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_total_score ON users(total_score);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created);

CREATE TRIGGER IF NOT EXISTS update_users_modified
AFTER UPDATE ON users
BEGIN
    UPDATE users SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

PRAGMA foreign_keys = ON;
