"""Admin service for BLT-Pool.

Keeps admin auth and mentor management out of worker.py.
"""

import base64
import binascii
from datetime import datetime, timezone as dt_timezone
import hmac
import html as _html
import json
import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, quote_plus, urlparse

from js import Headers, Response, console, fetch
from version import APP_VERSION


_ADMIN_BASIC_USER_ENV = "ADMIN_BASIC_AUTH_USERNAME"
_ADMIN_BASIC_PASS_ENV = "ADMIN_BASIC_AUTH_PASSWORD"
_ADMIN_BASIC_REALM = "BLT-Pool Admin"
_GH_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$")
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,}$")
_SLACK_USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\- ]{0,79}$")
_ASSIGNMENT_REF_RE = re.compile(r"^(?:(?P<org>[A-Za-z0-9_.-]+)/)?(?P<repo>[A-Za-z0-9_.-]+)#(?P<number>\d+)$")


def _escape(value: str) -> str:
    return _html.escape(value or "", quote=True)


def _normalize_admin_path(raw_path: str) -> str:
    value = (raw_path or "").strip()
    if not value:
        return "/admin"
    if not value.startswith("/"):
        value = "/" + value
    value = value.rstrip("/")
    return value or "/admin"


def _parse_basic_auth_header(auth_header: str) -> Tuple[str, str]:
    """Parse a Basic auth header and return (username, password)."""
    if not auth_header:
        return "", ""
    prefix = "Basic "
    if not auth_header.startswith(prefix):
        return "", ""

    encoded = auth_header[len(prefix):].strip()
    if not encoded:
        return "", ""

    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return "", ""

    if ":" not in decoded:
        return "", ""

    username, password = decoded.split(":", 1)
    return username, password


