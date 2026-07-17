#![allow(dead_code)]
use crate::models::{self, Issue, Repo, Hunt, Stats};

pub fn get_api_key() -> Option<String> {
    if let Ok(api_key) = std::env::var("BLT_API_KEY") {
        if !api_key.trim().is_empty() {
            return Some(api_key);
        }
    }
    
    // Fallback to local credentials.json
    let home = dirs::home_dir().unwrap_or_default();
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

pub fn parse_issues_from_json(root: &serde_json::Value) -> Result<Vec<Issue>, String> {
    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else if let Some(bugs) = root.get("bugs") {
        bugs.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Err("Payload is not an array".to_string());
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

    Ok(issues)
}

pub async fn get_issues(api_base: &str) -> Result<Vec<Issue>, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let url = format!("{}/v2/bugs", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;
    
    let issues = parse_issues_from_json(&root).map_err(|e| Box::<dyn std::error::Error>::from(e))?;

    Ok(issues)
}

pub fn parse_repos_from_json(root: &serde_json::Value) -> Result<Vec<Repo>, String> {
    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Err("Payload is not an array".to_string());
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

    Ok(repos)
}

pub async fn get_repos(api_base: &str) -> Result<Vec<Repo>, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let url = format!("{}/v2/repos", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;

    let repos = parse_repos_from_json(&root).map_err(|e| Box::<dyn std::error::Error>::from(e))?;

    Ok(repos)
}

pub async fn get_hunts(api_base: &str) -> Result<Vec<Hunt>, Box<dyn std::error::Error>> {
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

pub async fn get_stats(api_base: &str) -> Result<Stats, Box<dyn std::error::Error>> {
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

pub async fn submit_issue_triage(api_base: &str, issue_id: &str, target_status: &str) -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let url = format!("{}/v2/bugs/{}", api_base, issue_id);
    
    let mut payload = std::collections::HashMap::new();
    payload.insert("status", target_status);

    let mut req = client.patch(&url).json(&payload);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?;
    resp.error_for_status()?;
    Ok(())
}

pub async fn add_comment(api_base: &str, issue_id: &str, text: &str) -> Result<(), Box<dyn std::error::Error>> {
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

pub async fn submit_issue(api_base: &str, url: &str, title: &str, severity: &str, bug_type: &str, description: &str, steps_to_reproduce: &str, screenshot_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let api_url = format!("{}/v2/bugs", api_base);
    
    let mut payload = std::collections::HashMap::new();
    payload.insert("url".to_string(), url.to_string());
    payload.insert("title".to_string(), title.to_string());
    payload.insert("severity".to_string(), severity.to_string());
    payload.insert("bug_type".to_string(), bug_type.to_string());
    payload.insert("description".to_string(), description.to_string());
    payload.insert("steps_to_reproduce".to_string(), steps_to_reproduce.to_string());
    
    if !screenshot_path.trim().is_empty() {
        if screenshot_path.starts_with("http") {
            payload.insert("screenshot".to_string(), screenshot_path.to_string());
        } else {
            let meta = tokio::fs::metadata(screenshot_path).await?;
            if meta.len() > 10 * 1024 * 1024 {
                return Err("Screenshot exceeds 10MB limit".into());
            }
            // Read local file and base64 encode
            let bytes = tokio::fs::read(screenshot_path).await?;
            use base64::{Engine as _, engine::general_purpose::STANDARD};
            let b64 = STANDARD.encode(&bytes);
            let mime = if screenshot_path.to_lowercase().ends_with(".png") {
                "image/png"
            } else if screenshot_path.to_lowercase().ends_with(".gif") {
                "image/gif"
            } else if screenshot_path.to_lowercase().ends_with(".jpg") || screenshot_path.to_lowercase().ends_with(".jpeg") {
                "image/jpeg"
            } else {
                return Err("Unsupported screenshot MIME type".into());
            };
            let data_url = format!("data:{};base64,{}", mime, b64);
            payload.insert("screenshot".to_string(), data_url);
        }
    }

    let mut req = client.post(&api_url).json(&payload);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?;
    resp.error_for_status()?;
    Ok(())
}

pub async fn get_leaderboard(api_base: &str) -> Result<Vec<models::LeaderboardEntry>, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let url = format!("{}/v2/leaderboard", api_base);
    
    let mut req = client.get(&url);
    if let Some(api_key) = get_api_key() {
        req = req.header("X-BLT-API-Key", api_key);
    }

    let resp = req.send().await?.error_for_status()?;
    let root = resp.json::<serde_json::Value>().await?;

    Ok(parse_leaderboard_from_json(&root))
}

pub fn parse_leaderboard_from_json(root: &serde_json::Value) -> Vec<models::LeaderboardEntry> {
    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Vec::new();
    };

    let mut leaderboard = Vec::new();
    let mut current_rank = 1;
    for item in arr {
        let rank = item.get("rank")
            .and_then(|v| v.as_u64())
            .unwrap_or(current_rank as u64) as u32;

        let name = item.get("name")
            .or_else(|| item.get("username"))
            .and_then(|v| v.as_str())
            .unwrap_or("Unknown")
            .to_string();

        let bacon_points = item.get("bacon_points")
            .or_else(|| item.get("total_score"))
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;

        let reputation = item.get("reputation")
            .or_else(|| item.get("title"))
            .and_then(|v| v.as_str())
            .unwrap_or("Contributor")
            .to_string();

        leaderboard.push(models::LeaderboardEntry {
            rank,
            name,
            bacon_points,
            reputation,
        });
        current_rank += 1;
    }

    leaderboard
}

pub fn parse_good_first_issues_from_json(root: &serde_json::Value) -> Vec<models::GoodFirstIssue> {
    let raw_arr = if let Some(data) = root.get("data") {
        data.as_array()
    } else {
        root.as_array()
    };

    let Some(arr) = raw_arr else {
        return Vec::new();
    };

    let mut issues = Vec::new();
    for item in arr {
        let id = item.get("id").and_then(|v| v.as_u64()).unwrap_or(0);
        let title = item.get("title").and_then(|v| v.as_str()).unwrap_or("Untitled").to_string();
        let repository = item.get("repository").and_then(|v| v.as_str()).unwrap_or("Unknown").to_string();
        let web_url = item.get("web_url").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let description = item.get("description").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let bacon_estimate = item.get("bacon_estimate").and_then(|v| v.as_u64()).unwrap_or(100) as u32;

        issues.push(models::GoodFirstIssue {
            id,
            title,
            repository,
            web_url,
            description,
            bacon_estimate,
        });
    }
    
    issues
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_parse_leaderboard_from_json() {
        let json_data = json!({
            "data": [
                {
                    "rank": 1,
                    "name": "Alice",
                    "bacon_points": 100,
                    "reputation": "Admin"
                },
                {
                    "username": "Bob",
                    "total_score": 50,
                    "title": "Contributor"
                }
            ]
        });

        let leaderboard = parse_leaderboard_from_json(&json_data);
        assert_eq!(leaderboard.len(), 2);
        
        assert_eq!(leaderboard[0].rank, 1);
        assert_eq!(leaderboard[0].name, "Alice");
        assert_eq!(leaderboard[0].bacon_points, 100);
        assert_eq!(leaderboard[0].reputation, "Admin");

        assert_eq!(leaderboard[1].rank, 2); // Auto-incremented rank
        assert_eq!(leaderboard[1].name, "Bob");
        assert_eq!(leaderboard[1].bacon_points, 50);
        assert_eq!(leaderboard[1].reputation, "Contributor");
    }

    #[test]
    fn test_parse_good_first_issues_from_json() {
        let json_data = json!([
            {
                "id": 1,
                "title": "Fix typo",
                "repository": "owasp-blt/blt-university",
                "web_url": "https://gitlab.com/owasp-blt/blt-university/-/issues/1",
                "description": "There is a typo.",
                "bacon_estimate": 10
            }
        ]);

        let issues = parse_good_first_issues_from_json(&json_data);
        assert_eq!(issues.len(), 1);
        assert_eq!(issues[0].id, 1);
        assert_eq!(issues[0].title, "Fix typo");
        assert_eq!(issues[0].repository, "owasp-blt/blt-university");
        assert_eq!(issues[0].web_url, "https://gitlab.com/owasp-blt/blt-university/-/issues/1");
        assert_eq!(issues[0].bacon_estimate, 10);
    }
}
