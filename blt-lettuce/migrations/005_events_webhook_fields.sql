-- Add explicit webhook metadata columns to events for easier debugging/reporting

ALTER TABLE events ADD COLUMN webhook_body_type TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN webhook_event_id TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN webhook_event_time TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN webhook_event_subtype TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN webhook_retry_num TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN webhook_retry_reason TEXT DEFAULT '';
