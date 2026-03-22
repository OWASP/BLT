"""HTML template rendering for BLT-Lettuce."""

import json
from pathlib import Path

_TEMPLATE_CACHE = {}
_TEMPLATES_DIR = Path(__file__).with_name("templates")


def _load_template(template_name):
    """Load and cache a template file by name."""
    if template_name not in _TEMPLATE_CACHE:
        template_path = _TEMPLATES_DIR / template_name
        _TEMPLATE_CACHE[template_name] = template_path.read_text(encoding="utf-8")
    return _TEMPLATE_CACHE[template_name]


def _render_template(template_name, replacements):
    """Render a template by replacing {{ token }} placeholders with values."""
    rendered = _load_template(template_name)
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))
    return rendered


def html_escape(text):
    """Escape HTML special characters to prevent XSS."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def get_homepage_html(user=None):
    """Generate the homepage HTML."""
    auth_button_href = "/workspace/add"
    auth_button_text = "Connect Workspace"

    return _render_template(
        "homepage.html",
        {
            "AUTH_BUTTON_HREF": auth_button_href,
            "AUTH_BUTTON_TEXT": auth_button_text,
        },
    )


def _status_item(name, description, value, required):
    """Render one environment variable status row for the status page."""
    raw_value = str(value or "").strip()
    is_set = bool(raw_value)

    if is_set:
        status_chip = '<span class="inline-flex items-center gap-1 rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-semibold"><i class="fas fa-check"></i> Set</span>'
        preview = f'<code class="text-xs text-gray-500">{html_escape(raw_value[:12])}...</code>'
        card_class = "status-item set border-green-200"
    else:
        level = "Required" if required else "Optional"
        status_chip = (
            '<span class="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-semibold">'
            f'<i class="fas fa-triangle-exclamation"></i> Missing ({level})'
            "</span>"
        )
        preview = '<span class="text-xs text-gray-400">Not configured</span>'
        card_class = "status-item missing border-red-200"

    return (
        f'<div class="{card_class} border rounded-lg p-3">'
        '<div class="flex items-start justify-between gap-3">'
        "<div>"
        f'<p class="text-sm font-semibold text-gray-800">{html_escape(name)}</p>'
        f'<p class="text-xs text-gray-500">{html_escape(description)}</p>'
        "</div>"
        f"{status_chip}"
        "</div>"
        f'<div class="mt-2">{preview}</div>'
        "</div>"
    )


def get_status_html(env):
    """Generate HTML status page with environment configuration checks."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    signing_secret = getattr(env, "SIGNING_SECRET", None)
    slack_client_id = getattr(env, "SLACK_CLIENT_ID", None)
    slack_client_secret = getattr(env, "SLACK_CLIENT_SECRET", None)
    sentry_dsn = getattr(env, "SENTRY_DSN", None)
    base_url = getattr(env, "BASE_URL", None)
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", None)
    contribute_id = getattr(env, "CONTRIBUTE_ID", None)

    replacements = {
        "SLACK_TOKEN_STATUS": _status_item(
            "SLACK_TOKEN",
            "Slack Bot User OAuth Token (xoxb-...) for API calls",
            slack_token,
            required=True,
        ),
        "SIGNING_SECRET_STATUS": _status_item(
            "SIGNING_SECRET",
            "Slack App Signing Secret for webhook verification",
            signing_secret,
            required=True,
        ),
        "SLACK_CLIENT_ID_STATUS": _status_item(
            "SLACK_CLIENT_ID",
            "Slack OAuth App Client ID for user authentication",
            slack_client_id,
            required=True,
        ),
        "SLACK_CLIENT_SECRET_STATUS": _status_item(
            "SLACK_CLIENT_SECRET",
            "Slack OAuth App Client Secret for token exchange",
            slack_client_secret,
            required=True,
        ),
        "SENTRY_DSN_STATUS": _status_item(
            "SENTRY_DSN",
            "Sentry Data Source Name for error tracking",
            sentry_dsn,
            required=False,
        ),
        "BASE_URL_STATUS": _status_item(
            "BASE_URL",
            "Base URL for OAuth redirects (e.g., https://lettuce.owaspblt.org)",
            base_url,
            required=False,
        ),
        "JOINS_CHANNEL_ID_STATUS": _status_item(
            "JOINS_CHANNEL_ID",
            "Channel ID where join notifications are posted",
            joins_channel,
            required=False,
        ),
        "CONTRIBUTE_ID_STATUS": _status_item(
            "CONTRIBUTE_ID",
            "Channel ID for contribution guidelines",
            contribute_id,
            required=False,
        ),
    }

    return _render_template("status.html", replacements)


