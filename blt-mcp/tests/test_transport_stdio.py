import subprocess
import json
import sys
import os

def test_initialize_handshake():
    """Test valid JSON-RPC initialize message and its response structure."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    
    # We set environment variables if needed
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
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        req_str = json.dumps(init_request) + "\n"
        process.stdin.write(req_str)
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        
        assert response_line, "Expected a response from stdout"
        response = json.loads(response_line)
        
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == 1
        assert "result" in response
        
        result = response["result"]
        
        # Verify protocol version
        assert "protocolVersion" in result
        
        # Verify server metadata (name, version)
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "blt-mcp"
        assert "version" in result["serverInfo"]
        
        # Verify supported capabilities
        assert "capabilities" in result
        assert "tools" in result["capabilities"]
        assert "resources" in result["capabilities"]
    finally:
        process.terminate()
        process.wait(timeout=2)

def test_capability_negotiation():
    """Test that the server properly negotiates capabilities with the client."""
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
        # Client advertises specific capabilities (like sampling or roots)
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "sampling": {},
                    "roots": {"listChanged": True}
                },
                "clientInfo": {
                    "name": "test-client-with-capabilities",
                    "version": "1.0.0"
                }
            }
        }
        
        req_str = json.dumps(init_request) + "\n"
        process.stdin.write(req_str)
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        assert response_line, "Expected a response from stdout"
        response = json.loads(response_line)
        
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == 1
        
        # Verify server capabilities are correct regardless of client capabilities
        capabilities = response["result"]["capabilities"]
        assert "tools" in capabilities
        assert "resources" in capabilities
        assert "prompts" in capabilities
        
    finally:
        process.terminate()
        process.wait(timeout=2)

def test_malformed_input():
    """Test that the server handles malformed JSON without crashing."""
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
        # Send malformed JSON
        process.stdin.write("{malformed_json\n")
        process.stdin.flush()
        
        # Send a valid request after malformed one to ensure it's still alive
        init_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        req_str = json.dumps(init_request) + "\n"
        process.stdin.write(req_str)
        process.stdin.flush()
        
        # The MCP server might send an error for the malformed JSON
        # and then process the valid request.
        line1 = process.stdout.readline()
        assert line1, "Expected a response from stdout"
        resp1 = json.loads(line1)
        
        if resp1.get("id") != 2:
            # First line might be an error response or a log notification
            if "error" in resp1:
                pass
            elif resp1.get("method") == "notifications/message":
                assert resp1["params"]["level"] == "error", f"Expected error level notification, got: {resp1}"
            else:
                assert False, f"Expected an error response for malformed JSON, got: {resp1}"
            
            # Second line should be our valid request response
            line2 = process.stdout.readline()
            assert line2, "Expected a response from stdout"
            resp2 = json.loads(line2)
            assert resp2.get("id") == 2, f"Expected id 2 response, got {resp2}"
        else:
            # Or it might just ignore the malformed JSON and respond to the valid one
            assert resp1.get("id") == 2
    finally:
        process.terminate()
        process.wait(timeout=2)
