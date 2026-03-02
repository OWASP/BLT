#!/usr/bin/env python3
"""
CLI Time Tracker
Command-line interface for tracking development time with Fresh Time Tracker.

Usage:
    python cli_tracker.py
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error


class CLITracker:
    def __init__(self, api_url: str, user_id: str, project_id: str):
        self.api_url = api_url
        self.user_id = user_id
        self.project_id = project_id
        self.session_id = None
        self._last_commit = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _request(self, url: str, method: str = "GET", data=None, headers=None):
        req_headers = headers or {}
        body = json.dumps(data).encode() if data is not None else None
        if body:
            req_headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        print("🚀 Starting time tracking session...")
        try:
            data = self._request(
                f"{self.api_url}/api/sessions/start",
                method="POST",
                data={"projectId": self.project_id},
                headers={"X-User-ID": self.user_id},
            )
            self.session_id = data["session"]["id"]
            print(f"✅ Session started: {self.session_id}")
            print("📊 Tracking: Git activity")
            print("⏸️  Press Ctrl+C to stop tracking\n")

            signal.signal(signal.SIGINT, lambda _sig, _frame: self.stop())
            self._poll_git()
        except Exception as exc:
            print(f"❌ Failed to start session: {exc}")
            sys.exit(1)

    def stop(self) -> None:
        if not self.session_id:
            sys.exit(0)

        print("\n⏹️  Stopping time tracking session...")
        try:
            data = self._request(
                f"{self.api_url}/api/sessions/{self.session_id}/end",
                method="POST",
                headers={"X-User-ID": self.user_id},
            )
            duration_min = (data["session"].get("duration") or 0) // 1000 // 60
            print(f"✅ Session ended")
            print(f"⏱️  Total time: {duration_min} minutes")
            self._print_summary()
        except Exception as exc:
            print(f"❌ Failed to stop session: {exc}")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Git monitoring
    # ------------------------------------------------------------------

    def _get_latest_commit(self):
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or None
        except Exception:
            return None

    def _get_repo_name(self) -> str:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5,
            )
            url = result.stdout.strip()
            import re
            m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
            return m.group(1) if m else "unknown"
        except Exception:
            return "unknown"

    def _track_commit(self, commit_line: str) -> None:
        if not self.session_id:
            return
        parts = commit_line.split(" ", 1)
        sha = parts[0]
        message = parts[1] if len(parts) > 1 else ""
        try:
            self._request(
                f"{self.api_url}/api/activity",
                method="POST",
                data={
                    "sessionId": self.session_id,
                    "type": "github",
                    "data": {
                        "type": "github",
                        "action": "commit",
                        "repository": self._get_repo_name(),
                        "commitSha": sha,
                    },
                },
                headers={"X-User-ID": self.user_id},
            )
            print(f"📝 Tracked commit: {sha[:7]} - {message}")
        except Exception as exc:
            print(f"Failed to track commit {sha[:7]} (session={self.session_id}): {exc}")

    def _poll_git(self) -> None:
        """Poll for new commits every 30 seconds (blocking loop)."""
        self._last_commit = self._get_latest_commit()
        while True:
            time.sleep(30)
            latest = self._get_latest_commit()
            if latest and latest != self._last_commit:
                self._track_commit(latest)
                self._last_commit = latest

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _print_summary(self) -> None:
        if not self.session_id:
            return
        try:
            data = self._request(
                f"{self.api_url}/api/sessions/{self.session_id}/summary",
                headers={"X-User-ID": self.user_id},
            )
            summary = data["summary"]
            print("\n📊 Session Summary:")
            print(f"   GitHub Events: {summary['githubEvents']}")
            print(f"   Agent Prompts: {summary['agentPrompts']}")
            print(f"   Productivity: {summary['productivity'].upper()}")
            print("")
        except Exception as exc:
            print(f"Failed to get summary: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _prompt(question: str, default: str = "") -> str:
    answer = input(question).strip()
    return answer if answer else default


def main() -> None:
    print("🕐 Fresh Time Tracker CLI\n")

    api_url = _prompt("API URL (default: http://localhost:8787): ", "http://localhost:8787")
    user_id = _prompt("User ID: ")
    project_id = _prompt("Project ID: ")

    if not user_id or not project_id:
        print("❌ User ID and Project ID are required")
        sys.exit(1)

    tracker = CLITracker(api_url=api_url, user_id=user_id, project_id=project_id)
    tracker.start()


if __name__ == "__main__":
    main()
