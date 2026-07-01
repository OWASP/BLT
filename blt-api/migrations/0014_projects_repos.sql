-- Migration number: 0014 	 2026-07-01T00:00:00.000Z

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS update_projects_modified 
AFTER UPDATE ON projects
BEGIN
    UPDATE projects SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    project_id INTEGER,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS update_repositories_modified 
AFTER UPDATE ON repositories
BEGIN
    UPDATE repositories SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Contributors table
CREATE TABLE IF NOT EXISTS contributors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    project_id INTEGER,
    repository_id INTEGER,
    score INTEGER DEFAULT 0,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
