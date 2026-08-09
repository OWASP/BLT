"""
VCR Recording Utility Script for MCP Stdio Interactions.

This script automates recording test sessions against the local Python MCP server using `mcp-vcr`.

Key Functions:
- `record_session()`: Locates `mcp-vcr` on the system PATH, starts it with recording parameters pointing
  to the server (`uv run -m blt_mcp.server`), writes mock JSON-RPC requests (init, resources/list)
  into its stdin stream, and saves the output logs to `sessions/`.
- `_read_response(stdout, expected_id)`: Helper function to parse JSON-RPC response lines
  and identify matches to the target ID without hanging on network streams.

Usage:
- Executed directly: `python -m tests.record_test_session` or `uv run tests/record_test_session.py`.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time

MAX_RESPONSE_LINES = 200


def _read_response(stdout, expected_id, timeout=30.0):
    """Read lines from stdout until a JSON-RPC response with the expected id is found.

    Enforces a real time deadline to prevent blocking indefinitely.
    Retains MAX_RESPONSE_LINES as a secondary guard.
    Returns the parsed response dict, or None on timeout/EOF.
    """
    deadline = time.monotonic() + timeout
    for _ in range(MAX_RESPONSE_LINES):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        # Time-bounded readline using a daemon thread
        result = [None]

        def _readline(res=result):
            res[0] = stdout.readline()

        t = threading.Thread(target=_readline, daemon=True)
        t.start()
        t.join(timeout=remaining)

        if t.is_alive():
            # readline is still blocking — deadline exceeded
            break

        line = result[0]
        if not line:
            break
        try:
            resp = json.loads(line)
            if resp.get("id") == expected_id:
                return resp
        except json.JSONDecodeError:
            continue
    return None


def record_session():
    """Run an MCP client interaction through mcp-vcr to record a session."""
    vcr_exe = shutil.which("mcp-vcr")
    if vcr_exe is None:
        print(
            "ERROR: mcp-vcr not found on PATH. Install it or activate the venv.",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = [
        vcr_exe,
        "record",
        "--name",
        "issues_list",
        "--",
        "uv",
        "run",
        "-m",
        "blt_mcp.server",
    ]
    env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
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

        resp = _read_response(process.stdout, 1)
        if resp is None:
            print("ERROR: No init response received.", file=sys.stderr)
            sys.exit(1)
        if "error" in resp:
            print(f"ERROR: Init failed: {resp['error']}", file=sys.stderr)
            sys.exit(1)

        # 2. Send notifications/initialized (required by 2024-11-05 protocol)
        init_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        process.stdin.write(json.dumps(init_notification) + "\n")
        process.stdin.flush()

        # 3. Call resources/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/list",
            "params": {},
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()

        resp = _read_response(process.stdout, 2)
        if resp is None:
            print("ERROR: No list response received.", file=sys.stderr)
            sys.exit(1)
        if "error" in resp:
            print(f"ERROR: resources/list failed: {resp['error']}", file=sys.stderr)
            sys.exit(1)

        print("Session recorded successfully. Check the sessions/ directory.")

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    record_session()
