-- Database schema for PR tracker
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_repo ON prs(repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_pr_number ON prs(pr_number);
