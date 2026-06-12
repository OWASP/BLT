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
pub struct Stats {
    pub total_issues: u32,
    pub active_repos: u32,
    pub total_contributors: u32,
    pub bacon_points: u32,
}

pub fn get_mock_issues() -> Vec<Issue> {
    vec![
        Issue {
            id: "1201".to_string(),
            repository: "owasp-blt/api".to_string(),
            title: "Potential SQL Injection in /v1/auth/verify handler".to_string(),
            description: "A SQL injection vulnerability was identified in the auth verification API endpoint. The token query parameter is concatenated directly into the database selection statement without parameterization or query binding.".to_string(),
            status: "Triage".to_string(),
            severity: "Critical".to_string(),
            author: "Agent-03".to_string(),
            comments: vec![
                "shivam: Confirmed vulnerability on staging environment.".to_string(),
                "altafur: Marking this critical. Please prepare a patch immediately.".to_string(),
                "rosai: Working on using parameterized queries in verify handler.".to_string(),
            ],
        },
        Issue {
            id: "1198".to_string(),
            repository: "owasp-blt/rewards".to_string(),
            title: "Bacon rewards points overflow vulnerability".to_string(),
            description: "Points calculation allows signed integer overflow when awarding bacon points in bulk, resulting in potential negative point state or massive point gains.".to_string(),
            status: "Open".to_string(),
            severity: "High".to_string(),
            author: "NachiketRoy".to_string(),
            comments: vec![
                "shivam: Verified. Needs an assertion check before processing arithmetic.".to_string(),
            ],
        },
        Issue {
            id: "1182".to_string(),
            repository: "owasp-blt/next".to_string(),
            title: "Cross-Site Scripting (XSS) in leaderboard search".to_string(),
            description: "Reflected Cross-Site Scripting (XSS) exists on the username search input param on the main leaderboard view page because output is rendered raw without HTML escaping.".to_string(),
            status: "In Review".to_string(),
            severity: "Medium".to_string(),
            author: "rosai".to_string(),
            comments: vec![
                "nachiket.roy: Opened a pull request to sanitize search query output.".to_string(),
            ],
        },
    ]
}

pub fn get_mock_repos() -> Vec<Repo> {
    vec![
        Repo {
            id: "1".to_string(),
            name: "owasp-blt/api".to_string(),
            description: "The core FastAPI backend REST service".to_string(),
            url: "https://github.com/OWASP-BLT/blt-api".to_string(),
            language: "Python".to_string(),
        },
        Repo {
            id: "2".to_string(),
            name: "owasp-blt/rewards".to_string(),
            description: "Bacon point calculations and contributor rewards module".to_string(),
            url: "https://github.com/OWASP-BLT/blt-rewards".to_string(),
            language: "Python".to_string(),
        },
        Repo {
            id: "3".to_string(),
            name: "owasp-blt/next".to_string(),
            description: "Developer landing pages and leaderboard web dashboard".to_string(),
            url: "https://github.com/OWASP-BLT/blt-next".to_string(),
            language: "TypeScript".to_string(),
        },
    ]
}

pub fn get_mock_hunts() -> Vec<Hunt> {
    vec![
        Hunt {
            name: "CHAOSS Hunt 2026".to_string(),
            description: "Vulnerability hunt focusing on SDG classifier integrations".to_string(),
            status: "Active".to_string(),
            reward: "1,500 Bacon Points".to_string(),
        },
        Hunt {
            name: "Scoring Logic Audit".to_string(),
            description: "Hunt focusing on self-review exploits and N+1 query patterns".to_string(),
            status: "Active".to_string(),
            reward: "800 Bacon Points".to_string(),
        },
    ]
}

pub fn get_mock_stats() -> Stats {
    Stats {
        total_issues: 1482,
        active_repos: 8,
        total_contributors: 154,
        bacon_points: 42900,
    }
}
