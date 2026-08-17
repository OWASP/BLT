"""
Integration Tests for the Prompts Primitive Endpoints.

This module validates registered prompt listing (`prompts/list`) and template retrieval (`prompts/get`)
across the FastMCP server via JSON-RPC stdio pipes.

Test Scenarios:
- `test_prompts_list`: Verifies that `prompts/list` returns all three registered prompts (`triage_vulnerability`,
  `plan_remediation`, `review_contribution`).
- `test_prompt_get_triage`: Verifies that `prompts/get` for `triage_vulnerability` returns the expected prompt user messages
  with parameter interpolation.
"""

import json
import os
import subprocess
import sys

from tests.utils import read_jsonrpc_response


def test_prompts_list():
    """Verify that the prompts list returns all three registered prompts."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
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
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        read_jsonrpc_response(process, 1)

        # 2. List Prompts
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "prompts/list",
            "params": {},
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()

        response = read_jsonrpc_response(process, 2)
        assert "result" in response
        assert "prompts" in response["result"]

        prompts = response["result"]["prompts"]
        names = [p["name"] for p in prompts]
        assert "triage_vulnerability" in names
        assert "plan_remediation" in names
        assert "review_contribution" in names

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_prompt_get_triage():
    """Verify prompts/get for triage_vulnerability returns the expected prompt content."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
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
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        read_jsonrpc_response(process, 1)

        # 2. Get prompt
        get_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "prompts/get",
            "params": {
                "name": "triage_vulnerability",
                "arguments": {
                    "vulnerability_description": "SQL Injection in Search Form",
                    "affected_component": "API Search Endpoint",
                },
            },
        }
        process.stdin.write(json.dumps(get_request) + "\n")
        process.stdin.flush()

        response = read_jsonrpc_response(process, 2)
        assert "result" in response
        assert "messages" in response["result"]
        messages = response["result"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]

        # FastMCP text content might be a dict or a string depending on version, let's verify text content
        if isinstance(content, dict):
            text_val = content.get("text", "")
        else:
            text_val = str(content)

        assert "SQL Injection in Search Form" in text_val
        assert "API Search Endpoint" in text_val

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
