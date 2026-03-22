-- Add cached channel/member counts on workspaces for quick stats rendering

ALTER TABLE workspaces ADD COLUMN channel_count INTEGER DEFAULT 0;
ALTER TABLE workspaces ADD COLUMN member_count INTEGER DEFAULT 0;
