-- Migration: 0010_repro_status.sql
-- Records whether reproduction steps were extracted from the report, so an
-- empty repro_steps array can be told apart from "steps missing/insufficient".
-- Values: extracted | insufficient | missing | unknown. NULL for rows created
-- before this migration.

ALTER TABLE triage_summaries ADD COLUMN repro_status TEXT;
