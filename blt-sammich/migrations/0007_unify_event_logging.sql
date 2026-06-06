ALTER TABLE events ADD COLUMN slack_response_data TEXT DEFAULT '';

CREATE TABLE IF NOT EXISTS slack_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_kind TEXT NOT NULL,
    slack_type TEXT,
    command_name TEXT,
    team_id TEXT,
    user_id TEXT,
    channel_id TEXT,
    payload_json TEXT NOT NULL,
    received_at TEXT NOT NULL
);

INSERT INTO events (
    workspace_id,
    event_type,
    user_slack_id,
    channel_id,
    slack_team_id,
    request_data,
    verified,
    status,
    created_at,
    webhook_body_type
)
SELECT
    w.id,
    CASE
        WHEN sa.activity_kind = 'slash_command' THEN 'Command'
        WHEN sa.slack_type = 'team_join' THEN 'Team_Join'
        WHEN sa.slack_type = 'app_mention' THEN 'App_Mention'
        WHEN sa.slack_type = 'message' THEN 'Message'
        ELSE COALESCE(sa.slack_type, sa.activity_kind, 'Activity')
    END,
    COALESCE(sa.user_id, ''),
    COALESCE(sa.channel_id, ''),
    COALESCE(sa.team_id, ''),
    COALESCE(sa.payload_json, '{}'),
    0,
    'success',
    COALESCE(sa.received_at, datetime('now')),
    COALESCE(sa.slack_type, '')
FROM slack_activity sa
LEFT JOIN workspaces w ON w.team_id = sa.team_id
WHERE NOT EXISTS (
    SELECT 1 FROM events e
    WHERE e.request_data = sa.payload_json
    AND e.created_at = sa.received_at
    AND e.event_type = CASE
        WHEN sa.activity_kind = 'slash_command' THEN 'Command'
        WHEN sa.slack_type = 'team_join' THEN 'Team_Join'
        WHEN sa.slack_type = 'app_mention' THEN 'App_Mention'
        WHEN sa.slack_type = 'message' THEN 'Message'
        ELSE COALESCE(sa.slack_type, sa.activity_kind, 'Activity')
    END
);

CREATE INDEX IF NOT EXISTS idx_events_slack_team_created
ON events(slack_team_id, created_at DESC);

DROP TABLE IF EXISTS slack_activity;
