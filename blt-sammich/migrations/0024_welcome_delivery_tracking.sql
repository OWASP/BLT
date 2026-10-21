-- Delivery and open tracking for welcome DMs, on the one Team_Join_Welcome row per welcome
-- (no extra rows). tracking_id is the unguessable id in the message's logo URL (/logo-hit?tid=);
-- delivered_at is set when chat.postMessage returns ok with a ts; opened_at is set by the first
-- logo load (by a Slack client or Slack's image proxy, see README "Welcome delivery").
-- ADD COLUMN with a constant default doesn't rewrite the table. The partial index only holds
-- rows that have a tracking id, so other events don't pay for it.
ALTER TABLE events ADD COLUMN tracking_id TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN delivered_at TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN opened_at TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN opened_via TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_events_tracking_id
ON events(tracking_id) WHERE tracking_id != '';
