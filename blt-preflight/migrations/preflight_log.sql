CREATE TABLE IF NOT EXISTS advisory_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mr_iid INTEGER NOT NULL,
  timestamp TEXT NOT NULL,
  severity TEXT NOT NULL,
  owasp_category TEXT NOT NULL,
  dismissed INTEGER NOT NULL DEFAULT 0,
  inapplicable_label INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_advisory_log_mr ON advisory_log(mr_iid);