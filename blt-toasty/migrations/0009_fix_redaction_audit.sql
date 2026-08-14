-- Fix schema mismatch for redaction_audit table
-- Adds original_length column to match insertion logic in redaction_engine.py

ALTER TABLE redaction_audit ADD COLUMN original_length INTEGER;
