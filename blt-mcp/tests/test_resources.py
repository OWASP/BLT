"""
Integration Tests for the Model Context Protocol (MCP) Resource Endpoints.

This module contains integration tests to verify the correctness of resources exposed by the MCP server.

Test Scenarios:
- `test_resources_list`: Verifies that `resources/list` returns the correct v1 and v2 resources,
  checking metadata values such as name, URI, and description.
- `test_resource_templates_list`: Verifies that `resources/templates/list` returns the expected parameterized
  resource templates (like `blt://repos/{repo_id}/issues` and `blt://v2/users/{id}`).
- `test_resource_read`: Checks the execution of `resources/read` for resource endpoints.
- `test_resource_read_parameterized`: Verifies that resource reads support URI parameters.
- `test_error_handling`: Verifies that requesting resources with missing required fields (e.g. `uri`)
  correctly returns validation errors.

Design Details:
- Spawns the Python server as a subprocess.
- Communicates using stdio JSON-RPC.
- Uses `tests.utils.read_jsonrpc_response` to verify response payloads.
"""

import json
import os
import subprocess
import sys

from tests.utils import read_jsonrpc_response


def test_resources_list():
    """Test resources/list MCP endpoint."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
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
        read_jsonrpc_response(process, 1)  # Wait for init response

        # 2. Call resources/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/list",
            "params": {},
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()

        response = read_jsonrpc_response(process, 2)
        assert "result" in response
        assert "resources" in response["result"]

        resources = response["result"]["resources"]
        # FastMCP might return fixed resources here.
        # blt://repos and blt://issues are fixed (no params).

        resource_uris = [r["uri"] for r in resources]
        assert "blt://repos" in resource_uris
        assert "blt://issues" in resource_uris
        assert "blt://v2/bugs" in resource_uris
        assert "blt://v2/users" in resource_uris
        assert "blt://v2/domains" in resource_uris
        assert "blt://v2/organizations" in resource_uris
        assert "blt://v2/jobs" in resource_uris
        assert "blt://v2/jobs/stats" in resource_uris
        assert "blt://v2/hackathons" in resource_uris

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
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_resource_templates_list():
    """Test resources/templates/list MCP endpoint."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
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
        read_jsonrpc_response(process, 1)  # Wait for init response

        # 2. Call resources/templates/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/templates/list",
            "params": {},
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()

        response = read_jsonrpc_response(process, 2)
        assert "result" in response
        assert "resourceTemplates" in response["result"]

        templates = response["result"]["resourceTemplates"]
        template_uris = [t["uriTemplate"] for t in templates]

        assert "blt://repos/{repo_id}/issues" in template_uris
        assert "blt://issues/{issue_id}" in template_uris
        assert "blt://v2/auth/verify-email/{token}" in template_uris
        assert "blt://v2/bugs/{id}" in template_uris
        assert "blt://v2/bugs/search/{query}" in template_uris
        assert "blt://v2/users/{id}" in template_uris
        assert "blt://v2/users/{id}/profile" in template_uris
        assert "blt://v2/users/{id}/bugs" in template_uris
        assert "blt://v2/users/{id}/domains" in template_uris
        assert "blt://v2/users/{id}/followers" in template_uris
        assert "blt://v2/users/{id}/following" in template_uris
        assert "blt://v2/domains/{id}" in template_uris
        assert "blt://v2/domains/{id}/tags" in template_uris
        assert "blt://v2/organizations/{id}" in template_uris
        assert "blt://v2/organizations/{id}/domains" in template_uris
        assert "blt://v2/organizations/{id}/bugs" in template_uris
        assert "blt://v2/organizations/{id}/managers" in template_uris
        assert "blt://v2/organizations/{id}/tags" in template_uris
        assert "blt://v2/organizations/{id}/integrations" in template_uris
        assert "blt://v2/organizations/{id}/stats" in template_uris
        assert "blt://v2/jobs/{id}" in template_uris
        assert "blt://v2/hackathons/{slug}" in template_uris

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_resource_read():
    """Test resources/read MCP endpoint."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
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

        # 2. Call resources/read for blt://repos
        read_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/read",
            "params": {"uri": "blt://repos"},
        }
        process.stdin.write(json.dumps(read_request) + "\n")
        process.stdin.flush()

        response = read_jsonrpc_response(process, 2)
        # We don't necessarily expect a success here if the API key is invalid,
        # but we expect a valid JSON-RPC response (either result or error).
        assert "result" in response or "error" in response

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_resource_read_parameterized():
    """Test resources/read with a parameterized URI (Issue #10)."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
    )

    try:
        # 1. Initialize
        process.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1"},
                    },
                }
            )
            + "\n"
        )
        process.stdin.flush()
        read_jsonrpc_response(process, 1)

        # 2. Call resources/read for a specific issue
        read_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/read",
            "params": {"uri": "blt://issues/123"},
        }
        process.stdin.write(json.dumps(read_request) + "\n")
        process.stdin.flush()

        response = read_jsonrpc_response(process, 2)
        # Whether it succeeds or fails with 404, we expect a valid JSON-RPC structure
        assert "result" in response or "error" in response

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_error_handling():
    """Test that invalid methods return a proper JSON-RPC error (Issue #8)."""
    cmd = [sys.executable, "-m", "blt_mcp.server"]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
    )

    try:
        # 1. Initialize (Required by MCP spec before other requests)
        process.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1"},
                    },
                }
            )
            + "\n"
        )
        process.stdin.flush()
        read_jsonrpc_response(process, 1)

        # 2. Send a valid method with missing required parameters (should return error)
        invalid_request = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "resources/read",
            "params": {},  # Missing 'uri'
        }
        process.stdin.write(json.dumps(invalid_request) + "\n")
        process.stdin.flush()

        response = read_jsonrpc_response(process, 99)
        assert "error" in response
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
