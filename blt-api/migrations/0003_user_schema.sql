
-- Migration number: 0003 	 2026-02-20T00:00:00.000Z

-- User table with complete schema
-- Relationships:
--   1 user : many bugs (user reports bugs)
--   1 user : many domains (user submits domains)
--   1 user : many bugs closed (user can close bugs)
--   many users : many users (follow relationship)
--   many users : many bugs (upvote, save, flag)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE CHECK(LENGTH(username) >= 1 AND LENGTH(username) <= 150),
    password TEXT NOT NULL CHECK(LENGTH(password) <= 128),
    email TEXT NOT NULL UNIQUE CHECK(LENGTH(email) >= 1 AND LENGTH(email) <= 254),
    title INTEGER CHECK(title IS NULL OR (title >= 1 AND title <= 5)),
    user_avatar TEXT CHECK(user_avatar IS NULL OR LENGTH(user_avatar) <= 200),
    description TEXT,
    winnings REAL DEFAULT 0.0 CHECK(winnings >= 0),
    total_score INTEGER DEFAULT 0 CHECK(total_score >= 0),
    is_active BOOLEAN DEFAULT 1,
    is_staff BOOLEAN DEFAULT 0,
    is_superuser BOOLEAN DEFAULT 0,
    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User follows junction table (many-to-many: users follow other users)
CREATE TABLE IF NOT EXISTS user_follows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id INTEGER NOT NULL,
    following_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(follower_id, following_id),
    CHECK(follower_id != following_id)
);

-- User bug upvotes junction table (many-to-many: users upvote bugs)
CREATE TABLE IF NOT EXISTS user_bug_upvotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bug_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    UNIQUE(user_id, bug_id)
);

-- User bug saves junction table (many-to-many: users save bugs)
CREATE TABLE IF NOT EXISTS user_bug_saves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bug_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    UNIQUE(user_id, bug_id)
);

-- User bug flags junction table (many-to-many: users flag bugs)
CREATE TABLE IF NOT EXISTS user_bug_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bug_id INTEGER NOT NULL,
    flag_reason TEXT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    UNIQUE(user_id, bug_id)
);

-- Add user column to domains table
-- Note: SQLite doesn't support ALTER TABLE ADD CONSTRAINT for foreign keys
-- Foreign keys must be defined at table creation time
-- The bugs.user, bugs.closed_by, and bug_team_members.user_id columns already exist
-- but cannot have FK constraints added retroactively in SQLite
ALTER TABLE domains ADD COLUMN user INTEGER;

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_total_score ON users(total_score);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created);

CREATE INDEX IF NOT EXISTS idx_user_follows_follower ON user_follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_user_follows_following ON user_follows(following_id);

CREATE INDEX IF NOT EXISTS idx_user_bug_upvotes_user ON user_bug_upvotes(user_id);
CREATE INDEX IF NOT EXISTS idx_user_bug_upvotes_bug ON user_bug_upvotes(bug_id);

CREATE INDEX IF NOT EXISTS idx_user_bug_saves_user ON user_bug_saves(user_id);
CREATE INDEX IF NOT EXISTS idx_user_bug_saves_bug ON user_bug_saves(bug_id);

CREATE INDEX IF NOT EXISTS idx_user_bug_flags_user ON user_bug_flags(user_id);
CREATE INDEX IF NOT EXISTS idx_user_bug_flags_bug ON user_bug_flags(bug_id);

CREATE INDEX IF NOT EXISTS idx_domains_user ON domains(user);

-- Triggers to update modified timestamp automatically
CREATE TRIGGER IF NOT EXISTS update_users_modified 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;