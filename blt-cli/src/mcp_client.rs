//! Client Library to Communicate with a Local Python MCP Server Subprocess.
//!
//! This module implements JSON-RPC communication over piped stdio streams with the local
//! Python-based FastMCP server subprocess.
//!
//! Key Functions and Methods:
//! - `McpSubprocessClient::spawn(executable, args)`: Spawns the subprocess (e.g. `uv` or `python`), redirection loops,
//!   and opens stderr file handlers pointing to `~/.blt-mcp/mcp_error.log`.
//! - `initialize()`: Conducts the protocol version negotiation handshake and notifies the server of completion.
//! - `list_resources()`: Requests the list of resources supported by the server.
//! - `read_resource(uri)`: Retrieves text contents for a given resource URI string.
//! - `call_tool(name, arguments)`: Invokes a registered server tool, returns the execution result.
//! - `send_request()` & `send_notification()`: Formats and sends standard JSON-RPC packets.
//! - `read_response(expected_id)`: Asynchronously reads lines from stdout until it captures a matching JSON-RPC response ID.
//!
//! Error Handling:
//! - Performs timeouts (75 seconds default) on reads to prevent blocking the TUI thread.
//! - Parses and propagates server errors.
//! - Employs a cancellation-safe `PoisonGuard` on all active read and write operations;
//!   if a future is dropped (e.g., timed out or canceled), the client is marked as corrupted
//!   (`is_corrupted = true`) to prevent subsequent request/response desynchronization.

#![allow(dead_code)]

use serde_json::json;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, ChildStdout, Command};

/// Default response read timeout (75 seconds to cover long-running vision AI tools).
pub const DEFAULT_READ_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(75);

/// A guard that marks the client as corrupted/poisoned if it is dropped before being defused.
/// This ensures cancellation safety when futures are dropped due to timeouts or other cancellations.
struct PoisonGuard<'a> {
    is_corrupted: &'a mut bool,
    active: bool,
}

impl<'a> PoisonGuard<'a> {
    fn new(is_corrupted: &'a mut bool) -> Self {
        Self {
            is_corrupted,
            active: true,
        }
    }

    fn defuse(mut self) {
        self.active = false;
    }
}

impl<'a> Drop for PoisonGuard<'a> {
    fn drop(&mut self) {
        if self.active {
            *self.is_corrupted = true;
        }
    }
}

pub struct McpSubprocessClient {
    _child: Child,
    stdin: ChildStdin,
    stdout_reader: BufReader<ChildStdout>,
    request_id: i64,
    pub cmd_name: String,
    pub cmd_args: Vec<String>,
    pub is_corrupted: bool,
}

impl McpSubprocessClient {
    /// Spawn the Python MCP server as a subprocess.
    pub async fn spawn(
        cmd_name: &str,
        args: &[String],
    ) -> Result<Self, Box<dyn std::error::Error>> {
        if cmd_name.trim().is_empty() {
            return Err("Empty MCP server path provided".into());
        }

        let mut cmd = Command::new(cmd_name);
        for arg in args {
            cmd.arg(arg);
        }

        let home = dirs::home_dir().unwrap_or_default();
        let config_dir = home.join(".blt-mcp");
        let _ = std::fs::create_dir_all(&config_dir);
        let log_path = config_dir.join("mcp_error.log");
        let stderr_file = std::fs::OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(log_path)?;

        let mut child = cmd
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::from(stderr_file))
            .kill_on_drop(true)
            .spawn()?;

        let stdin = child.stdin.take().ok_or("Failed to grab stdin pipe")?;
        let stdout = child.stdout.take().ok_or("Failed to grab stdout pipe")?;
        let stdout_reader = BufReader::new(stdout);

