-- Migration number: 0006    2026-10-20
-- Daily reminder schedule: reminder weekdays and a per-day "already sent" marker.
--
-- notification_days: comma-separated ISO weekdays (1 = Monday ... 7 = Sunday).
--   Existing users keep daily reminders ('1,2,3,4,5,6,7').
-- last_reminder_date: the user's local date (YYYY-MM-DD) of the last reminder claimed.
--   The scheduler sets it with a conditional UPDATE before sending, so a day is never
--   reminded twice.
-- last_reminder_status: sending | sent | partial | failed, for diagnosis.
-- last_test_notification_at: rate limit for the "Send test reminder" button.
-- Additive only; the users table is tiny, so this costs a handful of row writes.

ALTER TABLE users ADD COLUMN notification_days TEXT NOT NULL DEFAULT '1,2,3,4,5,6,7';
ALTER TABLE users ADD COLUMN last_reminder_date TEXT;
ALTER TABLE users ADD COLUMN last_reminder_status TEXT;
ALTER TABLE users ADD COLUMN last_reminder_at DATETIME;
ALTER TABLE users ADD COLUMN last_test_notification_at DATETIME;
