-- Migration: Create indexes for performance
-- Created: 2026-02-19
-- Description: Add indexes for frequently queried and sorted columns

-- Basic lookup indexes
CREATE INDEX IF NOT EXISTS idx_repo ON prs(repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_pr_number ON prs(pr_number);

-- Indexes for sortable readiness columns to improve sorting performance
CREATE INDEX IF NOT EXISTS idx_merge_ready ON prs(merge_ready);
CREATE INDEX IF NOT EXISTS idx_overall_score ON prs(overall_score);
CREATE INDEX IF NOT EXISTS idx_ci_score ON prs(ci_score);
CREATE INDEX IF NOT EXISTS idx_review_score ON prs(review_score);
CREATE INDEX IF NOT EXISTS idx_response_rate ON prs(response_rate);
CREATE INDEX IF NOT EXISTS idx_responded_feedback ON prs(responded_feedback);
