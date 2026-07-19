-- Migration 002: Drop redundant idempotency index.
-- The UNIQUE NOT NULL constraint on events.idempotency_key already creates an
-- implicit unique index, so the explicit idx_events_idempotency from migration
-- 001 is redundant. Dropping it removes a small storage cost and clarifies
-- which index is authoritative.

DROP INDEX IF EXISTS idx_events_idempotency;