def get_404_html():
    """Generate the 404 not found HTML page."""
    return _load_template("404.html")


def get_500_html():
    """Generate the 500 internal server error HTML page."""
    return _load_template("500.html")


def get_privacy_html():
    """Generate the privacy policy HTML page."""
    return _load_template("privacy.html")


def get_terms_html():
    """Generate the terms of service HTML page."""
    return _load_template("terms.html")


def get_sub_processors_html():
    """Generate the sub-processors information HTML page."""
    return _load_template("sub-processors.html")


# ---------------------------------------------------------------------------
# Dashboard helpers
# ---------------------------------------------------------------------------


def _build_user_avatar(user):
    """Return an <img> or initials <div> for the logged-in user."""
    avatar_url = (user or {}).get("avatar_url") or ""
    if avatar_url:
        return (
            f'<img src="{html_escape(avatar_url)}" '
            'class="w-8 h-8 rounded-full flex-shrink-0" alt="avatar"/>'
        )
    initials = ((user or {}).get("name") or "?")[:1].upper()
    return (
        f'<div class="w-8 h-8 rounded-full bg-red-100 text-red-700 '
        'flex items-center justify-center text-sm font-bold flex-shrink-0">'
        f"{html_escape(initials)}</div>"
    )


def _build_ws_tabs(workspaces, selected_id):
    """Build sidebar workspace links pointing to /ws/<id>."""
    tabs = []
    for ws in workspaces:
        ws_id = ws.get("id")
        name = html_escape(ws.get("team_name") or "Workspace")
        icon_url = ws.get("icon_url") or ""
        is_active = ws_id == selected_id
        active_cls = (
            "bg-red-50 text-red-700 font-semibold border-l-2 border-red-500 pl-2"
            if is_active
            else "text-gray-600 hover:bg-gray-50"
        )
        icon_html = (
            f'<img src="{html_escape(icon_url)}" class="w-5 h-5 rounded flex-shrink-0" alt=""/>'
            if icon_url
            else '<span class="w-5 h-5 rounded bg-gray-200 flex-shrink-0 inline-block"></span>'
        )
        tabs.append(
            f'<a href="/ws/{ws_id}" '
            f'class="flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm {active_cls}">'
            f'{icon_html}<span class="truncate">{name}</span>'
            f"</a>"
        )
    if not tabs:
        tabs = [
            '<p class="text-xs text-gray-400 px-3 py-2">'
            "No workspaces yet.<br/>Add one using the buttons below."
            "</p>"
        ]
    return "\n".join(tabs)


def _build_events_html(events):
    """Build HTML <tr> rows for the recent-activities table."""
    if not events:
        return (
            '<tr><td colspan="7" class="py-6 text-center text-sm text-gray-400">'
            "No recent activity recorded yet.</td></tr>"
        )
    rows = []
    for e in events:
        etype = html_escape(e.get("event_type") or "\u2014")
        user = html_escape(e.get("user_slack_id") or e.get("user_name") or "\u2014")
        channel = html_escape(e.get("channel_name") or "\u2014")
        status = e.get("status") or "\u2014"
        status_cls = "text-green-600" if status == "success" else "text-red-500"
        req = html_escape((e.get("request_data") or "")[:60])
        verified = "\u2713" if e.get("verified") else "\u2014"
        ts = e.get("created_at") or "\u2014"
        rows.append(
            f'<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-2 px-4 text-xs font-mono text-gray-800">{etype}</td>'
            f'<td class="py-2 px-4 text-xs text-gray-600">{user}</td>'
            f'<td class="py-2 px-4 text-xs text-gray-600">{channel}</td>'
            f'<td class="py-2 px-4 text-xs {status_cls}">{html_escape(status)}</td>'
            f'<td class="py-2 px-4 text-xs text-gray-500 max-w-xs truncate">{req}</td>'
            f'<td class="py-2 px-4 text-xs text-gray-400">{verified}</td>'
            f'<td class="py-2 px-4 text-xs text-gray-400 timeago"'
            f' data-timestamp="{html_escape(ts)}">{html_escape(ts)}</td>'
            f"</tr>"
        )
    return "\n".join(rows)


