use serde::{Deserialize, Serialize};

fn default_repo() -> String { "owasp-blt/api".to_string() }
fn default_status() -> String { "Triage".to_string() }
fn default_severity() -> String { "Medium".to_string() }
fn default_author() -> String { "Community".to_string() }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Issue {
    pub id: String,
    #[serde(default = "default_repo")]
    pub repository: String,
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
    pub name: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub url: String,
    #[serde(default)]
    pub language: String,
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
    pub bacon_points: u32,
    pub reputation: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Stats {
    pub total_issues: u32,
    pub active_repos: u32,
    pub total_contributors: u32,
    pub bacon_points: u32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GoodFirstIssue {
    pub id: u64,
    pub title: String,
    pub repository: String,
    pub web_url: String,
    pub description: String,
    pub bacon_estimate: u32,
}