def _github_headers(token: str = "") -> Headers:
    headers = {
        "Accept": "application/vnd.github+json",
    "User-Agent": f"BLT-Pool/{APP_VERSION}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return Headers.new(headers.items())


def _github_next_link(link_header: str) -> str:
    """Extract the next-page URL from a GitHub Link header."""
    if not link_header:
        return ""
    for part in link_header.split(","):
        segment = part.strip()
        if 'rel="next"' not in segment:
            continue
        if not segment.startswith("<"):
            continue
        end = segment.find(">")
        if end <= 1:
            continue
        return segment[1:end]
    return ""


def _int_or_default(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _github_rate_limit_snapshot(resp) -> dict:
    """Return normalized GitHub rate-limit data from a response."""
    if not resp:
        return {}
    headers = getattr(resp, "headers", None)
    if not headers:
        return {}
    limit = _int_or_default(headers.get("X-RateLimit-Limit"), 0)
    remaining = _int_or_default(headers.get("X-RateLimit-Remaining"), 0)
    used = _int_or_default(headers.get("X-RateLimit-Used"), max(limit - remaining, 0))
    reset_at = _int_or_default(headers.get("X-RateLimit-Reset"), 0)
    return {
        "limit": limit,
        "remaining": remaining,
        "used": used,
        "reset_at": reset_at,
    }


def _github_owner_from_repo_api_url(repo_api_url: str) -> str:
    """Parse owner from URLs like https://api.github.com/repos/{owner}/{repo}."""
    if not repo_api_url:
        return ""
    try:
        path_parts = [p for p in urlparse(str(repo_api_url)).path.split("/") if p]
    except Exception:
        return ""
    if len(path_parts) >= 3 and path_parts[0].lower() == "repos":
        return path_parts[1]
    return ""


def _github_owner_from_any_url(raw_url: str) -> str:
    """Parse owner from API or html URL forms that include /owner/repo."""
    if not raw_url:
        return ""
    try:
        path_parts = [p for p in urlparse(str(raw_url)).path.split("/") if p]
    except Exception:
        return ""
    if len(path_parts) >= 3 and path_parts[0].lower() == "repos":
        return path_parts[1]
    if len(path_parts) >= 2:
        return path_parts[0]
    return ""


async def has_merged_pr_in_org(env, github_username: str, org: str = "OWASP-BLT") -> bool:
    """Return True when the user has at least one merged PR in the org."""
    if not github_username:
        return False

    token = getattr(env, "GITHUB_TOKEN", "") if env else ""
    query = quote_plus(f"is:pr is:merged org:{org} author:{github_username}")
    url = f"https://api.github.com/search/issues?q={query}&per_page=1"

    try:
        resp = await fetch(url, method="GET", headers=_github_headers(token))
        if resp.status != 200:
            console.error(
                f"[AdminService] Merged PR lookup failed for {github_username}: status={resp.status}"
            )
            return False
        payload = json.loads(await resp.text())
        return int(payload.get("total_count") or 0) > 0
    except Exception as exc:
        console.error(f"[AdminService] Merged PR lookup error for {github_username}: {exc}")
        return False


class AdminService:
    """D1-backed admin auth and mentor management UI."""

    def __init__(self, env):
        self.env = env
        self.db = getattr(env, "LEADERBOARD_DB", None) if env else None
        self.admin_path = _normalize_admin_path(getattr(env, "ADMIN_PATH", "/admin") if env else "/admin")
        self.mentor_action_path = f"{self.admin_path}/mentors/action"

    async def handle(self, request):
        """Handle admin routes, or return None when the path is not for this service."""
        path = urlparse(str(request.url)).path.rstrip("/") or "/"
        legacy_mentor_action_path = "/admin/mentors/action"

        # Reset endpoint is handled in worker.py.
        if path in {"/admin/reset-leaderboard-month", f"{self.admin_path}/reset-leaderboard-month"}:
            return None

        if not (
            path == self.admin_path
            or path.startswith(f"{self.admin_path}/")
            or path == legacy_mentor_action_path
        ):
            return None

        if not self.db:
            return self._html(
                self._shell(
                    "Admin unavailable",
                    "<p class='text-sm text-gray-600'>The D1 database binding is not configured.</p>",
                ),
                500,
            )

        await self._ensure_tables()

        if path in {
            f"{self.admin_path}/login",
            f"{self.admin_path}/signup",
            f"{self.admin_path}/logout",
        }:
            return self._redirect(self.admin_path)

        configured_user, configured_pass = self._configured_basic_auth()
        if not configured_user or not configured_pass:
            return self._html(
                self._shell(
                    "Admin unavailable",
                    "<p class='text-sm text-gray-600'>"
                    f"Set {_ADMIN_BASIC_USER_ENV} and {_ADMIN_BASIC_PASS_ENV} "
                    f"to enable Basic Auth for {self.admin_path}.</p>",
                ),
                500,
            )

        request_user = self._authorized_admin(request, configured_user, configured_pass)
        if not request_user:
            return self._basic_auth_challenge()

        if path in {self.mentor_action_path, legacy_mentor_action_path} and request.method == "POST":
            return await self._handle_mentor_action(request, request_user)

        if path == self.admin_path:
            return await self._handle_dashboard(request_user)

        return self._json({"error": "Not found"}, 404)

    async def _d1_run(self, sql: str, params: tuple = ()):
        stmt = self.db.prepare(sql)
        if params:
            stmt = stmt.bind(*params)
        return await stmt.run()

    async def _d1_all(self, sql: str, params: tuple = ()) -> list:
        stmt = self.db.prepare(sql)
        if params:
            stmt = stmt.bind(*params)
        raw_result = await stmt.all()

        try:
            from js import JSON as JS_JSON  # noqa: PLC0415

            parsed = json.loads(str(JS_JSON.stringify(raw_result)))
            rows = parsed.get("results") if isinstance(parsed, dict) else None
            if isinstance(rows, list):
                return rows
        except Exception:
            pass

        try:
            from pyodide.ffi import to_py  # noqa: PLC0415

            result = to_py(raw_result)
        except Exception:
            result = raw_result

        rows = None
        if isinstance(result, dict):
            rows = result.get("results")
        else:
            rows = getattr(result, "results", None)

        if rows is None:
            return []
        try:
            return list(rows)
        except Exception:
            return []

    async def _d1_first(self, sql: str, params: tuple = ()):
        rows = await self._d1_all(sql, params)
        return rows[0] if rows else None

    async def _ensure_tables(self) -> None:
        await self._d1_run(
            """
            CREATE TABLE IF NOT EXISTS mentors (
                github_username TEXT NOT NULL PRIMARY KEY,
                name TEXT NOT NULL,
                specialties TEXT NOT NULL DEFAULT '[]',
                max_mentees INTEGER NOT NULL DEFAULT 3,
                active INTEGER NOT NULL DEFAULT 1,
                timezone TEXT NOT NULL DEFAULT '',
                referred_by TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
              slack_username TEXT NOT NULL DEFAULT '',
              total_prs INTEGER NOT NULL DEFAULT 0,
              total_reviews INTEGER NOT NULL DEFAULT 0,
              total_comments INTEGER NOT NULL DEFAULT 0,
              last_rate_limit INTEGER NOT NULL DEFAULT 0,
              last_rate_remaining INTEGER NOT NULL DEFAULT 0,
              last_rate_used INTEGER NOT NULL DEFAULT 0,
              last_rate_reset_at INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            )
            """
        )
        if not await self._d1_has_column("mentors", "email"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN email TEXT NOT NULL DEFAULT ''"
            )
        if not await self._d1_has_column("mentors", "slack_username"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN slack_username TEXT NOT NULL DEFAULT ''"
            )
        if not await self._d1_has_column("mentors", "total_prs"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN total_prs INTEGER NOT NULL DEFAULT 0"
            )
        if not await self._d1_has_column("mentors", "total_reviews"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN total_reviews INTEGER NOT NULL DEFAULT 0"
            )
        if not await self._d1_has_column("mentors", "total_comments"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN total_comments INTEGER NOT NULL DEFAULT 0"
            )
        if not await self._d1_has_column("mentors", "last_rate_limit"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN last_rate_limit INTEGER NOT NULL DEFAULT 0"
            )
        if not await self._d1_has_column("mentors", "last_rate_remaining"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN last_rate_remaining INTEGER NOT NULL DEFAULT 0"
            )
        if not await self._d1_has_column("mentors", "last_rate_used"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN last_rate_used INTEGER NOT NULL DEFAULT 0"
            )
        if not await self._d1_has_column("mentors", "last_rate_reset_at"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN last_rate_reset_at INTEGER NOT NULL DEFAULT 0"
            )
        if not await self._d1_has_column("mentors", "created_at"):
            await self._d1_run(
                "ALTER TABLE mentors ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0"
            )
            await self._d1_run(
                "UPDATE mentors SET created_at = strftime('%s','now') WHERE created_at = 0"
            )
        await self._d1_run(
            """
            CREATE TABLE IF NOT EXISTS mentor_assignments (
                org TEXT NOT NULL,
                mentor_login TEXT NOT NULL,
                issue_repo TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                assigned_at INTEGER NOT NULL,
            mentee_login TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (org, issue_repo, issue_number)
            )
            """
        )
        if not await self._d1_has_column("mentor_assignments", "mentee_login"):
            await self._d1_run(
                "ALTER TABLE mentor_assignments ADD COLUMN mentee_login TEXT NOT NULL DEFAULT ''"
            )

    async def _count_user_prs_in_org(self, github_username: str, org: str) -> Tuple[int, dict]:
        """Count all PRs authored by github_username across all repos in org."""
        username = (github_username or "").strip().lstrip("@")
        if not username:
            return 0, {}

        token = getattr(self.env, "GITHUB_TOKEN", "") if self.env else ""
        org_login = (org or "").strip().lower()
        last_snapshot = {}
        if not token:
            query = quote_plus(f"is:pr org:{org} author:{username}")
            url = f"https://api.github.com/search/issues?q={query}&per_page=1"
            try:
                resp = await fetch(url, method="GET", headers=_github_headers(token))
                last_snapshot = _github_rate_limit_snapshot(resp)
                if resp.status != 200:
                    return 0, last_snapshot
                payload = json.loads(await resp.text())
                return int(payload.get("total_count") or 0), last_snapshot
            except Exception:
                return 0, last_snapshot

        graphql_query = """
        query($login: String!, $cursor: String) {
          user(login: $login) {
            pullRequests(
              first: 100,
              after: $cursor,
              orderBy: {field: CREATED_AT, direction: DESC},
              states: [OPEN, CLOSED, MERGED]
            ) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                repository {
                  owner {
                    login
                  }
                }
              }
            }
          }
        }
        """

        cursor = None
        total = 0
        while True:
            body = json.dumps(
                {
                    "query": graphql_query,
                    "variables": {
                        "login": username,
                        "cursor": cursor,
                    },
                }
            )
            try:
                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                  "User-Agent": f"BLT-Pool/{APP_VERSION}",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                resp = await fetch(
                    "https://api.github.com/graphql",
                    method="POST",
                    headers=Headers.new(headers.items()),
                    body=body,
                )
            except Exception as exc:
                console.error(f"[AdminService] PR lookup error for {username}: {exc}")
                break

            last_snapshot = _github_rate_limit_snapshot(resp)
            if resp.status != 200:
                console.error(
                    f"[AdminService] PR lookup failed for {username}: status={resp.status} (graphql)"
                )
                break

            try:
                payload = json.loads(await resp.text())
            except Exception as exc:
                console.error(f"[AdminService] PR lookup parse failure for {username}: {exc}")
                break

            if isinstance(payload, dict) and payload.get("errors"):
                console.error(f"[AdminService] PR lookup graphql errors for {username}: {payload.get('errors')}")
                break

            user_data = ((payload.get("data") or {}).get("user") if isinstance(payload, dict) else None) or {}
            pr_connection = user_data.get("pullRequests") if isinstance(user_data, dict) else None
            if not isinstance(pr_connection, dict):
                break

            nodes = pr_connection.get("nodes") if isinstance(pr_connection, dict) else []
            if not isinstance(nodes, list):
                nodes = []

            for node in nodes:
                repo = (node or {}).get("repository") if isinstance(node, dict) else None
                owner = (repo or {}).get("owner") if isinstance(repo, dict) else None
                owner_login = ((owner or {}).get("login") or "").strip().lower() if isinstance(owner, dict) else ""
                if owner_login == org_login:
                    total += 1

            page_info = pr_connection.get("pageInfo") if isinstance(pr_connection, dict) else {}
            has_next = bool((page_info or {}).get("hasNextPage")) if isinstance(page_info, dict) else False
            cursor = (page_info or {}).get("endCursor") if isinstance(page_info, dict) else None
            if not has_next:
                break

        return total, last_snapshot

    async def _github_graphql(self, query: str, variables: dict, token: str) -> Tuple[Optional[dict], dict]:
        """Execute a GitHub GraphQL request and return (data, rate_limit_snapshot)."""
        body = json.dumps({"query": query, "variables": variables or {}})
        last_snapshot: dict = {}

        try:
            resp = await fetch(
                "https://api.github.com/graphql",
                method="POST",
                headers=_github_headers(token),
                body=body,
            )
        except Exception as exc:
            console.error(f"[AdminService] GraphQL lookup error: {exc}")
            return None, last_snapshot

        last_snapshot = _github_rate_limit_snapshot(resp)
        if resp.status != 200:
            console.error(f"[AdminService] GraphQL lookup failed: status={resp.status}")
            return None, last_snapshot

        try:
            payload = json.loads(await resp.text())
        except Exception as exc:
            console.error(f"[AdminService] GraphQL lookup parse error: {exc}")
            return None, last_snapshot

        if not isinstance(payload, dict):
            return None, last_snapshot

        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            console.error(f"[AdminService] GraphQL lookup returned errors: {errors}")
            return None, last_snapshot

        data = payload.get("data")
        return data if isinstance(data, dict) else None, last_snapshot

    async def _github_org_id(self, org: str, token: str) -> Tuple[str, dict]:
        """Return the GraphQL node ID for a GitHub org."""
        org_login = (org or "").strip()
        if not org_login:
            return "", {}

        query = """
        query($org: String!) {
          organization(login: $org) {
            id
          }
        }
        """
        data, snapshot = await self._github_graphql(query, {"org": org_login}, token)
        organization = (data or {}).get("organization") if isinstance(data, dict) else None
        if not isinstance(organization, dict):
            return "", snapshot
        return str(organization.get("id") or ""), snapshot

    async def _github_rate_limit_status(self) -> dict:
        """Return current core rate-limit details and seconds until reset."""
        token = getattr(self.env, "GITHUB_TOKEN", "") if self.env else ""

        snapshot = {}
        try:
            resp = await fetch(
                "https://api.github.com/rate_limit",
                method="GET",
                headers=_github_headers(token),
            )
            snapshot = _github_rate_limit_snapshot(resp)
            if resp.status != 200:
                return snapshot

            payload = json.loads(await resp.text())
            core = ((payload.get("resources") or {}).get("core") if isinstance(payload, dict) else None) or {}
            if isinstance(core, dict):
                limit = _int_or_default(core.get("limit"), snapshot.get("limit") or 0)
                remaining = _int_or_default(core.get("remaining"), snapshot.get("remaining") or 0)
                used = _int_or_default(core.get("used"), snapshot.get("used") or max(limit - remaining, 0))
                reset_at = _int_or_default(core.get("reset"), snapshot.get("reset_at") or 0)
                snapshot = {
                    "limit": limit,
                    "remaining": remaining,
                    "used": used,
                    "reset_at": reset_at,
                }
        except Exception as exc:
            console.error(f"[AdminService] Rate limit lookup failed: {exc}")
            return snapshot

        now_ts = int(datetime.now(tz=dt_timezone.utc).timestamp())
        reset_at = _int_or_default(snapshot.get("reset_at"), 0)
        snapshot["seconds_remaining"] = max(0, reset_at - now_ts) if reset_at > 0 else 0
        return snapshot

    def _format_seconds_remaining(self, seconds_remaining: int) -> str:
        total = max(0, _int_or_default(seconds_remaining, 0))
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

    def _seconds_until_timestamp(self, reset_at: int) -> int:
        ts = _int_or_default(reset_at, 0)
        if ts <= 0:
            return 0
        now_ts = int(datetime.now(tz=dt_timezone.utc).timestamp())
        return max(0, ts - now_ts)

    async def _count_user_reviews_in_org(self, github_username: str, org: str) -> Tuple[int, dict]:
        """Count all-time PR reviews in org with APPROVED or CHANGES_REQUESTED states."""
        username = (github_username or "").strip().lstrip("@")
        org_login = (org or "").strip().lower()
        if not username or not org_login:
            return 0, {}

        token = getattr(self.env, "GITHUB_TOKEN", "") if self.env else ""

        total = 0
        last_snapshot = {}

        # Two search queries mirror requested review outcomes.
        for qualifier in ("review:approved", "review:changes_requested"):
            query = quote_plus(f"is:pr org:{org_login} reviewed-by:{username} {qualifier}")
            url = f"https://api.github.com/search/issues?q={query}&per_page=1"
            try:
                resp = await fetch(url, method="GET", headers=_github_headers(token))
            except Exception as exc:
                console.error(f"[AdminService] Review lookup error for {username}: {exc}")
                continue

            snapshot = _github_rate_limit_snapshot(resp)
            if snapshot:
                last_snapshot = snapshot
            if resp.status != 200:
                console.error(
                    f"[AdminService] Review lookup failed for {username}: status={resp.status}"
                )
                continue

            try:
                payload = json.loads(await resp.text())
            except Exception as exc:
                console.error(f"[AdminService] Review lookup parse error for {username}: {exc}")
                continue

            total += int(payload.get("total_count") or 0)

        return total, last_snapshot

    async def _count_user_comment_endpoint_in_org(self, url: str, org: str, token: str) -> Tuple[int, dict]:
        org_login = (org or "").strip().lower()
        next_url = url
        total = 0
        last_snapshot = {}

        while next_url:
            try:
                resp = await fetch(next_url, method="GET", headers=_github_headers(token))
            except Exception as exc:
                console.error(f"[AdminService] Comment lookup error: {exc}")
                break

            last_snapshot = _github_rate_limit_snapshot(resp)
            if resp.status != 200:
                console.error(
                    f"[AdminService] Comment lookup failed: status={resp.status} url={next_url}"
                )
                break

            try:
                payload = json.loads(await resp.text())
            except Exception as exc:
                console.error(f"[AdminService] Comment lookup parse error: {exc}")
                break

            if not isinstance(payload, list):
                break

            for comment in payload:
                if not isinstance(comment, dict):
                    continue
                owner_login = _github_owner_from_repo_api_url(str(comment.get("repository_url") or ""))
                if not owner_login:
                    owner_login = _github_owner_from_any_url(str(comment.get("issue_url") or ""))
                if not owner_login:
                    owner_login = _github_owner_from_any_url(str(comment.get("pull_request_url") or ""))
                if not owner_login:
                    owner_login = _github_owner_from_any_url(str(comment.get("html_url") or ""))
                if owner_login.strip().lower() == org_login:
                    total += 1

            next_url = _github_next_link(resp.headers.get("Link") or "")

        return total, last_snapshot

    async def _count_user_graphql_comments_in_org(self, github_username: str, org: str, token: str) -> Tuple[Optional[int], dict]:
      """Count all-time comments in org using GraphQL comment connections."""
      username = (github_username or "").strip().lstrip("@")
      org_login = (org or "").strip().lower()
      if not username or not org_login:
        return 0, {}

      query = """
      query($username: String!, $issueCursor: String, $reviewCursor: String) {
        user(login: $username) {
        issueComments(first: 100, after: $issueCursor) {
          pageInfo { hasNextPage endCursor }
          nodes {
          repository {
            owner { login }
          }
          }
        }
        pullRequestReviewComments(first: 100, after: $reviewCursor) {
          pageInfo { hasNextPage endCursor }
          nodes {
          repository {
            owner { login }
          }
          }
        }
        }
      }
      """

      issue_cursor = None
      review_cursor = None
      issue_done = False
      review_done = False
      total = 0
      last_snapshot = {}
      had_valid_connection = False

      while not (issue_done and review_done):
        variables = {
          "username": username,
          "issueCursor": issue_cursor,
          "reviewCursor": review_cursor,
        }
        data, snapshot = await self._github_graphql(query, variables, token)
        if snapshot:
          last_snapshot = snapshot
        user = (data or {}).get("user") if isinstance(data, dict) else None
        if not isinstance(user, dict):
          break

        if not issue_done:
          issue_connection = user.get("issueComments") if isinstance(user, dict) else None
          if not isinstance(issue_connection, dict):
            issue_done = True
          else:
            had_valid_connection = True
            issue_nodes = issue_connection.get("nodes") if isinstance(issue_connection, dict) else []
            if not isinstance(issue_nodes, list):
              issue_nodes = []
            for node in issue_nodes:
              repo = (node or {}).get("repository") if isinstance(node, dict) else None
              owner = (repo or {}).get("owner") if isinstance(repo, dict) else None
              owner_login = ((owner or {}).get("login") or "").strip().lower() if isinstance(owner, dict) else ""
              if owner_login == org_login:
                total += 1
            issue_page_info = issue_connection.get("pageInfo") if isinstance(issue_connection, dict) else {}
            issue_has_next = bool((issue_page_info or {}).get("hasNextPage")) if isinstance(issue_page_info, dict) else False
            issue_cursor = (issue_page_info or {}).get("endCursor") if isinstance(issue_page_info, dict) else None
            issue_done = not issue_has_next

        if not review_done:
          review_connection = user.get("pullRequestReviewComments") if isinstance(user, dict) else None
          if not isinstance(review_connection, dict):
            review_done = True
          else:
            had_valid_connection = True
            review_nodes = review_connection.get("nodes") if isinstance(review_connection, dict) else []
            if not isinstance(review_nodes, list):
              review_nodes = []
            for node in review_nodes:
              repo = (node or {}).get("repository") if isinstance(node, dict) else None
              owner = (repo or {}).get("owner") if isinstance(repo, dict) else None
              owner_login = ((owner or {}).get("login") or "").strip().lower() if isinstance(owner, dict) else ""
              if owner_login == org_login:
                total += 1
            review_page_info = review_connection.get("pageInfo") if isinstance(review_connection, dict) else {}
            review_has_next = bool((review_page_info or {}).get("hasNextPage")) if isinstance(review_page_info, dict) else False
            review_cursor = (review_page_info or {}).get("endCursor") if isinstance(review_page_info, dict) else None
            review_done = not review_has_next

      if not had_valid_connection:
        return None, last_snapshot
      return total, last_snapshot

    async def _count_user_comments_via_search_in_org(self, github_username: str, org: str, token: str) -> Tuple[int, dict]:
      """Fallback comment estimate via GitHub Search API commenter qualifiers."""
      username = (github_username or "").strip().lstrip("@")
      org_login = (org or "").strip()
      if not username or not org_login:
        return 0, {}

      last_snapshot = {}
      total = 0
      queries = (
        f"org:{org_login} is:issue commenter:{username}",
        f"org:{org_login} is:pr commenter:{username}",
      )

      for raw_query in queries:
        q = quote_plus(raw_query)
        url = f"https://api.github.com/search/issues?q={q}&per_page=1"
        try:
          resp = await fetch(url, method="GET", headers=_github_headers(token))
        except Exception as exc:
          console.error(f"[AdminService] Search comment fallback error for {username}: {exc}")
          continue

        snapshot = _github_rate_limit_snapshot(resp)
        if snapshot:
          last_snapshot = snapshot
        if resp.status != 200:
          continue

        try:
          payload = json.loads(await resp.text())
        except Exception:
          continue
        total += int(payload.get("total_count") or 0)

      return total, last_snapshot

    async def _count_user_comments_in_org(self, github_username: str, org: str) -> Tuple[int, dict]:
        """Count all-time issue comments + PR review comments left by user in org repos."""
        username = (github_username or "").strip().lstrip("@")
        org_login = (org or "").strip()
        if not username or not org_login:
            return 0, {}

        token = getattr(self.env, "GITHUB_TOKEN", "") if self.env else ""

        if token:
          gql_total, gql_snapshot = await self._count_user_graphql_comments_in_org(username, org_login, token)
          if gql_total is not None:
            return int(gql_total), gql_snapshot

        issue_comments_url = f"https://api.github.com/users/{quote_plus(username)}/issues/comments?per_page=100"
        pr_review_comments_url = f"https://api.github.com/users/{quote_plus(username)}/pulls/comments?per_page=100"

        issue_total, issue_snapshot = await self._count_user_comment_endpoint_in_org(issue_comments_url, org_login, token)
        pr_total, pr_snapshot = await self._count_user_comment_endpoint_in_org(pr_review_comments_url, org_login, token)
        rest_total = issue_total + pr_total
        rest_snapshot = (pr_snapshot or issue_snapshot)
        if rest_total > 0:
          return rest_total, rest_snapshot

        search_total, search_snapshot = await self._count_user_comments_via_search_in_org(username, org_login, token)
        return search_total, (search_snapshot or rest_snapshot)

    def _rate_limit_db_values(self, snapshot: dict) -> tuple:
        return (
            int((snapshot or {}).get("limit") or 0),
            int((snapshot or {}).get("remaining") or 0),
            int((snapshot or {}).get("used") or 0),
            int((snapshot or {}).get("reset_at") or 0),
        )

    async def _recalculate_all_mentor_pr_counts(self, clear_first: bool = False) -> int:
        org = str(getattr(self.env, "GITHUB_ORG", "OWASP-BLT") or "OWASP-BLT").strip() or "OWASP-BLT"
        if clear_first:
            await self._d1_run("UPDATE mentors SET total_prs = 0")

        mentors = await self._d1_all("SELECT github_username FROM mentors")
        refreshed = 0
        for row in mentors:
            username = (row.get("github_username") or "").strip().lstrip("@")
            if not username:
                continue
            pr_count, snapshot = await self._count_user_prs_in_org(username, org)
            rate_limit, rate_remaining, rate_used, rate_reset_at = self._rate_limit_db_values(snapshot)
            await self._d1_run(
                """
                UPDATE mentors
                SET total_prs = ?,
                    last_rate_limit = ?,
                    last_rate_remaining = ?,
                    last_rate_used = ?,
                    last_rate_reset_at = ?
                WHERE github_username = ?
                """,
                (int(pr_count), rate_limit, rate_remaining, rate_used, rate_reset_at, username),
            )
            refreshed += 1

        return refreshed

    async def _recalculate_all_mentor_review_counts(self, clear_first: bool = False) -> int:
        org = str(getattr(self.env, "GITHUB_ORG", "OWASP-BLT") or "OWASP-BLT").strip() or "OWASP-BLT"
        if clear_first:
            await self._d1_run("UPDATE mentors SET total_reviews = 0")

        mentors = await self._d1_all("SELECT github_username FROM mentors")
        refreshed = 0
        for row in mentors:
            username = (row.get("github_username") or "").strip().lstrip("@")
            if not username:
                continue
            review_count, snapshot = await self._count_user_reviews_in_org(username, org)
            rate_limit, rate_remaining, rate_used, rate_reset_at = self._rate_limit_db_values(snapshot)
            await self._d1_run(
                """
                UPDATE mentors
                SET total_reviews = ?,
                    last_rate_limit = ?,
                    last_rate_remaining = ?,
                    last_rate_used = ?,
                    last_rate_reset_at = ?
                WHERE github_username = ?
                """,
                (int(review_count), rate_limit, rate_remaining, rate_used, rate_reset_at, username),
            )
            refreshed += 1

        return refreshed

    async def _recalculate_all_mentor_comment_counts(self, clear_first: bool = False) -> int:
        org = str(getattr(self.env, "GITHUB_ORG", "OWASP-BLT") or "OWASP-BLT").strip() or "OWASP-BLT"
        if clear_first:
            await self._d1_run("UPDATE mentors SET total_comments = 0")

        mentors = await self._d1_all("SELECT github_username FROM mentors")
        refreshed = 0
        for row in mentors:
            username = (row.get("github_username") or "").strip().lstrip("@")
            if not username:
                continue
            comment_count, snapshot = await self._count_user_comments_in_org(username, org)
            rate_limit, rate_remaining, rate_used, rate_reset_at = self._rate_limit_db_values(snapshot)
            await self._d1_run(
                """
                UPDATE mentors
                SET total_comments = ?,
                    last_rate_limit = ?,
                    last_rate_remaining = ?,
                    last_rate_used = ?,
                    last_rate_reset_at = ?
                WHERE github_username = ?
                """,
                (int(comment_count), rate_limit, rate_remaining, rate_used, rate_reset_at, username),
            )
            refreshed += 1

        return refreshed

    async def _d1_has_column(self, table_name: str, column_name: str) -> bool:
        rows = await self._d1_all(f"PRAGMA table_info({table_name})")
        target = (column_name or "").strip().lower()
        for row in rows:
            if str(row.get("name") or "").strip().lower() == target:
                return True
        return False

    def _parse_assignment_refs(self, assignment_value: str) -> Optional[list]:
        org = str(getattr(self.env, "GITHUB_ORG", "OWASP-BLT") or "OWASP-BLT").strip() or "OWASP-BLT"
        refs = []
        seen = set()
        for raw_item in [item.strip() for item in (assignment_value or "").split(",") if item.strip()]:
            match = _ASSIGNMENT_REF_RE.match(raw_item)
            if not match:
                return None
            item_org = (match.group("org") or org).strip()
            repo = match.group("repo").strip()
            issue_number = int(match.group("number"))
            if item_org != org:
                return None
            key = (item_org, repo, issue_number)
            if key in seen:
                continue
            seen.add(key)
            refs.append(key)
        return refs

    async def _sync_assignments(self, original_login: str, new_login: str, assignment_value: str) -> bool:
        desired = self._parse_assignment_refs(assignment_value)
        if desired is None:
            return False

        org = str(getattr(self.env, "GITHUB_ORG", "OWASP-BLT") or "OWASP-BLT").strip() or "OWASP-BLT"
        current_rows = await self._d1_all(
            """
            SELECT org, issue_repo, issue_number
            FROM mentor_assignments
            WHERE org = ? AND mentor_login IN (?, ?)
            """,
            (org, original_login, new_login),
        )
        current = {
            (str(row.get("org") or org), str(row.get("issue_repo") or ""), int(row.get("issue_number") or 0))
            for row in current_rows
            if row.get("issue_repo") and int(row.get("issue_number") or 0) > 0
        }
        desired_set = set(desired)

        for item_org, repo, issue_number in current - desired_set:
            await self._d1_run(
                "DELETE FROM mentor_assignments WHERE org = ? AND issue_repo = ? AND issue_number = ?",
                (item_org, repo, issue_number),
            )

        for item_org, repo, issue_number in desired_set:
            await self._d1_run(
                """
                INSERT INTO mentor_assignments (org, mentor_login, issue_repo, issue_number, assigned_at, mentee_login)
                VALUES (?, ?, ?, ?, strftime('%s','now'), '')
                ON CONFLICT(org, issue_repo, issue_number) DO UPDATE SET
                    mentor_login = excluded.mentor_login,
                    assigned_at = excluded.assigned_at,
                    mentee_login = excluded.mentee_login
                """,
                (item_org, new_login, repo, issue_number),
            )
        return True

    def _configured_basic_auth(self) -> Tuple[str, str]:
        username = str(getattr(self.env, _ADMIN_BASIC_USER_ENV, "") or "").strip()
        password = str(getattr(self.env, _ADMIN_BASIC_PASS_ENV, "") or "")
        return username, password

    def _authorized_admin(self, request, expected_user: str, expected_pass: str) -> Optional[str]:
        supplied_user, supplied_pass = _parse_basic_auth_header(request.headers.get("Authorization") or "")
        if not supplied_user and not supplied_pass:
            return None
        if not hmac.compare_digest(supplied_user, expected_user):
            return None
        if not hmac.compare_digest(supplied_pass, expected_pass):
            return None
        return supplied_user

    def _basic_auth_challenge(self):
        return Response.new(
            "Authentication required",
            status=401,
            headers=Headers.new(
                {
                    "Content-Type": "text/plain; charset=utf-8",
                    "WWW-Authenticate": f'Basic realm="{_ADMIN_BASIC_REALM}", charset="UTF-8"',
                }.items()
            ),
        )

    async def _form_data(self, request) -> dict:
        body = await request.text()
        parsed = parse_qs(body, keep_blank_values=True)
        return {key: values[0].strip() if values else "" for key, values in parsed.items()}

    def _is_autosave_request(self, request) -> bool:
        return (request.headers.get("X-Admin-Autosave") or "").strip().lower() == "1"

    def _json(self, payload, status: int = 200):
        return Response.new(
            json.dumps(payload),
            status=status,
            headers=Headers.new({"Content-Type": "application/json"}.items()),
        )

    def _html(self, body: str, status: int = 200):
        headers = {"Content-Type": "text/html; charset=utf-8"}
        return Response.new(body, status=status, headers=Headers.new(headers.items()))

    def _redirect(self, location: str):
        headers = {"Location": location}
        return Response.new("", status=302, headers=Headers.new(headers.items()))

    def _shell(self, title: str, content: str, user: str = "", subtitle: str = "") -> str:
        auth_chip = (
            f'<div class="inline-flex items-center gap-2 rounded-full border border-[#E5E5E5] '
            f'bg-white px-3 py-1 text-xs font-semibold text-gray-600">Basic Auth as @{_escape(user)}</div>'
            if user
            else ""
        )
        subtitle_html = f"<p class='mt-3 text-sm leading-relaxed text-gray-600'>{subtitle}</p>" if subtitle else ""
        return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_escape(title)} | BLT-Pool Admin</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer">
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            'blt-primary': '#E10101',
            'blt-border': '#E5E5E5'
          }},
          fontFamily: {{
            sans: ['Plus Jakarta Sans', 'ui-sans-serif', 'system-ui', 'sans-serif']
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{
      background:
        radial-gradient(circle at 0% 0%, rgba(225, 1, 1, 0.09), transparent 32%),
        radial-gradient(circle at 95% 4%, rgba(225, 1, 1, 0.05), transparent 28%),
        #f8fafc;
    }}

    #admin-mentor-table thead th {{
      position: sticky;
      top: 0;
      z-index: 30;
      background: #f9fafb;
    }}
  </style>
