#![allow(dead_code)]
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, ChildStdout, Command};
use serde_json::json;

pub struct McpSubprocessClient {
    _child: Child,
    stdin: ChildStdin,
    stdout_reader: BufReader<ChildStdout>,
    request_id: i64,
}

impl McpSubprocessClient {
    /// Spawn the Python MCP server as a subprocess.
    pub async fn spawn(mcp_server_path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let parts: Vec<&str> = mcp_server_path.split_whitespace().collect();
        if parts.is_empty() {
            return Err("Empty MCP server path provided".into());
        }

        let mut cmd = Command::new(parts[0]);
        for arg in &parts[1..] {
            cmd.arg(arg);
        }

        let home = dirs::home_dir().unwrap_or_default();
        let config_dir = home.join(".blt-mcp");
        let _ = std::fs::create_dir_all(&config_dir);
        let log_path = config_dir.join("mcp_error.log");
        let stderr_file = std::fs::OpenOptions::new().create(true).write(true).truncate(true).open(log_path)?;

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

    /// Perform the initialize lifecycle handshake.
    pub async fn initialize(&mut self) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let id = self.next_id();
        let payload = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "blt-cli",
                    "version": "1.0.0"
                }
            }
        });

        self.send_request(&payload).await?;
        let resp = self.read_response(id).await?;
        
        // Let the server know we are initialized per MCP lifecycle
        let init_notif = json!({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        });
        self.send_request(&init_notif).await?;

        Ok(resp)
    }

    /// Read an MCP resource via its URI scheme.
    pub async fn read_resource(&mut self, uri: &str) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let id = self.next_id();
        let payload = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        });

        self.send_request(&payload).await?;
        self.read_response(id).await
    }

    /// Call an MCP tool.
    pub async fn call_tool(&mut self, name: &str, arguments: serde_json::Value) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let id = self.next_id();
        let payload = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        });

        self.send_request(&payload).await?;
        self.read_response(id).await
    }

    fn next_id(&mut self) -> i64 {
        self.request_id += 1;
        self.request_id
    }

    async fn send_request(&mut self, request: &serde_json::Value) -> Result<(), Box<dyn std::error::Error>> {
        let mut line = serde_json::to_string(request)?;
        line.push('\n');
        self.stdin.write_all(line.as_bytes()).await?;
        self.stdin.flush().await?;
        Ok(())
    }

    async fn read_response(&mut self, expected_id: i64) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let mut line = String::new();
        loop {
            line.clear();
            let read_fut = self.stdout_reader.read_line(&mut line);
            let bytes_read = match tokio::time::timeout(std::time::Duration::from_secs(10), read_fut).await {
                Ok(Ok(n)) => n,
                Ok(Err(e)) => return Err(e.into()),
                Err(_) => return Err("MCP Subprocess read timeout".into()),
            };
            
            if bytes_read == 0 {
                return Err("EOF reached on subprocess stdout pipe before receiving response".into());
            }

            let response: serde_json::Value = serde_json::from_str(&line)?;
            
            // Filters out notifications (which don't have id field)
            if let Some(id) = response.get("id") {
                if id.as_i64() == Some(expected_id) {
                    if let Some(error) = response.get("error") {
                        let msg = error.get("message").and_then(|m| m.as_str()).unwrap_or("Unknown MCP JSON-RPC error");
                        return Err(format!("MCP Error: {}", msg).into());
                    }
                    return Ok(response);
                }
            }
        }
    }
}
