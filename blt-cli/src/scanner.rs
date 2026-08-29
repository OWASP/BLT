//! Local Security Health Vulnerability Scanner Integration.
//!
//! This module runs security scanning tools locally.
//! It spawns background subprocesses to run security tools, parses their outputs,
//! and compiles finding messages for the TUI client.
//!
//! Key Functions:
//! - `run_scan() -> SecurityHealth`: Spawns concurrent tasks for Trivy, Semgrep, and Bandit,
//!   and combines their findings into a single report.
//! - `run_tool(tool, args) -> Result<Output, ToolStatus>`: Low-level wrapper that spawns the executable
//!   using platform-specific command executors (`cmd /c` on Windows, direct process fork on Unix).
//!   Implements a 30-second execution timeout.
//! - `run_trivy()`: Performs secret, vulnerability, and misconfiguration scans on the workspace directory.
//! - `run_semgrep()`: Scans code structure against standard rules, extracting paths and rule warnings.
//! - `run_bandit()`: Scans Python codebase directories for vulnerability patterns if a pyproject.toml, requirements.txt, or setup.py file is found.
//!
//! Data Structures:
//! - `ToolStatus`: Enum tracking execution state: `Pending`, `Missing` (binary not found on user path),
//!   `Error` (nonzero exit or timeout), `Skipped`, or `Success`.
//! - `SecurityHealth`: Encapsulates statuses and lists of findings.

use tokio::process::Command;

#[derive(Clone, Debug, PartialEq, Default)]
pub enum ToolStatus {
    #[default]
    Pending,
    Missing,
    Error(String),
    Skipped,
    Success,
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

    let (trivy_res, semgrep_res, bandit_res) =
        tokio::join!(trivy_future, semgrep_future, bandit_future);

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
        let child = match Command::new("cmd")
            .args(&all_args)
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .kill_on_drop(true)
            .spawn()
        {
            Ok(c) => c,
            Err(e) => return Err(ToolStatus::Error(format!("Spawn failed: {}", e))),
        };

        match tokio::time::timeout(std::time::Duration::from_secs(30), child.wait_with_output())
            .await
        {
            Ok(Ok(output)) => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                if !output.status.success() && stderr.contains("is not recognized") {
                    Err(ToolStatus::Missing)
                } else {
                    Ok(output)
                }
            }
            Ok(Err(e)) => Err(ToolStatus::Error(format!("Execution failed: {}", e))),
            Err(_) => Err(ToolStatus::Error("Execution timed out".to_string())),
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let child = match Command::new(tool)
            .args(args)
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .kill_on_drop(true)
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                if e.kind() == std::io::ErrorKind::NotFound {
                    return Err(ToolStatus::Missing);
                } else {
                    return Err(ToolStatus::Error(format!("Spawn failed: {}", e)));
                }
            }
        };

        match tokio::time::timeout(std::time::Duration::from_secs(30), child.wait_with_output())
            .await
        {
            Ok(Ok(output)) => Ok(output),
            Ok(Err(e)) => Err(ToolStatus::Error(format!("Execution failed: {}", e))),
            Err(_) => Err(ToolStatus::Error("Execution timed out".to_string())),
        }
    }
}