        Ok(McpSubprocessClient {
            _child: child,
            stdin,
            stdout_reader,
            request_id: 1,
            cmd_name: cmd_name.to_string(),
            cmd_args: args.to_vec(),
            is_corrupted: false,
        })
    }

    pub async fn initialize(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let req_id = self.request_id;
        self.request_id += 1;

        let req = json!({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "blt-cli",
                    "version": "0.1.0"
                }
            }
        });

        self.send_request(req).await?;
        let _resp = self.read_response(req_id).await?;

        // Send initialized notification
        let notif = json!({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        });
        self.send_notification(notif).await?;

        Ok(())
    }

    pub async fn list_resources(
        &mut self,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let req_id = self.request_id;
        self.request_id += 1;

        let req = json!({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "resources/list"
        });

        self.send_request(req).await?;
        let resp = self.read_response(req_id).await?;
        Ok(resp)
    }

    /// Read an MCP resource via its URI scheme.
    pub async fn read_resource(
        &mut self,
        uri: &str,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let req_id = self.request_id;
        self.request_id += 1;

        let req = json!({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        });

        self.send_request(req).await?;
        let resp = self.read_response(req_id).await?;
        Ok(resp)
    }

    /// Call an MCP tool.
    pub async fn call_tool(
        &mut self,
        name: &str,
        arguments: serde_json::Value,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let req_id = self.request_id;
        self.request_id += 1;

        let req = json!({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        });

        self.send_request(req).await?;
        let resp = self.read_response(req_id).await?;
        Ok(resp)
    }

    async fn send_request(
        &mut self,
        req: serde_json::Value,
    ) -> Result<(), Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let guard = PoisonGuard::new(&mut self.is_corrupted);
        let line = serde_json::to_string(&req)? + "\n";
        self.stdin.write_all(line.as_bytes()).await?;
        self.stdin.flush().await?;
        guard.defuse();
        Ok(())
    }

    async fn send_notification(
        &mut self,
        notif: serde_json::Value,
    ) -> Result<(), Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let guard = PoisonGuard::new(&mut self.is_corrupted);
        let line = serde_json::to_string(&notif)? + "\n";
        self.stdin.write_all(line.as_bytes()).await?;
        self.stdin.flush().await?;
        guard.defuse();
        Ok(())
    }

    async fn read_response(
        &mut self,
        expected_id: i64,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        self.read_response_with_timeout(expected_id, DEFAULT_READ_TIMEOUT)
            .await
    }

    pub async fn read_response_with_timeout(
        &mut self,
        expected_id: i64,
        timeout: std::time::Duration,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let guard = PoisonGuard::new(&mut self.is_corrupted);
        let mut line = String::new();
        let deadline = tokio::time::Instant::now() + timeout;
        loop {
            let now = tokio::time::Instant::now();
            if now >= deadline {
                return Err("MCP Subprocess read timeout".into());
            }
            let remaining = deadline - now;
            line.clear();
            let read_fut = self.stdout_reader.read_line(&mut line);
            let bytes_read = match tokio::time::timeout(remaining, read_fut).await {
                Ok(Ok(n)) => n,
                Ok(Err(e)) => return Err(e.into()),
                Err(_) => return Err("MCP Subprocess read timeout".into()),
            };

            if bytes_read == 0 {
                return Err(
                    "EOF reached on subprocess stdout pipe before receiving response".into(),
                );
            }

            let response: serde_json::Value = serde_json::from_str(&line)?;

            // Filters out notifications (which don't have id field)
            if let Some(id) = response.get("id") {
                if id.as_i64() == Some(expected_id) {
                    if let Some(error) = response.get("error") {
                        let msg = error
                            .get("message")
                            .and_then(|m| m.as_str())
                            .unwrap_or("Unknown MCP JSON-RPC error");
                        guard.defuse();
                        return Err(format!("MCP Error: {}", msg).into());
                    }
                    guard.defuse();
                    return Ok(response);
                }
            }
        }
    }

    /// Check if the subprocess is still running.
    pub fn is_alive(&mut self) -> bool {
        if self.is_corrupted {
            return false;
        }
        match self._child.try_wait() {
            Ok(None) => true, // Still running
            _ => false,       // Terminated or failed
        }
    }

    /// Send a lightweight MCP ping request.
    pub async fn ping(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        self.ping_with_timeout(std::time::Duration::from_secs(5))
            .await
    }

    /// Send a lightweight MCP ping request with a custom timeout covering both send and read.
    pub async fn ping_with_timeout(
        &mut self,
        timeout: std::time::Duration,
    ) -> Result<(), Box<dyn std::error::Error>> {
        if self.is_corrupted {
            return Err("MCP Subprocess client is corrupted/poisoned due to a previous timeout or cancellation".into());
        }
        let req_id = self.request_id;
        self.request_id += 1;

        let req = json!({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "ping",
            "params": {}
        });

        tokio::time::timeout(timeout, async {
            self.send_request(req).await?;
            let _resp = self.read_response_with_timeout(req_id, timeout).await?;
            Ok::<(), Box<dyn std::error::Error>>(())
        })
        .await
        .map_err(|_| "Ping operation timed out")?
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    // Helper to run commands that simulate different server behaviors, trying python3, python, sh, and bash
    async fn run_mock_server_test<F, Fut>(python_script: &str, sh_script: &str, f: F)
    where
        F: FnOnce(McpSubprocessClient) -> Fut,
        Fut: std::future::Future<Output = ()>,
    {
        let mut client =
            McpSubprocessClient::spawn("python3", &["-c".to_string(), python_script.to_string()])
                .await
                .ok();
        if client.is_none() {
            client = McpSubprocessClient::spawn(
                "python",
                &["-c".to_string(), python_script.to_string()],
            )
            .await
            .ok();
        }
        if client.is_none() {
            client = McpSubprocessClient::spawn("sh", &["-c".to_string(), sh_script.to_string()])
                .await
                .ok();
        }
        if client.is_none() {
            client = McpSubprocessClient::spawn("bash", &["-c".to_string(), sh_script.to_string()])
                .await
                .ok();
        }

        if let Some(c) = client {
            f(c).await;
        } else {
            eprintln!("Skipping test: no python3, python, sh, or bash interpreter found in test environment.");
        }
    }

    #[tokio::test]
    async fn test_client_normal_reuse() {
        // Normal server that reads requests and responds properly
        let py_script = r#"
import sys, json
for line in sys.stdin:
    req = json.loads(line)
    resp = {"jsonrpc": "2.0", "id": req["id"], "result": "ok"}
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
"#;
        let sh_script = r#"
while read line; do
  id=$(printf '%s\n' "$line" | sed -n 's/.*"id":[[:space:]]*\([0-9][0-9]*\).*/\1/p')
  printf '{"jsonrpc":"2.0","id":%s,"result":"ok"}\n' "$id"
done
"#;
        run_mock_server_test(py_script, sh_script, |mut client| async move {
            assert!(!client.is_corrupted);

            let res1 = client.ping().await;
            assert!(res1.is_ok());
            assert!(!client.is_corrupted);

            let res2 = client.ping().await;
            assert!(res2.is_ok());
            assert!(!client.is_corrupted);
        })
        .await;
    }

    #[tokio::test]
    async fn test_client_poison_on_partial_read_timeout() {
        // Server that receives a request, sends a partial JSON, and stalls
        let py_script = r#"
import sys, time
sys.stdin.readline()
sys.stdout.write('{"jsonrpc": "2.0", "id": 1,')
sys.stdout.flush()
time.sleep(10)
"#;
        let sh_script = r#"
read line
printf '{"jsonrpc": "2.0", "id": 1,'
sleep 10
"#;
        run_mock_server_test(py_script, sh_script, |mut client| async move {
            assert!(!client.is_corrupted);

            // Timeout set to 200ms
            let res = client.ping_with_timeout(Duration::from_millis(200)).await;
            assert!(res.is_err());
            assert!(client.is_corrupted);

            // Subsequent pings should immediately return Err of corruption
            let res2 = client.ping().await;
            assert!(res2.is_err());
            let err_msg = res2.unwrap_err().to_string();
            assert!(err_msg.contains("corrupted") || err_msg.contains("poisoned"));
        })
        .await;
    }

    #[tokio::test]
    async fn test_client_poison_on_cancellation() {
        // Server that stalls forever
        let py_script = r#"
import time
time.sleep(10)
"#;
        let sh_script = "sleep 10";
        run_mock_server_test(py_script, sh_script, |mut client| async move {
            assert!(!client.is_corrupted);

            // Drop/cancel the ping future by timing out the task using tokio select or timeout
            let res = tokio::time::timeout(Duration::from_millis(200), client.ping()).await;
            assert!(res.is_err()); // tokio timeout error

            // The client must be poisoned/corrupted because the future was dropped/canceled
            assert!(client.is_corrupted);

            // Subsequent requests must fail immediately
            let res2 = client.ping().await;
            assert!(res2.is_err());
        })
        .await;
    }
}
