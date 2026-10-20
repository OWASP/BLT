-- PR review asks: when someone posts a pull request link in #owasp-blt and the PR has no
-- peer review, sammich asks in the thread. One row per (team, PR), written only when it asks.
-- pr_key is 'forge:owasp-blt/BLT#<n>' or 'github:<owner>/<repo>#<n>'. Times are Unix seconds.
-- asked_at gives the 24-hour dedupe (an upsert that only succeeds when the last ask is older);
-- nudge_due_at is set to asked_at + 24h and cleared once the follow-up check has run.
CREATE TABLE IF NOT EXISTS pr_review_asks (
    team_id TEXT NOT NULL,
    pr_key TEXT NOT NULL,
    app_id TEXT NOT NULL DEFAULT '',
    channel_id TEXT NOT NULL,
    thread_ts TEXT NOT NULL,
    pr_url TEXT NOT NULL,
    asked_at INTEGER NOT NULL,
    nudge_due_at INTEGER,
    nudged_at INTEGER,
    PRIMARY KEY (team_id, pr_key)
);

-- The blt-cron follow-up: WHERE nudge_due_at IS NOT NULL AND nudge_due_at <= ? reads only
-- the due rows (a partial index, so answered rows cost nothing).
CREATE INDEX IF NOT EXISTS idx_pr_review_asks_nudge_due
ON pr_review_asks(nudge_due_at) WHERE nudge_due_at IS NOT NULL;
