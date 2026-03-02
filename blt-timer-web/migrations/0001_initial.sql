-- Fresh Time Tracker: initial D1 schema

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    projectId TEXT NOT NULL,
    startTime INTEGER NOT NULL,
    endTime INTEGER,
    duration INTEGER,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_sessions_userId ON sessions(userId);

CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    sessionId TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    userId TEXT NOT NULL,
    type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    data TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activities_sessionId ON activities(sessionId);
