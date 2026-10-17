ALTER TABLE workspaces RENAME TO teams;

DROP INDEX IF EXISTS idx_workspace_team_id;
CREATE UNIQUE INDEX IF NOT EXISTS idx_team_team_id
ON teams(team_id);

ALTER TABLE channels ADD COLUMN team_id TEXT DEFAULT '';

UPDATE channels
SET team_id = COALESCE(
  (
    SELECT teams.team_id
    FROM teams
    WHERE teams.id = channels.workspace_id
    LIMIT 1
  ),
  ''
)
WHERE team_id = '';

DELETE FROM channels
WHERE id NOT IN (
  SELECT MAX(id)
  FROM channels
  GROUP BY team_id, channel_id
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_channels_team_channel
ON channels(team_id, channel_id);

DROP TABLE IF EXISTS sessions;
