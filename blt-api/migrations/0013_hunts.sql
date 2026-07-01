-- Migration number: 0013 	 2026-07-01T00:00:00.000Z

-- Hunts table
CREATE TABLE IF NOT EXISTS hunts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK(LENGTH(title) >= 1 AND LENGTH(title) <= 200),
    description TEXT CHECK(description IS NULL OR LENGTH(description) <= 5000),
    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hunts_active ON hunts(is_active);
CREATE INDEX IF NOT EXISTS idx_hunts_starts ON hunts(starts_at);
CREATE INDEX IF NOT EXISTS idx_hunts_ends ON hunts(ends_at);

CREATE TRIGGER IF NOT EXISTS update_hunts_modified 
AFTER UPDATE ON hunts
BEGIN
    UPDATE hunts SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Insert a mock hunt for testing
INSERT INTO hunts (
    title, 
    description, 
    starts_at, 
    ends_at, 
    is_active
) VALUES (
    'OWASP BLT Summer Bug Hunt', 
    'Join us for the annual summer bug hunt to help secure open source projects.', 
    datetime('now', '-1 days'), 
    datetime('now', '+30 days'), 
    1
);
