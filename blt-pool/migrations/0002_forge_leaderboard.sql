-- Forge source for the PR leaderboard (git.owaspblt.org/BLT pull requests).
--
-- GitHub-era rows stay as they are. Forge activity is added to the same
-- leaderboard_monthly_stats / leaderboard_open_prs rows (keyed by the GitHub login when the
-- README roster maps the forge account to one), so each person's totals combine both.
--
-- Write cost: ADD COLUMN with a constant default only changes the schema (SQLite does not
-- rewrite existing rows); the two tables and the index are created empty. A handful of
-- sqlite_master rows in all, no data rows.

-- PRs opened per author and month (0 for GitHub-era rows, which never counted them).
ALTER TABLE leaderboard_monthly_stats ADD COLUMN opened_prs INTEGER NOT NULL DEFAULT 0;

-- One row per forge pull: the ledger folder oid it was read at (the incremental cursor per
-- pull), what is shown on the page, and the contributions it added to the leaderboard
-- (JSON {"<month>|<login>|<field>": n, "open|<login>": 1}) so a change applies only the difference.
CREATE TABLE IF NOT EXISTS leaderboard_forge_pulls (
    org TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    oid TEXT NOT NULL,
    author_login TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    projects TEXT NOT NULL DEFAULT '',
    opened_at INTEGER NOT NULL DEFAULT 0,
    merged_at INTEGER NOT NULL DEFAULT 0,
    closed_at INTEGER NOT NULL DEFAULT 0,
    contrib TEXT NOT NULL DEFAULT '{}',
    updated_at INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (org, pr_number)
);

-- "Recent pull requests" on /leaderboard reads the newest rows through this index.
CREATE INDEX IF NOT EXISTS idx_leaderboard_forge_pulls_updated
    ON leaderboard_forge_pulls (org, updated_at);

-- One row per org: the ledger commit last read completely, the compact README roster and the
-- forge logins seen (JSON in state). Written only when it changes.
CREATE TABLE IF NOT EXISTS leaderboard_forge_cursor (
    org TEXT NOT NULL PRIMARY KEY,
    ledger_commit TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT '{}',
    updated_at INTEGER NOT NULL DEFAULT 0
);
