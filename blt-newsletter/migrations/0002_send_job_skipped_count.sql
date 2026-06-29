ALTER TABLE newsletter_send_jobs
  ADD COLUMN skipped_count INTEGER NOT NULL DEFAULT 0;
