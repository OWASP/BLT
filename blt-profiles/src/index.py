import json
import re
from datetime import datetime, timezone

from js import fetch
from workers import Response, WorkerEntrypoint


RESERVED_PATHS = {
    "api",
    "favicon.ico",
    "index.html",
    "profile.html",
    "profiles",
    "robots.txt",
    "webhooks",
}

ROLE_SECTIONS = {
    "Leads",
    "Co-Leads",
    "Ambassadors",
    "Interns",
    "Contributors",
    "Mentors",
}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url
        path = _path_from_url(url)

        if path == "/api/health":
            return _json({"ok": True, "service": "blt-profiles"})

        if path == "/webhooks/gitlab/profile-submission":
            return await self._handle_gitlab_issue_webhook(request)

        if request.method in ("GET", "HEAD") and _maybe_profile_page(path):
            return await self.env.ASSETS.fetch("https://assets.local/profile.html")

        return await self.env.ASSETS.fetch(request)

    async def _handle_gitlab_issue_webhook(self, request):
        if request.method != "POST":
            return Response("Method Not Allowed", status=405)

        expected_token = _env(self.env, "GITLAB_WEBHOOK_TOKEN")
        if expected_token and request.headers.get("x-gitlab-token") != expected_token:
            return _json({"ok": False, "error": "invalid webhook token"}, status=401)

        try:
            event = json.loads(await request.text())
        except Exception:
            return _json({"ok": False, "error": "invalid json"}, status=400)

        issue = event.get("object_attributes") or {}
        if event.get("object_kind") != "issue" or not issue:
            return _json({"ok": True, "skipped": "not an issue event"})

        labels = _extract_labels(event)
        if "profile-submission" not in labels:
            return _json({"ok": True, "skipped": "issue is not a profile submission"})

        action = issue.get("action") or "open"
        if action not in {"open", "reopen", "update"}:
            return _json({"ok": True, "skipped": f"unsupported issue action: {action}"})

        access_token = _env(self.env, "GITLAB_ACCESS_TOKEN")
        if not access_token:
            return _json({"ok": False, "error": "missing GITLAB_ACCESS_TOKEN"}, status=500)

        fields = _parse_issue_description(issue.get("description") or "")
        profile = _build_profile(fields, issue, event.get("user") or {})
        project_id = _env(self.env, "GITLAB_PROJECT_ID") or event.get("project", {}).get("id") or _env(self.env, "GITLAB_PROJECT_PATH")
        default_branch = _env(self.env, "GITLAB_DEFAULT_BRANCH") or event.get("project", {}).get("default_branch") or "main"
        timestamp = int(datetime.now(timezone.utc).timestamp())
        branch = f"profile/{profile['username']}-{issue.get('iid') or timestamp}-{timestamp}"
        site_url = (_env(self.env, "PUBLIC_SITE_URL") or _origin_from_url(request.url)).rstrip("/")

        api = GitLabApi(self.env, project_id, access_token)

        try:
            await api.create_branch(branch, default_branch)
            index = await api.get_json_file("profiles/index.json", default_branch, [])
            updated_index = _upsert_index(index, profile)
            await api.commit(
                branch,
                f"profile: add @{profile['username']}",
                [
                    {
                        "action": "create",
                        "file_path": f"profiles/{profile['username']}.json",
                        "content": json.dumps(profile, indent=2) + "\n",
                    },
                    {
                        "action": "update",
                        "file_path": "profiles/index.json",
                        "content": json.dumps(updated_index, indent=2) + "\n",
                    },
                ],
            )
            merge_request = await api.create_merge_request(
                {
                    "source_branch": branch,
                    "target_branch": default_branch,
                    "title": f"Add profile for @{profile['username']}",
                    "description": "\n".join(
                        [
                            f"Created from profile submission issue #{issue.get('iid')}.",
                            "",
                            f"Preview after merge: {site_url}/{profile['username']}",
                        ]
                    ),
                    "remove_source_branch": True,
                }
            )
            mr_url = merge_request.get("web_url") or merge_request.get("url") or ""
            await api.create_issue_note(
                issue.get("iid"),
                "\n".join(
                    item
                    for item in [
                        "Profile merge request created.",
                        "",
                        f"Merge request: {mr_url}" if mr_url else "",
                        f"Profile URL after merge: {site_url}/{profile['username']}",
                    ]
                    if item
                ),
            )
            return _json({"ok": True, "username": profile["username"], "merge_request": mr_url})
        except Exception as exc:
            message = str(exc)
            await _safe_issue_note(api, issue.get("iid"), f"Profile automation failed: {message}")
            return _json({"ok": False, "error": message}, status=500)


