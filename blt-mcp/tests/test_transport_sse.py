"""
Server-Sent Events (SSE) Transport Protocol Integration Tests.

This module validates that the MCP server operates correctly under the SSE transport layer (`--transport sse`),
verifying unauthenticated requests, query parameter token auth (`/sse?token=...`), Bearer token auth, and anonymous execution.

Test Scenarios:
- `test_sse_transport_unauthenticated`: Verifies 401 Unauthorized responses for missing or bad tokens,
  and successful connection for query parameter and Authorization header token authentication.
- `test_sse_transport_anonymous`: Verifies that if `BLT_MCP_TOKEN` is unset, SSE endpoints accept anonymous connections.
"""

import os
import subprocess
import sys
import time

import httpx


def test_sse_transport_unauthenticated():
    """Verify that if BLT_MCP_TOKEN is set, unauthorized requests get 401."""
    cmd = [
        sys.executable,
        "-m",
        "blt_mcp.cli",
        "run",
        "--transport",
        "sse",
        "--port",
        "8085",
    ]
    env = os.environ.copy()
    env["BLT_MCP_TOKEN"] = "super-secret-token"

    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give uvicorn some time to start up
    time.sleep(1.5)

    try:
        # Request /sse without token
        with httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0, read=None)
        ) as client:
            resp = client.get("http://127.0.0.1:8085/sse")
            assert resp.status_code == 401
            assert "Unauthorized" in resp.json().get("error", "")

            # Request with incorrect token
            resp_bad = client.get(
                "http://127.0.0.1:8085/sse",
                headers={"Authorization": "Bearer bad-token"},
            )
            assert resp_bad.status_code == 401

            # Request with valid token in query parameter (EventSource auth support)
            with client.stream(
                "GET",
                "http://127.0.0.1:8085/sse?token=super-secret-token",
            ) as resp_qp:
                assert resp_qp.status_code == 200

            time.sleep(0.3)

            # Request with correct token in Authorization header
            with client.stream(
                "GET",
                "http://127.0.0.1:8085/sse",
                headers={"Authorization": "Bearer super-secret-token"},
            ) as resp_ok:
                # SSE request with correct token should stay open / return 200 OK
                assert resp_ok.status_code == 200

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_sse_transport_anonymous():
    """Verify that if BLT_MCP_TOKEN is NOT set, requests succeed anonymously."""
    cmd = [
        sys.executable,
        "-m",
        "blt_mcp.cli",
        "run",
        "--transport",
        "sse",
        "--port",
        "8086",
    ]
    env = os.environ.copy()
    if "BLT_MCP_TOKEN" in env:
        del env["BLT_MCP_TOKEN"]

    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(1.5)

    try:
        with (
            httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0, read=None)) as client,
            client.stream("GET", "http://127.0.0.1:8086/sse") as resp,
        ):
            assert resp.status_code == 200
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
