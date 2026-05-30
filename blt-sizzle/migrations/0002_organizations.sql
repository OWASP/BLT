-- Migration number: 0002    2026-03-21
-- Add GitHub organization support and store access token in sessions

-- Store encrypted access token so we can verify org membership
ALTER TABLE sessions ADD COLUMN encrypted_access_token TEXT;


-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_org_name TEXT UNIQUE NOT NULL,
    encrypted_slack_webhook_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orgs_name ON organizations(github_org_name);

-- User <-> Organization membership mapping
CREATE TABLE IF NOT EXISTS user_organizations (
    user_id TEXT NOT NULL,
    org_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, org_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_user_orgs_user ON user_organizations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_orgs_org ON user_organizations(org_id);

-- Tag check-ins with an org (NULL = personal / unfiled check-in)
ALTER TABLE checkins ADD COLUMN org_id INTEGER REFERENCES organizations(id);


CREATE INDEX IF NOT EXISTS idx_checkins_org_date ON checkins(org_id, checkin_date);