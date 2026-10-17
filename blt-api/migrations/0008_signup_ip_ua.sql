-- Migration number: 0008   2026-03-20T00:00:00.000Z
-- Add encrypted signup IP / User-Agent columns for abuse prevention.
-- signup_ip_hash is a blind index used to enforce one-account-per-IP.

ALTER TABLE users ADD COLUMN signup_ip_encrypted TEXT;
ALTER TABLE users ADD COLUMN signup_ip_hash TEXT;
ALTER TABLE users ADD COLUMN signup_ua_encrypted TEXT;

CREATE INDEX IF NOT EXISTS idx_users_signup_ip_hash ON users(signup_ip_hash);
