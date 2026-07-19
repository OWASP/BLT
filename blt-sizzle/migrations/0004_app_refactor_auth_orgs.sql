-- Migration number: 0004    2026-06-28
-- App refactor foundation: email OTP auth, generic org metadata, roles, and org-scoped check-ins.
-- This is intentionally additive. It does not drop legacy GitHub OAuth columns yet so deployed data can migrate safely.

-- Email/session auth tables. Session tokens and OTPs are stored as HMAC hashes, never plaintext.
CREATE TABLE IF NOT EXISTS auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_hash TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_hash ON auth_sessions(session_hash);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS email_otps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'login',
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at DATETIME NOT NULL,
    consumed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_otps_email_purpose ON email_otps(email, purpose);
CREATE INDEX IF NOT EXISTS idx_email_otps_expires ON email_otps(expires_at);

-- User profile additions for email-first accounts. Existing encrypted_email remains for legacy rows.
ALTER TABLE users ADD COLUMN email TEXT;
ALTER TABLE users ADD COLUMN email_hash TEXT;
ALTER TABLE users ADD COLUMN password_hash TEXT;
ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active';
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

-- Generic organization metadata. Legacy github_org_name remains during transition and can be copied into slug.
ALTER TABLE organizations ADD COLUMN name TEXT;
ALTER TABLE organizations ADD COLUMN slug TEXT;
ALTER TABLE organizations ADD COLUMN description TEXT;
ALTER TABLE organizations ADD COLUMN created_by_user_id TEXT;
ALTER TABLE organizations ADD COLUMN default_timezone TEXT NOT NULL DEFAULT 'UTC';
ALTER TABLE organizations ADD COLUMN checkin_enabled INTEGER NOT NULL DEFAULT 1;

UPDATE organizations
SET slug = COALESCE(NULLIF(slug, ''), github_org_name),
    name = COALESCE(NULLIF(name, ''), github_org_name)
WHERE github_org_name IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_orgs_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_orgs_created_by ON organizations(created_by_user_id);

-- Membership role/approval metadata. Existing status/joined_at columns are created by 0003.
ALTER TABLE user_organizations ADD COLUMN role TEXT NOT NULL DEFAULT 'member';
ALTER TABLE user_organizations ADD COLUMN requested_at DATETIME;
ALTER TABLE user_organizations ADD COLUMN approved_by_user_id TEXT;
ALTER TABLE user_organizations ADD COLUMN approved_at DATETIME;

UPDATE user_organizations
SET role = CASE WHEN role IS NULL OR role = '' THEN 'member' ELSE role END,
    requested_at = COALESCE(requested_at, joined_at, CURRENT_TIMESTAMP),
    approved_at = CASE WHEN status = 'approved' THEN COALESCE(approved_at, joined_at, CURRENT_TIMESTAMP) ELSE approved_at END;

CREATE INDEX IF NOT EXISTS idx_user_orgs_role ON user_organizations(org_id, role);
CREATE INDEX IF NOT EXISTS idx_user_orgs_status_role ON user_organizations(org_id, status, role);

-- Check-in metadata for editable org-scoped daily records.
ALTER TABLE checkins ADD COLUMN updated_at DATETIME;

UPDATE checkins SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP);

CREATE INDEX IF NOT EXISTS idx_checkins_org_user_date ON checkins(org_id, user_id, checkin_date);
CREATE INDEX IF NOT EXISTS idx_checkins_user_org_date ON checkins(user_id, org_id, checkin_date);