class GitLabApi:
    def __init__(self, env, project_id, access_token):
        self.api_base = _env(env, "GITLAB_API_BASE") or "https://gitlab.com/api/v4"
        self.project = _encode_component(str(project_id))
        self.access_token = access_token

    async def create_branch(self, branch, ref):
        return await self._request(
            "/repository/branches",
            method="POST",
            body={"branch": branch, "ref": ref},
        )

    async def get_json_file(self, file_path, ref, fallback):
        encoded_path = _encode_component(file_path)
        url = f"{self.api_base}/projects/{self.project}/repository/files/{encoded_path}/raw?ref={_encode_component(ref)}"
        response = await fetch(url, headers={"PRIVATE-TOKEN": self.access_token})
        if response.status == 404:
            return fallback
        if not response.ok:
            raise Exception(f"GitLab API {response.status}: {await response.text()}")
        try:
            return json.loads(await response.text())
        except Exception as exc:
            raise Exception(f"{file_path} is not valid JSON") from exc

    async def commit(self, branch, message, actions):
        return await self._request(
            "/repository/commits",
            method="POST",
            body={
                "branch": branch,
                "commit_message": message,
                "actions": actions,
            },
        )

    async def create_merge_request(self, body):
        return await self._request("/merge_requests", method="POST", body=body)

    async def create_issue_note(self, issue_iid, body):
        return await self._request(
            f"/issues/{issue_iid}/notes",
            method="POST",
            body={"body": body},
        )

    async def _request(self, path, method="GET", body=None):
        response = await fetch(
            f"{self.api_base}/projects/{self.project}{path}",
            method=method,
            headers={
                "PRIVATE-TOKEN": self.access_token,
                "Content-Type": "application/json",
            },
            body=json.dumps(body) if body is not None else None,
        )
        text = await response.text()
        payload = json.loads(text) if text else {}
        if not response.ok:
            raise Exception(f"GitLab API {response.status}: {json.dumps(payload)}")
        return payload


def _parse_issue_description(description):
    fields = {}
    pattern = re.compile(r"^##\s+(.+?)\s*\n([\s\S]*?)(?=^##\s+|\s*$)", re.MULTILINE)
    for key, value in pattern.findall(description):
        fields[key.strip()] = _cleanup_value(value)
    return fields


def _cleanup_value(value):
    value = re.sub(r"<!--[\s\S]*?-->", "", value)
    value = re.sub(r"^- \[[ xX]\].*$", "", value, flags=re.MULTILINE)
    return value.strip()


def _build_profile(fields, issue, user):
    gitlab_username = _required_username(
        fields.get("GitLab Username") or user.get("username") or issue.get("author_username")
    )
    github_username = _clean_username(fields.get("GitHub Username"))
    display_name = _clean_text(fields.get("Display Name")) or user.get("name") or gitlab_username
    role_section = _normalize_role_section(fields.get("Role Section"))
    role = _clean_text(fields.get("Role / Title")) or role_section.rstrip("s")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "username": gitlab_username,
        "name": display_name,
        "role": role,
        "role_section": role_section,
        "avatar": user.get("avatar_url") or "",
        "gitlab": f"https://gitlab.com/{gitlab_username}",
        "github": f"https://github.com/{github_username}" if github_username else "",
        "linkedin": _clean_url(fields.get("LinkedIn Profile URL")),
        "website": _clean_url(fields.get("Website URL")),
        "wallet": _clean_text(fields.get("Wallet / ID String")),
        "bio": "",
        "followers": 0,
        "following": 0,
        "public_repos": 0,
        "questions": {
            "involvement": _clean_text(fields.get("Question 1: What is your involvement in cybersecurity?")),
            "evolution": _clean_text(fields.get("Question 2: How do you see cybersecurity evolving?")),
            "achievement": _clean_text(fields.get("Question 3: What is your most significant cybersecurity achievement or contribution?")),
        },
        "streak": {
            "current": 0,
            "longest": 0,
            "days_visited": 0,
            "last_visit": "",
            "last_checkin": "",
        },
        "stats": {
            "bugs_reported": 0,
            "open_issues": 0,
            "closed_issues": 0,
        },
        "issue_stats": {
            "general": 0,
            "functional": 0,
            "performance": 0,
            "security": 0,
            "typo": 0,
            "design": 0,
        },
        "bacon": {
            "earned": 0,
            "pending": 0,
            "completed": 0,
        },
        "prs": {
            "total": 0,
            "merged": 0,
            "open": 0,
            "closed": 0,
        },
        "pr_list": [],
        "badges": [],
        "tags": _parse_tags(fields.get("Tags / Labels")),
        "rank": "Newcomer",
        "monthly_report": {
            "top_finding": "",
        },
        "created_at": now,
    }


