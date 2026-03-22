-- Add channel_id to events so channel-level activity can be queried directly

ALTER TABLE events ADD COLUMN channel_id TEXT DEFAULT '';