def _build_chart_data(daily_data):
    """Return (labels_json, joins_json, commands_json) for the 30-day chart."""
    dates = {}
    for row in daily_data or []:
        d = row.get("date") or ""
        etype = row.get("event_type") or ""
        count = int(row.get("count") or 0)
        if d not in dates:
            dates[d] = {"joins": 0, "commands": 0}
        if etype == "Team_Join":
            dates[d]["joins"] += count
        elif etype == "Command":
            dates[d]["commands"] += count
    sorted_dates = sorted(dates.keys())
    return (
        json.dumps(sorted_dates),
        json.dumps([dates[d]["joins"] for d in sorted_dates]),
        json.dumps([dates[d]["commands"] for d in sorted_dates]),
    )


def get_dashboard_html(user, workspaces, selected_ws, ws_stats, events, daily_data):
    """Render the authenticated dashboard page."""
    user = user or {}
    workspaces = workspaces or []

    user_name = html_escape(user.get("name") or user.get("slack_user_id") or "User")
    user_slack_id = html_escape(user.get("slack_user_id") or "")
    user_avatar = _build_user_avatar(user)

    ws_count = len(workspaces)
    ws_summary = f"{ws_count} workspace{'s' if ws_count != 1 else ''} connected"
    selected_id = (selected_ws or {}).get("id")
    ws_tabs = _build_ws_tabs(workspaces, selected_id)

    if selected_id:
        delete_btn = (
            f'<div class="mt-2">'
            f'<button onclick="deleteWorkspace({selected_id})"'
            f' class="inline-flex w-full justify-center items-center gap-2 px-3 py-2'
            f" bg-white text-red-600 border border-red-200 rounded-lg"
            f' hover:bg-red-50 transition-colors text-sm font-medium">'
            f'<i class="fas fa-trash-can"></i> Delete Workspace'
            f"</button></div>"
        )
    else:
        delete_btn = ""

    if selected_ws and selected_id:
        ws_name = html_escape(selected_ws.get("team_name") or "Workspace")
        app_id = selected_ws.get("app_id") or ""
        app_edit_url = (
            f"https://api.slack.com/apps/{html_escape(app_id)}" if app_id else "#"
        )

        ws_stats = ws_stats or {}
        total = ws_stats.get("total_activities", 0)
        last24 = ws_stats.get("last_24h_activities", 0)
        success_rate = ws_stats.get("success_rate", 100.0)
        last_event_time = ws_stats.get("last_event_time") or "\u2014"
        joins = ws_stats.get("joins", 0)
        commands = ws_stats.get("commands", 0)

        scan_btn = (
            f'<button id="scan-btn" onclick="scanChannels({selected_id})"'
            f' class="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-white'
            f' border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors font-medium">'
            f'<i class="fas fa-sync-alt mr-1"></i>Scan Channels'
            f"</button>"
            f'<input type="file" id="import-history-file" accept=".csv,text/csv"'
            f' class="hidden" onchange="handleImportHistoryFile(event, {selected_id})" />'
            f'<button id="import-btn" onclick="importHistory({selected_id})"'
            f' class="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-white'
            f' border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors font-medium">'
            f'<i class="fas fa-file-csv mr-1"></i>Upload CSV'
            f"</button>"
            f'<button id="test-msg-btn" onclick="sendTestMessage({selected_id})"'
            f' class="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-white'
            f' border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors font-medium">'
            f'<i class="fas fa-paper-plane mr-1"></i>Test Message'
            f"</button>"
        )
        purge_btn = (
            f'<button id="purge-events-btn" onclick="purgeRecentActivities({selected_id})"'
            f' class="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-red-600'
            f' bg-white border border-red-200 rounded-lg hover:bg-red-50 transition-colors font-medium">'
            f'<i class="fas fa-trash"></i> Purge'
            f"</button>"
        )
        test_inactivity_btn = (
            f'<button id="test-inactivity-alert-btn" onclick="testInactivityAlert({selected_id})"'
            f' class="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-white'
            f' border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors font-medium">'
            f'<i class="fas fa-triangle-exclamation"></i> Test Alert'
            f"</button>"
        )

        events_html = _build_events_html(events)

        workspace_section = _render_template(
            "dashboard_workspace_section.html",
            {
                "WS_NAME": ws_name,
                "APP_EDIT_URL": app_edit_url,
                "SCAN_BTN": scan_btn,
                "TOTAL": total,
                "LAST24": last24,
                "SUCCESS_RATE": success_rate,
                "WS_COUNT": ws_count,
                "LAST_EVENT_TIME": html_escape(str(last_event_time)),
                "JOINS": joins,
                "COMMANDS": commands,
                "EVENTS_HTML": events_html,
                "TEST_INACTIVITY_ALERT_BTN": test_inactivity_btn,
                "PURGE_EVENTS_BTN": purge_btn,
            },
        )

        detail_link = (
            f'<div class="flex justify-end mb-2">'
            f'<a href="/ws/{selected_id}"'
            f' class="inline-flex items-center gap-1.5 text-sm text-red-600'
            f' hover:text-red-700 font-medium">'
            f'<i class="fas fa-chart-bar"></i>'
            f" View 2-Year Chart &amp; Full Detail</a>"
            f"</div>"
        )
        workspace_section = detail_link + workspace_section

        ws_id_json = json.dumps(selected_id)
    else:
        workspace_section = (
            '<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">'
            '<i class="fas fa-building text-5xl text-gray-200 mb-4"></i>'
            '<h2 class="text-xl font-semibold text-gray-700 mb-2">No Workspace Selected</h2>'
            '<p class="text-gray-500 mb-6">Connect a workspace to start tracking activity.</p>'
            '<a href="/workspace/add"'
            ' class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white'
            ' rounded-lg hover:bg-red-700 transition-colors font-medium">'
            '<i class="fas fa-plus"></i> Add Workspace</a>'
            "</div>"
        )
        ws_id_json = "null"

    labels, chart_joins, chart_commands = _build_chart_data(daily_data)

    return _render_template(
        "dashboard.html",
        {
            "USER_AVATAR": user_avatar,
            "USER_NAME": user_name,
            "USER_SLACK_ID": user_slack_id,
            "WS_SUMMARY": html_escape(ws_summary),
            "WS_TABS": ws_tabs,
            "DASHBOARD_TABS": "",
            "WORKSPACE_SECTION": workspace_section,
            "WS_ID_JSON": ws_id_json,
            "DELETE_WORKSPACE_BTN": delete_btn,
            "CHART_LABELS": labels,
            "CHART_JOINS": chart_joins,
            "CHART_COMMANDS": chart_commands,
        },
    )