def _upsert_index(index, profile):
    entry = {
        "username": profile["username"],
        "name": profile["name"],
        "role": profile["role"],
        "role_section": profile["role_section"],
        "avatar": profile["avatar"],
        "tags": profile["tags"],
        "stats": profile["stats"],
        "prs": profile["prs"],
        "questions": {
            "involvement": _truncate(profile["questions"]["involvement"], 200),
        },
        "created_at": profile["created_at"],
    }
    return sorted(
        [item for item in index if item.get("username") != profile["username"]] + [entry],
        key=lambda item: item.get("username", ""),
    )


def _extract_labels(event):
    labels = event.get("labels") or event.get("object_attributes", {}).get("labels") or []
    names = []
    for label in labels:
        if isinstance(label, str):
            names.append(label)
        elif isinstance(label, dict):
            names.append(label.get("title") or label.get("name"))
    return [name for name in names if name]


def _maybe_profile_page(path):
    parts = [part for part in path.split("/") if part]
    if len(parts) != 1:
        return False
    slug = parts[0]
    if slug in RESERVED_PATHS:
        return False
    return re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,38}$", slug) is not None


def _path_from_url(url):
    match = re.match(r"^https?://[^/]+([^?#]*)", str(url))
    return match.group(1) or "/" if match else "/"


def _origin_from_url(url):
    match = re.match(r"^(https?://[^/]+)", str(url))
    return match.group(1) if match else ""


def _env(env, name):
    return getattr(env, name, None)


def _clean_username(value):
    return str(value or "").strip().lstrip("@").lower()


def _required_username(value):
    username = _clean_username(value)
    if re.match(r"^[a-z0-9][a-z0-9._-]{1,38}$", username) is None:
        raise Exception("GitLab Username must be 2-39 characters using letters, numbers, dots, underscores, or hyphens")
    return username


def _normalize_role_section(value):
    raw = _clean_text(value)
    for role in ROLE_SECTIONS:
        if role.lower() == raw.lower():
            return role
    return "Contributors"


def _clean_text(value):
    return str(value or "").strip()


def _clean_url(value):
    url = _clean_text(value)
    if not url:
        return ""
    return url if re.match(r"^https?://", url, re.IGNORECASE) else ""


def _parse_tags(value):
    return [tag.strip() for tag in re.split(r"[,;]+", _clean_text(value)) if tag.strip()][:12]


def _truncate(value, max_length):
    text = _clean_text(value)
    if len(text) <= max_length:
        return text
    short = text[:max_length]
    last_space = short.rfind(" ")
    if last_space > 0:
        short = short[:last_space]
    return short.strip() + "..."


def _encode_component(value):
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    encoded = []
    for char in str(value):
        if char in safe:
            encoded.append(char)
        else:
            for byte in char.encode("utf-8"):
                encoded.append(f"%{byte:02X}")
    return "".join(encoded)


async def _safe_issue_note(api, issue_iid, body):
    try:
        await api.create_issue_note(issue_iid, body)
    except Exception:
        pass


def _json(data, status=200):
    return Response(
        json.dumps(data, indent=2),
        status=status,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
