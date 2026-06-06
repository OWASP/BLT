-- Migration number: 0012   2026-06-06T00:00:00.000Z
-- User-owned jobs and hackathons for BLT-API v2.

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by_user_id INTEGER NOT NULL,
    title TEXT NOT NULL CHECK(LENGTH(title) >= 1 AND LENGTH(title) <= 200),
    description TEXT NOT NULL CHECK(LENGTH(description) >= 1 AND LENGTH(description) <= 5000),
    company_name TEXT CHECK(company_name IS NULL OR LENGTH(company_name) <= 200),
    location TEXT CHECK(location IS NULL OR LENGTH(location) <= 200),
    url TEXT CHECK(url IS NULL OR LENGTH(url) <= 500),
    apply_url TEXT CHECK(apply_url IS NULL OR LENGTH(apply_url) <= 500),
    job_type TEXT CHECK(job_type IS NULL OR job_type IN ('full-time', 'part-time', 'contract', 'internship', 'other')),
    salary_range TEXT CHECK(salary_range IS NULL OR LENGTH(salary_range) <= 200),
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('draft', 'open', 'closed')),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    expires_at TIMESTAMP,
    views INTEGER NOT NULL DEFAULT 0 CHECK(views >= 0),
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_created_by_user
    ON jobs(created_by_user_id);

CREATE INDEX IF NOT EXISTS idx_jobs_user_status
    ON jobs(created_by_user_id, status);

CREATE INDEX IF NOT EXISTS idx_jobs_user_active
    ON jobs(created_by_user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_jobs_created
    ON jobs(created);

CREATE TABLE IF NOT EXISTS hackathons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by_user_id INTEGER NOT NULL,
    title TEXT NOT NULL CHECK(LENGTH(title) >= 1 AND LENGTH(title) <= 200),
    slug TEXT NOT NULL CHECK(LENGTH(slug) >= 3 AND LENGTH(slug) <= 100),
    description TEXT CHECK(description IS NULL OR LENGTH(description) <= 5000),
    starts_at TIMESTAMP NOT NULL,
    ends_at TIMESTAMP NOT NULL,
    location TEXT CHECK(location IS NULL OR LENGTH(location) <= 200),
    url TEXT CHECK(url IS NULL OR LENGTH(url) <= 500),
    capacity INTEGER CHECK(capacity IS NULL OR capacity > 0),
    is_published BOOLEAN NOT NULL DEFAULT 1,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(created_by_user_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_hackathons_created_by_user
    ON hackathons(created_by_user_id);

CREATE INDEX IF NOT EXISTS idx_hackathons_user_slug
    ON hackathons(created_by_user_id, slug);

CREATE INDEX IF NOT EXISTS idx_hackathons_user_starts
    ON hackathons(created_by_user_id, starts_at);

CREATE TABLE IF NOT EXISTS hackathon_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hackathon_id INTEGER NOT NULL,
    created_by_user_id INTEGER NOT NULL,
    registrant_user_id INTEGER,
    participant_name TEXT CHECK(participant_name IS NULL OR LENGTH(participant_name) <= 200),
    participant_email_encrypted TEXT NOT NULL,
    participant_email_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'registered' CHECK(status IN ('registered', 'cancelled')),
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hackathon_id) REFERENCES hackathons(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (registrant_user_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(hackathon_id, participant_email_hash)
);

CREATE INDEX IF NOT EXISTS idx_hackathon_registrations_hackathon
    ON hackathon_registrations(hackathon_id);

CREATE INDEX IF NOT EXISTS idx_hackathon_registrations_owner
    ON hackathon_registrations(created_by_user_id);

CREATE TRIGGER IF NOT EXISTS update_jobs_modified
AFTER UPDATE ON jobs
BEGIN
    UPDATE jobs SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_hackathons_modified
AFTER UPDATE ON hackathons
BEGIN
    UPDATE hackathons SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_hackathon_registrations_modified
AFTER UPDATE ON hackathon_registrations
BEGIN
    UPDATE hackathon_registrations SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

INSERT INTO jobs (
    created_by_user_id,
    title,
    description,
    company_name,
    location,
    url,
    apply_url,
    job_type,
    status,
    is_active
)
SELECT
    id,
    'Security Engineer',
    'Example user-owned job for BLT-API local exploration.',
    'OWASP BLT',
    'Remote',
    'https://owaspblt.org',
    'https://owaspblt.org',
    'full-time',
    'open',
    1
FROM users
ORDER BY id
LIMIT 1;

INSERT INTO hackathons (
    created_by_user_id,
    title,
    slug,
    description,
    starts_at,
    ends_at,
    location,
    url,
    capacity,
    is_published
)
SELECT
    id,
    'BLT Build Day',
    'blt-build-day',
    'Example user-owned hackathon for BLT-API local exploration.',
    datetime('now', '+7 days'),
    datetime('now', '+9 days'),
    'Remote',
    'https://owaspblt.org',
    100,
    1
FROM users
ORDER BY id
LIMIT 1;
