CREATE TABLE IF NOT EXISTS leaderboard_monthly_stats (
    org TEXT NOT NULL,
    month_key TEXT NOT NULL,
    user_login TEXT NOT NULL,
    merged_prs INTEGER NOT NULL DEFAULT 0,
    closed_prs INTEGER NOT NULL DEFAULT 0,
    reviews INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (org, month_key, user_login)
);

CREATE TABLE IF NOT EXISTS leaderboard_open_prs (
    org TEXT NOT NULL,
    user_login TEXT NOT NULL,
    open_prs INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (org, user_login)
);

CREATE TABLE IF NOT EXISTS leaderboard_pr_state (
    org TEXT NOT NULL,
    repo TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    author_login TEXT NOT NULL,
    state TEXT NOT NULL,
    merged INTEGER NOT NULL DEFAULT 0,
    closed_at INTEGER,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (org, repo, pr_number)
);

CREATE TABLE IF NOT EXISTS leaderboard_review_credits (
    org TEXT NOT NULL,
    repo TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    month_key TEXT NOT NULL,
    reviewer_login TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (org, repo, pr_number, month_key, reviewer_login)
);

CREATE TABLE IF NOT EXISTS leaderboard_backfill_state (
    org TEXT NOT NULL,
    month_key TEXT NOT NULL,
    next_page INTEGER NOT NULL DEFAULT 1,
    completed INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (org, month_key)
);

CREATE TABLE IF NOT EXISTS leaderboard_backfill_repo_done (
    org TEXT NOT NULL,
    month_key TEXT NOT NULL,
    repo TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (org, month_key, repo)
);

CREATE TABLE IF NOT EXISTS mentor_assignments (
    org TEXT NOT NULL,
    mentor_login TEXT NOT NULL,
    issue_repo TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    assigned_at INTEGER NOT NULL,
    mentee_login TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (org, issue_repo, issue_number)
);

CREATE TABLE IF NOT EXISTS mentors (
    github_username TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    specialties TEXT NOT NULL DEFAULT '[]',
    max_mentees INTEGER NOT NULL DEFAULT 3,
    active INTEGER NOT NULL DEFAULT 1,
    timezone TEXT NOT NULL DEFAULT '',
    referred_by TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    slack_username TEXT NOT NULL DEFAULT '',
    total_prs INTEGER NOT NULL DEFAULT 0,
    total_reviews INTEGER NOT NULL DEFAULT 0,
    total_comments INTEGER NOT NULL DEFAULT 0,
    last_rate_limit INTEGER NOT NULL DEFAULT 0,
    last_rate_remaining INTEGER NOT NULL DEFAULT 0,
    last_rate_used INTEGER NOT NULL DEFAULT 0,
    last_rate_reset_at INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS mentor_stats_cache (
    org TEXT NOT NULL,
    github_username TEXT NOT NULL,
    merged_prs INTEGER NOT NULL DEFAULT 0,
    reviews INTEGER NOT NULL DEFAULT 0,
    fetched_at INTEGER NOT NULL,
    PRIMARY KEY (org, github_username)
);

CREATE TABLE IF NOT EXISTS contributor_referrals (
    org TEXT NOT NULL,
    month_key TEXT NOT NULL,
    referrer_login TEXT NOT NULL,
    referred_login TEXT NOT NULL,
    repo TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (org, month_key, referrer_login, referred_login)
);

CREATE TABLE IF NOT EXISTS leaderboard_processed_comments (
    comment_id INTEGER NOT NULL PRIMARY KEY,
    processed_at INTEGER NOT NULL
);
