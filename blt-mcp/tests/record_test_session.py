import subprocess
import json
import sys
import os


def record_session():
    """Run an MCP client interaction through mcp-vcr to record a session."""
    cmd = [
        r".venv\Scripts\mcp-vcr.exe",
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

        # Read until we get the init response
        for line in process.stdout:
            try:
                resp = json.loads(line)
                if resp.get("id") == 1:
                    break
            except:
                pass

        # 2. Call resources/list
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/list",
            "params": {},
        }
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()

        # Read until list response
        for line in process.stdout:
            try:
                resp = json.loads(line)
                if resp.get("id") == 2:
                    break
            except:
                pass

        print("Session recorded successfully. Check the sessions/ directory.")

    finally:
        process.terminate()
        process.wait()


if __name__ == "__main__":
    record_session()
