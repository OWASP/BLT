-- Migration number: 0005   2026-03-20T00:00:00.000Z

-- Add encrypted storage and blind index columns for sensitive user fields.
ALTER TABLE users ADD COLUMN email_encrypted TEXT;
ALTER TABLE users ADD COLUMN email_hash TEXT;
ALTER TABLE users ADD COLUMN description_encrypted TEXT;
ALTER TABLE users ADD COLUMN user_avatar_encrypted TEXT;

-- Unique blind index for fast secure equality lookups.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_hash_unique ON users(email_hash);

-- NOTE:
-- Existing plaintext rows are intentionally not mutated here to avoid destructive
-- migration behavior. New/updated user writes now store encrypted fields plus
-- blind indexes. Existing rows should be migrated with an application-level
-- backfill task that has access to USER_DATA_ENCRYPTION_KEY.
