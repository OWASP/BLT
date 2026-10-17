-- Migration: Create timeline_cache table
-- Created: 2026-02-19
-- Description: Cache table for PR timeline data to reduce GitHub API calls

CREATE TABLE IF NOT EXISTS timeline_cache (
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    data TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    PRIMARY KEY (owner, repo, pr_number)
);
