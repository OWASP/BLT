//! Core Domain Model Schema Definitions for the OWASP BLT System.
//!
//! This module defines Rust structures representing the domain model objects returned by the API
//! or used to pass arguments to tools. Serde traits are used for serialization and deserialization.
//!
//! Key Structures:
//! - `Issue`: Represents reported security vulnerabilities, bugs, or anomalies. Includes id, repository,
//!   title, description, status (e.g. Triage, In Review, Resolved), severity, author, and comments.
//! - `Repo`: Represents tracked codebases on the platform. Includes name, description, URL, and language.
//! - `Hunt`: Represents bug bounty hunts. Includes title, active status, and point rewards.
//! - `LeaderboardEntry`: Developer rank entries containing bacon scores and reputation titles.
//! - `Stats`: Platform metrics mapping total issues, tracked repos, and active contributors.
//! - `GoodFirstIssue`: Struct representing issues labeled for onboarding new developers.
//!
//! Default Handlers:
//! - Implements standard deserialization fallback functions (`default_repo`, `default_status`,
//!   `default_severity`, `default_author`) to handle missing JSON keys safely.

use serde::{Deserialize, Serialize};

fn default_repo() -> String {
    "owasp-blt/api".to_string()
}

fn default_url() -> String {
    "Unknown URL".to_string()
}
fn default_status() -> String {
    "Triage".to_string()
}
fn default_severity() -> String {
    "Medium".to_string()
}
fn default_author() -> String {
    "Community".to_string()
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Issue {
    pub id: String,
    #[serde(default = "default_url")]
    pub url: String,
    pub title: String,
    pub description: String,
    #[serde(default = "default_status")]
    pub status: String,
    #[serde(default = "default_severity")]
    pub severity: String,
    #[serde(default = "default_author")]
    pub author: String,
    #[serde(default)]
    pub comments: Vec<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Repo {
    pub id: String,
    pub organization_id: Option<u64>,
    pub project_id: Option<u64>,
    pub name: String,
    #[serde(default)]
    pub url: String,
    pub created: Option<String>,
    pub modified: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Hunt {
    pub name: String,
    pub description: String,
    pub status: String,
    pub reward: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LeaderboardEntry {
    pub rank: u32,
    pub name: String,
    #[serde(alias = "bacon_points")]
    pub points: u32,
    pub reputation: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Stats {
    pub total_issues: u32,
    pub active_repos: u32,
    pub total_contributors: u32,
    #[serde(alias = "bacon_points")]
    pub points: u32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GoodFirstIssue {
    pub id: u64,
    pub title: String,
    pub repository: String,
    pub web_url: String,
    pub description: String,
    #[serde(alias = "bacon_estimate")]
    pub points_estimate: u32,
}
