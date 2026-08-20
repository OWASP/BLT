-- D1 fallback for evidence attachments when R2 is not bound.
CREATE TABLE IF NOT EXISTS evidence_blobs (
  id TEXT PRIMARY KEY,
  data_b64 TEXT NOT NULL
);
