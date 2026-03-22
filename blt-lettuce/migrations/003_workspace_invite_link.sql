-- Add workspace invite link for homepage card join button and slash command updates

ALTER TABLE workspaces ADD COLUMN invite_link TEXT DEFAULT '';