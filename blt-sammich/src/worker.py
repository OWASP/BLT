import base64
import csv
import hashlib
import hmac
import io
import json
import time
import traceback
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
SCHEMA_READY = False
SLACK_COMMAND_DEFINITIONS = [
    ("/contrib", "Guide to contributing to OWASP projects"),
    ("/stats", "Show OWASP project and Sammich connection stats"),
    ("/discover [search term]", "Discover OWASP projects to work on"),
    ("/gsoc25 [technology, mentor, or project]", "Find OWASP GSoC project details"),
    ("/blt", "Show Sammich command help"),
    ("/installed_apps", "List installed apps and logged activity"),
]
SUPPORTED_SLACK_COMMANDS = set(
    command.split(" ", 1)[0] for command, _ in SLACK_COMMAND_DEFINITIONS
)
ADMIN_TABLE_SCHEMAS = {
    "workspace_installations": {
        "pk": "team_id",
        "auto_pk": False,
        "columns": [
            ("team_id", "TEXT"),
            ("installer_user_id", "TEXT"),
            ("installed_at", "TEXT"),
        ],
    },
    "connected_workspaces": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("team_id", "TEXT"),
            ("team_name", "TEXT"),
            ("icon_url", "TEXT"),
            ("installer_user_id", "TEXT"),
            ("bot_user_id", "TEXT"),
            ("invite_link", "TEXT"),
            ("github_org_url", "TEXT"),
            ("repo_count", "INTEGER"),
            ("channel_count", "INTEGER"),
            ("member_count", "INTEGER"),
            ("status", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "slack_apps": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("app_id", "TEXT"),
            ("app_name", "TEXT"),
            ("app_icon_url", "TEXT"),
            ("client_id", "TEXT"),
            ("client_secret", "TEXT"),
            ("signing_secret", "TEXT"),
            ("app_token", "TEXT"),
            ("manifest_yaml", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "managed_servers": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("name", "TEXT"),
            ("url", "TEXT"),
            ("status", "TEXT"),
            ("description", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "workspaces": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("team_id", "TEXT"),
            ("team_name", "TEXT"),
            ("icon_url", "TEXT"),
            ("app_id", "TEXT"),
            ("app_name", "TEXT"),
            ("app_icon_url", "TEXT"),
            ("manifest_yaml", "TEXT"),
            ("installer_slack_user_id", "TEXT"),
            ("installer_name", "TEXT"),
            ("channel_count", "INTEGER"),
            ("member_count", "INTEGER"),
            ("invite_link", "TEXT"),
            ("access_token", "TEXT"),
            ("app_token", "TEXT"),
            ("bot_token", "TEXT"),
            ("bot_user_id", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "channels": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("workspace_id", "INTEGER"),
            ("channel_id", "TEXT"),
            ("channel_name", "TEXT"),
            ("member_count", "INTEGER"),
            ("topic", "TEXT"),
            ("purpose", "TEXT"),
            ("is_private", "INTEGER"),
            ("is_channel", "INTEGER"),
            ("is_group", "INTEGER"),
            ("is_im", "INTEGER"),
            ("is_mpim", "INTEGER"),
            ("is_archived", "INTEGER"),
            ("is_general", "INTEGER"),
            ("is_shared", "INTEGER"),
            ("is_ext_shared", "INTEGER"),
            ("is_org_shared", "INTEGER"),
            ("is_pending_ext_shared", "INTEGER"),
            ("is_member", "INTEGER"),
            ("creator", "TEXT"),
            ("locale", "TEXT"),
            ("metadata_json", "TEXT"),
            ("send_join_message", "INTEGER"),
            ("join_message_id", "INTEGER"),
            ("join_delivery_mode", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "repositories": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("workspace_id", "INTEGER"),
            ("repo_url", "TEXT"),
            ("repo_name", "TEXT"),
            ("description", "TEXT"),
            ("language", "TEXT"),
            ("stars", "INTEGER"),
            ("source_type", "TEXT"),
            ("metadata_json", "TEXT"),
            ("created_at", "TEXT"),
        ],
    },
    "github_organizations": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("workspace_id", "INTEGER"),
            ("org_login", "TEXT"),
            ("org_type", "TEXT"),
            ("metadata_json", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "events": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("workspace_id", "INTEGER"),
            ("event_type", "TEXT"),
            ("user_slack_id", "TEXT"),
            ("channel_name", "TEXT"),
            ("channel_id", "TEXT"),
            ("slack_team_id", "TEXT"),
            ("api_app_id", "TEXT"),
            ("command", "TEXT"),
            ("command_text", "TEXT"),
            ("is_enterprise_install", "TEXT"),
            ("response_url", "TEXT"),
            ("team_domain", "TEXT"),
            ("trigger_id", "TEXT"),
            ("user_name", "TEXT"),
            ("slack_token", "TEXT"),
            ("request_data", "TEXT"),
            ("verified", "INTEGER"),
            ("status", "TEXT"),
            ("webhook_body_type", "TEXT"),
            ("webhook_event_id", "TEXT"),
            ("webhook_event_time", "TEXT"),
            ("webhook_event_subtype", "TEXT"),
            ("webhook_retry_num", "TEXT"),
            ("webhook_retry_reason", "TEXT"),
            ("slack_response_data", "TEXT"),
            ("created_at", "TEXT"),
        ],
    },
    "join_messages": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("workspace_id", "INTEGER"),
            ("name", "TEXT"),
            ("message_text", "TEXT"),
            ("is_active", "INTEGER"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "users": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("slack_user_id", "TEXT"),
            ("team_id", "TEXT"),
            ("name", "TEXT"),
            ("real_name", "TEXT"),
            ("email", "TEXT"),
            ("access_token", "TEXT"),
            ("avatar_url", "TEXT"),
            ("deleted", "INTEGER"),
            ("is_bot", "INTEGER"),
            ("is_admin", "INTEGER"),
            ("is_owner", "INTEGER"),
            ("is_primary_owner", "INTEGER"),
            ("is_restricted", "INTEGER"),
            ("is_ultra_restricted", "INTEGER"),
            ("is_app_user", "INTEGER"),
            ("tz", "TEXT"),
            ("tz_label", "TEXT"),
            ("tz_offset", "INTEGER"),
            ("profile_json", "TEXT"),
            ("metadata_json", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },
    "sessions": {
        "pk": "id",
        "auto_pk": False,
        "columns": [
            ("id", "TEXT"),
            ("user_id", "INTEGER"),
            ("created_at", "TEXT"),
            ("expires_at", "TEXT"),
        ],
    },
    "user_workspaces": {
        "pk": "id",
        "auto_pk": True,
        "columns": [
            ("id", "INTEGER"),
            ("user_id", "INTEGER"),
            ("workspace_id", "INTEGER"),
            ("role", "TEXT"),
            ("created_at", "TEXT"),
        ],
    },
}
ADMIN_CASCADE_RELATIONSHIPS = [
    {
        "parent_table": "workspaces",
        "parent_column": "id",
        "child_table": "channels",
        "child_column": "workspace_id",
        "action": "delete",
    },
    {
        "parent_table": "workspaces",
        "parent_column": "id",
        "child_table": "repositories",
        "child_column": "workspace_id",
        "action": "delete",
    },
    {
        "parent_table": "workspaces",
        "parent_column": "id",
        "child_table": "github_organizations",
        "child_column": "workspace_id",
        "action": "delete",
    },
    {
        "parent_table": "workspaces",
        "parent_column": "id",
        "child_table": "events",
        "child_column": "workspace_id",
        "action": "delete",
    },
    {
        "parent_table": "workspaces",
        "parent_column": "id",
        "child_table": "join_messages",
        "child_column": "workspace_id",
        "action": "delete",
    },
    {
        "parent_table": "workspaces",
        "parent_column": "id",
        "child_table": "user_workspaces",
        "child_column": "workspace_id",
        "action": "delete",
    },
    {
        "parent_table": "workspaces",
        "parent_column": "team_id",
        "child_table": "connected_workspaces",
        "child_column": "team_id",
        "action": "delete",
    },
    {
        "parent_table": "workspaces",
        "parent_column": "team_id",
        "child_table": "workspace_installations",
        "child_column": "team_id",
        "action": "delete",
    },
    {
        "parent_table": "users",
        "parent_column": "id",
        "child_table": "sessions",
        "child_column": "user_id",
        "action": "delete",
    },
    {
        "parent_table": "users",
        "parent_column": "id",
        "child_table": "user_workspaces",
        "child_column": "user_id",
        "action": "delete",
    },
    {
        "parent_table": "join_messages",
        "parent_column": "id",
        "child_table": "channels",
        "child_column": "join_message_id",
        "action": "null",
    },
]


def _to_js_options(value: Dict[str, Any]) -> Any:
    if _to_js is None or Object is None:
        return value
    return _to_js(value, dict_converter=Object.fromEntries)


def to_python(value: Any) -> Any:
    try:
        return value.to_py()
    except Exception:
        return value


def normalize_d1_param(value: Any) -> Any:
    value = to_python(value)
    if value is None:
        return ""
    if str(type(value)).endswith(".JsProxy'>") and str(value) == "undefined":
        return ""
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


def redirect_response(location: str) -> Any:
    return build_response("", status=303, headers={"location": location})


def flatten_form_values(values: Dict[str, List[str]]) -> Dict[str, str]:
    return dict((key, item[0] if item else "") for key, item in values.items())


def parse_form_encoded(body: str) -> Dict[str, str]:
    return flatten_form_values(parse_qs(body, keep_blank_values=True))


def html_escape(text: Any) -> str:
    return (
        str(text if text is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def admin_path(env: Any) -> str:
    path = (env_value(env, "ADMIN_URL") or "").strip()
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/")


def admin_credentials(env: Any) -> Tuple[str, str]:
    return env_value(env, "ADMIN_USERNAME", "") or "", env_value(
        env, "ADMIN_PASSWORD", ""
    ) or ""


def request_basic_auth_credentials(request: Any) -> Tuple[str, str]:
    header = request.headers.get("authorization", "") or ""
    if not header.lower().startswith("basic "):
        return "", ""
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
    except Exception:
        return "", ""
    username, separator, password = decoded.partition(":")
    if not separator:
        return "", ""
    return username, password


def is_admin_request(request: Any, env: Any) -> bool:
    username, password = request_basic_auth_credentials(request)
    expected_username, expected_password = admin_credentials(env)
    if not expected_username or not expected_password:
        return False
    return hmac.compare_digest(username, expected_username) and hmac.compare_digest(
        password, expected_password
    )


def basic_auth_response() -> Any:
    return build_response(
        "Authentication required.",
        status=401,
        headers={"WWW-Authenticate": 'Basic realm="BLT-Sammich Admin"'},
    )


def log_exception_one_line(
    error: Exception,
    context: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    stack = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    ).replace("\n", "\\n")
    payload = {
        "level": "error",
        "context": context,
        "error_type": type(error).__name__,
        "error": str(error),
        "stack": stack,
    }
    if extra:
        payload["extra"] = extra
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def log_json_event(event: str, payload: Dict[str, Any]) -> None:
    return None


def payload_team_id(payload: Dict[str, Any]) -> str:
    event = payload.get("event") or {}
    authorizations = payload.get("authorizations") or []
    if isinstance(authorizations, list) and authorizations:
        auth_team_id = (authorizations[0] or {}).get("team_id")
    else:
        auth_team_id = ""
    return str(
        payload.get("team_id")
        or (payload.get("team") or {}).get("id")
        or event.get("team")
        or auth_team_id
        or ""
    )


def payload_user_id(payload: Dict[str, Any]) -> str:
    event = payload.get("event") or {}
    user_profile = event.get("user_profile") or {}
    payload_user = payload.get("user")
    event_user = event.get("user")
    if isinstance(payload_user, dict):
        payload_user = payload_user.get("id") or payload_user.get("user_id")
    if isinstance(event_user, dict):
        event_user = event_user.get("id") or event_user.get("user_id")
    return str(
        payload.get("user_id")
        or payload_user
        or event_user
        or event.get("bot_id")
        or user_profile.get("id")
        or ""
    )


def payload_channel_id(payload: Dict[str, Any]) -> str:
    event = payload.get("event") or {}
    payload_channel = payload.get("channel")
    event_channel = event.get("channel")
    item = event.get("item") or {}
    if isinstance(payload_channel, dict):
        payload_channel = payload_channel.get("id")
    if isinstance(event_channel, dict):
        event_channel = event_channel.get("id")
    return str(
        payload.get("channel_id")
        or payload_channel
        or event_channel
        or item.get("channel")
        or ""
    )


def payload_channel_name(payload: Dict[str, Any]) -> str:
    event = payload.get("event") or {}
    payload_channel = payload.get("channel")
    if isinstance(payload_channel, dict):
        return str(payload_channel.get("name") or "")
    return str(payload.get("channel_name") or event.get("channel_name") or "")


def payload_app_id(payload: Dict[str, Any]) -> str:
    return str(payload.get("api_app_id") or payload.get("app_id") or "")


def bool_int(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.lower() in ("1", "true", "yes", "on") else 0
    return 1 if value else 0


def compact_json(value: Any) -> str:
    if not value:
        return ""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(value)


def payload_user_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    user_obj: Dict[str, Any] = {}
    raw_user = event.get("user") or payload.get("user")
    if isinstance(raw_user, dict):
        user_obj = raw_user
    elif isinstance(event.get("user_profile"), dict):
        user_obj = {"id": event.get("user"), "profile": event.get("user_profile")}
    elif isinstance(payload.get("authed_user"), dict):
        user_obj = payload.get("authed_user") or {}
    profile = user_obj.get("profile") if isinstance(user_obj.get("profile"), dict) else {}
    user_id = str(
        user_obj.get("id")
        or user_obj.get("user_id")
        or payload_user_id(payload)
        or ""
    )
    name = str(
        user_obj.get("name")
        or profile.get("display_name")
        or profile.get("real_name")
        or payload.get("user_name")
        or user_id
        or ""
    )
    real_name = str(user_obj.get("real_name") or profile.get("real_name") or "")
    avatar_url = str(
        profile.get("image_512")
        or profile.get("image_192")
        or profile.get("image_72")
        or user_obj.get("avatar_url")
        or ""
    )
    return {
        "slack_user_id": user_id,
        "team_id": str(user_obj.get("team_id") or payload_team_id(payload) or "unknown"),
        "name": name,
        "real_name": real_name,
        "email": str(user_obj.get("email") or profile.get("email") or ""),
        "avatar_url": avatar_url,
        "deleted": bool_int(user_obj.get("deleted")),
        "is_bot": bool_int(user_obj.get("is_bot")),
        "is_admin": bool_int(user_obj.get("is_admin")),
        "is_owner": bool_int(user_obj.get("is_owner")),
        "is_primary_owner": bool_int(user_obj.get("is_primary_owner")),
        "is_restricted": bool_int(user_obj.get("is_restricted")),
        "is_ultra_restricted": bool_int(user_obj.get("is_ultra_restricted")),
        "is_app_user": bool_int(user_obj.get("is_app_user")),
        "tz": str(user_obj.get("tz") or ""),
        "tz_label": str(user_obj.get("tz_label") or ""),
        "tz_offset": int(user_obj.get("tz_offset") or 0),
        "profile_json": compact_json(profile),
        "metadata_json": compact_json(user_obj),
    }


def payload_channel_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    channel_obj: Dict[str, Any] = {}
    raw_channel = payload.get("channel")
    event_channel = event.get("channel")
    if isinstance(raw_channel, dict):
        channel_obj = raw_channel
    elif isinstance(event_channel, dict):
        channel_obj = event_channel
    elif isinstance(event.get("item"), dict) and isinstance(event["item"].get("channel"), dict):
        channel_obj = event["item"]["channel"]
    topic = channel_obj.get("topic") if isinstance(channel_obj.get("topic"), dict) else {}
    purpose = (
        channel_obj.get("purpose") if isinstance(channel_obj.get("purpose"), dict) else {}
    )
    channel_type = str(event.get("channel_type") or channel_obj.get("channel_type") or "")
    return {
        "channel_id": str(channel_obj.get("id") or payload_channel_id(payload) or ""),
        "channel_name": str(
            channel_obj.get("name")
            or channel_obj.get("name_normalized")
            or payload_channel_name(payload)
            or payload_channel_id(payload)
            or ""
        ),
        "member_count": int(
            channel_obj.get("num_members") or channel_obj.get("member_count") or 0
        ),
        "topic": str(topic.get("value") or channel_obj.get("topic") or ""),
        "purpose": str(purpose.get("value") or channel_obj.get("purpose") or ""),
        "is_private": bool_int(channel_obj.get("is_private") or channel_type == "im"),
        "is_channel": bool_int(channel_obj.get("is_channel")),
        "is_group": bool_int(channel_obj.get("is_group")),
        "is_im": bool_int(channel_obj.get("is_im") or channel_type == "im"),
        "is_mpim": bool_int(channel_obj.get("is_mpim")),
        "is_archived": bool_int(channel_obj.get("is_archived")),
        "is_general": bool_int(channel_obj.get("is_general")),
        "is_shared": bool_int(channel_obj.get("is_shared")),
        "is_ext_shared": bool_int(channel_obj.get("is_ext_shared")),
        "is_org_shared": bool_int(channel_obj.get("is_org_shared")),
        "is_pending_ext_shared": bool_int(channel_obj.get("is_pending_ext_shared")),
        "is_member": bool_int(channel_obj.get("is_member")),
        "creator": str(channel_obj.get("creator") or ""),
        "locale": str(channel_obj.get("locale") or ""),
        "metadata_json": compact_json(channel_obj),
    }


def event_slash_command_fields(payload: Dict[str, Any]) -> Dict[str, str]:
    return {
        "api_app_id": str(payload.get("api_app_id") or ""),
        "command": str(payload.get("command") or ""),
        "command_text": str(payload.get("text") or ""),
        "is_enterprise_install": str(payload.get("is_enterprise_install") or ""),
        "response_url": str(payload.get("response_url") or ""),
        "team_domain": str(payload.get("team_domain") or ""),
        "trigger_id": str(payload.get("trigger_id") or ""),
        "user_name": str(payload.get("user_name") or ""),
        "slack_token": str(payload.get("token") or ""),
    }


def model_event_type_for_activity(activity_kind: str, payload: Dict[str, Any]) -> str:
    event = payload.get("event") or {}
    raw_type = (
        "Command"
        if activity_kind == "slash_command"
        else "Interaction"
        if activity_kind == "interaction"
        else event.get("type") or payload.get("type") or activity_kind
    )
    if raw_type == "team_join":
        return "Team_Join"
    if raw_type == "app_mention":
        return "App_Mention"
    if raw_type == "message":
        return "Message"
    if raw_type == "http_request":
        return "Http_Request"
    return str(raw_type or activity_kind)


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


def available_commands_text(include_descriptions: bool = False) -> str:
    lines = []
    for command, description in SLACK_COMMAND_DEFINITIONS:
        if include_descriptions:
            lines.append("• `{0}` - {1}".format(command, description))
        else:
            lines.append("• {0}".format(command))
    return "\n".join(lines)


def app_home_view() -> Dict[str, Any]:
    return {
        "type": "home",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "BLT Sammich", "emoji": True},
            },
            make_section_block(
                "Use these commands from any Slack channel where Sammich is available."
            ),
            make_section_block(
                "*Available commands*\n{0}".format(available_commands_text(True))
            ),
        ],
    }


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
        statement = statement.bind(*[normalize_d1_param(param) for param in params])
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
    SCHEMA_READY = True


async def record_activity(
    env: Any, activity_kind: str, payload: Dict[str, Any]
) -> None:
    if activity_kind == "http_request" or payload.get("type") == "http_request":
        return

    try:
        getattr(env, "DB")
    except Exception:
        return

    await ensure_schema(env)
    received_at = datetime.now(timezone.utc).isoformat()
    slack_type = payload.get("type") or payload.get("event", {}).get("type")
    command_name = payload.get("command")
    team_id = payload_team_id(payload)
    user_id = payload_user_id(payload)
    channel_id = payload_channel_id(payload)
    channel_name = payload_channel_name(payload)
    app_id = payload_app_id(payload)
    user_metadata = payload_user_metadata(payload)
    channel_metadata = payload_channel_metadata(payload)
    payload_json = json.dumps(payload, sort_keys=True)
    workspace_id = None
    command_fields = event_slash_command_fields(payload)
    if app_id:
        try:
            await db_upsert_slack_app(env, app_id=app_id)
        except Exception as error:
            log_exception_one_line(
                error,
                "record_activity_slack_app_upsert_failed",
                {"app_id": app_id, "team_id": team_id},
            )
    if team_id:
        try:
            team = payload.get("team") if isinstance(payload.get("team"), dict) else {}
            workspace_id = await db_upsert_workspace(
                env,
                team_id=team_id,
                team_name=str(
                    team.get("name") or payload.get("team_name") or team_id
                ),
                app_id=app_id,
            )
            workspace = (
                await db_get_workspace_by_team_and_app(env, team_id, app_id)
                if app_id
                else await db_get_workspace_by_team(env, team_id)
            )
            workspace_id = workspace.get("id") if workspace else None
        except Exception as error:
            log_exception_one_line(
                error,
                "record_activity_workspace_lookup_failed",
                {"team_id": team_id},
            )
    if user_id:
        try:
            await db_get_or_create_user(
                env,
                user_id,
                user_metadata.get("team_id") or team_id or "unknown",
                user_metadata.get("name") or user_id,
                user_metadata.get("email") or "",
                "",
                user_metadata.get("avatar_url") or "",
                real_name=user_metadata.get("real_name") or "",
                deleted=int(user_metadata.get("deleted") or 0),
                is_bot=int(user_metadata.get("is_bot") or 0),
                is_admin=int(user_metadata.get("is_admin") or 0),
                is_owner=int(user_metadata.get("is_owner") or 0),
                is_primary_owner=int(user_metadata.get("is_primary_owner") or 0),
                is_restricted=int(user_metadata.get("is_restricted") or 0),
                is_ultra_restricted=int(user_metadata.get("is_ultra_restricted") or 0),
                is_app_user=int(user_metadata.get("is_app_user") or 0),
                tz=user_metadata.get("tz") or "",
                tz_label=user_metadata.get("tz_label") or "",
                tz_offset=int(user_metadata.get("tz_offset") or 0),
                profile_json=user_metadata.get("profile_json") or "",
                metadata_json=user_metadata.get("metadata_json") or "",
            )
        except Exception as error:
            log_exception_one_line(
                error,
                "record_activity_user_upsert_failed",
                {"team_id": team_id, "user_id": user_id},
            )
    if workspace_id and channel_id:
        try:
            await db_upsert_channel(
                env,
                workspace_id,
                channel_id,
                channel_metadata.get("channel_name") or channel_name or channel_id,
                member_count=int(channel_metadata.get("member_count") or 0),
                topic=channel_metadata.get("topic") or "",
                purpose=channel_metadata.get("purpose") or "",
                is_private=(
                    1
                    if int(channel_metadata.get("is_private") or 0)
                    else 0
                ),
                is_channel=int(channel_metadata.get("is_channel") or 0),
                is_group=int(channel_metadata.get("is_group") or 0),
                is_im=int(channel_metadata.get("is_im") or 0),
                is_mpim=int(channel_metadata.get("is_mpim") or 0),
                is_archived=int(channel_metadata.get("is_archived") or 0),
                is_general=int(channel_metadata.get("is_general") or 0),
                is_shared=int(channel_metadata.get("is_shared") or 0),
                is_ext_shared=int(channel_metadata.get("is_ext_shared") or 0),
                is_org_shared=int(channel_metadata.get("is_org_shared") or 0),
                is_pending_ext_shared=int(channel_metadata.get("is_pending_ext_shared") or 0),
                is_member=int(channel_metadata.get("is_member") or 0),
                creator=channel_metadata.get("creator") or "",
                locale=channel_metadata.get("locale") or "",
                metadata_json=channel_metadata.get("metadata_json") or "",
            )
        except Exception as error:
            log_exception_one_line(
                error,
                "record_activity_channel_upsert_failed",
                {"workspace_id": workspace_id, "channel_id": channel_id},
            )
    event_payload = payload.get("event") or {}
    model_event_type = model_event_type_for_activity(activity_kind, payload)
    try:
        await db_log_event(
            env,
            workspace_id,
            model_event_type,
            user_slack_id=user_id or "",
            channel_name=channel_name,
            channel_id=channel_id or "",
            slack_team_id=team_id,
            request_data=payload_json,
            status="success",
            webhook_body_type=str(payload.get("type") or ""),
            webhook_event_id=str(payload.get("event_id") or ""),
            webhook_event_time=str(payload.get("event_time") or ""),
            webhook_event_subtype=str(event_payload.get("subtype") or ""),
            webhook_retry_num=str(payload.get("retry_num") or ""),
            webhook_retry_reason=str(payload.get("retry_reason") or ""),
            api_app_id=command_fields["api_app_id"],
            command=command_fields["command"],
            command_text=command_fields["command_text"],
            is_enterprise_install=command_fields["is_enterprise_install"],
            response_url=command_fields["response_url"],
            team_domain=command_fields["team_domain"],
            trigger_id=command_fields["trigger_id"],
            user_name=command_fields["user_name"],
            slack_token=command_fields["slack_token"],
        )
        log_json_event(
            "model_event_logged",
            {
                "activity_kind": activity_kind,
                "event_type": model_event_type,
                "team_id": team_id,
                "workspace_id": workspace_id,
                "channel_id": channel_id,
                "user_id": user_id,
            },
        )
    except Exception as error:
        log_exception_one_line(error, "record_model_activity_failed")


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def result_rows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = result.get("results") or []
    return [row for row in rows if isinstance(row, dict)]


def result_first(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = result_rows(result)
    return rows[0] if rows else None


async def db_get_workspace_by_id(env: Any, workspace_id: Any) -> Optional[Dict[str, Any]]:
    await ensure_schema(env)
    return result_first(
        await d1_run(env, "SELECT * FROM workspaces WHERE id = ? LIMIT 1", [workspace_id])
    )


async def db_get_workspace_by_team(env: Any, team_id: str) -> Optional[Dict[str, Any]]:
    await ensure_schema(env)
    return result_first(
        await d1_run(
            env,
            "SELECT * FROM workspaces WHERE team_id = ? ORDER BY updated_at DESC LIMIT 1",
            [team_id],
        )
    )


async def db_get_workspace_by_team_and_app(
    env: Any, team_id: str, app_id: str
) -> Optional[Dict[str, Any]]:
    await ensure_schema(env)
    return result_first(
        await d1_run(
            env,
            "SELECT * FROM workspaces WHERE team_id = ? AND app_id = ? LIMIT 1",
            [team_id, app_id or ""],
        )
    )


async def db_get_workspace_by_channel_id(
    env: Any, channel_id: str
) -> Optional[Dict[str, Any]]:
    await ensure_schema(env)
    return result_first(
        await d1_run(
            env,
            (
                "SELECT w.* FROM channels c "
                "JOIN workspaces w ON w.id = c.workspace_id "
                "WHERE c.channel_id = ? ORDER BY w.updated_at DESC LIMIT 1"
            ),
            [channel_id],
        )
    )


async def db_upsert_slack_app(
    env: Any,
    app_id: str,
    app_name: str = "",
    app_icon_url: str = "",
    client_id: str = "",
    client_secret: str = "",
    signing_secret: str = "",
    app_token: str = "",
    manifest_yaml: str = "",
) -> Optional[int]:
    if not app_id:
        return None
    await ensure_schema(env)
    now = utc_now()
    await d1_run(
        env,
        (
            "INSERT INTO slack_apps ("
            "app_id, app_name, app_icon_url, client_id, client_secret, signing_secret, app_token, manifest_yaml, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(app_id) DO UPDATE SET "
            "app_name = CASE WHEN excluded.app_name != '' THEN excluded.app_name ELSE slack_apps.app_name END, "
            "app_icon_url = CASE WHEN excluded.app_icon_url != '' THEN excluded.app_icon_url ELSE slack_apps.app_icon_url END, "
            "client_id = CASE WHEN excluded.client_id != '' THEN excluded.client_id ELSE slack_apps.client_id END, "
            "client_secret = CASE WHEN excluded.client_secret != '' THEN excluded.client_secret ELSE slack_apps.client_secret END, "
            "signing_secret = CASE WHEN excluded.signing_secret != '' THEN excluded.signing_secret ELSE slack_apps.signing_secret END, "
            "app_token = CASE WHEN excluded.app_token != '' THEN excluded.app_token ELSE slack_apps.app_token END, "
            "manifest_yaml = CASE WHEN excluded.manifest_yaml != '' THEN excluded.manifest_yaml ELSE slack_apps.manifest_yaml END, "
            "updated_at = excluded.updated_at"
        ),
        [
            app_id,
            app_name or "",
            app_icon_url or "",
            client_id or "",
            client_secret or "",
            signing_secret or "",
            app_token or "",
            manifest_yaml or "",
            now,
            now,
        ],
    )
    row = result_first(
        await d1_run(env, "SELECT id FROM slack_apps WHERE app_id = ? LIMIT 1", [app_id])
    )
    return int(row["id"]) if row and row.get("id") is not None else None


async def db_get_slack_app_by_app_id(
    env: Any, app_id: str
) -> Optional[Dict[str, Any]]:
    if not app_id:
        return None
    await ensure_schema(env)
    return result_first(
        await d1_run(env, "SELECT * FROM slack_apps WHERE app_id = ? LIMIT 1", [app_id])
    )


async def db_get_workspace_bot_token(
    env: Any, team_id: str = "", channel_id: str = ""
) -> str:
    try:
        getattr(env, "DB")
    except Exception:
        return ""
    await ensure_schema(env)
    row = None
    if team_id:
        row = await db_get_workspace_by_team(env, team_id)
    if not row and channel_id:
        row = await db_get_workspace_by_channel_id(env, channel_id)
    return str(
        (row or {}).get("bot_token") or (row or {}).get("access_token") or ""
    )


async def db_get_workspace_bot_user_id(
    env: Any, team_id: str = "", channel_id: str = ""
) -> str:
    try:
        getattr(env, "DB")
    except Exception:
        return ""
    await ensure_schema(env)
    row = None
    if team_id:
        row = await db_get_workspace_by_team(env, team_id)
    if not row and channel_id:
        row = await db_get_workspace_by_channel_id(env, channel_id)
    return str((row or {}).get("bot_user_id") or "")


async def db_get_slack_app_signing_secret(
    env: Any, app_id: str = ""
) -> str:
    try:
        getattr(env, "DB")
    except Exception:
        return ""
    await ensure_schema(env)
    row = await db_get_slack_app_by_app_id(env, app_id)
    return str((row or {}).get("signing_secret") or "")


async def db_upsert_workspace(
    env: Any,
    team_id: str,
    team_name: str,
    access_token: str = "",
    app_token: str = "",
    bot_token: str = "",
    bot_user_id: str = "",
    app_id: str = "",
    app_name: str = "",
    app_icon_url: str = "",
    icon_url: str = "",
    invite_link: str = "",
    manifest_yaml: str = "",
    installer_slack_user_id: str = "",
    installer_name: str = "",
) -> Optional[int]:
    if not team_id:
        return None
    await ensure_schema(env)
    now = utc_now()
    await d1_run(
        env,
        (
            "INSERT INTO workspaces ("
            "team_id, team_name, access_token, app_token, bot_token, bot_user_id, app_id, app_name, app_icon_url, "
            "icon_url, invite_link, manifest_yaml, installer_slack_user_id, installer_name, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(team_id, app_id) DO UPDATE SET "
            "team_name = excluded.team_name, "
            "access_token = CASE WHEN excluded.access_token != '' THEN excluded.access_token ELSE workspaces.access_token END, "
            "app_token = CASE WHEN excluded.app_token != '' THEN excluded.app_token ELSE workspaces.app_token END, "
            "bot_token = CASE WHEN excluded.bot_token != '' THEN excluded.bot_token ELSE workspaces.bot_token END, "
            "bot_user_id = CASE WHEN excluded.bot_user_id != '' THEN excluded.bot_user_id ELSE workspaces.bot_user_id END, "
            "app_name = CASE WHEN excluded.app_name != '' THEN excluded.app_name ELSE workspaces.app_name END, "
            "app_icon_url = CASE WHEN excluded.app_icon_url != '' THEN excluded.app_icon_url ELSE workspaces.app_icon_url END, "
            "icon_url = CASE WHEN excluded.icon_url != '' THEN excluded.icon_url ELSE workspaces.icon_url END, "
            "invite_link = CASE WHEN excluded.invite_link != '' THEN excluded.invite_link ELSE workspaces.invite_link END, "
            "manifest_yaml = CASE WHEN excluded.manifest_yaml != '' THEN excluded.manifest_yaml ELSE workspaces.manifest_yaml END, "
            "installer_slack_user_id = CASE WHEN excluded.installer_slack_user_id != '' THEN excluded.installer_slack_user_id ELSE workspaces.installer_slack_user_id END, "
            "installer_name = CASE WHEN excluded.installer_name != '' THEN excluded.installer_name ELSE workspaces.installer_name END, "
            "updated_at = excluded.updated_at"
        ),
        [
            team_id,
            team_name or team_id,
            access_token or "",
            app_token or "",
            bot_token or access_token or "",
            bot_user_id or "",
            app_id or "",
            app_name or "",
            app_icon_url or "",
            icon_url or app_icon_url or "",
            invite_link or "",
            manifest_yaml or "",
            installer_slack_user_id or "",
            installer_name or "",
            now,
            now,
        ],
    )
    row = await db_get_workspace_by_team_and_app(env, team_id, app_id or "")
    return int(row["id"]) if row and row.get("id") is not None else None


async def db_update_workspace_icon(env: Any, workspace_id: Any, icon_url: str) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        "UPDATE workspaces SET icon_url = ?, updated_at = ? WHERE id = ?",
        [icon_url or "", utc_now(), workspace_id],
    )
    return True


async def db_update_workspace_manifest(
    env: Any, workspace_id: Any, manifest_yaml: str
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        "UPDATE workspaces SET manifest_yaml = ?, updated_at = ? WHERE id = ?",
        [str(manifest_yaml or ""), utc_now(), workspace_id],
    )
    return True


async def db_update_workspace_app_metadata(
    env: Any, workspace_id: Any, app_name: str = "", app_icon_url: str = "", app_id: str = ""
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        (
            "UPDATE workspaces SET app_name = ?, app_icon_url = ?, app_id = ?, "
            "updated_at = ? WHERE id = ?"
        ),
        [app_name or "", app_icon_url or "", app_id or "", utc_now(), workspace_id],
    )
    return True


async def db_update_workspace_installer(
    env: Any, workspace_id: Any, installer_slack_user_id: str = "", installer_name: str = ""
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        (
            "UPDATE workspaces SET installer_slack_user_id = ?, installer_name = ?, "
            "updated_at = ? WHERE id = ?"
        ),
        [
            installer_slack_user_id or "",
            installer_name or "",
            utc_now(),
            workspace_id,
        ],
    )
    return True


async def db_update_workspace_channel_member_counts(
    env: Any, workspace_id: Any, channel_count: int = 0, member_count: int = 0
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        "UPDATE workspaces SET channel_count = ?, member_count = ?, updated_at = ? WHERE id = ?",
        [int(channel_count or 0), int(member_count or 0), utc_now(), workspace_id],
    )
    return True


async def db_update_workspace_invite_link(
    env: Any, workspace_id: Any, invite_link: str = ""
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        "UPDATE workspaces SET invite_link = ?, updated_at = ? WHERE id = ?",
        [str(invite_link or "").strip(), utc_now(), workspace_id],
    )
    return True


async def db_get_workspace_invite_link(env: Any, workspace_id: Any) -> str:
    await ensure_schema(env)
    row = result_first(
        await d1_run(
            env,
            "SELECT invite_link FROM workspaces WHERE id = ? LIMIT 1",
            [workspace_id],
        )
    )
    return str((row or {}).get("invite_link") or "").strip()


async def db_get_workspace_admin_identity(
    env: Any, workspace: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    workspace = workspace or {}
    installer_id = str(workspace.get("installer_slack_user_id") or "").strip()
    installer_name = str(workspace.get("installer_name") or "").strip()
    if installer_id:
        return {"slack_user_id": installer_id, "name": installer_name or installer_id}

    workspace_id = workspace.get("id")
    if not workspace_id:
        return None
    installers = await db_get_workspace_installers(env, workspace_id)
    for installer in installers:
        slack_user_id = str(installer.get("slack_user_id") or "").strip()
        if slack_user_id:
            name = str(installer.get("name") or slack_user_id).strip()
            await db_update_workspace_installer(env, workspace_id, slack_user_id, name)
            return {"slack_user_id": slack_user_id, "name": name}
    return None


async def db_get_or_create_user(
    env: Any,
    slack_user_id: str,
    team_id: str,
    name: str,
    email: str,
    access_token: str,
    avatar_url: str = "",
    real_name: str = "",
    deleted: int = 0,
    is_bot: int = 0,
    is_admin: int = 0,
    is_owner: int = 0,
    is_primary_owner: int = 0,
    is_restricted: int = 0,
    is_ultra_restricted: int = 0,
    is_app_user: int = 0,
    tz: str = "",
    tz_label: str = "",
    tz_offset: int = 0,
    profile_json: str = "",
    metadata_json: str = "",
) -> Optional[Dict[str, Any]]:
    if not slack_user_id:
        return None
    await ensure_schema(env)
    now = utc_now()
    existing = result_first(
        await d1_run(
            env,
            "SELECT * FROM users WHERE slack_user_id = ? LIMIT 1",
            [slack_user_id],
        )
    )
    if existing:
        effective_name = name or existing.get("name") or slack_user_id
        await d1_run(
            env,
            (
                "UPDATE users SET name = ?, real_name = ?, email = ?, access_token = ?, avatar_url = ?, "
                "team_id = ?, deleted = ?, is_bot = ?, is_admin = ?, is_owner = ?, is_primary_owner = ?, "
                "is_restricted = ?, is_ultra_restricted = ?, is_app_user = ?, tz = ?, tz_label = ?, "
                "tz_offset = ?, profile_json = ?, metadata_json = ?, updated_at = ? WHERE slack_user_id = ?"
            ),
            [
                effective_name,
                real_name or existing.get("real_name") or "",
                email or "",
                access_token or "",
                avatar_url or "",
                team_id or "unknown",
                int(deleted or 0),
                int(is_bot or 0),
                int(is_admin or 0),
                int(is_owner or 0),
                int(is_primary_owner or 0),
                int(is_restricted or 0),
                int(is_ultra_restricted or 0),
                int(is_app_user or 0),
                tz or "",
                tz_label or "",
                int(tz_offset or 0),
                profile_json or existing.get("profile_json") or "",
                metadata_json or existing.get("metadata_json") or "",
                now,
                slack_user_id,
            ],
        )
    else:
        await d1_run(
            env,
            (
                "INSERT INTO users (slack_user_id, team_id, name, real_name, email, access_token, avatar_url, "
                "deleted, is_bot, is_admin, is_owner, is_primary_owner, is_restricted, is_ultra_restricted, "
                "is_app_user, tz, tz_label, tz_offset, profile_json, metadata_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            [
                slack_user_id,
                team_id or "unknown",
                name or slack_user_id,
                real_name or "",
                email or "",
                access_token or "",
                avatar_url or "",
                int(deleted or 0),
                int(is_bot or 0),
                int(is_admin or 0),
                int(is_owner or 0),
                int(is_primary_owner or 0),
                int(is_restricted or 0),
                int(is_ultra_restricted or 0),
                int(is_app_user or 0),
                tz or "",
                tz_label or "",
                int(tz_offset or 0),
                profile_json or "",
                metadata_json or "",
                now,
                now,
            ],
        )
    return result_first(
        await d1_run(
            env,
            "SELECT * FROM users WHERE slack_user_id = ? LIMIT 1",
            [slack_user_id],
        )
    )


async def db_create_session(env: Any, user_id: Any, token: str) -> Optional[str]:
    if not token:
        return None
    await ensure_schema(env)
    await d1_run(
        env,
        "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        [
            token,
            user_id,
            utc_now(),
            (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        ],
    )
    return token


async def db_get_session(env: Any, token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    await ensure_schema(env)
    return result_first(
        await d1_run(
            env,
            (
                "SELECT s.id AS session_id, s.user_id, s.expires_at, "
                "u.slack_user_id, u.team_id, u.name, u.email, u.avatar_url "
                "FROM sessions s JOIN users u ON s.user_id = u.id "
                "WHERE s.id = ? AND s.expires_at > ? LIMIT 1"
            ),
            [token, utc_now()],
        )
    )


async def db_delete_session(env: Any, token: str) -> bool:
    await ensure_schema(env)
    await d1_run(env, "DELETE FROM sessions WHERE id = ?", [token])
    return True


async def db_link_user_workspace(
    env: Any, user_id: Any, workspace_id: Any, role: str = "owner"
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        (
            "INSERT INTO user_workspaces (user_id, workspace_id, role, created_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(user_id, workspace_id) DO NOTHING"
        ),
        [user_id, workspace_id, role or "owner", utc_now()],
    )
    return True


async def db_get_user_workspaces(env: Any, user_id: Any) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    return result_rows(
        await d1_run(
            env,
            (
                "SELECT w.* FROM workspaces w "
                "JOIN user_workspaces uw ON w.id = uw.workspace_id "
                "WHERE uw.user_id = ? ORDER BY w.team_name ASC"
            ),
            [user_id],
        )
    )


async def db_user_owns_workspace(
    env: Any, user_id: Any, workspace_id: Any
) -> bool:
    await ensure_schema(env)
    return (
        result_first(
            await d1_run(
                env,
                "SELECT id FROM user_workspaces WHERE user_id = ? AND workspace_id = ? LIMIT 1",
                [user_id, workspace_id],
            )
        )
        is not None
    )


async def db_get_user_workspace_role(
    env: Any, user_id: Any, workspace_id: Any
) -> str:
    await ensure_schema(env)
    row = result_first(
        await d1_run(
            env,
            "SELECT role FROM user_workspaces WHERE user_id = ? AND workspace_id = ? LIMIT 1",
            [user_id, workspace_id],
        )
    )
    return str((row or {}).get("role") or "")


async def db_get_workspace_installers(
    env: Any, workspace_id: Any
) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    return result_rows(
        await d1_run(
            env,
            (
                "SELECT u.name, u.slack_user_id, uw.role, uw.created_at "
                "FROM user_workspaces uw JOIN users u ON u.id = uw.user_id "
                "WHERE uw.workspace_id = ? "
                "ORDER BY CASE WHEN uw.role = 'owner' THEN 0 ELSE 1 END, uw.created_at ASC"
            ),
            [workspace_id],
        )
    )


async def db_delete_workspace(env: Any, workspace_id: Any) -> bool:
    await ensure_schema(env)
    await d1_run(env, "DELETE FROM user_workspaces WHERE workspace_id = ?", [workspace_id])
    for table in (
        "events",
        "channels",
        "repositories",
        "github_organizations",
        "join_messages",
    ):
        await d1_run(env, "DELETE FROM {0} WHERE workspace_id = ?".format(table), [workspace_id])
    await d1_run(env, "DELETE FROM workspaces WHERE id = ?", [workspace_id])
    return True


async def db_upsert_channel(
    env: Any,
    workspace_id: Any,
    channel_id: str,
    channel_name: str,
    member_count: int = 0,
    topic: str = "",
    purpose: str = "",
    is_private: int = 0,
    is_channel: int = 0,
    is_group: int = 0,
    is_im: int = 0,
    is_mpim: int = 0,
    is_archived: int = 0,
    is_general: int = 0,
    is_shared: int = 0,
    is_ext_shared: int = 0,
    is_org_shared: int = 0,
    is_pending_ext_shared: int = 0,
    is_member: int = 0,
    creator: str = "",
    locale: str = "",
    metadata_json: str = "",
) -> bool:
    await ensure_schema(env)
    now = utc_now()
    await d1_run(
        env,
        (
            "INSERT INTO channels (workspace_id, channel_id, channel_name, member_count, "
            "topic, purpose, is_private, is_channel, is_group, is_im, is_mpim, is_archived, "
            "is_general, is_shared, is_ext_shared, is_org_shared, is_pending_ext_shared, is_member, "
            "creator, locale, metadata_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(workspace_id, channel_id) DO UPDATE SET "
            "channel_name = excluded.channel_name, "
            "member_count = excluded.member_count, "
            "topic = excluded.topic, "
            "purpose = excluded.purpose, "
            "is_private = excluded.is_private, "
            "is_channel = excluded.is_channel, "
            "is_group = excluded.is_group, "
            "is_im = excluded.is_im, "
            "is_mpim = excluded.is_mpim, "
            "is_archived = excluded.is_archived, "
            "is_general = excluded.is_general, "
            "is_shared = excluded.is_shared, "
            "is_ext_shared = excluded.is_ext_shared, "
            "is_org_shared = excluded.is_org_shared, "
            "is_pending_ext_shared = excluded.is_pending_ext_shared, "
            "is_member = excluded.is_member, "
            "creator = excluded.creator, "
            "locale = excluded.locale, "
            "metadata_json = excluded.metadata_json, "
            "updated_at = excluded.updated_at"
        ),
        [
            workspace_id,
            channel_id,
            channel_name,
            int(member_count or 0),
            topic or "",
            purpose or "",
            1 if is_private else 0,
            int(is_channel or 0),
            int(is_group or 0),
            int(is_im or 0),
            int(is_mpim or 0),
            int(is_archived or 0),
            int(is_general or 0),
            int(is_shared or 0),
            int(is_ext_shared or 0),
            int(is_org_shared or 0),
            int(is_pending_ext_shared or 0),
            int(is_member or 0),
            creator or "",
            locale or "",
            metadata_json or "",
            now,
            now,
        ],
    )
    return True


async def db_get_channels(env: Any, workspace_id: Any) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    return result_rows(
        await d1_run(
            env,
            "SELECT * FROM channels WHERE workspace_id = ? ORDER BY member_count DESC",
            [workspace_id],
        )
    )


async def db_get_channel_by_slack_id(
    env: Any, workspace_id: Any, channel_id: str
) -> Optional[Dict[str, Any]]:
    await ensure_schema(env)
    return result_first(
        await d1_run(
            env,
            "SELECT * FROM channels WHERE workspace_id = ? AND channel_id = ? LIMIT 1",
            [workspace_id, channel_id],
        )
    )


async def db_update_channel_join_config(
    env: Any,
    workspace_id: Any,
    channel_id: str,
    join_message_id: Any,
    join_delivery_mode: str = "dm",
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        (
            "UPDATE channels SET send_join_message = ?, join_message_id = ?, "
            "join_delivery_mode = ?, updated_at = ? WHERE workspace_id = ? AND channel_id = ?"
        ),
        [
            1 if join_message_id else 0,
            join_message_id,
            join_delivery_mode or "dm",
            utc_now(),
            workspace_id,
            channel_id,
        ],
    )
    return True


async def db_get_channel_name(env: Any, workspace_id: Any, channel_id: str) -> str:
    row = await db_get_channel_by_slack_id(env, workspace_id, channel_id)
    return str((row or {}).get("channel_name") or "")


async def db_get_channel_join_message_sent_counts(
    env: Any, workspace_id: Any
) -> Dict[str, int]:
    await ensure_schema(env)
    rows = result_rows(
        await d1_run(
            env,
            (
                "SELECT request_data FROM events WHERE workspace_id = ? "
                "AND event_type = 'Channel_Join_Message' AND status = 'success' "
                "ORDER BY id DESC LIMIT 10000"
            ),
            [workspace_id],
        )
    )
    counts: Dict[str, int] = {}
    for row in rows:
        try:
            payload = json.loads(row.get("request_data") or "{}")
        except Exception:
            payload = {}
        channel_id = str(payload.get("channel") or "").strip()
        if channel_id:
            counts[channel_id] = counts.get(channel_id, 0) + 1
    return counts


async def db_add_repository(
    env: Any,
    workspace_id: Any,
    repo_url: str,
    repo_name: str = "",
    description: str = "",
    language: str = "",
    stars: int = 0,
    source_type: str = "repo",
    metadata_json: str = "",
) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        (
            "INSERT INTO repositories (workspace_id, repo_url, repo_name, description, "
            "language, stars, source_type, metadata_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(workspace_id, repo_url) DO UPDATE SET "
            "repo_name = excluded.repo_name, "
            "description = excluded.description, "
            "language = excluded.language, "
            "stars = excluded.stars, "
            "source_type = excluded.source_type, "
            "metadata_json = excluded.metadata_json"
        ),
        [
            workspace_id,
            repo_url,
            repo_name or "",
            description or "",
            language or "",
            int(stars or 0),
            source_type or "repo",
            metadata_json or "",
            utc_now(),
        ],
    )
    return True


async def db_get_repositories(env: Any, workspace_id: Any) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    return result_rows(
        await d1_run(
            env,
            "SELECT * FROM repositories WHERE workspace_id = ? ORDER BY stars DESC",
            [workspace_id],
        )
    )


async def db_delete_repository(env: Any, repo_id: Any, workspace_id: Any) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        "DELETE FROM repositories WHERE id = ? AND workspace_id = ?",
        [repo_id, workspace_id],
    )
    return True


async def db_upsert_github_organization(
    env: Any,
    workspace_id: Any,
    org_login: str,
    org_type: str = "org",
    metadata_json: str = "",
) -> bool:
    await ensure_schema(env)
    now = utc_now()
    await d1_run(
        env,
        (
            "INSERT INTO github_organizations (workspace_id, org_login, org_type, "
            "metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(workspace_id, org_login) DO UPDATE SET "
            "org_type = excluded.org_type, "
            "metadata_json = excluded.metadata_json, "
            "updated_at = excluded.updated_at"
        ),
        [
            workspace_id,
            str(org_login or "").strip(),
            str(org_type or "org").strip() or "org",
            metadata_json or "",
            now,
            now,
        ],
    )
    return True


async def db_get_workspace_github_org_count(env: Any, workspace_id: Any) -> int:
    await ensure_schema(env)
    row = result_first(
        await d1_run(
            env,
            "SELECT COUNT(*) AS count FROM github_organizations WHERE workspace_id = ?",
            [workspace_id],
        )
    )
    return int((row or {}).get("count") or 0)


async def db_get_workspace_latest_org_login(env: Any, workspace_id: Any) -> str:
    await ensure_schema(env)
    row = result_first(
        await d1_run(
            env,
            (
                "SELECT org_login FROM github_organizations WHERE workspace_id = ? "
                "ORDER BY updated_at DESC, created_at DESC, id DESC LIMIT 1"
            ),
            [workspace_id],
        )
    )
    return str((row or {}).get("org_login") or "").strip()


async def db_add_join_message(
    env: Any, workspace_id: Any, name: str, message_text: str
) -> bool:
    await ensure_schema(env)
    now = utc_now()
    await d1_run(
        env,
        (
            "INSERT INTO join_messages (workspace_id, name, message_text, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, ?, ?)"
        ),
        [workspace_id, name, message_text, now, now],
    )
    return True


async def db_get_join_messages(env: Any, workspace_id: Any) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    return result_rows(
        await d1_run(
            env,
            "SELECT * FROM join_messages WHERE workspace_id = ? ORDER BY created_at DESC",
            [workspace_id],
        )
    )


async def db_get_join_message_by_id(
    env: Any, workspace_id: Any, message_id: Any
) -> Optional[Dict[str, Any]]:
    await ensure_schema(env)
    return result_first(
        await d1_run(
            env,
            "SELECT * FROM join_messages WHERE id = ? AND workspace_id = ? LIMIT 1",
            [message_id, workspace_id],
        )
    )


async def db_delete_join_message(env: Any, workspace_id: Any, message_id: Any) -> bool:
    await ensure_schema(env)
    await d1_run(
        env,
        (
            "UPDATE channels SET join_message_id = NULL, send_join_message = 0, updated_at = ? "
            "WHERE workspace_id = ? AND join_message_id = ?"
        ),
        [utc_now(), workspace_id, message_id],
    )
    await d1_run(
        env,
        "DELETE FROM join_messages WHERE id = ? AND workspace_id = ?",
        [message_id, workspace_id],
    )
    return True


async def db_log_event(
    env: Any,
    workspace_id: Any,
    event_type: str,
    user_slack_id: str = "",
    status: str = "success",
    channel_name: str = "",
    request_data: str = "",
    verified: int = 0,
    channel_id: str = "",
    slack_team_id: str = "",
    webhook_body_type: str = "",
    webhook_event_id: str = "",
    webhook_event_time: str = "",
    webhook_event_subtype: str = "",
    webhook_retry_num: str = "",
    webhook_retry_reason: str = "",
    slack_response_data: str = "",
    api_app_id: str = "",
    command: str = "",
    command_text: str = "",
    is_enterprise_install: str = "",
    response_url: str = "",
    team_domain: str = "",
    trigger_id: str = "",
    user_name: str = "",
    slack_token: str = "",
) -> bool:
    return await db_insert_event(
        env,
        workspace_id,
        event_type,
        user_slack_id=user_slack_id,
        status=status,
        channel_name=channel_name,
        request_data=request_data,
        verified=verified,
        channel_id=channel_id,
        slack_team_id=slack_team_id,
        webhook_body_type=webhook_body_type,
        webhook_event_id=webhook_event_id,
        webhook_event_time=webhook_event_time,
        webhook_event_subtype=webhook_event_subtype,
        webhook_retry_num=webhook_retry_num,
        webhook_retry_reason=webhook_retry_reason,
        slack_response_data=slack_response_data,
        api_app_id=api_app_id,
        command=command,
        command_text=command_text,
        is_enterprise_install=is_enterprise_install,
        response_url=response_url,
        team_domain=team_domain,
        trigger_id=trigger_id,
        user_name=user_name,
        slack_token=slack_token,
    )


async def db_insert_event(
    env: Any,
    workspace_id: Any,
    event_type: str,
    user_slack_id: str = "",
    status: str = "success",
    created_at: Optional[str] = None,
    channel_name: str = "",
    request_data: str = "",
    verified: int = 0,
    channel_id: str = "",
    slack_team_id: str = "",
    webhook_body_type: str = "",
    webhook_event_id: str = "",
    webhook_event_time: str = "",
    webhook_event_subtype: str = "",
    webhook_retry_num: str = "",
    webhook_retry_reason: str = "",
    slack_response_data: str = "",
    api_app_id: str = "",
    command: str = "",
    command_text: str = "",
    is_enterprise_install: str = "",
    response_url: str = "",
    team_domain: str = "",
    trigger_id: str = "",
    user_name: str = "",
    slack_token: str = "",
) -> bool:
    if str(event_type or "").lower() == "http_request":
        return False
    await ensure_schema(env)
    created = created_at or utc_now()
    common_params = [
        workspace_id,
        event_type,
        user_slack_id or "",
        channel_name or "",
        channel_id or "",
        request_data or "",
        1 if verified else 0,
        status or "success",
        created,
        webhook_body_type or "",
        webhook_event_id or "",
        webhook_event_time or "",
        webhook_event_subtype or "",
        webhook_retry_num or "",
        webhook_retry_reason or "",
        slack_response_data or "",
    ]
    common_params_without_response = common_params[:-1]
    try:
        await d1_run(
            env,
            (
                "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, "
                "channel_id, slack_team_id, api_app_id, command, command_text, is_enterprise_install, "
                "response_url, team_domain, trigger_id, user_name, slack_token, request_data, verified, status, "
                "created_at, webhook_body_type, webhook_event_id, webhook_event_time, webhook_event_subtype, "
                "webhook_retry_num, webhook_retry_reason, slack_response_data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            [
                workspace_id,
                event_type,
                user_slack_id or "",
                channel_name or "",
                channel_id or "",
                slack_team_id or "",
                api_app_id or "",
                command or "",
                command_text or "",
                is_enterprise_install or "",
                response_url or "",
                team_domain or "",
                trigger_id or "",
                user_name or "",
                slack_token or "",
                request_data or "",
                1 if verified else 0,
                status or "success",
                created,
                webhook_body_type or "",
                webhook_event_id or "",
                webhook_event_time or "",
                webhook_event_subtype or "",
                webhook_retry_num or "",
                webhook_retry_reason or "",
                slack_response_data or "",
            ],
        )
    except Exception as error:
        missing_optional_event_column = any(
            column_name in str(error)
            for column_name in (
                "api_app_id",
                "command_text",
                "is_enterprise_install",
                "response_url",
                "team_domain",
                "trigger_id",
                "user_name",
                "slack_token",
                "slack_response_data",
            )
        )
        if missing_optional_event_column:
            try:
                await d1_run(
                    env,
                    (
                        "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, "
                        "channel_id, slack_team_id, request_data, verified, status, created_at, webhook_body_type, "
                        "webhook_event_id, webhook_event_time, webhook_event_subtype, webhook_retry_num, webhook_retry_reason) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    [
                        workspace_id,
                        event_type,
                        user_slack_id or "",
                        channel_name or "",
                        channel_id or "",
                        slack_team_id or "",
                        request_data or "",
                        1 if verified else 0,
                        status or "success",
                        created,
                        webhook_body_type or "",
                        webhook_event_id or "",
                        webhook_event_time or "",
                        webhook_event_subtype or "",
                        webhook_retry_num or "",
                        webhook_retry_reason or "",
                    ],
                )
            except Exception as fallback_error:
                if "slack_team_id" not in str(fallback_error):
                    raise
                await d1_run(
                    env,
                    (
                        "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, "
                        "channel_id, request_data, verified, status, created_at, webhook_body_type, "
                        "webhook_event_id, webhook_event_time, webhook_event_subtype, webhook_retry_num, webhook_retry_reason) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    common_params_without_response,
                )
            return True
        if "slack_team_id" not in str(error):
            raise
        log_json_event(
            "events_insert_retry_without_slack_team_id",
            {"event_type": event_type, "slack_team_id": slack_team_id or ""},
        )
        try:
            await d1_run(
                env,
                (
                    "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, "
                    "channel_id, request_data, verified, status, created_at, webhook_body_type, "
                    "webhook_event_id, webhook_event_time, webhook_event_subtype, webhook_retry_num, webhook_retry_reason, "
                    "slack_response_data) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                common_params,
            )
        except Exception as fallback_error:
            if "slack_response_data" not in str(fallback_error):
                raise
            await d1_run(
                env,
                (
                    "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, "
                    "channel_id, request_data, verified, status, created_at, webhook_body_type, "
                    "webhook_event_id, webhook_event_time, webhook_event_subtype, webhook_retry_num, webhook_retry_reason) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                common_params_without_response,
            )
    return True


def normalize_event_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return utc_now()
    cleaned = raw.replace(" ", "T")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return utc_now()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


async def import_workspace_history_csv(
    env: Any, workspace_id: Any, csv_text: str
) -> Dict[str, Any]:
    if not csv_text or not str(csv_text).strip():
        return {"ok": False, "error": "CSV file is empty"}

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return {"ok": False, "error": "CSV must include a header row"}

    imported = 0
    skipped = 0
    errors = []
    normalized_fieldnames = [str(name or "").strip().lower() for name in reader.fieldnames]

    for row_index, row in enumerate(reader, start=2):
        normalized_row = {}
        for index, key in enumerate(reader.fieldnames or []):
            normalized_key = normalized_fieldnames[index]
            normalized_row[normalized_key] = row.get(key)

        event_type = str(
            normalized_row.get("event_type") or normalized_row.get("type") or ""
        ).strip()
        if not event_type:
            skipped += 1
            if len(errors) < 5:
                errors.append("Line {0}: missing event_type".format(row_index))
            continue

        verified = str(normalized_row.get("verified") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "verified",
        )
        ok = await db_insert_event(
            env,
            workspace_id,
            event_type,
            user_slack_id=str(
                normalized_row.get("user_slack_id") or normalized_row.get("user") or ""
            ).strip(),
            status=str(normalized_row.get("status") or "success").strip() or "success",
            created_at=normalize_event_timestamp(
                normalized_row.get("created_at")
                or normalized_row.get("time")
                or normalized_row.get("timestamp")
            ),
            channel_name=str(normalized_row.get("channel_name") or "").strip(),
            channel_id=str(normalized_row.get("channel_id") or "").strip(),
            request_data=str(normalized_row.get("request_data") or "").strip(),
            verified=1 if verified else 0,
        )
        if ok:
            imported += 1
        else:
            skipped += 1

    return {
        "ok": imported > 0,
        "events_imported": imported,
        "rows_skipped": skipped,
        "errors": errors,
    }


async def db_get_events(
    env: Any, workspace_id: Any, limit: int = 20
) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    return result_rows(
        await d1_run(
            env,
            (
                "SELECT e.* FROM events e "
                "WHERE e.workspace_id = ? ORDER BY e.created_at DESC LIMIT ?"
            ),
            [workspace_id, int(limit or 20)],
        )
    )


def build_public_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": event.get("id"),
            "event_type": event.get("event_type"),
            "status": event.get("status"),
            "verified": event.get("verified"),
            "created_at": event.get("created_at"),
        }
        for event in events or []
    ]


async def db_purge_events(env: Any, workspace_id: Any) -> Dict[str, Any]:
    await ensure_schema(env)
    result = await d1_run(env, "DELETE FROM events WHERE workspace_id = ?", [workspace_id])
    meta = result.get("meta") or {}
    return {"ok": True, "deleted": int(meta.get("changes") or 0)}


async def db_get_last_event_time(
    env: Any, workspace_id: Any, event_type: str
) -> str:
    await ensure_schema(env)
    row = result_first(
        await d1_run(
            env,
            "SELECT MAX(created_at) AS last_time FROM events WHERE workspace_id = ? AND event_type = ?",
            [workspace_id, event_type],
        )
    )
    return str((row or {}).get("last_time") or "").strip()


async def db_has_team_join_event_id(
    env: Any, workspace_id: Any, event_id: str
) -> bool:
    if not event_id:
        return False
    await ensure_schema(env)
    row = result_first(
        await d1_run(
            env,
            (
                "SELECT id FROM events WHERE workspace_id = ? AND event_type = 'Team_Join' "
                "AND request_data LIKE ? ORDER BY id DESC LIMIT 1"
            ),
            [workspace_id, '%"event_id":"{0}"%'.format(event_id)],
        )
    )
    return row is not None


async def db_mark_join_message_verified_by_tracking(
    env: Any, tracking_id: str, ip_address: str, user_agent: str
) -> bool:
    if not tracking_id:
        return False
    await ensure_schema(env)
    row = result_first(
        await d1_run(
            env,
            (
                "SELECT id, request_data FROM events "
                "WHERE event_type IN ('Channel_Join_Message', 'Team_Join') "
                "AND request_data LIKE ? ORDER BY id DESC LIMIT 1"
            ),
            ['%"logo_tracking_id": "{0}"%'.format(tracking_id)],
        )
    )
    if not row:
        return False
    try:
        payload = json.loads(row.get("request_data") or "{}")
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["verification_ip"] = ip_address or ""
    payload["verification_user_agent"] = str(user_agent or "")[:512]
    payload["verified_at"] = utc_now()
    await d1_run(
        env,
        "UPDATE events SET request_data = ?, verified = 1 WHERE id = ?",
        [json.dumps(payload), row.get("id")],
    )
    return True


async def db_get_daily_stats(
    env: Any, workspace_id: Any, days: int = 30
) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return result_rows(
        await d1_run(
            env,
            (
                "SELECT substr(created_at, 1, 10) AS date, event_type, COUNT(*) AS count "
                "FROM events WHERE workspace_id = ? AND created_at >= ? "
                "GROUP BY date, event_type ORDER BY date ASC"
            ),
            [workspace_id, since],
        )
    )


async def db_get_workspace_stats(env: Any, workspace_id: Any) -> Dict[str, Any]:
    await ensure_schema(env)
    since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    total = int(
        (result_first(await d1_run(env, "SELECT COUNT(*) AS n FROM events WHERE workspace_id = ?", [workspace_id])) or {}).get("n")
        or 0
    )
    last24 = int(
        (
            result_first(
                await d1_run(
                    env,
                    "SELECT COUNT(*) AS n FROM events WHERE workspace_id = ? AND created_at >= ?",
                    [workspace_id, since_24h],
                )
            )
            or {}
        ).get("n")
        or 0
    )
    success = int(
        (
            result_first(
                await d1_run(
                    env,
                    "SELECT COUNT(*) AS n FROM events WHERE workspace_id = ? AND status='success'",
                    [workspace_id],
                )
            )
            or {}
        ).get("n")
        or 0
    )
    last_event = result_first(
        await d1_run(
            env,
            "SELECT created_at FROM events WHERE workspace_id = ? ORDER BY created_at DESC LIMIT 1",
            [workspace_id],
        )
    )
    joins = int(
        (
            result_first(
                await d1_run(
                    env,
                    "SELECT COUNT(*) AS n FROM events WHERE workspace_id = ? AND event_type='Team_Join'",
                    [workspace_id],
                )
            )
            or {}
        ).get("n")
        or 0
    )
    commands = int(
        (
            result_first(
                await d1_run(
                    env,
                    "SELECT COUNT(*) AS n FROM events WHERE workspace_id = ? AND event_type='Command'",
                    [workspace_id],
                )
            )
            or {}
        ).get("n")
        or 0
    )
    return {
        "total_activities": total,
        "last_24h_activities": last24,
        "success_rate": round(success / total * 100, 1) if total else 100.0,
        "last_event_time": (last_event or {}).get("created_at"),
        "joins": joins,
        "commands": commands,
    }


async def db_list_workspaces_public(env: Any) -> List[Dict[str, Any]]:
    await ensure_schema(env)
    rows = result_rows(
        await d1_run(
            env,
            (
                "SELECT w.id, w.team_id, w.team_name, w.icon_url, w.invite_link, "
                "w.member_count, w.channel_count, w.created_at, "
                "(SELECT COUNT(*) FROM events e WHERE e.workspace_id = w.id) AS total_activities, "
                "(SELECT COUNT(*) FROM events e WHERE e.workspace_id = w.id AND e.event_type = 'Team_Join') AS joins, "
                "(SELECT MAX(e2.created_at) FROM events e2 WHERE e2.workspace_id = w.id) AS last_event_time, "
                "(SELECT COUNT(*) FROM repositories r WHERE r.workspace_id = w.id) AS repo_count, "
                "(SELECT go.org_login FROM github_organizations go WHERE go.workspace_id = w.id "
                "ORDER BY go.updated_at DESC, go.created_at DESC, go.id DESC LIMIT 1) AS github_org_login "
                "FROM workspaces w ORDER BY w.created_at DESC"
            ),
        )
    )
    for row in rows:
        org_login = str(row.get("github_org_login") or "").strip()
        row["github_org_login"] = org_login
        row["github_org_url"] = "https://github.com/{0}".format(org_login) if org_login else ""
        row["status"] = "connected"
        row["channel_count"] = int(row.get("channel_count") or 0)
        row["member_count"] = int(row.get("member_count") or 0)
        row["repo_count"] = int(row.get("repo_count") or 0)
    return rows


async def upsert_connected_workspace(
    env: Any,
    team_id: str,
    team_name: str,
    installer_user_id: str = "",
    bot_user_id: str = "",
    icon_url: str = "",
    invite_link: str = "",
    github_org_url: str = "",
    repo_count: int = 0,
    channel_count: int = 0,
    member_count: int = 0,
    status: str = "connected",
) -> None:
    if not team_id:
        return
    try:
        getattr(env, "DB")
    except Exception:
        return

    await ensure_schema(env)
    now = datetime.now(timezone.utc).isoformat()
    await d1_run(
        env,
        (
            "INSERT INTO connected_workspaces ("
            "team_id, team_name, icon_url, installer_user_id, bot_user_id, invite_link, "
            "github_org_url, repo_count, channel_count, member_count, status, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(team_id) DO UPDATE SET "
            "team_name = excluded.team_name, "
            "icon_url = excluded.icon_url, "
            "installer_user_id = excluded.installer_user_id, "
            "bot_user_id = excluded.bot_user_id, "
            "invite_link = excluded.invite_link, "
            "github_org_url = excluded.github_org_url, "
            "repo_count = excluded.repo_count, "
            "channel_count = excluded.channel_count, "
            "member_count = excluded.member_count, "
            "status = excluded.status, "
            "updated_at = excluded.updated_at"
        ),
        [
            team_id,
            team_name or team_id,
            icon_url,
            installer_user_id,
            bot_user_id,
            invite_link,
            github_org_url,
            int(repo_count or 0),
            int(channel_count or 0),
            int(member_count or 0),
            status or "connected",
            now,
            now,
        ],
    )
    if not await db_get_workspace_by_team(env, team_id):
        await db_upsert_workspace(
            env,
            team_id=team_id,
            team_name=team_name or team_id,
            bot_user_id=bot_user_id,
            icon_url=icon_url,
            installer_slack_user_id=installer_user_id,
        )


async def delete_connected_workspace(
    env: Any, team_id: str = "", workspace_id: str = ""
) -> None:
    try:
        getattr(env, "DB")
    except Exception:
        return
    await ensure_schema(env)
    if team_id:
        await d1_run(env, "DELETE FROM connected_workspaces WHERE team_id = ?", [team_id])
    if workspace_id:
        await db_delete_workspace(env, workspace_id)


async def save_managed_server(
    env: Any,
    name: str,
    url: str,
    status: str = "online",
    description: str = "",
    server_id: Optional[int] = None,
) -> None:
    try:
        getattr(env, "DB")
    except Exception:
        return
    await ensure_schema(env)
    now = datetime.now(timezone.utc).isoformat()
    if server_id:
        await d1_run(
            env,
            (
                "UPDATE managed_servers SET name = ?, url = ?, status = ?, "
                "description = ?, updated_at = ? WHERE id = ?"
            ),
            [name, url, status or "online", description, now, server_id],
        )
        return
    await d1_run(
        env,
        (
            "INSERT INTO managed_servers (name, url, status, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        ),
        [name, url, status or "online", description, now, now],
    )


async def delete_managed_server(env: Any, server_id: int) -> None:
    try:
        getattr(env, "DB")
    except Exception:
        return
    await ensure_schema(env)
    await d1_run(env, "DELETE FROM managed_servers WHERE id = ?", [server_id])


async def list_managed_servers(env: Any) -> List[Dict[str, Any]]:
    try:
        getattr(env, "DB")
    except Exception:
        return []
    await ensure_schema(env)
    result = await d1_run(
        env,
        "SELECT * FROM managed_servers ORDER BY updated_at DESC, id DESC",
    )
    return result.get("results") or []


async def list_connected_workspaces(env: Any) -> List[Dict[str, Any]]:
    try:
        getattr(env, "DB")
    except Exception:
        return []
    await ensure_schema(env)
    connected_result = await d1_run(
        env,
        (
            "SELECT cw.*, "
            "COALESCE(ev.total_activities, 0) AS total_activities, "
            "COALESCE(ev.joins, 0) AS joins, "
            "ev.last_event_time AS last_event_time "
            "FROM connected_workspaces cw "
            "LEFT JOIN ("
            "SELECT slack_team_id AS team_id, COUNT(*) AS total_activities, "
            "SUM(CASE WHEN event_type = 'Team_Join' THEN 1 ELSE 0 END) AS joins, "
            "MAX(created_at) AS last_event_time "
            "FROM events WHERE slack_team_id IS NOT NULL AND slack_team_id != '' "
            "GROUP BY slack_team_id"
            ") ev ON ev.team_id = cw.team_id "
            "ORDER BY COALESCE(ev.last_event_time, cw.updated_at) DESC"
        ),
    )
    connected_rows = result_rows(connected_result)
    workspace_rows = await db_list_workspaces_public(env)

    by_team: Dict[str, Dict[str, Any]] = {}
    for row in connected_rows:
        row["connected_workspace_id"] = row.get("id")
        team_key = str(row.get("team_id") or "connected:{0}".format(row.get("id")))
        by_team[team_key] = row
    for row in workspace_rows:
        row["workspace_id"] = row.get("id")
        team_key = str(row.get("team_id") or "workspace:{0}".format(row.get("id")))
        existing = by_team.get(team_key, {})
        merged = dict(existing)
        merged.update(row)
        by_team[team_key] = merged

    rows = list(by_team.values())
    rows.sort(
        key=lambda row: str(
            row.get("last_event_time") or row.get("updated_at") or row.get("created_at") or ""
        ),
        reverse=True,
    )
    return rows


async def public_connections_payload(env: Any) -> Dict[str, Any]:
    workspaces = await list_connected_workspaces(env)
    servers = await list_managed_servers(env)
    total_activities = sum(int(row.get("total_activities") or 0) for row in workspaces)
    joins = sum(int(row.get("joins") or 0) for row in workspaces)
    commands = max(total_activities - joins, 0)
    last_updated = ""
    for row in workspaces:
        timestamp = str(row.get("last_event_time") or row.get("updated_at") or "")
        if timestamp and timestamp > last_updated:
            last_updated = timestamp
    for row in servers:
        timestamp = str(row.get("updated_at") or "")
        if timestamp and timestamp > last_updated:
            last_updated = timestamp
    return {
        "ok": True,
        "workspaces": workspaces,
        "servers": servers,
        "stats": {
            "connected_workspaces": len(workspaces),
            "managed_servers": len(servers),
            "total_activities": total_activities,
            "team_joins": joins,
            "commands": commands,
            "last_updated": last_updated,
        },
    }


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
            "SELECT COUNT(DISTINCT slack_team_id) AS teams, COUNT(*) AS events "
            "FROM events WHERE slack_team_id IS NOT NULL AND slack_team_id != ''"
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
    text = "Available commands:\n{0}".format(available_commands_text())
    return {
        "response_type": "ephemeral",
        "text": text,
        "blocks": [
            make_section_block(
                "*BLT Sammich Commands*\n{0}".format(text.replace("\n", "\n"))
            )
        ],
    }


async def stats_response(env: Any) -> Dict[str, Any]:
    workspace_count = 0
    server_count = 0
    total_activities = 0
    try:
        payload = await public_connections_payload(env)
        stats = payload.get("stats") or {}
        workspace_count = int(stats.get("connected_workspaces") or 0)
        server_count = int(stats.get("managed_servers") or 0)
        total_activities = int(stats.get("total_activities") or 0)
    except Exception:
        pass

    project_count = len(PROJECT_DATA)
    technology_count = len(REPO_DATA)
    repo_count = sum(len(repos or []) for repos in REPO_DATA.values())
    message = (
        "*OWASP Project Stats*\n"
        "Projects indexed: {0}\n"
        "Technology groups: {1}\n"
        "Repository links indexed: {2}\n"
        "Connected workspaces: {3}\n"
        "Managed servers: {4}\n"
        "Logged activities: {5}"
    ).format(
        project_count,
        technology_count,
        repo_count,
        workspace_count,
        server_count,
        total_activities,
    )
    return {
        "response_type": "ephemeral",
        "text": message,
        "blocks": [make_section_block(message)],
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
        "All OWASP project channels start with #project- like #project-blt\n\n"
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

    if command_name == "/stats":
        return await stats_response(env)
    if command_name == "/contributors":
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


def is_direct_bot_message(event: Dict[str, Any]) -> bool:
    channel_id = str(event.get("channel") or "")
    channel_type = str(event.get("channel_type") or "")
    return channel_type == "im" or channel_id.startswith("D")


def message_mentions_bot(event: Dict[str, Any], bot_user_id: str = "") -> bool:
    text = str(event.get("text") or "")
    if not bot_user_id:
        return False
    return "<@{0}>".format(bot_user_id) in text


def bot_direct_message_response(text: str = "") -> str:
    cleaned = str(text or "").strip()
    if cleaned.lower() in ("help", "hi", "hello", "hey", "/blt"):
        return help_response()["text"]
    if cleaned:
        return (
            "I heard you. I can help with OWASP project discovery and BLT stats. "
            "Try `/contrib`, `/stats`, `/discover security`, `/gsoc25`, or `/installed_apps`."
        )
    return help_response()["text"]


async def log_slack_api_response(
    env: Any,
    team_id: str,
    channel_id: str,
    user_id: str,
    api_method: str,
    request_payload: Dict[str, Any],
    response_payload: Dict[str, Any],
    ok: bool,
    status_code: int,
) -> None:
    try:
        getattr(env, "DB")
    except Exception:
        return
    workspace_id = None
    try:
        workspace = await db_get_workspace_by_team(env, team_id) if team_id else None
        workspace_id = workspace.get("id") if workspace else None
    except Exception as error:
        log_exception_one_line(
            error,
            "slack_api_response_workspace_lookup_failed",
            {"team_id": team_id, "api_method": api_method},
        )
    try:
        await db_log_event(
            env,
            workspace_id,
            "Slack_API_Response",
            user_slack_id=user_id or "",
            channel_id=channel_id or "",
            slack_team_id=team_id or "",
            request_data=json.dumps(
                {
                    "api_method": api_method,
                    "request": request_payload,
                    "status_code": status_code,
                },
                sort_keys=True,
            ),
            slack_response_data=json.dumps(response_payload or {}, sort_keys=True),
            status="success" if ok else "error",
            webhook_body_type="slack_api",
        )
    except Exception as error:
        log_exception_one_line(
            error,
            "slack_api_response_log_failed",
            {"team_id": team_id, "api_method": api_method},
        )


async def slack_api_post_message(
    channel_id: str, text: str, env: Any, team_id: str = ""
) -> None:
    try:
        token = await db_get_workspace_bot_token(
            env, team_id=team_id, channel_id=channel_id
        )
    except Exception as error:
        log_exception_one_line(
            error,
            "slack_post_token_lookup_failed",
            {"team_id": team_id, "channel_id": channel_id},
        )
        token = ""
    if not token:
        token = env_value(env, "SLACK_BOT_TOKEN")
    if not token:
        return
    request_payload = {"channel": channel_id, "text": text}
    ok, payload, status_code = await fetch_json(
        "https://slack.com/api/chat.postMessage",
        method="POST",
        headers={
            "Authorization": "Bearer {0}".format(token),
            "Content-Type": "application/json",
        },
        body=json.dumps(request_payload),
    )
    await log_slack_api_response(
        env,
        team_id=team_id,
        channel_id=channel_id,
        user_id="",
        api_method="chat.postMessage",
        request_payload=request_payload,
        response_payload=payload,
        ok=ok and bool(payload.get("ok", True)),
        status_code=status_code,
    )


async def slack_api_publish_home(user_id: str, env: Any, team_id: str = "") -> None:
    if not user_id:
        return
    try:
        token = await db_get_workspace_bot_token(env, team_id=team_id)
    except Exception as error:
        log_exception_one_line(
            error,
            "slack_home_token_lookup_failed",
            {"team_id": team_id, "user_id": user_id},
        )
        token = ""
    if not token:
        token = env_value(env, "SLACK_BOT_TOKEN")
    if not token:
        return
    request_payload = {"user_id": user_id, "view": app_home_view()}
    ok, payload, status_code = await fetch_json(
        "https://slack.com/api/views.publish",
        method="POST",
        headers={
            "Authorization": "Bearer {0}".format(token),
            "Content-Type": "application/json",
        },
        body=json.dumps(request_payload),
    )
    await log_slack_api_response(
        env,
        team_id=team_id,
        channel_id="",
        user_id=user_id,
        api_method="views.publish",
        request_payload=request_payload,
        response_payload=payload,
        ok=ok and bool(payload.get("ok", True)),
        status_code=status_code,
    )


async def handle_event_payload(payload: Dict[str, Any], env: Any) -> Any:
    if payload.get("type") == "url_verification":
        return json_response({"challenge": payload.get("challenge", "")})

    event = payload.get("event") or {}
    team_id = payload_team_id(payload)
    if event.get("type") == "app_home_opened":
        if str(event.get("tab") or "home") == "home":
            user_id = str(event.get("user") or "")
            try:
                await slack_api_publish_home(user_id, env, team_id=team_id)
            except Exception as error:
                log_exception_one_line(
                    error,
                    "app_home_publish_failed",
                    {"team_id": team_id, "user_id": user_id},
                )
            return json_response({"ok": True})
    if event.get("type") == "app_mention":
        channel_id = event.get("channel")
        if channel_id:
            await slack_api_post_message(
                channel_id,
                bot_direct_message_response(str(event.get("text") or "")),
                env,
                team_id=team_id,
            )
    if event.get("type") == "team_join":
        user_id = event.get("user", {}).get("id")
        welcome_message = render_team_join_message(event, team_id)
        if user_id and welcome_message:
            await slack_api_post_message(
                user_id, welcome_message, env, team_id=team_id
            )
    if event.get("type") == "message":
        if event.get("subtype"):
            return json_response({"ok": True})
        user_id = event.get("user", "")
        channel_id = event.get("channel", "")
        bot_user_id = ""
        try:
            bot_user_id = await db_get_workspace_bot_user_id(
                env, team_id=team_id, channel_id=channel_id
            )
        except Exception as error:
            log_exception_one_line(
                error,
                "bot_user_lookup_failed",
                {"team_id": team_id, "channel_id": channel_id},
            )
        if bot_user_id and user_id == bot_user_id:
            return json_response({"ok": True})
        installer_user_id = ""
        try:
            installer_user_id = await get_workspace_installer(env, team_id) or ""
        except Exception as error:
            log_exception_one_line(
                error,
                "installer_lookup_failed",
                {"team_id": team_id, "channel_id": channel_id},
            )
        if installer_user_id and user_id == installer_user_id and channel_id:
            await slack_api_post_message(
                channel_id,
                current_config_message(env, team_id, installer_user_id),
                env,
                team_id=team_id,
            )
            return json_response({"ok": True})
        if channel_id and (
            is_direct_bot_message(event) or message_mentions_bot(event, bot_user_id)
        ):
            await slack_api_post_message(
                channel_id,
                bot_direct_message_response(str(event.get("text") or "")),
                env,
                team_id=team_id,
            )
    return json_response({"ok": True})


def render_status_chip(status: str) -> str:
    normalized = (status or "unknown").lower()
    classes = {
        "online": "bg-green-100 text-green-700",
        "connected": "bg-green-100 text-green-700",
        "degraded": "bg-yellow-100 text-yellow-700",
        "offline": "bg-red-100 text-red-700",
    }.get(normalized, "bg-gray-100 text-gray-700")
    return '<span class="px-2 py-1 rounded text-xs font-semibold {0}">{1}</span>'.format(
        classes,
        html_escape(status or "unknown"),
    )


def admin_table_schema(table_name: str) -> Dict[str, Any]:
    return ADMIN_TABLE_SCHEMAS.get(table_name) or ADMIN_TABLE_SCHEMAS["workspaces"]


def require_admin_table_name(table_name: str) -> str:
    if table_name not in ADMIN_TABLE_SCHEMAS:
        raise ValueError("Unknown database table: {0}".format(table_name))
    return table_name


def admin_redirect(env: Any, message: str = "", table_name: str = "") -> Any:
    query: Dict[str, str] = {}
    if table_name:
        query["table"] = table_name
    if message:
        query["message"] = message
    location = admin_path(env)
    if query:
        location += "?" + urlencode(query)
    return redirect_response(location)


def coerce_admin_db_value(column_type: str, value: str) -> Any:
    raw = str(value or "")
    if column_type == "INTEGER":
        if raw.strip() == "":
            return 0
        try:
            return int(raw)
        except ValueError:
            return 0
    return raw


def admin_editable_columns(schema: Dict[str, Any]) -> List[Tuple[str, str]]:
    pk = schema["pk"]
    if schema.get("auto_pk"):
        return [(name, kind) for name, kind in schema["columns"] if name != pk]
    return list(schema["columns"])


def admin_form_value(form: Dict[str, str], column_name: str, column_type: str) -> Any:
    return coerce_admin_db_value(column_type, form.get("field__" + column_name, ""))


def admin_cell_text(value: Any) -> str:
    text = str(value if value is not None else "")
    if len(text) > 140:
        return text[:137] + "..."
    return text


def admin_row_title(row: Dict[str, Any], schema: Dict[str, Any]) -> str:
    for column_name in (
        "team_name",
        "name",
        "app_name",
        "channel_name",
        "repo_name",
        "org_login",
        "event_type",
        "slack_user_id",
        "id",
        schema["pk"],
    ):
        value = row.get(column_name)
        if value not in (None, ""):
            return admin_cell_text(value)
    return "Untitled row"


def admin_row_detail(row: Dict[str, Any], schema: Dict[str, Any]) -> str:
    detail_parts = []
    for column_name, _ in schema["columns"]:
        if column_name == schema["pk"]:
            continue
        value = row.get(column_name)
        if value in (None, ""):
            continue
        detail_parts.append("{0}: {1}".format(column_name, admin_cell_text(value)))
        if len(detail_parts) >= 2:
            break
    return " | ".join(detail_parts)


def admin_row_identity(table_name: str, schema: Dict[str, Any], pk_value: str) -> str:
    return "{0}.{1} {2}".format(table_name, schema["pk"], pk_value)


def admin_row_pk_value(table_name: str, row: Dict[str, Any]) -> str:
    schema = admin_table_schema(table_name)
    value = row.get(schema["pk"])
    return str(value if value is not None else "")


def admin_row_summary(table_name: str, row: Dict[str, Any]) -> str:
    schema = admin_table_schema(table_name)
    pk_value = admin_row_pk_value(table_name, row)
    title = admin_row_title(row, schema)
    detail = admin_row_detail(row, schema)
    identity = admin_row_identity(table_name, schema, pk_value)
    if detail:
        return "{0} - {1} - {2}".format(identity, title, detail)
    return "{0} - {1}".format(identity, title)


def admin_cascade_relationships_for(table_name: str) -> List[Dict[str, str]]:
    return [
        relationship
        for relationship in ADMIN_CASCADE_RELATIONSHIPS
        if relationship["parent_table"] == table_name
    ]


async def db_admin_related_tree(
    env: Any,
    table_name: str,
    row: Dict[str, Any],
    visited: Optional[set] = None,
) -> List[Dict[str, Any]]:
    visited = visited or set()
    parent_key = (table_name, admin_row_pk_value(table_name, row))
    if parent_key in visited:
        return []
    visited.add(parent_key)
    related = []
    for relationship in admin_cascade_relationships_for(table_name):
        parent_value = row.get(relationship["parent_column"])
        if parent_value in (None, ""):
            continue
        child_table = relationship["child_table"]
        child_schema = admin_table_schema(child_table)
        rows = result_rows(
            await d1_run(
                env,
                "SELECT * FROM {0} WHERE {1} = ? ORDER BY {2} DESC LIMIT 100".format(
                    child_table,
                    relationship["child_column"],
                    child_schema["pk"],
                ),
                [parent_value],
            )
        )
        children = []
        if relationship["action"] == "delete":
            for child_row in rows:
                children.append(
                    {
                        "table": child_table,
                        "row": child_row,
                        "children": await db_admin_related_tree(
                            env, child_table, child_row, visited
                        ),
                    }
                )
        else:
            children = [{"table": child_table, "row": child_row, "children": []} for child_row in rows]
        related.append(
            {
                "relationship": relationship,
                "rows": children,
                "count": len(rows),
            }
        )
    visited.discard(parent_key)
    return related


def admin_cascade_count(related_tree: List[Dict[str, Any]]) -> int:
    total = 0
    for group in related_tree:
        total += int(group.get("count") or 0)
        for child in group.get("rows") or []:
            total += admin_cascade_count(child.get("children") or [])
    return total


async def db_admin_table_counts(env: Any) -> Dict[str, Any]:
    counts: Dict[str, Any] = {}
    for table_name in ADMIN_TABLE_SCHEMAS:
        try:
            row = result_first(
                await d1_run(env, "SELECT COUNT(*) AS n FROM {0}".format(table_name))
            )
            counts[table_name] = int((row or {}).get("n") or 0)
        except Exception:
            counts[table_name] = "?"
    return counts


async def db_admin_rows(env: Any, table_name: str) -> List[Dict[str, Any]]:
    table_name = require_admin_table_name(table_name)
    schema = admin_table_schema(table_name)
    pk = schema["pk"]
    try:
        return result_rows(
            await d1_run(
                env,
                "SELECT * FROM {0} ORDER BY {1} DESC LIMIT 100".format(table_name, pk),
            )
        )
    except Exception as error:
        log_exception_one_line(
            error,
            "db_admin_rows_failed",
            {"table": table_name},
        )
        return []


def admin_sort_params(
    table_name: str, sort_column: str = "", sort_direction: str = ""
) -> Tuple[str, str]:
    schema = admin_table_schema(table_name)
    columns = [name for name, _ in schema["columns"]]
    column = sort_column if sort_column in columns else schema["pk"]
    direction = "ASC" if str(sort_direction).lower() == "asc" else "DESC"
    return column, direction


async def db_admin_rows_sorted(
    env: Any, table_name: str, sort_column: str = "", sort_direction: str = ""
) -> List[Dict[str, Any]]:
    table_name = require_admin_table_name(table_name)
    sort_column, sort_direction = admin_sort_params(
        table_name, sort_column, sort_direction
    )
    try:
        return result_rows(
            await d1_run(
                env,
                "SELECT * FROM {0} ORDER BY {1} {2} LIMIT 100".format(
                    table_name, sort_column, sort_direction
                ),
            )
        )
    except Exception as error:
        log_exception_one_line(
            error,
            "db_admin_rows_failed",
            {"table": table_name, "sort": sort_column, "direction": sort_direction},
        )
        return []


async def db_admin_get_row(
    env: Any, table_name: str, pk_value: str
) -> Optional[Dict[str, Any]]:
    table_name = require_admin_table_name(table_name)
    schema = admin_table_schema(table_name)
    pk = schema["pk"]
    if not pk_value:
        return None
    return result_first(
        await d1_run(
            env,
            "SELECT * FROM {0} WHERE {1} = ? LIMIT 1".format(table_name, pk),
            [pk_value],
        )
    )


async def db_admin_context(
    env: Any,
    selected_table: str = "",
    edit_pk: str = "",
    add_row: bool = False,
    confirm_delete_pk: str = "",
    sort_column: str = "",
    sort_direction: str = "",
) -> Dict[str, Any]:
    table_name = selected_table if selected_table in ADMIN_TABLE_SCHEMAS else "workspaces"
    sort_column, sort_direction = admin_sort_params(
        table_name, sort_column, sort_direction
    )
    counts = await db_admin_table_counts(env)
    rows = await db_admin_rows_sorted(env, table_name, sort_column, sort_direction)
    edit_row = await db_admin_get_row(env, table_name, edit_pk) if edit_pk else None
    confirm_delete_row = (
        await db_admin_get_row(env, table_name, confirm_delete_pk)
        if confirm_delete_pk
        else None
    )
    confirm_related = (
        await db_admin_related_tree(env, table_name, confirm_delete_row)
        if confirm_delete_row
        else []
    )
    return {
        "tables": list(ADMIN_TABLE_SCHEMAS.keys()),
        "counts": counts,
        "selected_table": table_name,
        "schema": admin_table_schema(table_name),
        "rows": rows,
        "edit_row": edit_row,
        "edit_pk": edit_pk,
        "add_row": bool(add_row),
        "confirm_delete_pk": confirm_delete_pk,
        "confirm_delete_row": confirm_delete_row,
        "confirm_related": confirm_related,
        "sort_column": sort_column,
        "sort_direction": sort_direction,
    }


async def db_admin_create_row(
    env: Any, table_name: str, form: Dict[str, str]
) -> None:
    table_name = require_admin_table_name(table_name)
    schema = admin_table_schema(table_name)
    fields = []
    values = []
    for column_name, column_type in admin_editable_columns(schema):
        if schema.get("auto_pk") and column_name == schema["pk"]:
            continue
        fields.append(column_name)
        values.append(admin_form_value(form, column_name, column_type))
    placeholders = ", ".join("?" for _ in fields)
    await d1_run(
        env,
        "INSERT INTO {0} ({1}) VALUES ({2})".format(
            table_name, ", ".join(fields), placeholders
        ),
        values,
    )


async def db_admin_update_row(
    env: Any, table_name: str, pk_value: str, form: Dict[str, str]
) -> None:
    table_name = require_admin_table_name(table_name)
    schema = admin_table_schema(table_name)
    pk = schema["pk"]
    fields = []
    values = []
    for column_name, column_type in schema["columns"]:
        if column_name == pk:
            continue
        fields.append("{0} = ?".format(column_name))
        values.append(admin_form_value(form, column_name, column_type))
    values.append(pk_value)
    await d1_run(
        env,
        "UPDATE {0} SET {1} WHERE {2} = ?".format(
            table_name, ", ".join(fields), pk
        ),
        values,
    )


async def db_admin_delete_row(env: Any, table_name: str, pk_value: str) -> None:
    table_name = require_admin_table_name(table_name)
    schema = admin_table_schema(table_name)
    await d1_run(
        env,
        "DELETE FROM {0} WHERE {1} = ?".format(table_name, schema["pk"]),
        [pk_value],
    )


async def db_admin_delete_row_cascade(
    env: Any,
    table_name: str,
    pk_value: str,
    visited: Optional[set] = None,
) -> None:
    table_name = require_admin_table_name(table_name)
    schema = admin_table_schema(table_name)
    row = await db_admin_get_row(env, table_name, pk_value)
    if not row:
        return
    visited = visited or set()
    row_key = (table_name, str(pk_value))
    if row_key in visited:
        return
    visited.add(row_key)
    for relationship in admin_cascade_relationships_for(table_name):
        parent_value = row.get(relationship["parent_column"])
        if parent_value in (None, ""):
            continue
        child_table = relationship["child_table"]
        child_schema = admin_table_schema(child_table)
        if relationship["action"] == "null":
            await d1_run(
                env,
                "UPDATE {0} SET {1} = NULL WHERE {1} = ?".format(
                    child_table, relationship["child_column"]
                ),
                [parent_value],
            )
            continue
        child_rows = result_rows(
            await d1_run(
                env,
                "SELECT * FROM {0} WHERE {1} = ? ORDER BY {2} DESC".format(
                    child_table,
                    relationship["child_column"],
                    child_schema["pk"],
                ),
                [parent_value],
            )
        )
        for child_row in child_rows:
            child_pk = child_row.get(child_schema["pk"])
            if child_pk is not None:
                await db_admin_delete_row_cascade(
                    env, child_table, str(child_pk), visited
                )
    await db_admin_delete_row(env, table_name, pk_value)
    visited.discard(row_key)


def render_admin_db_field(
    column_name: str,
    column_type: str,
    value: Any = "",
    required: bool = False,
) -> str:
    text = str(value if value is not None else "")
    label = html_escape(column_name)
    required_attr = " required" if required else ""
    if len(text) > 80 or column_name.endswith("_json") or column_name in (
        "request_data",
        "manifest_yaml",
        "message_text",
        "metadata_json",
    ):
        return (
            '<div><label class="block text-xs font-semibold mb-1">{0}</label>'
            '<textarea name="field__{1}" class="w-full border border-gray-300 rounded px-2 py-1 font-mono text-xs" rows="4"{2}>{3}</textarea></div>'
        ).format(label, html_escape(column_name), required_attr, html_escape(text))
    input_type = "number" if column_type == "INTEGER" else "text"
    return (
        '<div><label class="block text-xs font-semibold mb-1">{0}</label>'
        '<input name="field__{1}" type="{2}" value="{3}" class="w-full border border-gray-300 rounded px-2 py-1 font-mono text-xs"{4} /></div>'
    ).format(label, html_escape(column_name), input_type, html_escape(text), required_attr)


def render_admin_cascade_tree(groups: List[Dict[str, Any]], depth: int = 0) -> str:
    if not groups:
        return (
            '<div class="rounded border border-dashed border-gray-200 p-3 text-sm text-gray-500">'
            "No related records were found."
            "</div>"
        )
    html_parts = []
    indent_class = "ml-4" if depth else ""
    for group in groups:
        relationship = group["relationship"]
        action_label = "will be deleted"
        if relationship["action"] == "null":
            action_label = "will be detached"
        rows = group.get("rows") or []
        html_parts.append(
            '<div class="{0} rounded border border-gray-200 p-3">'
            '<div class="mb-2 flex items-center justify-between gap-3">'
            '<span class="text-sm font-bold">{1}</span>'
            '<span class="text-xs text-gray-500">{2} {3}</span>'
            '</div>'.format(
                indent_class,
                html_escape(relationship["child_table"]),
                int(group.get("count") or 0),
                html_escape(action_label),
            )
        )
        if rows:
            html_parts.append('<div class="space-y-2">')
            for child in rows:
                child_table = child["table"]
                child_row = child["row"]
                html_parts.append(
                    '<div class="rounded bg-gray-50 p-2">'
                    '<div class="font-mono text-xs text-gray-700">{0}</div>'
                    '{1}'
                    '</div>'.format(
                        html_escape(admin_row_summary(child_table, child_row)),
                        render_admin_cascade_tree(child.get("children") or [], depth + 1)
                        if child.get("children")
                        else "",
                    )
                )
            html_parts.append("</div>")
        else:
            html_parts.append('<div class="text-sm text-gray-400">No matching rows.</div>')
        html_parts.append("</div>")
    return "\n".join(html_parts)


def render_admin_delete_confirm_html(context: Dict[str, Any], admin_url: str) -> str:
    table_name = context["selected_table"]
    schema = context["schema"]
    row = context.get("confirm_delete_row") or {}
    pk_value = str(context.get("confirm_delete_pk") or admin_row_pk_value(table_name, row))
    related = context.get("confirm_related") or []
    related_count = admin_cascade_count(related)
    return """
    <div class="min-w-0 border border-red-200 bg-red-50 rounded-lg p-4 space-y-4">
      <div>
        <h3 class="font-bold text-red-800">Confirm delete</h3>
        <p class="mt-1 text-sm text-red-700">Deleting {identity} will also affect {related_count} related records.</p>
      </div>
      <div class="rounded bg-white p-3">
        <div class="text-xs font-bold uppercase tracking-wide text-gray-500">Selected record</div>
        <div class="mt-1 font-mono text-xs text-gray-800">{summary}</div>
      </div>
      <div class="space-y-3">
        <div class="text-xs font-bold uppercase tracking-wide text-gray-500">Related data</div>
        {related_tree}
      </div>
      <form method="post" action="{admin_url}" class="grid gap-2 sm:grid-cols-2">
        <input type="hidden" name="action" value="db_delete_confirmed" />
        <input type="hidden" name="table" value="{table_name}" />
        <input type="hidden" name="pk" value="{pk_value}" />
        <button class="w-full px-4 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700" type="submit">Delete selected and related records</button>
        <a href="{admin_url}?table={table_name}&edit={pk_value}" class="w-full px-4 py-2 border border-gray-300 bg-white text-center text-gray-700 rounded-lg font-semibold hover:border-gray-400">Cancel</a>
      </form>
    </div>
    """.format(
        admin_url=html_escape(admin_url),
        table_name=html_escape(table_name),
        pk_value=html_escape(pk_value),
        identity=html_escape(admin_row_identity(table_name, schema, pk_value)),
        summary=html_escape(admin_row_summary(table_name, row)),
        related_count=related_count,
        related_tree=render_admin_cascade_tree(related),
    )


def render_admin_breadcrumbs(context: Dict[str, Any], admin_url: str) -> str:
    table_name = context["selected_table"]
    crumbs = [
        '<a class="text-gray-500 hover:text-red-600" href="{0}">Admin</a>'.format(
            html_escape(admin_url)
        ),
        '<a class="text-gray-500 hover:text-red-600" href="{0}?table={1}">{1}</a>'.format(
            html_escape(admin_url), html_escape(table_name)
        ),
    ]
    if context.get("add_row"):
        crumbs.append('<span class="text-gray-900">Add</span>')
    elif context.get("edit_row"):
        crumbs.append(
            '<span class="text-gray-900">Edit {0}</span>'.format(
                html_escape(context.get("edit_pk") or "")
            )
        )
    elif context.get("confirm_delete_row"):
        crumbs.append(
            '<span class="text-gray-900">Delete {0}</span>'.format(
                html_escape(context.get("confirm_delete_pk") or "")
            )
        )
    else:
        crumbs.append('<span class="text-gray-900">Rows</span>')
    return '<nav class="mb-4 flex flex-wrap items-center gap-2 text-sm">{0}</nav>'.format(
        '<span class="text-gray-300">/</span>'.join(crumbs)
    )


def render_admin_table_links(context: Dict[str, Any], admin_url: str) -> str:
    selected_table = context["selected_table"]
    links = []
    for table_name in context["tables"]:
        active = (
            " border-red-600 bg-red-50 text-red-700"
            if table_name == selected_table
            else " border-gray-200 bg-white text-gray-700 hover:border-gray-300"
        )
        links.append(
            '<a class="flex items-center justify-between gap-3 border rounded px-3 py-2 text-xs font-semibold{0}" href="{1}?table={2}"><span class="truncate">{2}</span><span class="text-[10px] opacity-70">{3}</span></a>'.format(
                active,
                html_escape(admin_url),
                html_escape(table_name),
                html_escape(context["counts"].get(table_name, "?")),
            )
        )
    return "\n".join(links)


def render_admin_row_table(context: Dict[str, Any], admin_url: str) -> str:
    selected_table = context["selected_table"]
    schema = context["schema"]
    sort_column = context.get("sort_column") or schema["pk"]
    sort_direction = context.get("sort_direction") or "DESC"
    header_cells = []
    for column_name, _ in schema["columns"]:
        next_direction = "desc" if column_name == sort_column and sort_direction == "ASC" else "asc"
        marker = ""
        if column_name == sort_column:
            marker = " ▲" if sort_direction == "ASC" else " ▼"
        header_cells.append(
            '<th class="sticky top-0 z-10 border-b border-gray-200 bg-gray-50 px-3 py-2 text-left text-xs font-bold text-gray-600">'
            '<a class="whitespace-nowrap hover:text-red-600" href="{0}?table={1}&sort={2}&direction={3}">{2}{4}</a></th>'.format(
                html_escape(admin_url),
                html_escape(selected_table),
                html_escape(column_name),
                next_direction,
                marker,
            )
        )
    header_cells.append(
        '<th class="sticky top-0 z-10 border-b border-gray-200 bg-gray-50 px-3 py-2 text-right text-xs font-bold text-gray-600">Actions</th>'
    )
    rows = []
    pk = schema["pk"]
    for row in context["rows"]:
        pk_value = str(row.get(pk) if row.get(pk) is not None else "")
        cells = []
        for column_name, _ in schema["columns"]:
            cells.append(
                '<td class="border-b border-gray-100 px-3 py-2 align-top font-mono text-xs text-gray-800"><div class="max-w-[28rem] whitespace-pre-wrap break-words">{0}</div></td>'.format(
                    html_escape(str(row.get(column_name) if row.get(column_name) is not None else ""))
                )
            )
        cells.append(
            '<td class="border-b border-gray-100 px-3 py-2 text-right align-top whitespace-nowrap">'
            '<a class="font-semibold text-red-600 hover:text-red-700" href="{0}?table={1}&edit={2}">Edit</a>'
            '<a class="ml-3 font-semibold text-gray-500 hover:text-red-700" href="{0}?table={1}&confirm_delete={2}">Delete</a>'
            "</td>".format(
                html_escape(admin_url),
                html_escape(selected_table),
                html_escape(pk_value),
            )
        )
        rows.append('<tr class="hover:bg-red-50/40">{0}</tr>'.format("".join(cells)))
    if not rows:
        rows.append(
            '<tr><td colspan="{0}" class="px-3 py-10 text-center text-sm text-gray-400">No rows found.</td></tr>'.format(
                len(schema["columns"]) + 1
            )
        )
    return """
    <div class="overflow-auto rounded border border-gray-200 max-h-[calc(100vh-250px)]">
      <table class="min-w-full border-collapse text-sm">
        <thead><tr>{headers}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """.format(headers="".join(header_cells), rows="\n".join(rows))


def render_admin_form_page(context: Dict[str, Any], admin_url: str) -> str:
    selected_table = context["selected_table"]
    schema = context["schema"]
    pk = schema["pk"]
    edit_row = context.get("edit_row")
    editing = bool(edit_row)
    form_action = "db_update" if editing else "db_create"
    form_title = "Edit {0}".format(selected_table) if editing else "Add {0}".format(selected_table)
    form_fields = []
    for column_name, column_type in admin_editable_columns(schema):
        value = (edit_row or {}).get(column_name, "")
        required = bool(column_name == pk and not schema.get("auto_pk"))
        form_fields.append(render_admin_db_field(column_name, column_type, value, required))
    hidden_pk = ""
    if editing:
        hidden_pk = '<input type="hidden" name="pk" value="{0}" />'.format(
            html_escape(str((edit_row or {}).get(pk) or context.get("edit_pk") or ""))
        )
    delete_link = ""
    if editing:
        delete_link = (
            '<a class="px-4 py-2 border border-gray-300 text-center text-gray-700 rounded-lg font-semibold hover:border-red-300 hover:text-red-700" '
            'href="{0}?table={1}&confirm_delete={2}">Delete Row</a>'.format(
                html_escape(admin_url),
                html_escape(selected_table),
                html_escape(str((edit_row or {}).get(pk) or context.get("edit_pk") or "")),
            )
        )
    return """
    <section class="rounded-lg bg-white p-6 shadow">
      <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 class="text-xl font-bold">{form_title}</h2>
        <a class="text-sm font-semibold text-gray-500 hover:text-red-600" href="{admin_url}?table={selected_table}">Back to table</a>
      </div>
      <form method="post" action="{admin_url}" class="space-y-4">
        <input type="hidden" name="action" value="{form_action}" />
        <input type="hidden" name="table" value="{selected_table}" />
        {hidden_pk}
        <div class="grid gap-4 lg:grid-cols-2">{form_fields}</div>
        <div class="flex flex-col gap-2 sm:flex-row">
          <button class="px-4 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700" type="submit">{button_text}</button>
          {delete_link}
        </div>
      </form>
    </section>
    """.format(
        admin_url=html_escape(admin_url),
        selected_table=html_escape(selected_table),
        form_title=html_escape(form_title),
        form_action=form_action,
        hidden_pk=hidden_pk,
        form_fields="\n".join(form_fields),
        button_text="Save Changes" if editing else "Create Row",
        delete_link=delete_link,
    )


def render_database_admin_html(context: Dict[str, Any], admin_url: str) -> str:
    selected_table = context["selected_table"]
    if context.get("confirm_delete_row"):
        main_content = render_admin_delete_confirm_html(context, admin_url)
    elif context.get("add_row") or context.get("edit_row"):
        main_content = render_admin_form_page(context, admin_url)
    else:
        main_content = """
        <section class="rounded-lg bg-white p-6 shadow">
          <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 class="text-xl font-bold">{selected_table}</h2>
              <p class="text-sm text-gray-500">Full table data. Click a column heading to sort.</p>
            </div>
            <a href="{admin_url}?table={selected_table}&add=1" class="inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"><i class="fas fa-plus"></i>Add row</a>
          </div>
          {table}
        </section>
        """.format(
            admin_url=html_escape(admin_url),
            selected_table=html_escape(selected_table),
            table=render_admin_row_table(context, admin_url),
        )
    return """
    {breadcrumbs}
    <div class="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
      <nav aria-label="Database tables" class="space-y-2">
        <h3 class="text-xs font-bold uppercase tracking-wide text-gray-500">Tables</h3>
        <div class="space-y-2">{table_links}</div>
      </nav>
      <div class="min-w-0">{main_content}</div>
    </div>
    """.format(
        breadcrumbs=render_admin_breadcrumbs(context, admin_url),
        table_links=render_admin_table_links(context, admin_url),
        main_content=main_content,
    )


def render_admin_html(
    env: Any,
    workspaces: List[Dict[str, Any]],
    servers: List[Dict[str, Any]],
    database_context: Optional[Dict[str, Any]] = None,
    message: str = "",
    admin_mode: str = "",
    edit_workspace_team_id: str = "",
    edit_server_id: str = "",
) -> str:
    admin_url = admin_path(env)
    alert = ""
    if message:
        alert = (
            '<div class="mb-6 rounded border border-green-200 bg-green-50 px-4 py-3 text-green-700">'
            + html_escape(message)
            + "</div>"
        )
    database_admin_html = (
        render_database_admin_html(database_context, admin_url)
        if database_context
        else ""
    )

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT-Sammich Admin</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
</head>
<body class="bg-gray-50 text-gray-900">
  <main class="w-full px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
      <div>
        <h1 class="text-3xl font-bold">BLT-Sammich Database Admin</h1>
        <p class="text-gray-500 text-sm">Browse, edit, create, and delete database records.</p>
      </div>
      <a href="/" class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-semibold hover:bg-gray-50"><i class="fas fa-home"></i>Homepage</a>
    </div>
    {alert}
    {database_admin_html}
  </main>
</body>
</html>""".format(
        alert=alert,
        admin_url=html_escape(admin_url),
        database_admin_html=database_admin_html,
    )


async def handle_admin_get(request: Any, env: Any) -> Any:
    if not is_admin_request(request, env):
        return basic_auth_response()
    parsed_url = urlparse(request.url)
    params = parse_qs(parsed_url.query)
    message = params.get("message", [""])[0]
    selected_table = params.get("table", ["workspaces"])[0]
    edit_pk = params.get("edit", [""])[0]
    add_db_row = params.get("add", [""])[0] == "1"
    confirm_delete_pk = params.get("confirm_delete", [""])[0]
    sort_column = params.get("sort", [""])[0]
    sort_direction = params.get("direction", [""])[0]
    try:
        return html_response(
            render_admin_html(
                env,
                [],
                [],
                database_context=await db_admin_context(
                    env,
                    selected_table,
                    edit_pk,
                    add_db_row,
                    confirm_delete_pk,
                    sort_column,
                    sort_direction,
                ),
                message=message,
            )
        )
    except Exception as error:
        log_exception_one_line(
            error,
            "admin_get_failed",
            {"table": selected_table, "edit": edit_pk, "add": add_db_row},
        )
        return html_response(
            "<h1>Admin error</h1><p>{0}</p>".format(html_escape(str(error))),
            status=500,
        )


async def handle_admin_form_action(env: Any, form: Dict[str, str]) -> Any:
    action = form.get("action", "")
    if action in ("db_create", "db_update", "db_delete"):
        table_name = form.get("table", "")
        if table_name not in ADMIN_TABLE_SCHEMAS:
            return admin_redirect(env, "Unknown database table")
        if action == "db_create":
            await db_admin_create_row(env, table_name, form)
            return admin_redirect(env, "Row created", table_name)
        if action == "db_update":
            await db_admin_update_row(env, table_name, form.get("pk", ""), form)
            return admin_redirect(env, "Row updated", table_name)
        return redirect_response(
            admin_path(env)
            + "?"
            + urlencode({"table": table_name, "confirm_delete": form.get("pk", "")})
        )
    if action == "db_delete_confirmed":
        table_name = form.get("table", "")
        if table_name not in ADMIN_TABLE_SCHEMAS:
            return admin_redirect(env, "Unknown database table")
        await db_admin_delete_row_cascade(env, table_name, form.get("pk", ""))
        return admin_redirect(env, "Row deleted", table_name)
    return redirect_response(admin_path(env) + "?message=No+changes+made")


async def handle_admin_post(request: Any, env: Any) -> Any:
    if not is_admin_request(request, env):
        return basic_auth_response()
    body_text = str(await request.text())
    form = parse_form_encoded(body_text)
    try:
        return await handle_admin_form_action(env, form)
    except Exception as error:
        table_name = form.get("table", "")
        extra = {
            "action": form.get("action", ""),
            "table": table_name,
            "pk": form.get("pk", ""),
        }
        log_exception_one_line(error, "admin_post_failed", extra)
        if table_name in ADMIN_TABLE_SCHEMAS:
            return admin_redirect(env, "Error: {0}".format(str(error)), table_name)
        return redirect_response(
            admin_path(env) + "?" + urlencode({"message": "Error: {0}".format(str(error))})
        )


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
    await db_upsert_slack_app(
        env,
        app_id=str(payload.get("app_id") or ""),
        client_id=env_value(env, "SLACK_CLIENT_ID", "") or "",
        client_secret=env_value(env, "SLACK_CLIENT_SECRET", "") or "",
        signing_secret=env_value(env, "SLACK_SIGNING_SECRET", "") or "",
        app_token=env_value(env, "SLACK_APP_TOKEN", "") or "",
    )
    await db_upsert_workspace(
        env,
        team_id=str(payload.get("team", {}).get("id") or ""),
        team_name=str(team_name),
        access_token=str(payload.get("access_token") or ""),
        bot_token=str(payload.get("access_token") or ""),
        bot_user_id=str(payload.get("bot_user_id") or ""),
        app_id=str(payload.get("app_id") or ""),
        installer_slack_user_id=str(payload.get("authed_user", {}).get("id") or ""),
    )
    await upsert_connected_workspace(
        env,
        str(payload.get("team", {}).get("id") or ""),
        str(team_name),
        installer_user_id=str(payload.get("authed_user", {}).get("id") or ""),
        bot_user_id=str(payload.get("bot_user_id") or ""),
        status="connected",
    )
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
    normalized_path = path.rstrip("/") or "/"
    method = str(request.method).upper()
    configured_admin_path = admin_path(env)

    if method == "GET" and normalized_path == "/health":
        return json_response({"ok": True, "service": "blt-sammich-worker"})

    if method == "GET" and normalized_path == "/api/workspaces-public":
        return json_response(await public_connections_payload(env))

    if normalized_path == configured_admin_path and method == "GET":
        return await handle_admin_get(request, env)

    if normalized_path == configured_admin_path and method == "POST":
        return await handle_admin_post(request, env)

    if method == "GET" and normalized_path == "/oauth/slack/callback":
        return await handle_oauth_callback(parsed_url, env)

    if method == "GET" and normalized_path == "/install-slack":
        try:
            install_url = build_slack_install_url(env)
        except ValueError as error:
            log_exception_one_line(
                error,
                "install_slack_misconfigured",
                {"path": path},
            )
            return html_response(
                "<h1>Install URL misconfigured</h1><p>{0}</p>".format(str(error)),
                status=500,
            )
        return build_response(
            "",
            status=302,
            headers={"location": install_url},
        )

    if method == "GET" and normalized_path in ("/slack/events", "/slack/commands"):
        endpoint_name = (
            "slack_events"
            if normalized_path == "/slack/events"
            else "slack_commands"
        )
        return json_response(
            {
                "ok": True,
                "endpoint": endpoint_name,
                "method": "POST required",
            }
        )

    if method == "POST" and normalized_path in ("/slack/commands", "/slack/events"):
        body_text = str(await request.text())
        content_type = request.headers.get("content-type", "")
        parsed_events_payload: Dict[str, Any] = {}

        if normalized_path == "/slack/events":
            if "application/x-www-form-urlencoded" in content_type:
                form = parse_form_encoded(body_text)
                if form.get("payload"):
                    try:
                        parsed_events_payload = json.loads(form["payload"])
                    except json.JSONDecodeError:
                        parsed_events_payload = {
                            "type": "unparseable_interaction",
                            "raw_body": body_text,
                        }
                    await record_activity(env, "interaction", parsed_events_payload)
            else:
                try:
                    parsed_events_payload = json.loads(body_text or "{}")
                except json.JSONDecodeError:
                    parsed_events_payload = {
                        "type": "unparseable_event",
                        "raw_body": body_text,
                    }
                await record_activity(env, "event", parsed_events_payload)

            # Slack URL verification can be sent before signing secret wiring is complete.
            if parsed_events_payload.get("type") == "url_verification":
                return json_response(
                    {"challenge": parsed_events_payload.get("challenge", "")}
                )

        signing_secret = env_value(env, "SLACK_SIGNING_SECRET", "") or ""
        secret_app_id = ""
        if normalized_path == "/slack/events":
            secret_app_id = payload_app_id(parsed_events_payload)
        elif "application/x-www-form-urlencoded" in content_type:
            signature_form = parse_form_encoded(body_text)
            secret_app_id = payload_app_id(signature_form)
        try:
            db_signing_secret = await db_get_slack_app_signing_secret(
                env,
                app_id=secret_app_id,
            )
        except Exception as error:
            log_exception_one_line(
                error,
                "slack_signing_secret_lookup_failed",
                {
                    "app_id": secret_app_id,
                },
            )
            db_signing_secret = ""
        if db_signing_secret:
            signing_secret = db_signing_secret
        timestamp = request.headers.get("x-slack-request-timestamp", "")
        signature = request.headers.get("x-slack-signature", "")
        if not verify_slack_signature(signing_secret, timestamp, body_text, signature):
            return build_response("Invalid Slack signature.", status=401)

        if "application/x-www-form-urlencoded" in content_type:
            form = parse_form_encoded(body_text)
            if normalized_path == "/slack/events" and form.get("payload"):
                payload = parsed_events_payload or json.loads(form["payload"])
                return json_response(interaction_response(payload))

            await record_activity(env, "slash_command", form)
            command_name = form.get("command", "")
            log_json_event(
                "slash_command_received",
                {
                    "command": command_name,
                    "team_id": form.get("team_id", ""),
                    "user_id": form.get("user_id", ""),
                    "channel_id": form.get("channel_id", ""),
                    "supported": command_name in SUPPORTED_SLACK_COMMANDS,
                },
            )
            response_payload = await command_response(form, env)
            log_json_event(
                "slash_command_responded",
                {
                    "command": command_name,
                    "team_id": form.get("team_id", ""),
                    "response_type": response_payload.get("response_type", ""),
                    "text": str(response_payload.get("text", ""))[:160],
                },
            )
            return json_response(response_payload)

        payload = (
            parsed_events_payload
            if normalized_path == "/slack/events"
            else json.loads(body_text or "{}")
        )
        if normalized_path != "/slack/events":
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
        try:
            return await handle_request(request, self.env)
        except Exception as error:
            log_exception_one_line(error, "unhandled_fetch_exception")
            return build_response("Internal Server Error", status=500)
