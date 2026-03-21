-- Migration number: 0007   2026-06-01T00:00:00.000Z
-- Add encrypted username columns and migrate existing plaintext usernames.

PRAGMA foreign_keys = OFF;

-- Step 1: Add new encrypted columns (nullable so existing rows are valid).
ALTER TABLE users ADD COLUMN username_encrypted TEXT;
ALTER TABLE users ADD COLUMN username_hash TEXT;

-- Step 2: Existing rows will have NULL in username_encrypted/username_hash.
-- Application code populates these on first login via a re-encryption job,
-- or they can be populated manually via the scripts/encrypt_usernames.sh helper.

-- Step 3: Once all rows are backfilled, the username_hash column should be
-- made UNIQUE. This is deferred to migration 0008 after backfill is confirmed.

CREATE INDEX IF NOT EXISTS idx_users_username_hash ON users(username_hash);

PRAGMA foreign_keys = ON;
