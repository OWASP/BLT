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
        with httpx.Client() as client:
            resp = client.get("http://127.0.0.1:8085/sse")
            assert resp.status_code == 401
            assert "Unauthorized" in resp.json().get("error", "")

            # Request with incorrect token
            resp_bad = client.get(
                "http://127.0.0.1:8085/sse",
                headers={"Authorization": "Bearer bad-token"},
            )
            assert resp_bad.status_code == 401

            # Request with correct token
            with client.stream(
                "GET",
                "http://127.0.0.1:8085/sse",
                headers={"Authorization": "Bearer super-secret-token"},
            ) as resp_ok:
                # SSE request with correct token should either stay open or redirect/succeed (not 401)
                assert resp_ok.status_code != 401

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
        with httpx.Client() as client:
            with client.stream("GET", "http://127.0.0.1:8086/sse") as resp:
                assert resp.status_code != 401
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
