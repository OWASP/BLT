-- Midterm triage: convert-to-issue linkage on findings
ALTER TABLE findings ADD COLUMN blt_issue_id TEXT;

CREATE INDEX IF NOT EXISTS idx_findings_org_blt_issue
  ON findings (org_id, blt_issue_id);
