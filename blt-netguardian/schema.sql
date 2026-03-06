-- BLT-NetGuardian D1 Database Schema
-- Apply with: wrangler d1 execute blt-netguardian --file=schema.sql

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    status TEXT NOT NULL,
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    task_ids TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    result_id TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS targets (
    target_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_url TEXT NOT NULL,
    scan_types TEXT,
    notes TEXT,
    registered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vulnerabilities (
    vuln_id TEXT PRIMARY KEY,
    result_id TEXT,
    task_id TEXT,
    type TEXT,
    severity TEXT,
    data TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_job_id ON tasks(job_id);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_severity ON vulnerabilities(severity);
