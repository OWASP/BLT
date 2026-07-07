use tokio::process::Command;

#[derive(Clone, Debug, PartialEq)]
pub enum ToolStatus {
    Pending,
    Missing,
    Error(String),
    Skipped,
    Success,
}

impl Default for ToolStatus {
    fn default() -> Self {
        ToolStatus::Pending
    }
}

#[derive(Clone, Debug, Default)]
pub struct SecurityHealth {
    pub trivy_status: ToolStatus,
    pub semgrep_status: ToolStatus,
    pub bandit_status: ToolStatus,
    pub findings: Vec<String>,
    pub scan_complete: bool,
}

pub async fn run_scan() -> SecurityHealth {
    let mut health = SecurityHealth::default();
    
    // Spawn tasks for each tool
    let trivy_future = run_trivy();
    let semgrep_future = run_semgrep();
    let bandit_future = run_bandit();

    let (trivy_res, semgrep_res, bandit_res) = tokio::join!(trivy_future, semgrep_future, bandit_future);

    // Process Trivy
    health.trivy_status = trivy_res.0;
    health.findings.extend(trivy_res.1);

    // Process Semgrep
    health.semgrep_status = semgrep_res.0;
    health.findings.extend(semgrep_res.1);

    // Process Bandit
    health.bandit_status = bandit_res.0;
    health.findings.extend(bandit_res.1);

    health.scan_complete = true;
    health
}

async fn run_tool(tool: &str, args: &[&str]) -> Result<std::process::Output, ToolStatus> {
    #[cfg(target_os = "windows")]
    {
        let mut all_args = vec!["/c", tool];
        all_args.extend_from_slice(args);
        match Command::new("cmd").args(&all_args).output().await {
            Ok(output) => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                if !output.status.success() && stderr.contains("is not recognized") {
                    Err(ToolStatus::Missing)
                } else {
                    Ok(output)
                }
            }
            Err(e) => Err(ToolStatus::Error(format!("Execution failed: {}", e))),
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        match Command::new(tool).args(args).output().await {
            Ok(output) => Ok(output),
            Err(e) => {
                if e.kind() == std::io::ErrorKind::NotFound {
                    Err(ToolStatus::Missing)
                } else {
                    Err(ToolStatus::Error(format!("Execution failed: {}", e)))
                }
            }
        }
    }
}

async fn run_trivy() -> (ToolStatus, Vec<String>) {
    let output = match run_tool("trivy", &["fs", "--format", "json", "--scanners", "vuln,secret,misconfig", "--skip-dirs", "node_modules", "--skip-dirs", "target", "."]).await {
        Ok(out) => out,
        Err(status) => return (status, vec![]),
    };

    let parsed: serde_json::Value = match serde_json::from_slice(&output.stdout) {
        Ok(v) => v,
        Err(e) => return (ToolStatus::Error(format!("JSON parse error (version mismatch?): {}", e)), vec![]),
    };

    let mut findings = Vec::new();
    if let Some(results) = parsed.get("Results").and_then(|r| r.as_array()) {
        for result in results {
            let target = result.get("Target").and_then(|t| t.as_str()).unwrap_or("unknown");
            
            if let Some(vulns) = result.get("Vulnerabilities").and_then(|v| v.as_array()) {
                for vuln in vulns {
                    let id = vuln.get("VulnerabilityID").and_then(|i| i.as_str()).unwrap_or("Unknown");
                    let severity = vuln.get("Severity").and_then(|s| s.as_str()).unwrap_or("UNKNOWN");
                    findings.push(format!("[Trivy] {} ({}) in {}", id, severity, target));
                }
            }
            if let Some(secrets) = result.get("Secrets").and_then(|s| s.as_array()) {
                for secret in secrets {
                    let title = secret.get("Title").and_then(|t| t.as_str()).unwrap_or("Secret");
                    let severity = secret.get("Severity").and_then(|s| s.as_str()).unwrap_or("UNKNOWN");
                    findings.push(format!("[Trivy] {} ({}) in {}", title, severity, target));
                }
            }
        }
    }

    (ToolStatus::Success, findings)
}

async fn run_semgrep() -> (ToolStatus, Vec<String>) {
    let output = match run_tool("semgrep", &["scan", "--json"]).await {
        Ok(out) => out,
        Err(status) => return (status, vec![]),
    };

    let parsed: serde_json::Value = match serde_json::from_slice(&output.stdout) {
        Ok(v) => v,
        Err(e) => return (ToolStatus::Error(format!("JSON parse error (version mismatch?): {}", e)), vec![]),
    };

    let mut findings = Vec::new();
    if let Some(results) = parsed.get("results").and_then(|r| r.as_array()) {
        for result in results {
            let check_id = result.get("check_id").and_then(|c| c.as_str()).unwrap_or("unknown");
            let path = result.get("path").and_then(|p| p.as_str()).unwrap_or("unknown");
            let extra = result.get("extra");
            let severity = extra.and_then(|e| e.get("severity")).and_then(|s| s.as_str()).unwrap_or("UNKNOWN");
            findings.push(format!("[Semgrep] {} ({}) in {}", check_id, severity, path));
        }
    }

    (ToolStatus::Success, findings)
}

async fn run_bandit() -> (ToolStatus, Vec<String>) {
    let is_python = std::path::Path::new("requirements.txt").exists() 
                 || std::path::Path::new("pyproject.toml").exists()
                 || std::path::Path::new("setup.py").exists();

    if !is_python {
        return (ToolStatus::Skipped, vec![]);
    }

    let output = match run_tool("bandit", &["-r", ".", "-f", "json"]).await {
        Ok(out) => out,
        Err(status) => return (status, vec![]),
    };

    let parsed: serde_json::Value = match serde_json::from_slice(&output.stdout) {
        Ok(v) => v,
        Err(e) => return (ToolStatus::Error(format!("JSON parse error (version mismatch?): {}", e)), vec![]),
    };

    let mut findings = Vec::new();
    if let Some(results) = parsed.get("results").and_then(|r| r.as_array()) {
        for result in results {
            let test_id = result.get("test_id").and_then(|t| t.as_str()).unwrap_or("unknown");
            let severity = result.get("issue_severity").and_then(|s| s.as_str()).unwrap_or("UNKNOWN");
            let filename = result.get("filename").and_then(|f| f.as_str()).unwrap_or("unknown");
            findings.push(format!("[Bandit] {} ({}) in {}", test_id, severity, filename));
        }
    }

    (ToolStatus::Success, findings)
}
