-- Database schema for PR tracker
-- Note: For existing databases, the application automatically migrates 
-- by checking for missing columns and adding them with ALTER TABLE.
-- This ensures backward compatibility when upgrading to newer versions.
CREATE TABLE IF NOT EXISTS prs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_url TEXT NOT NULL UNIQUE,
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    title TEXT,
    state TEXT,
    is_merged INTEGER DEFAULT 0,
    mergeable_state TEXT,
    files_changed INTEGER DEFAULT 0,
    author_login TEXT,
    author_avatar TEXT,
    checks_passed INTEGER DEFAULT 0,
    checks_failed INTEGER DEFAULT 0,
    checks_skipped INTEGER DEFAULT 0,
    review_status TEXT,
    last_updated_at TEXT,
    last_refreshed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_repo ON prs(repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_pr_number ON prs(pr_number);

-- Migration for existing databases (if needed manually)
-- Run this if the automatic migration in init_database_schema fails:
-- ALTER TABLE prs ADD COLUMN last_refreshed_at TEXT;
