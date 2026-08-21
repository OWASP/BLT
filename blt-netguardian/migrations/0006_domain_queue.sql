-- Shared domain discovery queue (distributed crawl across clients)
-- Applied via: wrangler d1 migrations apply blt-netguardian

CREATE TABLE IF NOT EXISTS domain_jobs (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  host_key TEXT NOT NULL,
  seed_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  discovered_at INTEGER NOT NULL,
  last_scan_at INTEGER,
  claimed_by TEXT,
  claim_until INTEGER,
  retry_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  result_json TEXT,
  source_url TEXT,
  UNIQUE (org_id, host_key)
);

CREATE INDEX IF NOT EXISTS idx_domain_jobs_org_status
  ON domain_jobs (org_id, status, discovered_at);

CREATE INDEX IF NOT EXISTS idx_domain_jobs_claim
  ON domain_jobs (org_id, status, claim_until);