</head>
<body class="min-h-screen font-sans text-gray-900 antialiased">
  <header data-admin-topbar class="sticky top-0 z-40 border-b border-[#E5E5E5] bg-white/90 backdrop-blur">
    <div class="mx-auto flex w-full max-w-[98vw] items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8">
      <a href="{self.admin_path}" class="flex items-center gap-3" aria-label="BLT-Pool admin home">
        <img src="/logo-sm.png" alt="OWASP BLT logo" class="h-10 w-10 rounded-xl border border-[#E5E5E5] bg-white object-contain p-1">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-gray-500">OWASP BLT</p>
          <h1 class="text-lg font-extrabold text-[#111827]">BLT-Pool Admin</h1>
        </div>
      </a>
      <div class="flex items-center gap-3">
        <a href="/" class="inline-flex items-center gap-1.5 rounded-md border border-[#E5E5E5] bg-white px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-[#E10101] hover:bg-[#feeae9] hover:text-[#E10101]">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Back to Pool
        </a>
        {auth_chip}
      </div>
    </div>
  </header>
  <main class="mx-auto w-full max-w-[98vw] px-4 py-8 sm:px-6 lg:px-8">
    <section class="overflow-visible rounded-3xl border border-[#E5E5E5] bg-white p-5 shadow-[0_14px_40px_rgba(225,1,1,0.10)] sm:p-6 lg:p-7">
      <div class="mb-8">
        <span class="inline-flex items-center gap-2 rounded-full border border-[#E5E5E5] bg-gray-50 px-3 py-1 text-xs font-semibold text-gray-700">
          <i class="fa-solid fa-shield-halved text-[#E10101]" aria-hidden="true"></i>
          Admin access
        </span>
        <h2 class="mt-4 text-3xl font-extrabold text-[#111827] sm:text-4xl">{_escape(title)}</h2>
        {subtitle_html}
      </div>
      {content}
    </section>
  </main>
  <div id="admin-confirm-overlay" class="fixed inset-0 z-50 hidden items-center justify-center bg-[#111827]/45 px-4 backdrop-blur-sm" aria-hidden="true">
    <div class="w-full max-w-md overflow-hidden rounded-3xl border border-[#E5E5E5] bg-white shadow-[0_24px_80px_rgba(17,24,39,0.20)]">
      <div class="border-b border-[#E5E5E5] bg-gradient-to-r from-[#fff5f5] via-white to-[#fff1f1] px-6 py-5">
        <div class="flex items-start gap-4">
          <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#feeae9] text-[#E10101]">
            <i class="fa-solid fa-triangle-exclamation text-lg" aria-hidden="true"></i>
          </div>
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Please confirm</p>
            <h3 id="admin-confirm-title" class="mt-1 text-xl font-extrabold text-[#111827]">Confirm action</h3>
          </div>
        </div>
      </div>
      <div class="px-6 py-5">
        <p id="admin-confirm-message" class="text-sm leading-relaxed text-gray-600">This action will update the mentor record.</p>
      </div>
      <div class="flex flex-col-reverse gap-3 border-t border-[#E5E5E5] bg-gray-50 px-6 py-4 sm:flex-row sm:justify-end">
        <button id="admin-confirm-cancel" type="button" class="inline-flex items-center justify-center rounded-md border border-[#E5E5E5] px-4 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-white">
          Cancel
        </button>
        <button id="admin-confirm-submit" type="button" class="inline-flex items-center justify-center gap-2 rounded-md bg-[#E10101] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-700">
          <i class="fa-solid fa-check" aria-hidden="true"></i>
          Continue
        </button>
      </div>
    </div>
  </div>
  <script>
    (() => {{
      const syncStickyHeaderOffset = () => {{
        const headerEl = document.querySelector('[data-admin-topbar]');
        const rect = headerEl ? headerEl.getBoundingClientRect() : null;
        const navHeight = rect ? rect.height : 80;
        const navTop = rect ? rect.top : 0;
        const offsetPx = Math.max(0, Math.ceil(navHeight + navTop + 1));
        document.documentElement.style.setProperty('--admin-header-offset', `${{offsetPx}}px`);
      }};
      syncStickyHeaderOffset();
      requestAnimationFrame(syncStickyHeaderOffset);
      window.addEventListener('resize', syncStickyHeaderOffset);
      window.addEventListener('load', syncStickyHeaderOffset);
      if (window.ResizeObserver) {{
        const headerEl = document.querySelector('[data-admin-topbar]');
        if (headerEl) {{
          const headerResizeObserver = new ResizeObserver(() => syncStickyHeaderOffset());
          headerResizeObserver.observe(headerEl);
        }}
      }}

      const overlay = document.getElementById('admin-confirm-overlay');
      const titleEl = document.getElementById('admin-confirm-title');
      const messageEl = document.getElementById('admin-confirm-message');
      const cancelBtn = document.getElementById('admin-confirm-cancel');
      const confirmBtn = document.getElementById('admin-confirm-submit');
      let pendingForm = null;
      let pendingButton = null;

      if (!overlay || !titleEl || !messageEl || !cancelBtn || !confirmBtn) {{
        return;
      }}

      const closeDialog = () => {{
        overlay.classList.add('hidden');
        overlay.classList.remove('flex');
        overlay.setAttribute('aria-hidden', 'true');
        pendingForm = null;
        pendingButton = null;
      }};

      const openDialog = (button, form) => {{
        pendingForm = form;
        pendingButton = button;
        titleEl.textContent = button.dataset.confirmTitle || 'Confirm action';
        messageEl.textContent = button.dataset.confirmMessage || 'Please confirm this action.';
        confirmBtn.innerHTML = button.dataset.confirmCta || '<i class="fa-solid fa-check" aria-hidden="true"></i>Continue';
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
        overlay.setAttribute('aria-hidden', 'false');
        confirmBtn.focus();
      }};

      document.addEventListener('click', (event) => {{
        const button = event.target.closest('button[data-confirm-title]');
        if (!button) {{
          return;
        }}
        const form = button.closest('form');
        if (!form || button.dataset.confirmed === 'true') {{
          return;
        }}
        event.preventDefault();
        openDialog(button, form);
      }});

      document.addEventListener('click', (event) => {{
        const toggle = event.target.closest('button[data-editor-target]');
        if (!toggle) {{
          return;
        }}
        const targetId = toggle.dataset.editorTarget;
        const panel = targetId ? document.getElementById(targetId) : null;
        if (!panel) {{
          return;
        }}
        const isHidden = panel.classList.contains('hidden');
        document.querySelectorAll('[data-editor-row]').forEach((row) => {{
          row.classList.add('hidden');
        }});
        document.querySelectorAll('button[data-editor-target]').forEach((btn) => {{
          btn.dataset.expanded = 'false';
          btn.innerHTML = '<i class="fa-solid fa-pen-to-square" aria-hidden="true"></i>Edit';
        }});
        if (isHidden) {{
          panel.classList.remove('hidden');
          toggle.dataset.expanded = 'true';
          toggle.innerHTML = '<i class="fa-solid fa-chevron-up" aria-hidden="true"></i>Close';
        }}
      }});

      cancelBtn.addEventListener('click', closeDialog);

      confirmBtn.addEventListener('click', () => {{
        if (!pendingForm || !pendingButton) {{
          closeDialog();
          return;
        }}
        pendingButton.dataset.confirmed = 'true';
        pendingButton.disabled = true;
        pendingForm.requestSubmit(pendingButton);
        closeDialog();
      }});

      overlay.addEventListener('click', (event) => {{
        if (event.target === overlay) {{
          closeDialog();
        }}
      }});

      document.addEventListener('keydown', (event) => {{
        if (event.key === 'Escape' && overlay.classList.contains('flex')) {{
          closeDialog();
        }}
      }});

      const autosaveTimers = new Map();

      const markRowStatus = (row, status, text) => {{
        const statusEl = row ? row.querySelector('[data-autosave-status]') : null;
        if (!statusEl) {{
          return;
        }}
        statusEl.dataset.state = status;
        statusEl.textContent = text;
        statusEl.classList.remove('text-gray-500', 'text-emerald-700', 'text-red-700');
        if (status === 'saved') {{
          statusEl.classList.add('text-emerald-700');
        }} else if (status === 'error') {{
          statusEl.classList.add('text-red-700');
        }} else {{
          statusEl.classList.add('text-gray-500');
        }}
      }};

      const getFieldAutosaveValue = (field) => {{
        if (!field) {{
          return '';
        }}
        if (field.type === 'checkbox') {{
          return field.checked ? '1' : '0';
        }}
        return (field.value || '').toString();
      }};

      const hasFieldChanged = (field) => {{
        const currentValue = getFieldAutosaveValue(field);
        if (!Object.prototype.hasOwnProperty.call(field.dataset, 'savedValue')) {{
          field.dataset.savedValue = currentValue;
          return false;
        }}
        return field.dataset.savedValue !== currentValue;
      }};

      const buildAutosaveParams = (field) => {{
        const row = field.closest('tr[data-mentor-row]');
        const form = field.form;
        if (!row || !form) {{
          return null;
        }}
        const originalField = form.querySelector('input[name="original_github_username"]');
        if (!originalField || !originalField.value.trim()) {{
          return null;
        }}

        const params = new URLSearchParams();
        params.set('action', 'save');
        params.set('original_github_username', originalField.value.trim());

        const githubField = form.querySelector('[data-field="github_username"]');
        params.set('github_username', githubField ? githubField.value.trim() : originalField.value.trim());

        const key = field.dataset.field;
        if (!key) {{
          return null;
        }}
        if (field.type === 'checkbox') {{
          params.set(key, field.checked ? '1' : '0');
        }} else {{
          params.set(key, field.value);
        }}
        return {{ row, form, params }};
      }};

      const queueAutosave = (field, delayMs) => {{
        if (!hasFieldChanged(field)) {{
          return;
        }}
        const payload = buildAutosaveParams(field);
        if (!payload) {{
          return;
        }}
        const {{ row, form, params }} = payload;
        const configuredActionPath = {json.dumps(self.mentor_action_path)};
        const currentPath = (window.location && window.location.pathname) ? window.location.pathname.replace(/\\/+$/, '') : '';
        const actionCandidates = [];
        if (form.action) {{
          actionCandidates.push(form.action);
        }}
        if (configuredActionPath && !actionCandidates.includes(configuredActionPath)) {{
          actionCandidates.push(configuredActionPath);
        }}
        if (currentPath) {{
          const currentPathAction = `${{currentPath}}/mentors/action`;
          if (!actionCandidates.includes(currentPathAction)) {{
            actionCandidates.push(currentPathAction);
          }}
        }}
        const timerKey = form.id || form.getAttribute('action') || Math.random().toString(16);
        const existingTimer = autosaveTimers.get(timerKey);
        if (existingTimer) {{
          clearTimeout(existingTimer);
        }}
        markRowStatus(row, 'saving', 'Saving...');

        const timer = setTimeout(async () => {{
          try {{
            let response = null;
            for (const actionUrl of actionCandidates) {{
              response = await fetch(actionUrl, {{
                method: 'POST',
                headers: {{
                  'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                  'X-Admin-Autosave': '1',
                }},
                body: params.toString(),
              }});
              if (response.status !== 404) {{
                break;
              }}
            }}
            if (!response) {{
              markRowStatus(row, 'error', 'Save failed');
              return;
            }}
            if (!response.ok) {{
              let errorCode = '';
              try {{
                const errorData = await response.json();
                errorCode = (errorData && errorData.error) ? String(errorData.error) : '';
              }} catch (_parseError) {{
                errorCode = '';
              }}
              markRowStatus(row, 'error', errorCode ? `Save failed (${{errorCode}})` : 'Save failed');
              return;
            }}
            const data = await response.json();
            if (!data || data.ok !== true) {{
              const errorCode = (data && data.error) ? String(data.error) : '';
              markRowStatus(row, 'error', errorCode ? `Save failed (${{errorCode}})` : 'Save failed');
              return;
            }}

            const nextUsername = (data.github_username || '').trim();
            if (nextUsername) {{
              const originalField = form.querySelector('input[name="original_github_username"]');
              const githubField = form.querySelector('[data-field="github_username"]');
              if (originalField) {{
                originalField.value = nextUsername;
              }}
              if (githubField) {{
                githubField.value = nextUsername;
                githubField.dataset.savedValue = nextUsername;
              }}
              row.dataset.github_username = nextUsername.toLowerCase();
            }}
            if (field.dataset.field !== 'github_username') {{
              field.dataset.savedValue = getFieldAutosaveValue(field);
            }}
            markRowStatus(row, 'saved', 'Saved');
          }} catch (_error) {{
            markRowStatus(row, 'error', 'Network error');
          }} finally {{
            autosaveTimers.delete(timerKey);
          }}
        }}, delayMs);

        autosaveTimers.set(timerKey, timer);
      }};

      const assignmentCountFromValue = (value) => {{
        const raw = (value || '').toString().trim();
        if (!raw) {{
          return 0;
        }}
        return raw.split(',').map((item) => item.trim()).filter((item) => item.length > 0).length;
      }};

      const updateAssignmentCountBadge = (row) => {{
        if (!row) {{
          return;
        }}
        const assignmentField = row.querySelector('[data-field="assignments"]');
        const countBadge = row.querySelector('[data-assignment-count]');
        if (!assignmentField || !countBadge) {{
          return;
        }}
        const count = assignmentCountFromValue(assignmentField.value);
        row.dataset.assignment_count = String(count);
        countBadge.textContent = `${{count}} total`;
      }};

      document.querySelectorAll('tr[data-mentor-row]').forEach((row) => {{
        updateAssignmentCountBadge(row);
      }});

      document.querySelectorAll('tr[data-mentor-row] [data-field]').forEach((field) => {{
        field.dataset.savedValue = getFieldAutosaveValue(field);
        const isToggle = field.type === 'checkbox';
        field.addEventListener(isToggle ? 'change' : 'input', () => {{
          queueAutosave(field, isToggle ? 0 : 320);
          if (field.dataset.field === 'assignments') {{
            updateAssignmentCountBadge(field.closest('tr[data-mentor-row]'));
          }}
        }});
        field.addEventListener('blur', () => {{
          queueAutosave(field, 0);
          if (field.dataset.field === 'assignments') {{
            updateAssignmentCountBadge(field.closest('tr[data-mentor-row]'));
          }}
        }});
      }});

      const getSortableValue = (row, key) => {{
        if (key === 'assignments') {{
          const assignmentField = row.querySelector('[data-field="assignments"]');
          if (assignmentField) {{
            return String(assignmentCountFromValue(assignmentField.value));
          }}
          return ((row.dataset.assignment_count || '0') + '').trim();
        }}
        if (key === 'actions') {{
          const statusEl = row.querySelector('[data-autosave-status]');
          return ((statusEl ? statusEl.textContent : '') || '').toString().trim().toLowerCase();
        }}
        const field = row.querySelector(`[data-field="${{key}}"]`);
        if (field) {{
          if (field.type === 'checkbox') {{
            return field.checked ? '1' : '0';
          }}
          return (field.value || '').toString().trim().toLowerCase();
        }}
        return ((row.dataset[key] || '') + '').trim().toLowerCase();
      }};

      const sortButtons = Array.from(document.querySelectorAll('[data-sort-key]'));
      const mentorTable = document.getElementById('admin-mentor-table');
      const mentorTbody = mentorTable ? mentorTable.querySelector('tbody') : null;
      const resetSortingButton = document.getElementById('admin-reset-sorting');
      let sortCriteria = [];

      if (mentorTbody) {{
        Array.from(mentorTbody.querySelectorAll('tr[data-mentor-row]')).forEach((row, index) => {{
          row.dataset.originalIndex = String(index);
        }});
      }}

      const compareValues = (leftValue, rightValue) => {{
        const leftNumber = Number(leftValue);
        const rightNumber = Number(rightValue);
        if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber) && leftValue !== '' && rightValue !== '') {{
          return leftNumber - rightNumber;
        }}
        return String(leftValue).localeCompare(String(rightValue));
      }};

      const syncSortButtonState = () => {{
        sortButtons.forEach((button) => {{
          const key = button.dataset.sortKey;
          const criteriaIndex = sortCriteria.findIndex((item) => item.key === key);
          if (criteriaIndex === -1) {{
            button.dataset.sortDirection = 'desc';
            button.classList.remove('text-[#111827]');
            button.title = 'Click to sort';
          }} else {{
            const direction = sortCriteria[criteriaIndex].direction;
            button.dataset.sortDirection = direction;
            button.classList.add('text-[#111827]');
            button.title = `Sort priority ${{criteriaIndex + 1}} (${{direction}})`;
          }}
        }});
      }};

      const applySortCriteria = () => {{
        if (!mentorTbody) {{
          return;
        }}
        const rows = Array.from(mentorTbody.querySelectorAll('tr[data-mentor-row]'));

        if (sortCriteria.length === 0) {{
          rows
            .sort((left, right) => Number(left.dataset.originalIndex || '0') - Number(right.dataset.originalIndex || '0'))
            .forEach((row) => mentorTbody.appendChild(row));
          syncSortButtonState();
          return;
        }}

        rows.sort((left, right) => {{
          for (const criterion of sortCriteria) {{
            const leftValue = getSortableValue(left, criterion.key);
            const rightValue = getSortableValue(right, criterion.key);
            const result = compareValues(leftValue, rightValue);
            if (result !== 0) {{
              return criterion.direction === 'asc' ? result : -result;
            }}
          }}
          return Number(left.dataset.originalIndex || '0') - Number(right.dataset.originalIndex || '0');
        }});

        rows.forEach((row) => mentorTbody.appendChild(row));
        syncSortButtonState();
      }};

      sortButtons.forEach((button) => {{
        button.addEventListener('click', (event) => {{
          const key = button.dataset.sortKey;
          const existingIndex = sortCriteria.findIndex((item) => item.key === key);

          if (!event.shiftKey) {{
            if (existingIndex >= 0) {{
              const currentDirection = sortCriteria[existingIndex].direction;
              sortCriteria = [{{ key, direction: currentDirection === 'asc' ? 'desc' : 'asc' }}];
            }} else {{
              sortCriteria = [{{ key, direction: 'asc' }}];
            }}
          }} else if (existingIndex >= 0) {{
            const currentDirection = sortCriteria[existingIndex].direction;
            sortCriteria[existingIndex].direction = currentDirection === 'asc' ? 'desc' : 'asc';
          }} else {{
            sortCriteria.push({{ key, direction: 'asc' }});
          }}

          applySortCriteria();
        }});
      }});

      if (resetSortingButton) {{
        resetSortingButton.addEventListener('click', () => {{
          sortCriteria = [];
          applySortCriteria();
        }});
      }}

      syncSortButtonState();
    }})();
  </script>
