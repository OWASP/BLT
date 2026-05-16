import subprocess
import json
import sys
import os

def test_resources_list():
    """Test resources/list MCP endpoint."""
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
        process.stdout.readline() # Skip init response
        
        # 2. Call resources/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/list",
            "params": {}
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        assert response_line, "Expected a response for resources/list"
        response = json.loads(response_line)
        
        assert response.get("id") == 2
        assert "result" in response
        assert "resources" in response["result"]
        
        resources = response["result"]["resources"]
        # FastMCP might return fixed resources here. 
        # blt://repos and blt://issues are fixed (no params).
        
        resource_uris = [r["uri"] for r in resources]
        assert "blt://repos" in resource_uris
        assert "blt://issues" in resource_uris
        
        # Check metadata
        for r in resources:
            assert "name" in r
            assert "uri" in r
            assert "description" in r
            assert r["uri"].startswith("blt://")
            
        # Specific checks
        repos_resource = next(r for r in resources if r["uri"] == "blt://repos")
        assert "repositories" in repos_resource["description"].lower()
        
        issues_resource = next(r for r in resources if r["uri"] == "blt://issues")
        assert "issues" in issues_resource["description"].lower()

        stats_resource = next(r for r in resources if r["uri"] == "blt://stats")
        assert "statistics" in stats_resource["description"].lower()

    finally:
        process.terminate()
        process.wait(timeout=2)

def test_resource_templates_list():
    """Test resources/templates/list MCP endpoint."""
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
        process.stdout.readline() # Skip init response
        
        # 2. Call resources/templates/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/templates/list",
            "params": {}
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        assert response_line, "Expected a response for resources/templates/list"
        response = json.loads(response_line)
        
        assert response.get("id") == 2
        assert "result" in response
        assert "resourceTemplates" in response["result"]
        
        templates = response["result"]["resourceTemplates"]
        template_uris = [t["uriTemplate"] for t in templates]
        
        assert "blt://repos/{repo_id}/issues" in template_uris
        assert "blt://issues/{issue_id}" in template_uris

    finally:
        process.terminate()
        process.wait(timeout=2)

def test_resource_read():
    """Test resources/read MCP endpoint."""
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
        
        # 2. Call resources/read for blt://repos
        read_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/read",
            "params": {
                "uri": "blt://repos"
            }
        }
        process.stdin.write(json.dumps(read_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        assert response_line, "Expected a response for resources/read"
        response = json.loads(response_line)
        
        assert response.get("id") == 2
        
        # We don't necessarily expect a success here if the API key is invalid, 
        # but we expect a valid JSON-RPC response (either result or error).
        assert "result" in response or "error" in response

    finally:
        process.terminate()
        process.wait(timeout=2)

def test_resource_read_parameterized():
    """Test resources/read with a parameterized URI (Issue #10)."""
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
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}
        }) + "\n")
        process.stdin.flush()
        process.stdout.readline()
        
        # 2. Call resources/read for a specific issue
        read_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/read",
            "params": {
                "uri": "blt://issues/123"
            }
        }
        process.stdin.write(json.dumps(read_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        assert response_line
        response = json.loads(response_line)
        
        assert response.get("id") == 2
        # Whether it succeeds or fails with 404, we expect a valid JSON-RPC structure
        assert "result" in response or "error" in response

    finally:
        process.terminate()
        process.wait(timeout=2)

def test_error_handling():
    """Test that invalid methods return a proper JSON-RPC error (Issue #8)."""
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
        # 1. Initialize (Required by MCP spec before other requests)
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}
        }) + "\n")
        process.stdin.flush()
        process.stdout.readline()

        # 2. Send a non-existent method
        invalid_request = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "non_existent_method",
            "params": {}
        }
        process.stdin.write(json.dumps(invalid_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        assert response_line
        response = json.loads(response_line)
        
        # FastMCP might return an error response or a log notification
        if "error" in response:
            assert response["error"]["code"] != 0
        elif response.get("method") == "notifications/message":
            assert response["params"]["level"] == "error"
        else:
            # If it's a success response for id 1, read the next line
            if response.get("id") == 1:
                response_line = process.stdout.readline()
                assert response_line
                response = json.loads(response_line)
                assert "error" in response or response.get("method") == "notifications/message"
            else:
                raise AssertionError(f"Expected an error response, got: {response}")
    finally:
        process.terminate()
        process.wait(timeout=2)
