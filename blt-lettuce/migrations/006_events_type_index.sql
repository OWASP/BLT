-- The cron's activity markers read the newest event of a type per workspace. With only
-- (workspace_id, created_at) they scanned every event in the workspace on each run.
CREATE INDEX IF NOT EXISTS idx_events_ws_type_created
ON events(workspace_id, event_type, created_at);