def get_workspace_detail_html(workspace, user):
    """Render the workspace detail page (2-year chart + activity log)."""
    workspace = workspace or {}

    ws_id = workspace.get("id")
    ws_name = html_escape(workspace.get("team_name") or "Workspace")
    team_id = html_escape(workspace.get("team_id") or "")
    member_count = workspace.get("member_count") or 0
    channel_count = workspace.get("channel_count") or 0
    app_name = html_escape(workspace.get("app_name") or "BLT-Lettuce")

    icon_url = workspace.get("icon_url") or ""
    if icon_url:
        ws_icon_html = (
            f'<img src="{html_escape(icon_url)}" '
            'class="w-14 h-14 rounded-xl flex-shrink-0 border border-gray-100" alt="workspace icon"/>'
        )
    else:
        initials = (workspace.get("team_name") or "W")[:1].upper()
        ws_icon_html = (
            f'<div class="w-14 h-14 rounded-xl bg-red-100 text-red-600 flex items-center '
            f'justify-center text-2xl font-bold flex-shrink-0">{html_escape(initials)}</div>'
        )

    return _render_template(
        "workspace_detail.html",
        {
            "WS_ID_JSON": json.dumps(ws_id),
            "WS_NAME": ws_name,
            "TEAM_ID": team_id,
            "MEMBER_COUNT": member_count,
            "CHANNEL_COUNT": channel_count,
            "APP_NAME": app_name,
            "WS_ICON_HTML": ws_icon_html,
        },
    )
