-- Migration number: 0015 	 2026-07-01T00:00:00.000Z

-- Add missing UI form fields to bugs table
ALTER TABLE bugs ADD COLUMN title TEXT;
ALTER TABLE bugs ADD COLUMN severity TEXT;
ALTER TABLE bugs ADD COLUMN bug_type TEXT;
ALTER TABLE bugs ADD COLUMN steps_to_reproduce TEXT;
