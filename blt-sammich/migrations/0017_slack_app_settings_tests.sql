ALTER TABLE slack_apps ADD COLUMN settings_test_status TEXT DEFAULT '';
ALTER TABLE slack_apps ADD COLUMN settings_test_result TEXT DEFAULT '';
ALTER TABLE slack_apps ADD COLUMN settings_tested_at TEXT DEFAULT '';
