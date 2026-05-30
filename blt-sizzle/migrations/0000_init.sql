-- Migration number: 0000 	 2026-02-24T17:52:46.000Z

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    email TEXT,
    display_name TEXT,
    slack_user_id TEXT,
    slack_webhook_url TEXT,
    notification_time TEXT DEFAULT '09:00',
    notification_enabled INTEGER DEFAULT 1,
    email_notifications INTEGER DEFAULT 0,
    timezone TEXT DEFAULT 'UTC',
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_check_in DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create checkins table
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    encrypted_previous_work TEXT,
    encrypted_today_plan TEXT,
    encrypted_blockers TEXT,
    mood TEXT,
    goal_accomplished INTEGER DEFAULT 0,
    checkin_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Create timelogs table
CREATE TABLE IF NOT EXISTS timelogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    github_issue_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, checkin_date);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_timelogs_user ON timelogs(user_id);