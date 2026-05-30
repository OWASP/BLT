-- Migration number: 0003    2026-03-21
-- 1. Encrypt github_issue_url in timelogs
-- 2. Add org encryption key support
-- 3. Add org membership approval workflow

-- Timelogs: add encrypted column alongside old one (old kept for migration safety,
-- app writes to encrypted column from now on)
ALTER TABLE timelogs ADD COLUMN encrypted_github_issue_url TEXT;

-- Copy existing plaintext values as-is so app can display them during transition;
-- the app will detect unencrypted legacy rows via the IV:data format check
UPDATE timelogs SET encrypted_github_issue_url = github_issue_url WHERE github_issue_url IS NOT NULL AND github_issue_url != '';

-- Organizations: store an org-level encryption key (encrypted with server's ENCRYPTION_KEY)
ALTER TABLE organizations ADD COLUMN encrypted_org_key TEXT;

-- User-org membership: support pending/approved states for join approval flow
ALTER TABLE user_organizations ADD COLUMN status TEXT NOT NULL DEFAULT 'approved';
ALTER TABLE user_organizations ADD COLUMN joined_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Index for efficient pending lookups
CREATE INDEX IF NOT EXISTS idx_user_orgs_status ON user_organizations(org_id, status);