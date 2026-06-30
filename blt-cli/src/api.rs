#![allow(dead_code)]
use crate::mock_data::{self, Issue, Repo, Hunt, Stats};

pub fn get_api_key() -> Option<String> {
    if let Ok(api_key) = std::env::var("BLT_API_KEY") {
        return Some(api_key);
    }
    
    // Fallback to local credentials.json
    let home = dirs::home_dir()?;
    let creds_path = home.join(".blt-mcp").join("credentials.json");
    if let Ok(content) = std::fs::read_to_string(creds_path) {
        if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
            if let Some(key) = json.get("BLT_API_KEY").and_then(|k| k.as_str()) {
                return Some(key.to_string());
            }
        }
    }
    None
}

pub fn parse_issues_from_json(root: &serde_json::Value) -> Vec<Issue> {
    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else if let Some(bugs) = root.get("bugs") {
        bugs.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Vec::new();
    };

    let mut issues = Vec::new();
    for item in arr {
        let id = match item.get("id").or_else(|| item.get("_id")) {
            Some(v) => {
                if let Some(s) = v.as_str() {
                    s.to_string()
                } else if let Some(n) = v.as_i64() {
                    n.to_string()
                } else {
                    continue;
                }
            }
            None => continue,
        };

        let repository = item.get("repository")
            .or_else(|| item.get("repo"))
            .and_then(|v| v.as_str())
            .unwrap_or("owasp-blt/api")
            .to_string();

        let title = item.get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("Untitled Issue")
            .to_string();

        let description = item.get("description")
            .or_else(|| item.get("content"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let status = item.get("status")
            .and_then(|v| v.as_str())
            .unwrap_or("Triage")
            .to_string();

        let severity = item.get("severity")
            .and_then(|v| v.as_str())
            .unwrap_or("Medium")
            .to_string();

        let author = item.get("author")
            .or_else(|| item.get("username"))
            .and_then(|v| v.as_str())
            .unwrap_or("Community")
            .to_string();

        let mut comments = Vec::new();
        if let Some(comments_val) = item.get("comments") {
            if let Some(c_arr) = comments_val.as_array() {
                for c in c_arr {
                    if let Some(c_str) = c.as_str() {
                        comments.push(c_str.to_string());
                    } else if let Some(c_obj) = c.as_object() {
                        let text = c_obj.get("text").or_else(|| c_obj.get("body")).and_then(|v| v.as_str()).unwrap_or("");
                        let c_author = c_obj.get("author").or_else(|| c_obj.get("username")).and_then(|v| v.as_str()).unwrap_or("community");
                        if !text.is_empty() {
                            comments.push(format!("{}: {}", c_author, text));
                        }
                    }
                }
            }
        }

        issues.push(Issue {
            id,
            repository,
            title,
            description,
            status,
            severity,
            author,
            comments,
        });
    }

    issues
}

pub async fn get_issues(api_base: &str, offline: bool) -> Result<Vec<Issue>, Box<dyn std::error::Error>> {
    if offline {
        return Ok(mock_data::get_mock_issues());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/bugs", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;
    
    let issues = parse_issues_from_json(&root);
    if issues.is_empty() {
        return Err("API response issues data was not an array or was empty".into());
    }

    Ok(issues)
}

pub fn parse_repos_from_json(root: &serde_json::Value) -> Vec<Repo> {
    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Vec::new();
    };

    let mut repos = Vec::new();
    for item in arr {
        let id = match item.get("id").or_else(|| item.get("_id")) {
            Some(v) => {
                if let Some(s) = v.as_str() {
                    s.to_string()
                } else if let Some(n) = v.as_i64() {
                    n.to_string()
                } else {
                    continue;
                }
            }
            None => continue,
        };

        let name = item.get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("Unnamed Repo")
            .to_string();

        let description = item.get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let url = item.get("url")
            .or_else(|| item.get("html_url"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let language = item.get("language")
            .and_then(|v| v.as_str())
            .unwrap_or("Unknown")
            .to_string();

        repos.push(Repo {
            id,
            name,
            description,
            url,
            language,
        });
    }

    repos
}

pub async fn get_repos(api_base: &str, offline: bool) -> Result<Vec<Repo>, Box<dyn std::error::Error>> {
    if offline {
        return Ok(mock_data::get_mock_repos());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/repos", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;

    let repos = parse_repos_from_json(&root);

    Ok(repos)
}

pub async fn get_hunts(api_base: &str, offline: bool) -> Result<Vec<Hunt>, Box<dyn std::error::Error>> {
    if offline {
        return Ok(mock_data::get_mock_hunts());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/hunts/active", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;

    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Ok(Vec::new());
    };

    let mut hunts = Vec::new();
    for item in arr {
        let name = item.get("name")
            .or_else(|| item.get("title"))
            .and_then(|v| v.as_str())
            .unwrap_or("Unnamed Hunt")
            .to_string();

        let description = item.get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let status = item.get("status")
            .and_then(|v| v.as_str())
            .unwrap_or("Active")
            .to_string();

        let reward = item.get("reward")
            .or_else(|| item.get("points"))
            .and_then(|v| v.as_str())
            .unwrap_or("50 Bacon")
            .to_string();

        hunts.push(Hunt {
            name,
            description,
            status,
            reward,
        });
    }

    Ok(hunts)
}

pub fn parse_stats_from_json(root: &serde_json::Value) -> Stats {
    let data = root.get("data").unwrap_or(root);

    let total_issues = data.get("bugs")
        .or_else(|| data.get("total_issues"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0) as u32;

    let active_repos = data.get("active_repos")
        .or_else(|| data.get("organization"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0) as u32;

    let total_contributors = data.get("users")
        .or_else(|| data.get("total_contributors"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0) as u32;

    let bacon_points = data.get("bacon_points")
        .and_then(|v| v.as_u64())
        .unwrap_or(0) as u32;

    Stats {
        total_issues,
        active_repos,
        total_contributors,
        bacon_points,
    }
}

pub async fn get_stats(api_base: &str, offline: bool) -> Result<Stats, Box<dyn std::error::Error>> {
    if offline {
        return Ok(mock_data::get_mock_stats());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/stats", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;

    Ok(parse_stats_from_json(&root))
}

pub async fn submit_issue_triage(api_base: &str, issue_id: &str, offline: bool) -> Result<(), Box<dyn std::error::Error>> {
    if offline {
        // Simulated success in offline mode
        return Ok(());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/bugs/{}", api_base, issue_id);
    
    let mut payload = std::collections::HashMap::new();
    payload.insert("status", "In Review");

    let mut req = client.patch(&url).json(&payload);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?;
    resp.error_for_status()?;
    Ok(())
}

pub async fn add_comment(api_base: &str, issue_id: &str, text: &str, offline: bool) -> Result<(), Box<dyn std::error::Error>> {
    if offline {
        return Ok(());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/bugs/{}/comments", api_base, issue_id);
    
    let mut payload = std::collections::HashMap::new();
    payload.insert("text", text);

    let mut req = client.post(&url).json(&payload);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?;
    resp.error_for_status()?;
    Ok(())
}

pub async fn submit_issue(api_base: &str, title: &str, repo: &str, severity: &str, description: &str, offline: bool) -> Result<(), Box<dyn std::error::Error>> {
    if offline {
        return Ok(());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/bugs", api_base);
    
    let mut payload = std::collections::HashMap::new();
    payload.insert("title", title);
    payload.insert("repository", repo);
    payload.insert("severity", severity);
    payload.insert("description", description);

    let mut req = client.post(&url).json(&payload);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?;
    resp.error_for_status()?;
    Ok(())
}

pub async fn get_leaderboard(api_base: &str, offline: bool) -> Result<Vec<mock_data::LeaderboardEntry>, Box<dyn std::error::Error>> {
    if offline {
        return Ok(mock_data::get_mock_leaderboard());
    }

    let client = reqwest::Client::new();
    let url = format!("{}/v2/leaderboard", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;

    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Ok(Vec::new());
    };

    let mut leaderboard = Vec::new();
    for item in arr {
        let rank = item.get("rank")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;

        let name = item.get("name")
            .or_else(|| item.get("username"))
            .and_then(|v| v.as_str())
            .unwrap_or("Unknown")
            .to_string();

        let bacon_points = item.get("bacon_points")
            .or_else(|| item.get("points"))
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;

        let reputation = item.get("reputation")
            .and_then(|v| v.as_str())
            .unwrap_or("Contributor")
            .to_string();

        leaderboard.push(mock_data::LeaderboardEntry {
            rank,
            name,
            bacon_points,
            reputation,
        });
    }

    Ok(leaderboard)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_offline_api_get_issues() {
        let issues = get_issues("", true).await.unwrap();
        assert!(!issues.is_empty(), "Should return mock data in offline mode");
    }

    #[tokio::test]
    async fn test_offline_api_get_hunts() {
        let hunts = get_hunts("", true).await.unwrap();
        assert!(!hunts.is_empty(), "Should return mock data in offline mode");
    }

    #[tokio::test]
    async fn test_offline_api_get_stats() {
        let stats = get_stats("", true).await.unwrap();
        assert!(stats.total_issues > 0, "Stats should have mock data");
    }
}

