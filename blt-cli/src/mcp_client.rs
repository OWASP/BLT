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
//! - `call_tool(name, arguments)`: Invokes an registered server tool, returns the execution result.
//! - `send_request()` & `send_notification()`: Formats and sends standard JSON-RPC packets.
//! - `read_response(expected_id)`: Asynchronously reads lines from stdout until it captures a matching JSON-RPC response ID.
//!
//! Error Handling:
//! - Performs timeouts (10 seconds) on reads to prevent blocking the TUI thread.
//! - Parses and propagates server errors.

#![allow(dead_code)]

use serde_json::json;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, ChildStdout, Command};

pub struct McpSubprocessClient {
    _child: Child,
    stdin: ChildStdin,
    stdout_reader: BufReader<ChildStdout>,
    request_id: i64,
}

impl McpSubprocessClient {
    /// Spawn the Python MCP server as a subprocess.
    pub async fn spawn(cmd_name: &str, args: &[String]) -> Result<Self, Box<dyn std::error::Error>> {
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
        })
    }

    pub async fn initialize(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let req = json!({
            "jsonrpc": "2.0",
            "id": self.request_id,
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
        let _resp = self.read_response(self.request_id).await?;
        self.request_id += 1;

        // Send initialized notification
        let notif = json!({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        });
        self.send_notification(notif).await?;

        Ok(())
    }

    pub async fn list_resources(&mut self) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let req = json!({
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "resources/list"
        });

        self.send_request(req).await?;
        let resp = self.read_response(self.request_id).await?;
        self.request_id += 1;
        Ok(resp)
    }

    /// Read an MCP resource via its URI scheme.
    pub async fn read_resource(
        &mut self,
        uri: &str,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let req = json!({
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        });

        self.send_request(req).await?;
        let resp = self.read_response(self.request_id).await?;
        self.request_id += 1;
        Ok(resp)
    }

    /// Call an MCP tool.
    pub async fn call_tool(
        &mut self,
        name: &str,
        arguments: serde_json::Value,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let req = json!({
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        });

        self.send_request(req).await?;
        let resp = self.read_response(self.request_id).await?;
        self.request_id += 1;
        Ok(resp)
    }

    async fn send_request(&mut self, req: serde_json::Value) -> Result<(), Box<dyn std::error::Error>> {
        let line = serde_json::to_string(&req)? + "\n";
        self.stdin.write_all(line.as_bytes()).await?;
        self.stdin.flush().await?;
        Ok(())
    }

    async fn send_notification(
        &mut self,
        notif: serde_json::Value,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let line = serde_json::to_string(&notif)? + "\n";
        self.stdin.write_all(line.as_bytes()).await?;
        self.stdin.flush().await?;
        Ok(())
    }

    async fn read_response(
        &mut self,
        expected_id: i64,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let mut line = String::new();
        let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(10);
        loop {
            let now = tokio::time::Instant::now();
            if now >= deadline {
                return Err("MCP Subprocess read timeout".into());
            }
            let remaining = deadline - now;
            line.clear();
            let read_fut = self.stdout_reader.read_line(&mut line);
            let bytes_read =
                match tokio::time::timeout(remaining, read_fut).await {
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
                        return Err(format!("MCP Error: {}", msg).into());
                    }
                    return Ok(response);
                }
            }
        }
    }
}
