"""
GitHub Integration Example
Shows how to integrate with GitHub webhooks and the Fresh Time Tracker API.
"""

import json
import urllib.request
import urllib.error
import os


class GitHubIntegration:
    def __init__(self, api_url: str, user_id: str, session_id: str, github_token: str = None):
        self.api_url = api_url
        self.user_id = user_id
        self.session_id = session_id
        self.github_token = github_token

    def _request(self, url: str, method: str = "GET", data=None, headers=None) -> dict:
        """Make an HTTP request and return the parsed JSON response."""
        req_headers = headers or {}
        body = json.dumps(data).encode() if data is not None else None
        if body:
            req_headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"HTTP {e.code} {e.reason}: {error_body}") from e

    def handle_webhook(self, payload: dict, event: str) -> None:
        """Forward a GitHub webhook payload to the tracker API."""
        self._request(
            f"{self.api_url}/api/webhooks/github",
            method="POST",
            data=payload,
            headers={"X-User-ID": self.user_id, "X-Session-ID": self.session_id},
        )

    def track_commit(self, repository: str, sha: str, branch: str) -> None:
        """Manually record a commit event."""
        self._request(
            f"{self.api_url}/api/activity",
            method="POST",
            data={
                "sessionId": self.session_id,
                "type": "github",
                "data": {
                    "type": "github",
                    "action": "commit",
                    "repository": repository,
                    "branch": branch,
                    "commitSha": sha,
                },
            },
            headers={"X-User-ID": self.user_id},
        )

    def track_pull_request(self, repository: str, pr_number: int, action: str) -> None:
        """Record a pull-request event (action: 'opened' | 'closed' | 'merged')."""
        self._request(
            f"{self.api_url}/api/activity",
            method="POST",
            data={
                "sessionId": self.session_id,
                "type": "github",
                "data": {
                    "type": "github",
                    "action": "pull-request",
                    "repository": repository,
                    "url": f"https://github.com/{repository}/pull/{pr_number}",
                },
            },
            headers={"X-User-ID": self.user_id},
        )

    def fetch_recent_activity(self) -> list:
        """Fetch recent public events for the authenticated GitHub user."""
        if not self.github_token:
            return []
        username = self._get_username()
        data = self._request(
            f"https://api.github.com/users/{username}/events/public",
            headers={
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        return data if isinstance(data, list) else []

    def _get_username(self) -> str:
        data = self._request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        return data.get("login", "")


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    integration = GitHubIntegration(
        api_url="https://your-worker.workers.dev",
        user_id="user-123",
        session_id="session-456",
        github_token=os.environ.get("GITHUB_TOKEN"),
    )

    # Track a commit
    integration.track_commit("OWASP-BLT/BLT-Timer-Web", "abc123def456", "main")

    # Track a PR
    integration.track_pull_request("OWASP-BLT/BLT-Timer-Web", 42, "opened")

    # Fetch recent activity from GitHub
    activities = integration.fetch_recent_activity()
    print(f"Fetched {len(activities)} recent GitHub events")
