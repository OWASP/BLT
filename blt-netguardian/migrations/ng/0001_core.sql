-- NetGuardian GSoC — core D1 schema (Week 1, Day 3)
-- Apply: wrangler d1 execute blt-netguardian --remote --file=migrations/ng/0001_core.sql
-- Local: wrangler d1 execute blt-netguardian --local --file=migrations/ng/0001_core.sql
--
-- Coexists with legacy scanner tables in schema.sql (jobs, tasks, targets, vulnerabilities).

-- Per-org sender credentials metadata (secrets in Worker Secrets, not D1)
CREATE TABLE IF NOT EXISTS sender_keys (
  org_id TEXT NOT NULL,
  sender_id TEXT NOT NULL,
  kid TEXT NOT NULL,
  alg TEXT NOT NULL DEFAULT 'hmac-sha256',
  secret_ref TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  rotated_at INTEGER,
  PRIMARY KEY (org_id, sender_id, kid)
);

CREATE INDEX IF NOT EXISTS idx_sender_keys_active
  ON sender_keys (org_id, sender_id, active);

-- Raw accepted envelopes (audit + replay source of truth)
CREATE TABLE IF NOT EXISTS envelopes (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  sender_id TEXT NOT NULL,
  kid TEXT NOT NULL,
  nonce TEXT NOT NULL,
  digest TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  issued_at INTEGER NOT NULL,
  received_at INTEGER NOT NULL,
  validated_at INTEGER,
  status TEXT NOT NULL DEFAULT 'accepted',
  payload_json TEXT NOT NULL,
  UNIQUE (org_id, sender_id, nonce)
);

CREATE INDEX IF NOT EXISTS idx_envelopes_org_received
  ON envelopes (org_id, received_at DESC);

-- Triage findings (denormalized from payload_plaintext)
-- 1:1 with envelopes: each finding links exactly one envelope; each envelope maps to at most one finding.
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  envelope_id TEXT NOT NULL UNIQUE,
  rule_id TEXT NOT NULL,
  severity TEXT NOT NULL,
  title TEXT NOT NULL,
  target TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  fingerprint TEXT,
  cve_id TEXT,
  cve_score REAL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY (envelope_id) REFERENCES envelopes(id)
);

-- Back-link envelope -> finding (column added after findings table exists)
ALTER TABLE envelopes ADD COLUMN finding_id TEXT REFERENCES findings(id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_envelopes_finding_id
  ON envelopes (finding_id);

CREATE INDEX IF NOT EXISTS idx_findings_org_status
  ON findings (org_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_findings_org_fingerprint
  ON findings (org_id, fingerprint);

CREATE INDEX IF NOT EXISTS idx_findings_org_cve
  ON findings (org_id, cve_id);

-- Large evidence in R2; metadata only in D1
CREATE TABLE IF NOT EXISTS evidence_meta (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  r2_key TEXT NOT NULL,
  digest TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  media_type TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (finding_id) REFERENCES findings(id)
);

CREATE INDEX IF NOT EXISTS idx_evidence_meta_finding
  ON evidence_meta (finding_id);

-- Immutable access audit (decrypt, export, convert-to-issue)
CREATE TABLE IF NOT EXISTS access_logs (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  detail_json TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (finding_id) REFERENCES findings(id)
);

CREATE INDEX IF NOT EXISTS idx_access_logs_finding
  ON access_logs (finding_id, created_at DESC);

-- Verified events for downstream (Rewards, RepoTrust, University)
CREATE TABLE IF NOT EXISTS events_outbox (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  dedupe_key TEXT,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_outbox_dedupe
  ON events_outbox (org_id, dedupe_key)
  WHERE dedupe_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_events_outbox_pending
  ON events_outbox (status, created_at);

-- Simple daily counters for mentor metrics (Week 3+ dashboards)
CREATE TABLE IF NOT EXISTS ng_metrics (
  org_id TEXT NOT NULL,
  day TEXT NOT NULL,
  ingest_accepted INTEGER NOT NULL DEFAULT 0,
  ingest_duplicate INTEGER NOT NULL DEFAULT 0,
  ingest_rejected INTEGER NOT NULL DEFAULT 0,
  findings_open INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (org_id, day)
);
