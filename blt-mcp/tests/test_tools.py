import subprocess
import json
import sys
import os
import pytest
from tests.utils import read_jsonrpc_response
from blt_mcp.tools import summarize_issue_context_impl

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
        read_jsonrpc_response(process, 1)
        
        # 2. Call tools/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()
        
        response = read_jsonrpc_response(process, 2)
        assert "result" in response
        assert "tools" in response["result"]
        
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "submit_issue" in tool_names
        assert "add_comment" in tool_names

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

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
        read_jsonrpc_response(process, 1)
        
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
        
        response = read_jsonrpc_response(process, 2)
        assert "result" in response or "error" in response

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

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
        read_jsonrpc_response(process, 1)
        
        # Call tools/list
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n")
        process.stdin.flush()
        
        response = read_jsonrpc_response(process, 2)
        tools = response["result"]["tools"]
        
        # Verify submit_issue schema (Issue #12)
        submit_tool = next(t for t in tools if t["name"] == "submit_issue")
        properties = submit_tool["inputSchema"]["properties"]
        assert "title" in properties
        assert "description" in properties
        assert "repo_id" in properties
        assert "labels" in properties
        assert "assignee" in properties
        assert submit_tool["inputSchema"]["required"] == ["title", "description"]
        
        # Verify add_comment schema (Issue #13)
        comment_tool = next(t for t in tools if t["name"] == "add_comment")
        properties = comment_tool["inputSchema"]["properties"]
        assert "issue_id" in properties
        assert "comment_text" in properties
        assert "confirmed" in properties
        assert comment_tool["inputSchema"]["required"] == ["issue_id", "comment_text"]
        
        # Verify summarize_issue_context schema (Issue #14)
        summary_tool = next(t for t in tools if t["name"] == "summarize_issue_context")
        properties = summary_tool["inputSchema"]["properties"]
        assert "issue_id" in properties
        assert summary_tool["inputSchema"]["required"] == ["issue_id"]

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

def test_tool_validation_errors():
    """Test that malformed/invalid inputs are rejected with clear JSON-RPC errors."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env
    )
    
    try:
        # 1. Initialize
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}
        }) + "\n")
        process.stdin.flush()
        read_jsonrpc_response(process, 1)
        
        # 2. Call submit_issue missing required 'title'
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 2,
            "method": "tools/call",
            "params": {
                "name": "submit_issue",
                "arguments": {
                    "description": "Missing title"
                }
            }
        }) + "\n")
        process.stdin.flush()
        
        response = read_jsonrpc_response(process, 2)
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "Missing required parameter" in response["error"]["message"]

        # 3. Call submit_issue with invalid type for repo_id (integer instead of string)
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 3,
            "method": "tools/call",
            "params": {
                "name": "submit_issue",
                "arguments": {
                    "title": "Valid title",
                    "description": "Valid description",
                    "repo_id": 123
                }
            }
        }) + "\n")
        process.stdin.flush()
        
        response = read_jsonrpc_response(process, 3)
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "must be of type str" in response["error"]["message"]

        # 4. Call submit_issue with blank title
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 4,
            "method": "tools/call",
            "params": {
                "name": "submit_issue",
                "arguments": {
                    "title": "   ",
                    "description": "Valid description"
                }
            }
        }) + "\n")
        process.stdin.flush()
        
        response = read_jsonrpc_response(process, 4)
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "cannot be empty" in response["error"]["message"]

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

def test_tool_confirmation_flow():
    """Test that write operations fail without the confirmed flag."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env
    )
    
    try:
        # 1. Initialize
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}
        }) + "\n")
        process.stdin.flush()
        read_jsonrpc_response(process, 1)
        
        # 2. Call submit_issue without confirmation
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 2,
            "method": "tools/call",
            "params": {
                "name": "submit_issue",
                "arguments": {
                    "title": "Valid title",
                    "description": "Valid description"
                }
            }
        }) + "\n")
        process.stdin.flush()
        
        response = read_jsonrpc_response(process, 2)
        assert "result" in response
        assert response["result"].get("isError") is True
        assert "requires confirmation" in response["result"]["content"][0]["text"]

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

@pytest.mark.asyncio
async def test_summarize_issue_context_logic():
    """Verify that summarize_issue_context_impl correctly formats the issue and comments."""
    mock_responses = {
        "/bugs/123": json.dumps({
            "title": "SQL Injection in Login Form",
            "status": "open",
            "description": "Found a SQL injection vulnerability in the username field."
        }),
        "/bugs/123/comments": json.dumps([
            {"content": "I confirmed this vulnerability.", "author": "security_researcher"},
            {"content": "Working on a fix now.", "author": "developer_bob"}
        ])
    }
    
    async def mock_fetch(path, context=None):
        if path in mock_responses:
            return mock_responses[path]
        raise RuntimeError("Not found")
        
    summary = await summarize_issue_context_impl("123", mock_fetch)
    
    assert "Issue ID: 123" in summary
    assert "Title: SQL Injection in Login Form" in summary
    assert "Status: open" in summary
    assert "Found a SQL injection vulnerability in the username field." in summary
    assert "- security_researcher: I confirmed this vulnerability." in summary
    assert "- developer_bob: Working on a fix now." in summary

@pytest.mark.asyncio
async def test_summarize_issue_context_missing_issue():
    """Verify that summarize_issue_context_impl handles missing issues gracefully."""
    async def mock_fetch(path, context=None):
        raise RuntimeError("404 Not Found")
        
    summary = await summarize_issue_context_impl("999", mock_fetch)
    assert "Error: Issue with ID '999' not found" in summary
