CREATE TABLE IF NOT EXISTS newsletter_subscribers (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  email_hash TEXT NOT NULL UNIQUE,
  name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  source TEXT NOT NULL DEFAULT 'landing_page',
  consent_version TEXT NOT NULL DEFAULT '2026-06-14',
  subscribed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  unsubscribed_at TEXT,
  last_sent_at TEXT,
  bounce_count INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_status
  ON newsletter_subscribers (status);

CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_source
  ON newsletter_subscribers (source);

CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_subscribed_at
  ON newsletter_subscribers (subscribed_at);

CREATE TABLE IF NOT EXISTS newsletter_admins (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  email_hash TEXT NOT NULL UNIQUE,
  name TEXT,
  role TEXT NOT NULL DEFAULT 'admin',
  password_hash TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_newsletter_admins_status
  ON newsletter_admins (status);

CREATE TABLE IF NOT EXISTS newsletter_admin_sessions (
  id TEXT PRIMARY KEY,
  admin_id TEXT NOT NULL,
  session_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT NOT NULL,
  last_seen_at TEXT,
  revoked_at TEXT,
  user_agent TEXT,
  ip_hash TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (admin_id) REFERENCES newsletter_admins (id)
);

CREATE INDEX IF NOT EXISTS idx_newsletter_admin_sessions_admin_id
  ON newsletter_admin_sessions (admin_id);

CREATE INDEX IF NOT EXISTS idx_newsletter_admin_sessions_expires_at
  ON newsletter_admin_sessions (expires_at);

CREATE TABLE IF NOT EXISTS newsletter_campaigns (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  subject TEXT NOT NULL,
  summary TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  markdown_body TEXT NOT NULL DEFAULT '',
  html_body TEXT,
  scheduled_for TEXT,
  published_at TEXT,
  sent_at TEXT,
  created_by_admin_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (created_by_admin_id) REFERENCES newsletter_admins (id)
);

CREATE INDEX IF NOT EXISTS idx_newsletter_campaigns_status
  ON newsletter_campaigns (status);

CREATE INDEX IF NOT EXISTS idx_newsletter_campaigns_scheduled_for
  ON newsletter_campaigns (scheduled_for);

CREATE TABLE IF NOT EXISTS newsletter_send_jobs (
  id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  provider TEXT NOT NULL DEFAULT 'sendgrid',
  total_recipients INTEGER NOT NULL DEFAULT 0,
  sent_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (campaign_id) REFERENCES newsletter_campaigns (id)
);

CREATE INDEX IF NOT EXISTS idx_newsletter_send_jobs_campaign_id
  ON newsletter_send_jobs (campaign_id);

CREATE INDEX IF NOT EXISTS idx_newsletter_send_jobs_status
  ON newsletter_send_jobs (status);

CREATE TABLE IF NOT EXISTS newsletter_delivery_events (
  id TEXT PRIMARY KEY,
  job_id TEXT,
  subscriber_id TEXT,
  event_type TEXT NOT NULL,
  provider_message_id TEXT,
  occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (job_id) REFERENCES newsletter_send_jobs (id),
  FOREIGN KEY (subscriber_id) REFERENCES newsletter_subscribers (id)
);

CREATE INDEX IF NOT EXISTS idx_newsletter_delivery_events_subscriber_id
  ON newsletter_delivery_events (subscriber_id);

CREATE INDEX IF NOT EXISTS idx_newsletter_delivery_events_job_id
  ON newsletter_delivery_events (job_id);

CREATE INDEX IF NOT EXISTS idx_newsletter_delivery_events_event_type
  ON newsletter_delivery_events (event_type);

CREATE TABLE IF NOT EXISTS newsletter_rate_limits (
  id TEXT PRIMARY KEY,
  rate_key TEXT NOT NULL,
  action TEXT NOT NULL,
  counter INTEGER NOT NULL DEFAULT 0,
  window_start TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  window_expires_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE (rate_key, action, window_start)
);

CREATE INDEX IF NOT EXISTS idx_newsletter_rate_limits_key_action
  ON newsletter_rate_limits (rate_key, action);

CREATE INDEX IF NOT EXISTS idx_newsletter_rate_limits_window_expires_at
  ON newsletter_rate_limits (window_expires_at);
