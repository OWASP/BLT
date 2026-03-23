import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

try:
    from js import Object, fetch
    from pyodide.ffi import to_js as _to_js
    from workers import Response, WorkerEntrypoint
except ImportError:
    Object = None
    Response = None
    WorkerEntrypoint = object
    _to_js = None
    fetch = None


PROJECTS_PER_PAGE = 100
SCHEMA_STATEMENTS = [
    (
        "CREATE TABLE IF NOT EXISTS slack_activity ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "activity_kind TEXT NOT NULL, "
        "slack_type TEXT, "
        "command_name TEXT, "
        "team_id TEXT, "
        "user_id TEXT, "
        "channel_id TEXT, "
        "payload_json TEXT NOT NULL, "
        "received_at TEXT NOT NULL"
        ")"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_slack_activity_received_at "
        "ON slack_activity(received_at)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS workspace_installations ("
        "team_id TEXT PRIMARY KEY, "
        "installer_user_id TEXT NOT NULL, "
        "installed_at TEXT NOT NULL"
        ")"
    ),
]
SCHEMA_READY = False


def _to_js_options(value: Dict[str, Any]) -> Any:
    if _to_js is None or Object is None:
        return value
    return _to_js(value, dict_converter=Object.fromEntries)


def to_python(value: Any) -> Any:
    try:
        return value.to_py()
    except Exception:
        return value


