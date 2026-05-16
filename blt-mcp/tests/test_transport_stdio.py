import subprocess
import json
import sys
import os
from tests.utils import read_jsonrpc_response

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
        response = read_jsonrpc_response(process, 1)
        
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
        assert "prompts" in result["capabilities"]
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
        response = read_jsonrpc_response(process, 1)
        
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
        # or it might just respond to the valid request.
        response = read_jsonrpc_response(process, 2)
        assert response.get("id") == 2
    finally:
        process.terminate()
        process.wait(timeout=2)
