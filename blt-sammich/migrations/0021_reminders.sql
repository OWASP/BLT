-- /setreminder: one row per reminder. Times are Unix seconds (UTC).
-- target_type is 'user' (a DM, also used for "me") or 'channel'.
-- status: pending -> sent | failed (after 3 attempts) | cancelled.
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    app_id TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    message TEXT NOT NULL,
    due_at INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL,
    sent_at INTEGER
);

-- The delivery job: WHERE status = 'pending' AND due_at <= ? ORDER BY due_at LIMIT 50
-- reads only the due rows.
CREATE INDEX IF NOT EXISTS idx_reminders_status_due
ON reminders(status, due_at);

-- /setreminder list, cancel and the 20-pending limit read one user's pending rows.
CREATE INDEX IF NOT EXISTS idx_reminders_team_user_status_due
ON reminders(team_id, user_id, status, due_at);
