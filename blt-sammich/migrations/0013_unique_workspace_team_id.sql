DROP TABLE IF EXISTS _workspace_team_dedupe;

CREATE TABLE _workspace_team_dedupe AS
SELECT loser.id AS loser_id, keeper.id AS keeper_id
FROM workspaces loser
JOIN workspaces keeper
  ON keeper.id = (
    SELECT candidate.id
    FROM workspaces candidate
    WHERE candidate.team_id = loser.team_id
    ORDER BY candidate.updated_at DESC, candidate.id DESC
    LIMIT 1
  )
WHERE loser.id != keeper.id;

UPDATE workspaces
SET
  access_token = COALESCE(NULLIF(access_token, ''), (
    SELECT loser.access_token
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.access_token != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  app_token = COALESCE(NULLIF(app_token, ''), (
    SELECT loser.app_token
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.app_token != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  bot_token = COALESCE(NULLIF(bot_token, ''), (
    SELECT loser.bot_token
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.bot_token != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  bot_user_id = COALESCE(NULLIF(bot_user_id, ''), (
    SELECT loser.bot_user_id
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.bot_user_id != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  app_id = COALESCE(NULLIF(app_id, ''), (
    SELECT loser.app_id
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.app_id != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  app_name = COALESCE(NULLIF(app_name, ''), (
    SELECT loser.app_name
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.app_name != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  app_icon_url = COALESCE(NULLIF(app_icon_url, ''), (
    SELECT loser.app_icon_url
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.app_icon_url != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  icon_url = COALESCE(NULLIF(icon_url, ''), (
    SELECT loser.icon_url
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.icon_url != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  invite_link = COALESCE(NULLIF(invite_link, ''), (
    SELECT loser.invite_link
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.invite_link != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  manifest_yaml = COALESCE(NULLIF(manifest_yaml, ''), (
    SELECT loser.manifest_yaml
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.manifest_yaml != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  installer_slack_user_id = COALESCE(NULLIF(installer_slack_user_id, ''), (
    SELECT loser.installer_slack_user_id
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.installer_slack_user_id != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  installer_name = COALESCE(NULLIF(installer_name, ''), (
    SELECT loser.installer_name
    FROM workspaces loser
    JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser.id
    WHERE dedupe.keeper_id = workspaces.id AND loser.installer_name != ''
    ORDER BY loser.updated_at DESC, loser.id DESC
    LIMIT 1
  ), ''),
  updated_at = CURRENT_TIMESTAMP
WHERE id IN (SELECT keeper_id FROM _workspace_team_dedupe);

DELETE FROM channels
WHERE id IN (
  SELECT loser_channel.id
  FROM channels loser_channel
  JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser_channel.workspace_id
  JOIN channels keeper_channel
    ON keeper_channel.workspace_id = dedupe.keeper_id
   AND keeper_channel.channel_id = loser_channel.channel_id
);

UPDATE channels
SET workspace_id = (
  SELECT keeper_id FROM _workspace_team_dedupe WHERE loser_id = channels.workspace_id
)
WHERE workspace_id IN (SELECT loser_id FROM _workspace_team_dedupe);

DELETE FROM repositories
WHERE id IN (
  SELECT loser_repo.id
  FROM repositories loser_repo
  JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser_repo.workspace_id
  JOIN repositories keeper_repo
    ON keeper_repo.workspace_id = dedupe.keeper_id
   AND keeper_repo.repo_url = loser_repo.repo_url
);

UPDATE repositories
SET workspace_id = (
  SELECT keeper_id FROM _workspace_team_dedupe WHERE loser_id = repositories.workspace_id
)
WHERE workspace_id IN (SELECT loser_id FROM _workspace_team_dedupe);

DELETE FROM github_organizations
WHERE id IN (
  SELECT loser_org.id
  FROM github_organizations loser_org
  JOIN _workspace_team_dedupe dedupe ON dedupe.loser_id = loser_org.workspace_id
  JOIN github_organizations keeper_org
    ON keeper_org.workspace_id = dedupe.keeper_id
   AND keeper_org.org_login = loser_org.org_login
);

UPDATE github_organizations
SET workspace_id = (
  SELECT keeper_id FROM _workspace_team_dedupe WHERE loser_id = github_organizations.workspace_id
)
WHERE workspace_id IN (SELECT loser_id FROM _workspace_team_dedupe);

UPDATE events
SET workspace_id = (
  SELECT keeper_id FROM _workspace_team_dedupe WHERE loser_id = events.workspace_id
)
WHERE workspace_id IN (SELECT loser_id FROM _workspace_team_dedupe);

DELETE FROM workspaces
WHERE id IN (SELECT loser_id FROM _workspace_team_dedupe);

UPDATE workspaces
SET
  channel_count = (
    SELECT COUNT(*) FROM channels WHERE channels.workspace_id = workspaces.id
  ),
  member_count = (
    SELECT COALESCE(SUM(member_count), 0) FROM channels WHERE channels.workspace_id = workspaces.id
  )
WHERE id IN (SELECT keeper_id FROM _workspace_team_dedupe);

DROP INDEX IF EXISTS idx_workspace_team_app;
CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_team_id
ON workspaces(team_id);

DROP TABLE IF EXISTS _workspace_team_dedupe;
