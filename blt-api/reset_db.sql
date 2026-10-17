PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS user_bug_flags;
DROP TABLE IF EXISTS user_bug_saves;
DROP TABLE IF EXISTS user_bug_upvotes;
DROP TABLE IF EXISTS user_follows;
DROP TABLE IF EXISTS bug_team_members;
DROP TABLE IF EXISTS bug_screenshots;
DROP TABLE IF EXISTS bug_tags;
DROP TABLE IF EXISTS bugs;

DROP TABLE IF EXISTS domain_tags;
DROP TABLE IF EXISTS domains;

DROP TABLE IF EXISTS organization_integrations;
DROP TABLE IF EXISTS organization_tags;
DROP TABLE IF EXISTS organization_managers;
DROP TABLE IF EXISTS organization;

DROP TABLE IF EXISTS user_api_keys;
DROP TABLE IF EXISTS user_auth_identities;

DROP TABLE IF EXISTS hackathon_registrations;
DROP TABLE IF EXISTS hackathons;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS hunts;

DROP TABLE IF EXISTS contributors;
DROP TABLE IF EXISTS repositories;
DROP TABLE IF EXISTS projects;

DROP TABLE IF EXISTS users_new;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tags;

DROP TABLE IF EXISTS d1_migrations;

PRAGMA foreign_keys = ON;