</body>
</html>"""

    async def _handle_dashboard(self, username: str):
        mentors = await self._mentor_rows()
        rate_status = await self._github_rate_limit_status()
        counts = {
            "total": len(mentors),
            "active": len([m for m in mentors if int(m.get("active") or 0) == 1]),
            "inactive": len([m for m in mentors if int(m.get("active") or 0) != 1]),
            "assignments": sum(int(m.get("assignment_count") or 0) for m in mentors),
            "total_prs": sum(int(m.get("total_prs") or 0) for m in mentors),
            "total_reviews": sum(int(m.get("total_reviews") or 0) for m in mentors),
            "total_comments": sum(int(m.get("total_comments") or 0) for m in mentors),
        }
        dashboard_rate_limit = int((rate_status or {}).get("limit") or 0)
        dashboard_rate_used = int((rate_status or {}).get("used") or 0)
        dashboard_rate_remaining = int((rate_status or {}).get("remaining") or 0)
        dashboard_rate_reset_at = int((rate_status or {}).get("reset_at") or 0)
        dashboard_rate_reset_label = self._format_timestamp(dashboard_rate_reset_at, with_time=True)
        dashboard_rate_remaining_label = self._format_seconds_remaining(
            int((rate_status or {}).get("seconds_remaining") or 0)
        )

        mentor_rows = "\n".join(self._mentor_row_html(row) for row in mentors)
        if not mentor_rows:
            mentor_rows = (
                "<div class='rounded-2xl border border-dashed border-[#E5E5E5] bg-gray-50 px-6 py-10 text-center text-sm text-gray-500'>"
                "No mentors found in D1 yet.</div>"
            )

        content = f"""
        <div class="mx-auto max-w-6xl">
          <div class="flex flex-wrap items-center gap-2 rounded-xl border border-[#E5E5E5] bg-gray-50 p-2 text-xs font-semibold text-gray-700">
            <span class="rounded-md bg-white px-2.5 py-1">Mentors: <strong class="text-[#111827]">{counts['total']}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Published: <strong class="text-[#111827]">{counts['active']}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Blocked: <strong class="text-[#111827]">{counts['inactive']}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Assignments: <strong class="text-[#111827]">{counts['assignments']}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">PRs: <strong class="text-[#111827]">{counts['total_prs']}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Reviews: <strong class="text-[#111827]">{counts['total_reviews']}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Comments: <strong class="text-[#111827]">{counts['total_comments']}</strong></span>
            <span class="rounded-md bg-[#111827] px-2.5 py-1 text-white">Version: <strong>v{_escape(APP_VERSION)}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">API: <strong class="text-[#111827]">{dashboard_rate_used}/{dashboard_rate_limit if dashboard_rate_limit > 0 else 'n/a'}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Remaining: <strong class="text-[#111827]">{dashboard_rate_remaining}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Reset: <strong class="text-[#111827]">{dashboard_rate_reset_label}</strong></span>
            <span class="rounded-md bg-white px-2.5 py-1">Time left: <strong class="text-[#111827]">{dashboard_rate_remaining_label}</strong></span>
          </div>
        </div>

        <div class="mt-8 -mx-5 overflow-visible border-t border-[#E5E5E5] bg-white sm:-mx-6 lg:-mx-7">
          <div class="border-b border-[#E5E5E5] px-5 py-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 class="text-lg font-bold text-[#111827]">Mentor management</h3>
                <p class="mt-1 text-sm text-gray-600">Inline editable mentor grid with sortable columns. Click to sort one column, Shift+click to add secondary columns.</p>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  id="admin-reset-sorting"
                  class="inline-flex items-center gap-2 rounded-md border border-[#E5E5E5] bg-white px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-[#E10101] hover:text-[#E10101]"
                  title="Reset table sorting to original order">
                  <i class="fa-solid fa-arrow-rotate-left" aria-hidden="true"></i>
                  Reset sorting
                </button>
                <form method="POST" action="{self.mentor_action_path}">
                  <input type="hidden" name="action" value="refresh_pr_counts">
                  <button
                    type="submit"
                    data-confirm-title="Refresh PR counts?"
                    data-confirm-message="This will recalculate total lifetime PR counts for all mentors across OWASP-BLT repositories."
                    data-confirm-cta="<i class=&quot;fa-solid fa-rotate&quot; aria-hidden=&quot;true&quot;></i>Refresh counts"
                    class="inline-flex items-center gap-2 rounded-md border border-[#E5E5E5] bg-white px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-[#E10101] hover:text-[#E10101]">
                    <i class="fa-solid fa-rotate" aria-hidden="true"></i>
                    Refresh PR counts
                  </button>
                </form>
                <form method="POST" action="{self.mentor_action_path}">
                  <input type="hidden" name="action" value="clear_and_refresh_pr_counts">
                  <button
                    type="submit"
                    data-confirm-title="Clear and recalculate PR counts?"
                    data-confirm-message="This will reset all mentor PR totals to zero and then fully recalculate them from GitHub with pagination."
                    data-confirm-cta="<i class=&quot;fa-solid fa-arrows-rotate&quot; aria-hidden=&quot;true&quot;></i>Clear + recalculate"
                    class="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-100">
                    <i class="fa-solid fa-arrows-rotate" aria-hidden="true"></i>
                    Clear + recalculate
                  </button>
                </form>
                <form method="POST" action="{self.mentor_action_path}">
                  <input type="hidden" name="action" value="refresh_review_counts">
                  <button
                    type="submit"
                    data-confirm-title="Refresh review totals?"
                    data-confirm-message="This will recalculate total approved/changes-requested review counts for all mentors in OWASP-BLT."
                    data-confirm-cta="<i class=&quot;fa-solid fa-rotate&quot; aria-hidden=&quot;true&quot;></i>Refresh reviews"
                    class="inline-flex items-center gap-2 rounded-md border border-[#E5E5E5] bg-white px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-[#E10101] hover:text-[#E10101]">
                    <i class="fa-solid fa-rotate" aria-hidden="true"></i>
                    Refresh reviews
                  </button>
                </form>
                <form method="POST" action="{self.mentor_action_path}">
                  <input type="hidden" name="action" value="clear_and_refresh_review_counts">
                  <button
                    type="submit"
                    data-confirm-title="Clear and recalculate review totals?"
                    data-confirm-message="This will reset mentor review totals to zero and fully recalculate approved and changes-requested PR review counts."
                    data-confirm-cta="<i class=&quot;fa-solid fa-arrows-rotate&quot; aria-hidden=&quot;true&quot;></i>Clear + recalculate reviews"
                    class="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-100">
                    <i class="fa-solid fa-arrows-rotate" aria-hidden="true"></i>
                    Clear + recalculate reviews
                  </button>
                </form>
                <form method="POST" action="{self.mentor_action_path}">
                  <input type="hidden" name="action" value="refresh_comment_counts">
                  <button
                    type="submit"
                    data-confirm-title="Refresh comment totals?"
                    data-confirm-message="This will recalculate total issue and PR comment counts for all mentors across OWASP-BLT repositories."
                    data-confirm-cta="<i class=&quot;fa-solid fa-rotate&quot; aria-hidden=&quot;true&quot;></i>Refresh comments"
                    class="inline-flex items-center gap-2 rounded-md border border-[#E5E5E5] bg-white px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-[#E10101] hover:text-[#E10101]">
                    <i class="fa-solid fa-rotate" aria-hidden="true"></i>
                    Refresh comments
                  </button>
                </form>
                <form method="POST" action="{self.mentor_action_path}">
                  <input type="hidden" name="action" value="clear_and_refresh_comment_counts">
                  <button
                    type="submit"
                    data-confirm-title="Clear and recalculate comment totals?"
                    data-confirm-message="This will reset mentor comment totals to zero and then fully recalculate issue and PR comments from GitHub."
                    data-confirm-cta="<i class=&quot;fa-solid fa-arrows-rotate&quot; aria-hidden=&quot;true&quot;></i>Clear + recalculate comments"
                    class="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-100">
                    <i class="fa-solid fa-arrows-rotate" aria-hidden="true"></i>
                    Clear + recalculate comments
                  </button>
                </form>
              </div>
            </div>
          </div>
          <div class="relative overflow-x-auto overflow-y-visible">
            <table id="admin-mentor-table" class="min-w-full text-left text-sm">
              <thead class="bg-gray-50 text-[11px] font-semibold uppercase tracking-wide text-gray-500 shadow-sm">
                <tr>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="mentor" data-sort-direction="desc" class="inline-flex items-center gap-1">Mentor <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="name" data-sort-direction="desc" class="inline-flex items-center gap-1">Name <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="github_username" data-sort-direction="desc" class="inline-flex items-center gap-1">GitHub <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="created_at" data-sort-direction="desc" class="inline-flex items-center gap-1">Added <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="total_prs" data-sort-direction="desc" class="inline-flex items-center gap-1">PRs (all-time) <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="total_reviews" data-sort-direction="desc" class="inline-flex items-center gap-1">Reviews (all-time) <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="total_comments" data-sort-direction="desc" class="inline-flex items-center gap-1">Comments (all-time) <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="last_rate_used" data-sort-direction="desc" class="inline-flex items-center gap-1">GitHub API limit <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="max_mentees" data-sort-direction="desc" class="inline-flex items-center gap-1">Cap <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="slack_username" data-sort-direction="desc" class="inline-flex items-center gap-1">Slack <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="email" data-sort-direction="desc" class="inline-flex items-center gap-1">Email <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="specialties" data-sort-direction="desc" class="inline-flex items-center gap-1">Specialties <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="active" data-sort-direction="desc" class="inline-flex items-center gap-1">Published <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="timezone" data-sort-direction="desc" class="inline-flex items-center gap-1">Timezone <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="referred_by" data-sort-direction="desc" class="inline-flex items-center gap-1">Referral <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3"><button type="button" data-sort-key="assignments" data-sort-direction="desc" class="inline-flex items-center gap-1">Assignments (count) <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                  <th class="sticky z-30 bg-gray-50 px-3 py-3 text-right"><button type="button" data-sort-key="actions" data-sort-direction="desc" class="inline-flex items-center gap-1">Actions <i class="fa-solid fa-sort text-[10px]" aria-hidden="true"></i></button></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[#E5E5E5]">
                {mentor_rows}
              </tbody>
            </table>
          </div>

          <div class="border-t border-[#E5E5E5] bg-gray-50/60 px-5 py-4">
            <h3 class="text-sm font-bold uppercase tracking-wide text-[#111827]">Add mentor</h3>
            <form method="POST" action="{self.mentor_action_path}" class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5 xl:grid-cols-10">
              <input type="hidden" name="action" value="create">
              <input name="name" required maxlength="100" placeholder="Name" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="github_username" required maxlength="39" placeholder="GitHub username" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="specialties" maxlength="300" placeholder="specialty1, specialty2" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="max_mentees" type="number" min="1" max="10" value="3" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="timezone" maxlength="60" placeholder="Timezone" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="referred_by" maxlength="39" placeholder="Referral" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="slack_username" maxlength="80" placeholder="Slack" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="email" type="email" maxlength="255" placeholder="Email" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <input name="assignments" placeholder="repo#123, repo#456" class="rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800">
              <div class="flex items-center justify-between gap-3 rounded-md border border-gray-300 bg-white px-3 py-2">
                <label class="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
                  <input name="active" type="checkbox" value="1" checked>
                  Published
                </label>
                <button type="submit" class="inline-flex items-center gap-2 rounded-md bg-[#E10101] px-3 py-2 text-xs font-semibold text-white transition hover:bg-red-700">
                  <i class="fa-solid fa-plus" aria-hidden="true"></i>
                  Add mentor
                </button>
              </div>
            </form>
          </div>
        </div>
        """
        return self._html(
            self._shell(
                "Admin dashboard",
                content,
                user=username,
                subtitle="Manage mentor publishing and keep the public mentor pool healthy.",
            )
        )

    async def _mentor_rows(self) -> list:
        rows = await self._d1_all(
            """
            SELECT
                m.github_username,
                m.name,
                m.specialties,
                m.max_mentees,
                m.active,
                m.timezone,
                m.referred_by,
                m.email,
                m.slack_username,
                m.total_prs,
                m.total_reviews,
                m.total_comments,
                m.last_rate_limit,
                m.last_rate_remaining,
                m.last_rate_used,
                m.last_rate_reset_at,
                m.created_at,
                COALESCE(a.assignment_refs, '') AS assignment_refs,
                COALESCE(a.assignment_count, 0) AS assignment_count
            FROM mentors m
            LEFT JOIN (
                SELECT mentor_login,
                       COUNT(*) AS assignment_count,
                       GROUP_CONCAT(issue_repo || '#' || issue_number, ', ') AS assignment_refs
                FROM mentor_assignments
                GROUP BY mentor_login
            ) a
            ON a.mentor_login = m.github_username
            ORDER BY m.active DESC, LOWER(m.name) ASC
            """
        )
        parsed = []
        for row in rows:
            try:
                specialties = json.loads(row.get("specialties") or "[]")
            except Exception:
                specialties = []
            parsed.append({**row, "specialties_list": specialties})
        return parsed

    def _format_timestamp(self, value, with_time: bool = False) -> str:
        ts = _int_or_default(value, 0)
        if ts <= 0:
            return "n/a"
        dt = datetime.fromtimestamp(ts, tz=dt_timezone.utc)
        if with_time:
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        return dt.strftime("%Y-%m-%d")

    def _mentor_row_html(self, mentor: dict) -> str:
        username = mentor.get("github_username", "")
        name = mentor.get("name", "")
        active = int(mentor.get("active") or 0) == 1
        specialties = mentor.get("specialties_list") or []
        specialties_value = ", ".join(str(item) for item in specialties)
        email = mentor.get("email") or ""
        slack_username = mentor.get("slack_username") or ""
        assignment_refs = mentor.get("assignment_refs") or ""
        assignment_count = int(mentor.get("assignment_count") or 0)
        total_prs = int(mentor.get("total_prs") or 0)
        total_reviews = int(mentor.get("total_reviews") or 0)
        total_comments = int(mentor.get("total_comments") or 0)
        last_rate_limit = int(mentor.get("last_rate_limit") or 0)
        last_rate_remaining = int(mentor.get("last_rate_remaining") or 0)
        last_rate_used = int(mentor.get("last_rate_used") or 0)
        rate_usage_label = f"{last_rate_used}/{last_rate_limit}" if last_rate_limit > 0 else "n/a"
        rate_reset_label = self._format_timestamp(mentor.get("last_rate_reset_at"), with_time=True)
        rate_time_remaining = self._format_seconds_remaining(
          self._seconds_until_timestamp(int(mentor.get("last_rate_reset_at") or 0))
        )
        added_label = self._format_timestamp(mentor.get("created_at"), with_time=False)
        form_id = f"mentor-form-{username.lower().replace('_', '-')}"
        return f"""
        <tr data-mentor-row data-mentor="{_escape(name).lower()}" data-name="{_escape(name).lower()}" data-github_username="{_escape(username).lower()}" data-active="{1 if active else 0}" data-created_at="{int(mentor.get('created_at') or 0)}" data-total_prs="{total_prs}" data-total_reviews="{total_reviews}" data-total_comments="{total_comments}" data-last_rate_used="{last_rate_used}" data-max_mentees="{int(mentor.get('max_mentees') or 3)}" data-assignment_count="{assignment_count}">
          <td class="px-3 py-2">
            <div class="flex items-center gap-2">
              <a href="https://github.com/{_escape(username)}" target="_blank" rel="noopener noreferrer" aria-label="Open @{_escape(username)} on GitHub" class="inline-flex h-8 w-8 shrink-0 overflow-hidden rounded-full border border-[#E5E5E5] bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E10101] focus-visible:ring-offset-2">
                <img src="https://github.com/{_escape(username)}.png" alt="{_escape(name)}" class="h-full w-full shrink-0 object-cover transition hover:opacity-90">
              </a>
              <span data-autosave-status data-state="idle" class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] font-semibold text-gray-500">Idle</span>
            </div>
            <form id="{form_id}" method="POST" action="{self.mentor_action_path}">
              <input type="hidden" name="action" value="save">
              <input type="hidden" name="original_github_username" value="{_escape(username)}">
            </form>
          </td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="name" name="name" value="{_escape(name)}" class="w-40 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" maxlength="100" required></td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="github_username" name="github_username" value="{_escape(username)}" class="w-36 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" maxlength="39" required></td>
          <td class="px-3 py-2">
            <span class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-semibold text-gray-700">{_escape(added_label)}</span>
          </td>
          <td class="px-3 py-2">
            <span class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-semibold text-gray-700">{total_prs}</span>
          </td>
          <td class="px-3 py-2">
            <span class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-semibold text-gray-700">{total_reviews}</span>
          </td>
          <td class="px-3 py-2">
            <span class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-semibold text-gray-700">{total_comments}</span>
          </td>
          <td class="px-3 py-2">
            <div class="space-y-1">
              <span class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] font-semibold text-gray-700">Used {rate_usage_label}</span>
              <p class="text-[11px] font-medium text-gray-500">Reset: {_escape(rate_reset_label)} | Remaining: {last_rate_remaining}</p>
              <p class="text-[11px] font-medium text-gray-500">Time remaining: {_escape(rate_time_remaining)}</p>
            </div>
          </td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="max_mentees" name="max_mentees" type="number" min="1" max="10" value="{int(mentor.get('max_mentees') or 3)}" class="w-20 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800"></td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="slack_username" name="slack_username" value="{_escape(slack_username)}" class="w-32 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" maxlength="80"></td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="email" name="email" type="email" value="{_escape(email)}" class="w-56 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" maxlength="255"></td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="specialties" name="specialties" value="{_escape(specialties_value)}" class="w-48 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" maxlength="300" placeholder="frontend, python"></td>
          <td class="px-3 py-2 text-center">
            <label class="inline-flex items-center justify-center">
              <input form="{form_id}" data-field="active" name="active" type="checkbox" value="1" {'checked' if active else ''}>
            </label>
          </td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="timezone" name="timezone" value="{_escape(mentor.get('timezone') or '')}" class="w-28 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" maxlength="60"></td>
          <td class="px-3 py-2"><input form="{form_id}" data-field="referred_by" name="referred_by" value="{_escape(mentor.get('referred_by') or '')}" class="w-28 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" maxlength="39"></td>
          <td class="px-3 py-2">
            <div class="space-y-1">
              <span data-assignment-count class="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] font-semibold text-gray-600">{assignment_count} total</span>
              <input form="{form_id}" data-field="assignments" name="assignments" value="{_escape(assignment_refs)}" class="w-48 rounded-md border border-gray-300 px-2.5 py-2 text-sm text-gray-800" placeholder="repo#123, repo#456">
            </div>
          </td>
          <td class="px-3 py-2">
            <div class="flex items-center justify-end gap-2">
              <form method="POST" action="{self.mentor_action_path}">
                <input type="hidden" name="github_username" value="{_escape(username)}">
                <input type="hidden" name="action" value="delete">
                <button
                  type="submit"
                  data-confirm-title="Delete mentor?"
                  data-confirm-message="This permanently removes the mentor record and clears related assignments from the admin panel."
                  data-confirm-cta="<i class=&quot;fa-solid fa-trash&quot; aria-hidden=&quot;true&quot;></i>Delete mentor"
                  class="inline-flex items-center gap-1 rounded-md border border-red-200 px-2.5 py-2 text-xs font-semibold text-red-700 transition hover:bg-red-50">
                  <i class="fa-solid fa-trash" aria-hidden="true"></i>
                  Delete
                </button>
              </form>
            </div>
          </td>
        </tr>
        """

    async def _handle_mentor_action(self, request, username: str):
        if not username:
            return self._basic_auth_challenge()

        form = await self._form_data(request)
        github_username = (form.get("github_username") or "").strip().lstrip("@")
        action = (form.get("action") or "").strip().lower()
        autosave = self._is_autosave_request(request)
        if action not in {
          "save",
          "delete",
          "create",
          "refresh_pr_counts",
          "clear_and_refresh_pr_counts",
          "refresh_review_counts",
          "clear_and_refresh_review_counts",
          "refresh_comment_counts",
          "clear_and_refresh_comment_counts",
        }:
            if autosave:
                return self._json({"ok": False, "error": "invalid_action"}, 400)
            return self._redirect(self.admin_path)

        try:
            if action == "create":
              name = (form.get("name") or "").strip()
              new_github_username = (form.get("github_username") or "").strip().lstrip("@")
              specialties_raw = (form.get("specialties") or "").strip()
              timezone = (form.get("timezone") or "").strip()
              referred_by = (form.get("referred_by") or "").strip().lstrip("@")
              email = (form.get("email") or "").strip().lower()
              slack_username = (form.get("slack_username") or "").strip().lstrip("@")
              assignments_value = (form.get("assignments") or "").strip()
              active = 1 if (form.get("active") or "") == "1" else 0

              if not name:
                if autosave:
                  return self._json({"ok": False, "error": "name_required"}, 400)
                return self._redirect(self.admin_path)
              if not _GH_USERNAME_RE.match(new_github_username):
                if autosave:
                  return self._json({"ok": False, "error": "invalid_github_username"}, 400)
                return self._redirect(self.admin_path)
              if referred_by and not _GH_USERNAME_RE.match(referred_by):
                if autosave:
                  return self._json({"ok": False, "error": "invalid_referred_by"}, 400)
                return self._redirect(self.admin_path)
              if email and not _EMAIL_RE.match(email):
                if autosave:
                  return self._json({"ok": False, "error": "invalid_email"}, 400)
                return self._redirect(self.admin_path)
              if slack_username and not _SLACK_USERNAME_RE.match(slack_username):
                if autosave:
                  return self._json({"ok": False, "error": "invalid_slack_username"}, 400)
                return self._redirect(self.admin_path)
              if assignments_value and self._parse_assignment_refs(assignments_value) is None:
                if autosave:
                  return self._json({"ok": False, "error": "invalid_assignments"}, 400)
                return self._redirect(self.admin_path)

              existing = await self._d1_first(
                "SELECT github_username FROM mentors WHERE github_username = ?",
                (new_github_username,),
              )
              if existing:
                if autosave:
                  return self._json({"ok": False, "error": "mentor_exists"}, 409)
                return self._redirect(self.admin_path)

              specialties_list = [
                item.strip().lower()
                for item in specialties_raw.split(",")
                if item.strip()
              ]
              try:
                max_mentees = int(form.get("max_mentees") or 3)
              except Exception:
                max_mentees = 3
              max_mentees = max(1, min(10, max_mentees))

              await self._d1_run(
                """
                INSERT INTO mentors (
                  github_username,
                  name,
                  specialties,
                  max_mentees,
                  active,
                  timezone,
                  referred_by,
                  email,
                  slack_username,
                  created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                  new_github_username,
                  name,
                  json.dumps(specialties_list),
                  max_mentees,
                  active,
                  timezone,
                  referred_by,
                  email,
                  slack_username,
                  int(datetime.now(tz=dt_timezone.utc).timestamp()),
                ),
              )

              if assignments_value:
                if not await self._sync_assignments(new_github_username, new_github_username, assignments_value):
                  if autosave:
                    return self._json({"ok": False, "error": "assignment_sync_failed"}, 400)
                  return self._redirect(self.admin_path)

              if autosave:
                return self._json({"ok": True, "github_username": new_github_username})

            elif action == "save":
                original_github_username = (form.get("original_github_username") or "").strip().lstrip("@")
                if not original_github_username:
                    if autosave:
                        return self._json({"ok": False, "error": "missing_original_github_username"}, 400)
                    return self._redirect(self.admin_path)

                existing = await self._d1_first(
                    """
                    SELECT github_username, name, specialties, max_mentees, active, timezone, referred_by, email, slack_username
                    FROM mentors
                    WHERE github_username = ?
                    """,
                    (original_github_username,),
                )
                if not existing:
                    if autosave:
                        return self._json({"ok": False, "error": "mentor_not_found"}, 404)
                    return self._redirect(self.admin_path)

                try:
                    existing_specialties = json.loads(existing.get("specialties") or "[]")
                except Exception:
                    existing_specialties = []

                new_github_username = (
                    (form.get("github_username") if "github_username" in form else existing.get("github_username") or "")
                    .strip()
                    .lstrip("@")
                )
                name = (form.get("name") if "name" in form else existing.get("name") or "").strip()
                specialties_raw = (
                    form.get("specialties")
                    if "specialties" in form
                    else ", ".join(str(item) for item in existing_specialties)
                ).strip()
                timezone = (form.get("timezone") if "timezone" in form else existing.get("timezone") or "").strip()
                referred_by = (
                    (form.get("referred_by") if "referred_by" in form else existing.get("referred_by") or "")
                    .strip()
                    .lstrip("@")
                )
                email = (form.get("email") if "email" in form else existing.get("email") or "").strip().lower()
                slack_username = (
                    (form.get("slack_username") if "slack_username" in form else existing.get("slack_username") or "")
                    .strip()
                    .lstrip("@")
                )
                assignments_value = (form.get("assignments") if "assignments" in form else "").strip()
                if "active" in form:
                    active = 1 if (form.get("active") or "") == "1" else 0
                else:
                    active = 1 if int(existing.get("active") or 0) == 1 else 0

                validate_name = (not autosave) or ("name" in form)
                validate_github_username = (not autosave) or ("github_username" in form)
                validate_referred_by = (not autosave) or ("referred_by" in form)
                validate_email = (not autosave) or ("email" in form)
                validate_slack_username = (not autosave) or ("slack_username" in form)

                if validate_name and not name:
                  if autosave:
                    return self._json({"ok": False, "error": "name_required"}, 400)
                  return self._redirect(self.admin_path)
                if validate_github_username and not _GH_USERNAME_RE.match(new_github_username):
                  if autosave:
                    return self._json({"ok": False, "error": "invalid_github_username"}, 400)
                  return self._redirect(self.admin_path)
                if validate_referred_by and referred_by and not _GH_USERNAME_RE.match(referred_by):
                  if autosave:
                    return self._json({"ok": False, "error": "invalid_referred_by"}, 400)
                  return self._redirect(self.admin_path)
                if validate_email and email and not _EMAIL_RE.match(email):
                  if autosave:
                    return self._json({"ok": False, "error": "invalid_email"}, 400)
                  return self._redirect(self.admin_path)
                if validate_slack_username and slack_username and not _SLACK_USERNAME_RE.match(slack_username):
                  if autosave:
                    return self._json({"ok": False, "error": "invalid_slack_username"}, 400)
                  return self._redirect(self.admin_path)
                if "assignments" in form and self._parse_assignment_refs(assignments_value) is None:
                    if autosave:
                        return self._json({"ok": False, "error": "invalid_assignments"}, 400)
                    return self._redirect(self.admin_path)

                specialties_list = [
                    item.strip().lower()
                    for item in specialties_raw.split(",")
                    if item.strip()
                ]
                try:
                    max_mentees = int(
                        form.get("max_mentees") if "max_mentees" in form else existing.get("max_mentees") or 3
                    )
                except Exception:
                    max_mentees = 3
                max_mentees = max(1, min(10, max_mentees))

                await self._d1_run(
                    """
                    UPDATE mentors
                    SET github_username = ?,
                        name = ?,
                        specialties = ?,
                        max_mentees = ?,
                        active = ?,
                        timezone = ?,
                        referred_by = ?,
                        email = ?,
                        slack_username = ?
                    WHERE github_username = ?
                    """,
                    (
                        new_github_username,
                        name,
                        json.dumps(specialties_list),
                        max_mentees,
                        active,
                        timezone,
                        referred_by,
                        email,
                        slack_username,
                        original_github_username,
                    ),
                )
                if new_github_username != original_github_username:
                    await self._d1_run(
                        "UPDATE mentor_assignments SET mentor_login = ? WHERE mentor_login = ?",
                        (new_github_username, original_github_username),
                    )
                if "assignments" in form:
                    if not await self._sync_assignments(original_github_username, new_github_username, assignments_value):
                        if autosave:
                            return self._json({"ok": False, "error": "assignment_sync_failed"}, 400)
                        return self._redirect(self.admin_path)

                if autosave:
                    return self._json({"ok": True, "github_username": new_github_username})
            elif action == "refresh_pr_counts":
                await self._recalculate_all_mentor_pr_counts(clear_first=False)
                if autosave:
                    return self._json({"ok": True})
            elif action == "clear_and_refresh_pr_counts":
                await self._recalculate_all_mentor_pr_counts(clear_first=True)
                if autosave:
                    return self._json({"ok": True})
            elif action == "refresh_review_counts":
              await self._recalculate_all_mentor_review_counts(clear_first=False)
              if autosave:
                return self._json({"ok": True})
            elif action == "clear_and_refresh_review_counts":
              await self._recalculate_all_mentor_review_counts(clear_first=True)
              if autosave:
                return self._json({"ok": True})
            elif action == "refresh_comment_counts":
              await self._recalculate_all_mentor_comment_counts(clear_first=False)
              if autosave:
                return self._json({"ok": True})
            elif action == "clear_and_refresh_comment_counts":
              await self._recalculate_all_mentor_comment_counts(clear_first=True)
              if autosave:
                return self._json({"ok": True})
            else:
                if not github_username:
                    if autosave:
                        return self._json({"ok": False, "error": "missing_github_username"}, 400)
                    return self._redirect(self.admin_path)
                await self._d1_run("DELETE FROM mentor_assignments WHERE mentor_login = ?", (github_username,))
                await self._d1_run("DELETE FROM mentors WHERE github_username = ?", (github_username,))
                if autosave:
                    return self._json({"ok": True})
        except Exception as exc:
            console.error(f"[AdminService] Mentor action '{action}' failed for {github_username}: {exc}")
            if autosave:
                return self._json({"ok": False, "error": "internal_error"}, 500)

        return self._redirect(self.admin_path)