def env_value(env: Any, name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = getattr(env, name)
    except Exception:
        return default
    if value is None:
        return default
    return str(value)


def required_env_value(env: Any, name: str) -> str:
    value = env_value(env, name)
    if not value:
        raise ValueError("Missing required environment variable: {0}".format(name))
    return value


def load_json_file(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}


def load_text_file(path: Path) -> Optional[str]:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None


ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_DATA = load_json_file(ROOT_DIR / "data" / "projects.json")
REPO_DATA = load_json_file(ROOT_DIR / "data" / "repos.json")


def get_team_message_template(team_id: str, event_name: str) -> Optional[str]:
    if not team_id:
        return None
    template_path = ROOT_DIR / "data" / "message-{0}-{1}.md".format(team_id, event_name)
    return load_text_file(template_path)


def render_team_join_message(
    event_payload: Dict[str, Any], team_id: str
) -> Optional[str]:
    template = get_team_message_template(team_id, "team_join")
    if not template:
        return None

    user = event_payload.get("user") or {}
    username = (
        user.get("name")
        or user.get("real_name")
        or user.get("profile", {}).get("display_name")
        or user.get("id")
        or "there"
    )
    return template.format(username=username)


def current_config_message(env: Any, team_id: str, installer_user_id: str) -> str:
    def _get_value(name: str) -> str:
        return env_value(env, name) or "(unset)"

    lines = [
        "Current BLT worker config:",
        "team_id: {0}".format(team_id or "(unknown)"),
        "installer_user_id: {0}".format(installer_user_id or "(unknown)"),
        "github_activity_repo: {0}/{1}".format(
            _get_value("GITHUB_ACTIVITY_OWNER"), _get_value("GITHUB_ACTIVITY_REPO")
        ),
        "github_issue_repo: {0}/{1}".format(
            _get_value("GITHUB_ISSUE_OWNER"), _get_value("GITHUB_ISSUE_REPO")
        ),
        "slack_redirect_url: {0}".format(_get_value("SLACK_REDIRECT_URL")),
        "slack_app_url: {0}".format(_get_value("SLACK_APP_URL")),
    ]
    return "\n".join(lines)


def build_slack_install_url(env: Any) -> str:
    client_id = required_env_value(env, "SLACK_CLIENT_ID")
    redirect_uri = required_env_value(env, "SLACK_REDIRECT_URL")
    state = required_env_value(env, "SLACK_OAUTH_STATE")
    scopes = required_env_value(env, "SLACK_OAUTH_SCOPES")
    user_scopes = env_value(env, "SLACK_OAUTH_USER_SCOPES")

    params = {
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if user_scopes:
        params["user_scope"] = user_scopes
    return "https://slack.com/oauth/v2/authorize?{0}".format(urlencode(params))


def build_response(
    body: str,
    status: int = 200,
    content_type: str = "text/plain; charset=utf-8",
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    if Response is None:
        raise RuntimeError("Cloudflare Workers runtime is required for HTTP responses")
    response_headers = {"content-type": content_type}
    if headers:
        response_headers.update(headers)
    return Response(body, status=status, headers=response_headers)


def json_response(payload: Dict[str, Any], status: int = 200) -> Any:
    return build_response(
        json.dumps(payload),
        status=status,
        content_type="application/json; charset=utf-8",
    )


def html_response(body: str, status: int = 200) -> Any:
    return build_response(body, status=status, content_type="text/html; charset=utf-8")


def flatten_form_values(values: Dict[str, List[str]]) -> Dict[str, str]:
    return dict((key, item[0] if item else "") for key, item in values.items())


def parse_form_encoded(body: str) -> Dict[str, str]:
    return flatten_form_values(parse_qs(body, keep_blank_values=True))


def verify_slack_signature(
    signing_secret: str,
    timestamp: str,
    body: str,
    signature: str,
    now_ts: Optional[int] = None,
) -> bool:
    if not signing_secret or not timestamp or not signature:
        return False
    try:
        request_ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    current_ts = int(now_ts if now_ts is not None else time.time())
    if abs(current_ts - request_ts) > 60 * 5:
        return False

    payload = "v0:{0}:{1}".format(timestamp, body).encode("utf-8")
    expected = (
        "v0="
        + hmac.new(signing_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


def chunked(items: List[str], size: int) -> List[List[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def make_section_block(text: str) -> Dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_project_selection_blocks(project_names: List[str]) -> List[Dict[str, Any]]:
    if not project_names:
        return [make_section_block("No projects are available right now.")]

    blocks = []
    project_pages = chunked(project_names, PROJECTS_PER_PAGE)
    for index, page in enumerate(project_pages):
        options = []
        for project_name in page:
            options.append(
                {
                    "text": {"type": "plain_text", "text": project_name[:75]},
                    "value": project_name,
                }
            )
        blocks.append(
            {
                "type": "section",
                "block_id": "project_select_block_{0}".format(index),
                "text": {
                    "type": "mrkdwn",
                    "text": "Select a project (Page {0})".format(index + 1),
                },
                "accessory": {
                    "type": "static_select",
                    "action_id": "project_select_action_{0}".format(index),
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose a project",
                    },
                    "options": options,
                },
            }
        )
    return blocks


def build_repo_selection_blocks(
    repo_data: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    technologies = sorted(repo_data.keys())
    if not technologies:
        return [make_section_block("No technologies are configured.")]

    buttons = []
    for tech_name in technologies[:25]:
        buttons.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": tech_name[:75]},
                "value": tech_name,
                "action_id": "plugin_repo_button_{0}".format(tech_name),
            }
        )

    return [
        make_section_block("Choose a technology to see matching repositories."),
        {"type": "actions", "block_id": "repo_select_block", "elements": buttons},
    ]


def make_project_detail(project_name: str) -> Optional[str]:
    project = PROJECT_DATA.get(project_name)
    if not project:
        return None
    description = project[0] if project else "No description available."
    link = project[1] if len(project) > 1 else ""
    detail_lines = ["*{0}*".format(project_name), description]
    if link:
        detail_lines.append(link)
    return "\n".join(detail_lines)


def search_projects(query: str, limit: int = 10) -> List[str]:
    normalized = query.strip().lower()
    if not normalized:
        return []
    matches = []
    for project_name in sorted(PROJECT_DATA.keys()):
        if normalized in project_name:
            matches.append(project_name)
        if len(matches) >= limit:
            break
    return matches


def make_repo_detail(technology: str) -> Optional[str]:
    repos = REPO_DATA.get(technology)
    if not repos:
        return None
    return "*{0} repositories*\n{1}".format(technology, "\n".join(repos))


def search_repo_technologies(query: str, limit: int = 10) -> List[str]:
    normalized = query.strip().lower()
    if not normalized:
        return []
    matches = []
    for tech_name in sorted(REPO_DATA.keys()):
        if normalized in tech_name:
            matches.append(tech_name)
        if len(matches) >= limit:
            break
    return matches


def format_contributor_blocks(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "response_type": "ephemeral",
            "text": "No contributor activity was found for the last 7 days.",
            "blocks": [
                make_section_block(
                    "No contributor activity was found for the last 7 days."
                )
            ],
        }

    user_width = max(len(str(row["user"])) for row in rows)
    prs_width = max(len("PRs Merged"), max(len(str(row["prs"])) for row in rows))
    issues_width = max(
        len("Issues Closed"), max(len(str(row["issues"])) for row in rows)
    )
    comments_width = max(
        len("Comments"), max(len(str(row["comments"])) for row in rows)
    )

    header = "{0:<{uw}}  {1:<{pw}}  {2:<{iw}}  {3:<{cw}}".format(
        "User",
        "PRs Merged",
        "Issues Closed",
        "Comments",
        uw=user_width,
        pw=prs_width,
        iw=issues_width,
        cw=comments_width,
    )
    separator = "{0}  {1}  {2}  {3}".format(
        "-" * user_width,
        "-" * prs_width,
        "-" * issues_width,
        "-" * comments_width,
    )
    body_rows = []
    for row in rows:
        body_rows.append(
            "{0:<{uw}}  {1:<{pw}}  {2:<{iw}}  {3:<{cw}}".format(
                row["user"],
                row["prs"],
                row["issues"],
                row["comments"],
                uw=user_width,
                pw=prs_width,
                iw=issues_width,
                cw=comments_width,
            )
        )

    table = "\n".join([header, separator] + body_rows)
    return {
        "response_type": "ephemeral",
        "text": "Contributor activity for the last 7 days.",
        "blocks": [
            make_section_block("*Contributor Activity*\n```{0}```".format(table))
        ],
    }


def summarize_contributors(
    pull_requests: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    user_data = {}
    for collection_name, collection in (
        ("prs", pull_requests),
        ("issues", issues),
        ("comments", comments),
    ):
        for item in collection:
            user = item.get("user", {}).get("login")
            if not user:
                continue
            if user not in user_data:
                user_data[user] = {"prs": 0, "issues": 0, "comments": 0}
            user_data[user][collection_name] += 1

    rows = []
    for user, counts in user_data.items():
        rows.append(
            {
                "user": user,
                "prs": counts["prs"],
                "issues": counts["issues"],
                "comments": counts["comments"],
                "total": counts["prs"] + counts["issues"] + counts["comments"],
            }
        )
    rows.sort(key=lambda row: (-row["total"], row["user"]))
    return rows


async def fetch_json(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any], int]:
    if fetch is None:
        raise RuntimeError("Cloudflare Workers runtime is required for outbound fetch")

    options = {"method": method, "headers": headers or {}}
    if body is not None:
        options["body"] = body

    response = await fetch(url, _to_js_options(options))
    text = await response.text()
    payload = {}
    if text:
        payload = json.loads(str(text))
    return bool(response.ok), payload, int(response.status)


async def d1_run(
    env: Any, sql: str, params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    statement = env.DB.prepare(sql)
    if params:
        statement = statement.bind(*params)
    result = await statement.run()
    return to_python(result)


async def ensure_schema(env: Any) -> None:
    global SCHEMA_READY
    if SCHEMA_READY:
        return
    try:
        getattr(env, "DB")
    except Exception:
        return
    for sql in SCHEMA_STATEMENTS:
        await d1_run(env, sql)
    SCHEMA_READY = True


async def record_activity(
    env: Any, activity_kind: str, payload: Dict[str, Any]
) -> None:
    try:
        getattr(env, "DB")
    except Exception:
        return

    await ensure_schema(env)
    received_at = datetime.now(timezone.utc).isoformat()
    slack_type = payload.get("type") or payload.get("event", {}).get("type")
    command_name = payload.get("command")
    team_id = payload.get("team_id")
    user_id = payload.get("user_id") or payload.get("event", {}).get("user")
    channel_id = payload.get("channel_id") or payload.get("channel", {}).get("id")
    payload_json = json.dumps(payload, sort_keys=True)

    await d1_run(
        env,
        (
            "INSERT INTO slack_activity ("
            "activity_kind, slack_type, command_name, team_id, user_id, channel_id, payload_json, received_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        [
            activity_kind,
            slack_type,
            command_name,
            team_id,
            user_id,
            channel_id,
            payload_json,
            received_at,
        ],
    )


async def save_workspace_installer(
    env: Any, team_id: str, installer_user_id: str
) -> None:
    if not team_id or not installer_user_id:
        return
    try:
        getattr(env, "DB")
    except Exception:
        return

    await ensure_schema(env)
    installed_at = datetime.now(timezone.utc).isoformat()
    await d1_run(
        env,
        (
            "INSERT INTO workspace_installations (team_id, installer_user_id, installed_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(team_id) DO UPDATE SET "
            "installer_user_id = excluded.installer_user_id, "
            "installed_at = excluded.installed_at"
        ),
        [team_id, installer_user_id, installed_at],
    )


async def get_workspace_installer(env: Any, team_id: str) -> Optional[str]:
    if not team_id:
        return env_value(env, "SLACK_INSTALLER_USER_ID")
    try:
        getattr(env, "DB")
    except Exception:
        return env_value(env, "SLACK_INSTALLER_USER_ID")

    await ensure_schema(env)
    result = await d1_run(
        env,
        "SELECT installer_user_id FROM workspace_installations WHERE team_id = ? LIMIT 1",
        [team_id],
    )
    rows = result.get("results") or []
    if rows and rows[0].get("installer_user_id"):
        return str(rows[0]["installer_user_id"])
    return env_value(env, "SLACK_INSTALLER_USER_ID")


async def installed_apps_summary(env: Any) -> str:
    try:
        getattr(env, "DB")
    except Exception:
        return "D1 is not configured yet. Bind a database to enable installation analytics."

    await ensure_schema(env)
    result = await d1_run(
        env,
        (
            "SELECT COUNT(DISTINCT team_id) AS teams, COUNT(*) AS events "
            "FROM slack_activity WHERE team_id IS NOT NULL"
        ),
    )
    rows = result.get("results") or []
    if not rows:
        return "No Slack activity has been recorded yet."
    teams = rows[0].get("teams", 0)
    events = rows[0].get("events", 0)
    return "Tracked workspaces: {0}\nLogged webhook events: {1}".format(teams, events)


async def fetch_contributor_activity(env: Any) -> List[Dict[str, Any]]:
    token = env_value(env, "GITHUB_TOKEN")
    owner = required_env_value(env, "GITHUB_ACTIVITY_OWNER")
    repo = required_env_value(env, "GITHUB_ACTIVITY_REPO")
    since_date = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    since_stamp = "{0}T00:00:00Z".format(since_date)

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer {0}".format(token)

    prs_query = "repo:{0}/{1} is:pr is:merged merged:>={2}".format(
        owner, repo, since_date
    )
    issues_query = "repo:{0}/{1} is:issue is:closed closed:>={2}".format(
        owner, repo, since_date
    )

    prs_url = "https://api.github.com/search/issues?{0}".format(
        urlencode({"q": prs_query, "per_page": "100"})
    )
    issues_url = "https://api.github.com/search/issues?{0}".format(
        urlencode({"q": issues_query, "per_page": "100"})
    )
    comments_url = "https://api.github.com/repos/{0}/{1}/issues/comments?{2}".format(
        owner,
        repo,
        urlencode({"since": since_stamp, "per_page": "100"}),
    )

    _, prs_payload, _ = await fetch_json(prs_url, headers=headers)
    _, issues_payload, _ = await fetch_json(issues_url, headers=headers)
    _, comments_payload, _ = await fetch_json(comments_url, headers=headers)

    prs = prs_payload.get("items") or []
    issues = issues_payload.get("items") or []
    comments = comments_payload if isinstance(comments_payload, list) else []
    return summarize_contributors(prs, issues, comments)


async def create_github_issue(title: str, env: Any) -> Tuple[bool, str]:
    token = env_value(env, "GITHUB_TOKEN")
    if not token:
        return False, "Set GITHUB_TOKEN to enable /ghissue."

    try:
        owner = required_env_value(env, "GITHUB_ISSUE_OWNER")
        repo = required_env_value(env, "GITHUB_ISSUE_REPO")
    except ValueError as error:
        return False, str(error)

    url = "https://api.github.com/repos/{0}/{1}/issues".format(owner, repo)
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer {0}".format(token),
        "Content-Type": "application/json",
    }
    ok, payload, _ = await fetch_json(
        url,
        method="POST",
        headers=headers,
        body=json.dumps({"title": title}),
    )
    if not ok or not payload.get("html_url"):
        message = payload.get("message") or "GitHub issue creation failed."
        return False, message
    return True, str(payload["html_url"])


def help_response() -> Dict[str, Any]:
    text = (
        "Available commands:\n"
        "• /contributors or /stats\n"
        "• /project [name]\n"
        "• /repo [technology]\n"
        "• /ghissue [title]\n"
        "• /blt-app-url"
    )
    return {
        "response_type": "ephemeral",
        "text": text,
        "blocks": [
            make_section_block(
                "*BLT Sammich Commands*\n{0}".format(text.replace("\n", "\n"))
            )
        ],
    }


def contrib_response() -> Dict[str, Any]:
    message = (
        ":rocket: Contributing to OWASP Projects\n\n"
        "    :small_blue_diamond: Join the OWASP Slack Channel: Find guidance and check pinned "
        "posts for projects seeking contributors.\n"
        "    :small_blue_diamond: Explore OWASP Projects Page: Identify projects that align "
        "with your skills and interests.\n\n"
        ":loudspeaker: Engaging on Slack\n\n"
        "    Many projects have dedicated project channels for collaboration.\n\n"
        "    :mag: Find and Join a Project Channel: To find project channels:\n\n"
        ":one: Use Slack's channel browser (Ctrl/Cmd + K)\n"
        ":two: Type #project- to see all project channels\n"
        ":three: Join the channels that interest you\n\n"
        "All OWASP project channels start with #project-\n\n"
        ":hammer_and_wrench: GSOC Projects: View this year's participating GSOC projects "
        "https://owasp.org/www-community/initiatives/gsoc/gsoc2026ideas\n\n"
        ":busts_in_silhouette: Identifying Key People and Activity\n\n"
        "    • Visit the OWASP Projects page to find project leaders and contributors.\n"
        "    • Review GitHub commit history for active developers.\n"
        "    • Check Slack activity for updates on project progress.\n\n"
        ":pushpin: Communication Guidelines\n\n"
        "    :white_check_mark: Check pinned messages in project channels for updates.\n"
        "    :white_check_mark: Ask questions in relevant project channels.\n"
        "    :white_check_mark: Introduce yourself while keeping personal details private.\n\n"
        ":hammer_and_wrench: How to Contribute\n\n"
        "    :one: Select a project and review its contribution guidelines.\n"
        "    :two: Work on an open GitHub issue or propose a new one.\n"
        "    :three: Coordinate with project leaders to prevent overlaps.\n"
        "    :four: Submit a pull request and keep the team informed.\n\n"
        "    :bulb: Focus on clear communication and teamwork! :rocket:"
    )
    return {
        "response_type": "ephemeral",
        "text": message,
        "blocks": [make_section_block(message)],
    }


def blt_app_url_response(env: Any) -> Dict[str, Any]:
    app_url = env_value(env, "SLACK_APP_URL")
    if not app_url:
        message = "Missing required environment variable: SLACK_APP_URL"
        return {
            "response_type": "ephemeral",
            "text": message,
            "blocks": [make_section_block(message)],
        }
    return {
        "response_type": "ephemeral",
        "text": app_url,
        "blocks": [make_section_block("Slack App URL:\n{0}".format(app_url))],
    }


def discover_response(query: str) -> Dict[str, Any]:
    project_matches = search_projects(query)
    repo_matches = search_repo_technologies(query)
    blocks = [
        make_section_block(
            "*Discovery results for* `{0}`".format(query or "everything")
        )
    ]

    if project_matches:
        blocks.append(make_section_block("*Projects*\n" + "\n".join(project_matches)))
    if repo_matches:
        blocks.append(make_section_block("*Technologies*\n" + "\n".join(repo_matches)))
    if len(blocks) == 1:
        blocks.append(
            make_section_block("No matching projects or technologies were found.")
        )

    return {
        "response_type": "ephemeral",
        "text": "Discovery results ready.",
        "blocks": blocks,
    }


def project_response(text: str) -> Dict[str, Any]:
    project_name = text.strip().lower()
    if project_name:
        detail = make_project_detail(project_name)
        if detail:
            return {
                "response_type": "ephemeral",
                "text": detail,
                "blocks": [make_section_block(detail)],
            }
        matches = search_projects(project_name)
        if matches:
            blocks = [make_section_block("Project not found. Similar matches:")]
            for match in matches:
                blocks.append(make_section_block("• {0}".format(match)))
            return {
                "response_type": "ephemeral",
                "text": "Similar project matches found.",
                "blocks": blocks,
            }
        return {
            "response_type": "ephemeral",
            "text": "Project not found.",
            "blocks": [make_section_block("Project not found.")],
        }

    blocks = build_project_selection_blocks(sorted(PROJECT_DATA.keys()))
    return {
        "response_type": "ephemeral",
        "text": "Choose a project to inspect.",
        "blocks": blocks,
    }


def repo_response(text: str) -> Dict[str, Any]:
    technology = text.strip().lower()
    if technology:
        detail = make_repo_detail(technology)
        if detail:
            return {
                "response_type": "ephemeral",
                "text": detail,
                "blocks": [make_section_block(detail)],
            }
        matches = search_repo_technologies(technology)
        if matches:
            return {
                "response_type": "ephemeral",
                "text": "Technology not found. Similar matches are available.",
                "blocks": [
                    make_section_block("Similar technologies:\n" + "\n".join(matches))
                ],
            }
        return {
            "response_type": "ephemeral",
            "text": "Technology not found.",
            "blocks": [make_section_block("Technology not found.")],
        }

    return {
        "response_type": "ephemeral",
        "text": "Choose a technology to inspect.",
        "blocks": build_repo_selection_blocks(REPO_DATA),
    }


async def command_response(form: Dict[str, str], env: Any) -> Dict[str, Any]:
    command_name = form.get("command", "")
    command_text = form.get("text", "")

    if command_name in ("/contributors", "/stats"):
        try:
            rows = await fetch_contributor_activity(env)
        except ValueError as error:
            return {
                "response_type": "ephemeral",
                "text": str(error),
                "blocks": [make_section_block(str(error))],
            }
        return format_contributor_blocks(rows)
    if command_name == "/ghissue":
        title = command_text.strip()
        if not title:
            return {
                "response_type": "ephemeral",
                "text": "Usage: /ghissue <title>",
                "blocks": [make_section_block("Usage: `/ghissue <title>`")],
            }
        ok, message = await create_github_issue(title, env)
        if ok:
            return {
                "response_type": "ephemeral",
                "text": "Issue created successfully: {0}".format(message),
                "blocks": [
                    make_section_block(
                        "Issue created successfully:\n{0}".format(message)
                    )
                ],
            }
        return {
            "response_type": "ephemeral",
            "text": message,
            "blocks": [make_section_block(message)],
        }
    if command_name == "/project":
        return project_response(command_text)
    if command_name == "/repo":
        return repo_response(command_text)
    if command_name == "/discover":
        return discover_response(command_text)
    if command_name == "/contrib":
        return contrib_response()
    if command_name == "/gsoc25":
        return {
            "response_type": "ephemeral",
            "text": "Use /discover with a technology or mentor keyword to explore matches.",
            "blocks": [
                make_section_block(
                    "Use `/discover <keyword>` to search the bundled project and repository data for GSoC-relevant terms."
                )
            ],
        }
    if command_name == "/installed_apps":
        summary = await installed_apps_summary(env)
        return {
            "response_type": "ephemeral",
            "text": summary,
            "blocks": [make_section_block(summary)],
        }
    if command_name == "/blt-app-url":
        return blt_app_url_response(env)
    if command_name == "/blt":
        return help_response()

    return {
        "response_type": "ephemeral",
        "text": "Unsupported command.",
        "blocks": [make_section_block("Unsupported command.")],
    }


def interaction_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    actions = payload.get("actions") or []
    if not actions:
        return {"text": "No action payload was provided.", "replace_original": False}

    action = actions[0]
    action_id = action.get("action_id", "")
    if action_id.startswith("project_select_action_"):
        project_name = action.get("selected_option", {}).get("value", "")
        detail = make_project_detail(project_name)
        if detail:
            return {
                "text": detail,
                "replace_original": False,
                "blocks": [make_section_block(detail)],
            }
    if action_id.startswith("plugin_repo_button_"):
        technology = action.get("value", "")
        detail = make_repo_detail(technology)
        if detail:
            return {
                "text": detail,
                "replace_original": False,
                "blocks": [make_section_block(detail)],
            }
    return {"text": "Interaction received.", "replace_original": False}


async def slack_api_post_message(channel_id: str, text: str, env: Any) -> None:
    token = env_value(env, "SLACK_BOT_TOKEN")
    if not token:
        return
    await fetch_json(
        "https://slack.com/api/chat.postMessage",
        method="POST",
        headers={
            "Authorization": "Bearer {0}".format(token),
            "Content-Type": "application/json",
        },
        body=json.dumps({"channel": channel_id, "text": text}),
    )


async def handle_event_payload(payload: Dict[str, Any], env: Any) -> Any:
    if payload.get("type") == "url_verification":
        return json_response({"challenge": payload.get("challenge", "")})

    event = payload.get("event") or {}
    if event.get("type") == "app_mention":
        channel_id = event.get("channel")
        if channel_id:
            await slack_api_post_message(
                channel_id,
                "Try /contributors, /project, /repo, or /ghissue from the slash command menu.",
                env,
            )
    if event.get("type") == "team_join":
        team_id = payload.get("team_id", "")
        user_id = event.get("user", {}).get("id")
        welcome_message = render_team_join_message(event, team_id)
        if user_id and welcome_message:
            await slack_api_post_message(user_id, welcome_message, env)
    if event.get("type") == "message":
        if event.get("subtype"):
            return json_response({"ok": True})
        team_id = payload.get("team_id", "")
        user_id = event.get("user", "")
        channel_id = event.get("channel", "")
        installer_user_id = await get_workspace_installer(env, team_id)
        if installer_user_id and user_id == installer_user_id and channel_id:
            await slack_api_post_message(
                channel_id,
                current_config_message(env, team_id, installer_user_id),
                env,
            )
    return json_response({"ok": True})


async def handle_oauth_callback(request_url: Any, env: Any) -> Any:
    params = parse_qs(request_url.query)
    if params.get("error"):
        return html_response(
            "<h1>Slack OAuth failed</h1><p>{0}</p>".format(params["error"][0]),
            status=400,
        )

    code = params.get("code", [""])[0]
    state = params.get("state", [""])[0]
    expected_state = env_value(env, "SLACK_OAUTH_STATE")
    if expected_state and state != expected_state:
        return html_response("<h1>State mismatch</h1>", status=400)
    if not code:
        return html_response("<h1>Missing OAuth code</h1>", status=400)

    client_id = env_value(env, "SLACK_CLIENT_ID")
    client_secret = env_value(env, "SLACK_CLIENT_SECRET")
    redirect_url = env_value(env, "SLACK_REDIRECT_URL")
    if not client_id or not client_secret:
        return html_response(
            (
                "<h1>OAuth callback reached</h1>"
                "<p>Configure SLACK_CLIENT_ID and SLACK_CLIENT_SECRET to complete installation.</p>"
            ),
            status=500,
        )
    if not redirect_url:
        return html_response(
            "<h1>Missing SLACK_REDIRECT_URL</h1>",
            status=500,
        )

    ok, payload, _ = await fetch_json(
        "https://slack.com/api/oauth.v2.access",
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_url,
            }
        ),
    )
    await record_activity(
        env,
        "oauth_callback",
        {
            "type": "oauth_callback",
            "team_id": payload.get("team", {}).get("id"),
            "payload": payload,
        },
    )

    await save_workspace_installer(
        env,
        str(payload.get("team", {}).get("id") or ""),
        str(payload.get("authed_user", {}).get("id") or ""),
    )

    if not ok or not payload.get("ok"):
        error_message = payload.get("error") or "OAuth exchange failed."
        return html_response(
            "<h1>Slack OAuth failed</h1><p>{0}</p>".format(error_message), status=500
        )

    team_name = payload.get("team", {}).get("name") or "your workspace"
    return html_response(
        (
            "<h1>Slack app installed</h1>"
            "<p>BLT Sammich is now connected to <strong>{0}</strong>.</p>"
            "<p>You can return to Slack and run /contributors, /project, /repo, or /ghissue.</p>"
        ).format(team_name)
    )


async def handle_request(request: Any, env: Any) -> Any:
    parsed_url = urlparse(request.url)
    path = parsed_url.path or "/"
    method = str(request.method).upper()

    if method == "GET" and path == "/health":
        return json_response({"ok": True, "service": "blt-sammich-worker"})

    if method == "GET" and path == "/oauth/slack/callback":
        return await handle_oauth_callback(parsed_url, env)

    if method == "GET" and path == "/install-slack":
        try:
            install_url = build_slack_install_url(env)
        except ValueError as error:
            return html_response(
                "<h1>Install URL misconfigured</h1><p>{0}</p>".format(str(error)),
                status=500,
            )
        return build_response(
            "",
            status=302,
            headers={"location": install_url},
        )

    if method == "POST" and path in ("/slack/commands", "/slack/events"):
        body_text = str(await request.text())
        signing_secret = env_value(env, "SLACK_SIGNING_SECRET", "") or ""
        timestamp = request.headers.get("x-slack-request-timestamp", "")
        signature = request.headers.get("x-slack-signature", "")
        if not verify_slack_signature(signing_secret, timestamp, body_text, signature):
            return build_response("Invalid Slack signature.", status=401)

        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            form = parse_form_encoded(body_text)
            if path == "/slack/events" and form.get("payload"):
                payload = json.loads(form["payload"])
                await record_activity(env, "interaction", payload)
                return json_response(interaction_response(payload))

            await record_activity(env, "slash_command", form)
            return json_response(await command_response(form, env))

        payload = json.loads(body_text or "{}")
        await record_activity(env, "event", payload)
        return await handle_event_payload(payload, env)

    try:
        return await env.ASSETS.fetch(request)
    except Exception:
        index_file = ROOT_DIR / "public" / "index.html"
        if path == "/" and index_file.exists():
            return html_response(index_file.read_text())
        return build_response("Not Found", status=404)


class Default(WorkerEntrypoint):
    async def fetch(self, request: Any) -> Any:
        return await handle_request(request, self.env)
