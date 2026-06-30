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
        let is_py_file = mcp_server_path.ends_with(".py");

        let mut cmd = if is_py_file && mcp_server_path.contains("blt_mcp") {
            let mut c = Command::new("uv");
            c.current_dir("..");
            c.arg("run").arg("--no-sync").arg("-m").arg("blt_mcp.server");
            c
        } else if is_py_file {
            let mut c = Command::new("uv");
            c.arg("run").arg("--no-sync").arg(mcp_server_path);
            c
        } else {
            // E.g. running a compiled binary or specific executable command
            Command::new(mcp_server_path)
        };

        let mut child = cmd
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null()) // Discard MCP logs so they don't corrupt the TUI buffer
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
            let bytes_read = self.stdout_reader.read_line(&mut line).await?;
            if bytes_read == 0 {
                return Err("EOF reached on subprocess stdout pipe before receiving response".into());
            }

            let response: serde_json::Value = serde_json::from_str(&line)?;
            
            // Filters out notifications (which don't have id field)
            if let Some(id) = response.get("id") {
                if id.as_i64() == Some(expected_id) {
                    return Ok(response);
                }
            }
        }
    }
}
