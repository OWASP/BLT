
-- Migration number: 0002 	 2026-02-18T00:00:00.000Z

-- Issues table
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL CHECK(LENGTH(url) >= 1 AND LENGTH(url) <= 200),
    description TEXT NOT NULL CHECK(LENGTH(description) >= 1),
    markdown_description TEXT,
    label INTEGER,
    views INTEGER CHECK(views IS NULL OR (views >= -2147483648 AND views <= 2147483647)),
    verified BOOLEAN DEFAULT 0,
    score INTEGER CHECK(score IS NULL OR (score >= -2147483648 AND score <= 2147483647)),
    status TEXT CHECK(status IS NULL OR LENGTH(status) <= 10),
    user_agent TEXT CHECK(user_agent IS NULL OR LENGTH(user_agent) <= 255),
    ocr TEXT,
    screenshot TEXT,
    closed_date TIMESTAMP,
    github_url TEXT CHECK(github_url IS NULL OR LENGTH(github_url) <= 200),
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_hidden BOOLEAN DEFAULT 0,
    rewarded INTEGER DEFAULT 0 CHECK(rewarded >= 0 AND rewarded <= 2147483647),
    reporter_ip_address TEXT,
    cve_id TEXT CHECK(cve_id IS NULL OR LENGTH(cve_id) <= 16),
    cve_score TEXT,
    hunt INTEGER,
    domain INTEGER,
    user INTEGER,
    closed_by INTEGER,
    FOREIGN KEY (domain) REFERENCES domains(id) ON DELETE SET NULL
);

-- Issue screenshots table
CREATE TABLE IF NOT EXISTS issue_screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image TEXT NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    issue INTEGER NOT NULL,
    FOREIGN KEY (issue) REFERENCES issues(id) ON DELETE CASCADE
);

-- Issue tags junction table (many-to-many)
CREATE TABLE IF NOT EXISTS issue_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(issue_id, tag_id)
);

-- Issue team members junction table (many-to-many)
-- Note: FK to user will be added in migration 0003
CREATE TABLE IF NOT EXISTS issue_team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    UNIQUE(issue_id, user_id)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_issues_domain ON issues(domain);
CREATE INDEX IF NOT EXISTS idx_issues_user ON issues(user);
CREATE INDEX IF NOT EXISTS idx_issues_hunt ON issues(hunt);
CREATE INDEX IF NOT EXISTS idx_issues_created ON issues(created);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_verified ON issues(verified);
CREATE INDEX IF NOT EXISTS idx_issue_screenshots_issue ON issue_screenshots(issue);
CREATE INDEX IF NOT EXISTS idx_issue_tags_issue ON issue_tags(issue_id);
CREATE INDEX IF NOT EXISTS idx_issue_tags_tag ON issue_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_issue_team_members_issue ON issue_team_members(issue_id);
CREATE INDEX IF NOT EXISTS idx_issue_team_members_user ON issue_team_members(user_id);

-- Triggers to update modified timestamp automatically
CREATE TRIGGER IF NOT EXISTS update_issues_modified 
AFTER UPDATE ON issues
BEGIN
    UPDATE issues SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
