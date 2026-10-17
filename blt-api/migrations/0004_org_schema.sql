-- Migration number: 0004 	 2026-02-22T00:00:00.000Z

-- Organization table with complete schema and optimizations
-- Relationships:
--   1 organization : many domains (organizations own domains)
--   1 user (admin) : many organizations (user administers organizations)
--   many users : many organizations (managers relationship)
--   many tags : many organizations (categorization)

CREATE TABLE IF NOT EXISTS organization (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Core fields
    name TEXT NOT NULL CHECK(LENGTH(name) >= 1 AND LENGTH(name) <= 255),
    slug TEXT UNIQUE CHECK(slug IS NULL OR (LENGTH(slug) <= 255 AND slug GLOB '[a-zA-Z0-9_-]*')),
    description TEXT CHECK(description IS NULL OR LENGTH(description) <= 500),
    logo TEXT CHECK(logo IS NULL OR LENGTH(logo) <= 200),
    url TEXT NOT NULL CHECK(LENGTH(url) >= 1 AND LENGTH(url) <= 255),
    email TEXT CHECK(email IS NULL OR LENGTH(email) <= 254),
    tagline TEXT CHECK(tagline IS NULL OR LENGTH(tagline) <= 255),
    license TEXT CHECK(license IS NULL OR LENGTH(license) <= 100),
    
    -- Social media links
    twitter TEXT CHECK(twitter IS NULL OR LENGTH(twitter) <= 200),
    facebook TEXT CHECK(facebook IS NULL OR LENGTH(facebook) <= 200),
    matrix_url TEXT CHECK(matrix_url IS NULL OR LENGTH(matrix_url) <= 200),
    slack_url TEXT CHECK(slack_url IS NULL OR LENGTH(slack_url) <= 200),
    discord_url TEXT CHECK(discord_url IS NULL OR LENGTH(discord_url) <= 200),
    gitter_url TEXT CHECK(gitter_url IS NULL OR LENGTH(gitter_url) <= 200),
    zulipchat_url TEXT CHECK(zulipchat_url IS NULL OR LENGTH(zulipchat_url) <= 200),
    element_url TEXT CHECK(element_url IS NULL OR LENGTH(element_url) <= 200),
    
    -- Project links
    source_code TEXT CHECK(source_code IS NULL OR LENGTH(source_code) <= 200),
    ideas_link TEXT CHECK(ideas_link IS NULL OR LENGTH(ideas_link) <= 200),
    contributor_guidance_url TEXT CHECK(contributor_guidance_url IS NULL OR LENGTH(contributor_guidance_url) <= 200),
    
    -- GitHub integration
    github_org TEXT CHECK(github_org IS NULL OR LENGTH(github_org) <= 255),
    repos_updated_at TIMESTAMP,
    
    -- GSoC participation
    gsoc_years TEXT CHECK(gsoc_years IS NULL OR LENGTH(gsoc_years) <= 255),
    
    -- Address fields
    address_line_1 TEXT CHECK(address_line_1 IS NULL OR LENGTH(address_line_1) <= 255),
    address_line_2 TEXT CHECK(address_line_2 IS NULL OR LENGTH(address_line_2) <= 255),
    city TEXT CHECK(city IS NULL OR LENGTH(city) <= 100),
    state TEXT CHECK(state IS NULL OR LENGTH(state) <= 100),
    country TEXT CHECK(country IS NULL OR LENGTH(country) <= 100),
    postal_code TEXT CHECK(postal_code IS NULL OR LENGTH(postal_code) <= 20),
    latitude REAL,
    longitude REAL,
    
    -- Organization metadata
    type TEXT NOT NULL CHECK(type IN ('company', 'nonprofit', 'education')),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    check_ins_enabled BOOLEAN NOT NULL DEFAULT 0,
    trademark_count INTEGER CHECK(trademark_count IS NULL OR (trademark_count >= -2147483648 AND trademark_count <= 2147483647)),
    trademark_check_date TIMESTAMP,
    team_points INTEGER DEFAULT 0 CHECK(team_points >= -2147483648 AND team_points <= 2147483647),
    
    -- Timestamps
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    admin INTEGER,
    subscription INTEGER,
    
    FOREIGN KEY (admin) REFERENCES users(id) ON DELETE SET NULL
);

-- Organization managers junction table (many-to-many: users manage organizations)
CREATE TABLE IF NOT EXISTS organization_managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organization(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(organization_id, user_id)
);

-- Organization tags junction table (many-to-many: organizations have multiple tags)
CREATE TABLE IF NOT EXISTS organization_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organization(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(organization_id, tag_id)
);

-- Organization integrations table (stores external service integrations)
CREATE TABLE IF NOT EXISTS organization_integrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    integration_type TEXT NOT NULL CHECK(LENGTH(integration_type) <= 50),
    integration_name TEXT NOT NULL CHECK(LENGTH(integration_name) <= 100),
    api_key TEXT CHECK(api_key IS NULL OR LENGTH(api_key) <= 255),
    webhook_url TEXT CHECK(webhook_url IS NULL OR LENGTH(webhook_url) <= 500),
    config_data TEXT, -- JSON data for flexible configuration
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organization(id) ON DELETE CASCADE,
    UNIQUE(organization_id, integration_type)
);

-- Add foreign key constraint to domains table for organization relationship
-- Note: This creates a proper relationship between domains and organizations
CREATE INDEX IF NOT EXISTS idx_domains_organization_fk ON domains(organization);

-- Indexes for better query performance on organization table
CREATE INDEX IF NOT EXISTS idx_organization_slug ON organization(slug);
CREATE INDEX IF NOT EXISTS idx_organization_name ON organization(name);
CREATE INDEX IF NOT EXISTS idx_organization_type ON organization(type);
CREATE INDEX IF NOT EXISTS idx_organization_is_active ON organization(is_active);
CREATE INDEX IF NOT EXISTS idx_organization_admin ON organization(admin);
CREATE INDEX IF NOT EXISTS idx_organization_created ON organization(created);
CREATE INDEX IF NOT EXISTS idx_organization_github_org ON organization(github_org);
CREATE INDEX IF NOT EXISTS idx_organization_country ON organization(country);
CREATE INDEX IF NOT EXISTS idx_organization_team_points ON organization(team_points);

-- Indexes for junction tables
CREATE INDEX IF NOT EXISTS idx_org_managers_organization ON organization_managers(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_managers_user ON organization_managers(user_id);

CREATE INDEX IF NOT EXISTS idx_org_tags_organization ON organization_tags(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_tags_tag ON organization_tags(tag_id);

CREATE INDEX IF NOT EXISTS idx_org_integrations_organization ON organization_integrations(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_integrations_type ON organization_integrations(integration_type);
CREATE INDEX IF NOT EXISTS idx_org_integrations_is_active ON organization_integrations(is_active);

-- Triggers to update modified timestamp automatically
CREATE TRIGGER IF NOT EXISTS update_organization_modified 
AFTER UPDATE ON organization
BEGIN
    UPDATE organization SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_organization_integrations_modified 
AFTER UPDATE ON organization_integrations
BEGIN
    UPDATE organization_integrations SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;