import subprocess
import json
import sys
import os

def test_tools_list():
    """Test tools/list MCP endpoint."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    try:
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        process.stdout.readline()
        
        # 2. Call tools/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        assert response_line, "Expected a response for tools/list"
        response = json.loads(response_line)
        
        assert response.get("id") == 2
        assert "result" in response
        assert "tools" in response["result"]
        
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "submit_issue" in tool_names
        assert "add_comment" in tool_names

    finally:
        process.terminate()
        process.wait(timeout=2)

def test_tool_call():
    """Test tools/call MCP endpoint."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    try:
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        process.stdout.readline()
        
        # 2. Call tools/call for submit_issue (will likely fail due to no API key, but verifies protocol)
        call_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "submit_issue",
                "arguments": {
                    "title": "Test Issue",
                    "description": "Testing tools/call protocol"
                }
            }
        }
        process.stdin.write(json.dumps(call_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        assert response_line, "Expected a response for tools/call"
        response = json.loads(response_line)
        
        assert response.get("id") == 2
        assert "result" in response or "error" in response

    finally:
        process.terminate()
        process.wait(timeout=2)

def test_tool_schemas():
    """Verify tool input schemas for Issues 12 and 13."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env
    )
    
    try:
        # Initialize
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}
        }) + "\n")
        process.stdin.flush()
        process.stdout.readline()
        
        # Call tools/list
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n")
        process.stdin.flush()
        
        response = json.loads(process.stdout.readline())
        tools = response["result"]["tools"]
        
        # Verify submit_issue schema (Issue #12)
        submit_tool = next(t for t in tools if t["name"] == "submit_issue")
        properties = submit_tool["inputSchema"]["properties"]
        assert "title" in properties
        assert "description" in properties
        assert "repo_id" in properties
        assert submit_tool["inputSchema"]["required"] == ["title", "description"]
        
        # Verify add_comment schema (Issue #13)
        comment_tool = next(t for t in tools if t["name"] == "add_comment")
        properties = comment_tool["inputSchema"]["properties"]
        assert "issue_id" in properties
        assert "content" in properties
        assert comment_tool["inputSchema"]["required"] == ["issue_id", "content"]

    finally:
        process.terminate()
        process.wait(timeout=2)
