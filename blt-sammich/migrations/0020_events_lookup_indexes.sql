-- Indexes for the hot event lookups. Before these, the team_join duplicate checks matched
-- request_data with LIKE and read every event in the workspace (~27k rows per Slack event),
-- and the per-type counts and history scanned the same range.
CREATE INDEX IF NOT EXISTS idx_events_ws_type_webhook
ON events(workspace_id, event_type, webhook_event_id);

CREATE INDEX IF NOT EXISTS idx_events_ws_type_created
ON events(workspace_id, event_type, created_at);

-- Logo-hit verification has no workspace; it filters by type and recent created_at.
CREATE INDEX IF NOT EXISTS idx_events_type_created
ON events(event_type, created_at);

CREATE INDEX IF NOT EXISTS idx_channels_workspace_name
ON channels(workspace_id, channel_name);
