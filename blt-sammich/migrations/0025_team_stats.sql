-- The workspace dashboard's stats (top channels, channel families, join patterns, newcomer
-- time zones, welcome opens), built by the hourly /__scheduled workspace sync so a page view
-- reads one row. ADD COLUMN with a constant default doesn't rewrite the table.
ALTER TABLE teams ADD COLUMN stats_json TEXT DEFAULT '';