async fn run_trivy() -> (ToolStatus, Vec<String>) {
    let output = match run_tool(
        "trivy",
        &[
            "fs",
            "--format",
            "json",
            "--scanners",
            "vuln,secret,misconfig",
            "--skip-dirs",
            "node_modules",
            "--skip-dirs",
            "target",
            ".",
        ],
    )
    .await
    {
        Ok(out) => out,
        Err(status) => return (status, vec![]),
    };

    // Trivy exits non-zero only on scan/report errors (not for findings)
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return (
            ToolStatus::Error(format!(
                "Trivy scan error (exit {}): {}",
                output.status.code().unwrap_or(-1),
                stderr.lines().next().unwrap_or("unknown error")
            )),
            vec![],
        );
    }

    let parsed: serde_json::Value = match serde_json::from_slice(&output.stdout) {
        Ok(v) => v,
        Err(e) => {
            return (
                ToolStatus::Error(format!("JSON parse error (version mismatch?): {}", e)),
                vec![],
            )
        }
    };

    let mut findings = Vec::new();
    if let Some(results) = parsed.get("Results").and_then(|r| r.as_array()) {
        for result in results {
            let target = result
                .get("Target")
                .and_then(|t| t.as_str())
                .unwrap_or("unknown");

            if let Some(vulns) = result.get("Vulnerabilities").and_then(|v| v.as_array()) {
                for vuln in vulns {
                    let id = vuln
                        .get("VulnerabilityID")
                        .and_then(|i| i.as_str())
                        .unwrap_or("Unknown");
                    let severity = vuln
                        .get("Severity")
                        .and_then(|s| s.as_str())
                        .unwrap_or("UNKNOWN");
                    findings.push(format!("[Trivy] {} ({}) in {}", id, severity, target));
                }
            }
            if let Some(secrets) = result.get("Secrets").and_then(|s| s.as_array()) {
                for secret in secrets {
                    let title = secret
                        .get("Title")
                        .and_then(|t| t.as_str())
                        .unwrap_or("Secret");
                    let severity = secret
                        .get("Severity")
                        .and_then(|s| s.as_str())
                        .unwrap_or("UNKNOWN");
                    findings.push(format!("[Trivy] {} ({}) in {}", title, severity, target));
                }
            }
            if let Some(misconfigs) = result.get("Misconfigurations").and_then(|m| m.as_array()) {
                for misconfig in misconfigs {
                    let id = misconfig
                        .get("ID")
                        .and_then(|i| i.as_str())
                        .unwrap_or("Unknown");
                    let severity = misconfig
                        .get("Severity")
                        .and_then(|s| s.as_str())
                        .unwrap_or("UNKNOWN");
                    findings.push(format!("[Trivy] {} ({}) in {}", id, severity, target));
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

    // Semgrep exits non-zero only on internal/config errors (not for findings)
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return (
            ToolStatus::Error(format!(
                "Semgrep scan error (exit {}): {}",
                output.status.code().unwrap_or(-1),
                stderr.lines().next().unwrap_or("unknown error")
            )),
            vec![],
        );
    }

    let parsed: serde_json::Value = match serde_json::from_slice(&output.stdout) {
        Ok(v) => v,
        Err(e) => {
            return (
                ToolStatus::Error(format!("JSON parse error (version mismatch?): {}", e)),
                vec![],
            )
        }
    };

    let mut findings = Vec::new();
    if let Some(results) = parsed.get("results").and_then(|r| r.as_array()) {
        for result in results {
            let check_id = result
                .get("check_id")
                .and_then(|c| c.as_str())
                .unwrap_or("unknown");
            let path = result
                .get("path")
                .and_then(|p| p.as_str())
                .unwrap_or("unknown");
            let extra = result.get("extra");
            let severity = extra
                .and_then(|e| e.get("severity"))
                .and_then(|s| s.as_str())
                .unwrap_or("UNKNOWN");
            findings.push(format!("[Semgrep] {} ({}) in {}", check_id, severity, path));
        }
    }

    let mut has_errors = false;
    if let Some(errors) = parsed.get("errors").and_then(|e| e.as_array()) {
        if !errors.is_empty() {
            has_errors = true;
        }
    }

    let status = if has_errors {
        ToolStatus::Error("Semgrep scan reported errors".to_string())
    } else {
        ToolStatus::Success
    };

    (status, findings)
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

    // Bandit exits 1 when findings exist (expected behavior);
    // treat only other non-zero codes as actual errors
    let bandit_exit = output.status.code().unwrap_or(-1);
    if bandit_exit != 0 && bandit_exit != 1 {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return (
            ToolStatus::Error(format!(
                "Bandit scan error (exit {}): {}",
                bandit_exit,
                stderr.lines().next().unwrap_or("unknown error")
            )),
            vec![],
        );
    }

    let parsed: serde_json::Value = match serde_json::from_slice(&output.stdout) {
        Ok(v) => v,
        Err(e) => {
            return (
                ToolStatus::Error(format!("JSON parse error (version mismatch?): {}", e)),
                vec![],
            )
        }
    };

    let mut findings = Vec::new();
    if let Some(results) = parsed.get("results").and_then(|r| r.as_array()) {
        for result in results {
            let test_id = result
                .get("test_id")
                .and_then(|t| t.as_str())
                .unwrap_or("unknown");
            let severity = result
                .get("issue_severity")
                .and_then(|s| s.as_str())
                .unwrap_or("UNKNOWN");
            let filename = result
                .get("filename")
                .and_then(|f| f.as_str())
                .unwrap_or("unknown");
            findings.push(format!(
                "[Bandit] {} ({}) in {}",
                test_id, severity, filename
            ));
        }
    }

    let mut has_errors = false;
    if let Some(errors) = parsed.get("errors").and_then(|e| e.as_array()) {
        if !errors.is_empty() {
            has_errors = true;
        }
    }

    let status = if has_errors {
        ToolStatus::Error("Bandit scan reported errors".to_string())
    } else {
        ToolStatus::Success
    };

    (status, findings)
}
