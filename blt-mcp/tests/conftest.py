import pytest
import subprocess
import sys
from pathlib import Path

def pytest_sessionfinish(session, exitstatus):
    """
    Automatically runs mcp-vcr verify after all pytest tests pass.
    """
    if exitstatus == 0:
        snapshots_dir = Path("snapshots")
        if snapshots_dir.exists() and any(snapshots_dir.glob("*.yaml")):
            print("\n=== Running Golden Snapshot Verification ===")
            mcp_vcr_bin = Path(sys.executable).parent / "mcp-vcr.exe" if sys.platform == "win32" else "mcp-vcr"
            cmd = [
                str(mcp_vcr_bin), "verify",
                str(snapshots_dir),
                "--", "uv", "run", "-m", "blt_mcp.server"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(f"WARNING: Golden snapshots verification failed:\n{result.stderr}", file=sys.stderr)
        else:
            print("\n=== No Golden Snapshots found. Run `mcp-vcr record` to create some! ===")
