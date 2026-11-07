-- A mentor's account on git.owaspblt.org, so forge `/mentor` requests (blt-pool/forge/mentor.mjs)
-- can @mention them there. Empty until the mentor adds it (signup form) or an admin sets it.
--
-- Write cost: ADD COLUMN with a constant default only changes the schema; no rows are rewritten.
ALTER TABLE mentors ADD COLUMN forge_username TEXT NOT NULL DEFAULT '';
