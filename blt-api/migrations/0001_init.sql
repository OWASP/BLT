-- Migration number: 0001 	 2026-02-17T06:27:29.552Z

-- Tags table (for domain tags relationship)
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Domains table
CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(LENGTH(name) >= 1 AND LENGTH(name) <= 255),
    url TEXT NOT NULL CHECK(LENGTH(url) >= 1 AND LENGTH(url) <= 200),
    logo TEXT CHECK(logo IS NULL OR LENGTH(logo) <= 200),
    webshot TEXT CHECK(webshot IS NULL OR LENGTH(webshot) <= 200),
    clicks INTEGER CHECK(clicks IS NULL OR (clicks >= -2147483648 AND clicks <= 2147483647)),
    email_event TEXT CHECK(email_event IS NULL OR LENGTH(email_event) <= 255),
    color TEXT CHECK(color IS NULL OR LENGTH(color) <= 10),
    github TEXT CHECK(github IS NULL OR LENGTH(github) <= 255),
    email TEXT CHECK(email IS NULL OR LENGTH(email) <= 254),
    twitter TEXT CHECK(twitter IS NULL OR LENGTH(twitter) <= 30),
    facebook TEXT CHECK(facebook IS NULL OR LENGTH(facebook) <= 200),
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    has_security_txt BOOLEAN DEFAULT 0,
    security_txt_checked_at TIMESTAMP,
    organization INTEGER
);

-- Domain tags junction table (many-to-many)
CREATE TABLE IF NOT EXISTS domain_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(domain_id, tag_id)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_domains_organization ON domains(organization);
CREATE INDEX IF NOT EXISTS idx_domains_is_active ON domains(is_active);
CREATE INDEX IF NOT EXISTS idx_domains_created ON domains(created);
CREATE INDEX IF NOT EXISTS idx_domain_tags_domain ON domain_tags(domain_id);
CREATE INDEX IF NOT EXISTS idx_domain_tags_tag ON domain_tags(tag_id);

-- Triggers to update modified timestamp automatically
CREATE TRIGGER IF NOT EXISTS update_domains_modified 
AFTER UPDATE ON domains
BEGIN
    UPDATE domains SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

