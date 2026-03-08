"""HTML template rendering for BLT-Lettuce."""

import json
from datetime import datetime, timedelta, timezone
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
    """Render a template by replacing {{ token }} placeholders with Jinja2-style syntax."""
    rendered = _load_template(template_name)
    for key, value in replacements.items():
        # Replace {{ KEY }} with value
        rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))
    return rendered


def _js_literal(value):
    """Convert Python values to JS literals for inline script usage."""
    if value in (None, ""):
        return "null"
    return json.dumps(value)


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


def get_login_page_html(sign_in_url, error=None):
    """Generate the login page HTML for Slack OAuth."""
    err_block = (
        f'<div class="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg '
        f'text-sm text-red-700">{html_escape(error)}</div>'
        if error
        else ""
    )
    return _render_template(
        "login.html",
        {
            "ERR_BLOCK": err_block,
            "SIGN_IN_URL": html_escape(sign_in_url),
        },
    )


def get_dashboard_html(
    user,
    workspaces,
    current_ws,
    ws_stats,
    channels,
    events,
    daily_stats,
    repos,
    active_tab="overview",
):
    """Generate the dashboard HTML with workspace statistics and controls."""
    user_name = html_escape((user or {}).get("name") or "User")
    user_avatar_url = (user or {}).get("avatar_url") or ""

    # Generate avatar HTML - either image or fallback icon
    if user_avatar_url:
        user_avatar_html = f'<img src="{html_escape(user_avatar_url)}" alt="{user_name}" class="w-8 h-8 rounded-full border border-gray-200"/>'
    else:
        user_avatar_html = '<i class="fas fa-user-circle text-red-500 text-2xl"></i>'
    ws_id = (current_ws or {}).get("id", "")
    ws_name = html_escape((current_ws or {}).get("team_name", "No workspace selected"))
    ws_app_id = (current_ws or {}).get("app_id", "")
    app_edit_url = (
        f"https://api.slack.com/apps/{ws_app_id}/general"
        if ws_app_id
        else "https://api.slack.com/apps"
    )
    ws_count = len(workspaces)

    ws_tabs = ""
    for ws in workspaces:
        active = (
            "bg-red-600 text-white"
            if ws.get("id") == ws_id
            else "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50"
        )
        ws_tabs += (
            f'<a href="/dashboard?ws={ws["id"]}" '
            f'class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium {active} transition-colors">'
            f'<span class="w-2 h-2 rounded-full bg-green-400 inline-block"></span>'
            f"{html_escape(ws['team_name'])}</a>"
        )

    total = ws_stats.get("total_activities", 0)
    last24 = ws_stats.get("last_24h_activities", 0)
    success_rate = ws_stats.get("success_rate", 100.0)
    joins = ws_stats.get("joins", 0)
    commands = ws_stats.get("commands", 0)
    last_event_time = ws_stats.get("last_event_time", "")

    channels_html = ""
    for ch in channels[:10]:
        channels_html += (
            '<div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">'
            f'<span class="text-sm font-medium text-gray-800">#{html_escape(ch.get("channel_name", ""))}</span>'
            f'<span class="text-xs text-gray-400">{ch.get("member_count", 0):,} members</span>'
            "</div>"
        )
    if not channels_html:
        channels_html = '<p class="text-sm text-gray-400 text-center py-4">No channels scanned yet.</p>'

    events_html = ""
    for ev in events:
        status_dot = (
            '<span class="inline-block w-2 h-2 rounded-full bg-green-400 mr-1"></span>'
            if ev.get("status") == "success"
            else '<span class="inline-block w-2 h-2 rounded-full bg-red-400 mr-1"></span>'
        )
        raw_status = str(ev.get("status") or "")
        status_label = "Success" if raw_status == "success" else (raw_status.title() or "Unknown")
        ev_id = int(ev.get("id") or 0)
        ws_int_id = int(ev.get("workspace_id") or 0)
        ev_type = html_escape(ev.get("event_type", ""))
        user_slack_id = html_escape(ev.get("user_slack_id", "") or "-")
        ev_time = html_escape(ev.get("created_at", "") or "-")
        events_html += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{ev_id}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{ws_int_id}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-700">{ev_type}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-500 font-mono">{user_slack_id}</td>'
            f'<td class="py-3 px-4 text-sm">{status_dot}{status_label}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-500 font-mono">{ev_time}</td>'
            "</tr>"
        )
    if not events_html:
        events_html = (
            '<tr><td colspan="6" class="py-6 text-center text-sm text-gray-400">'
            "No events recorded yet.</td></tr>"
        )

    ws_id_js = _js_literal(ws_id)
    repos_html = ""
    for repo in repos:
        safe_url = html_escape(repo.get("repo_url", "#"))
        safe_name = html_escape(repo.get("repo_name") or repo.get("repo_url", ""))
        safe_lang = html_escape(repo.get("language", ""))
        stars_text = f"  * {repo.get('stars', '')}" if repo.get("stars") else ""
        repos_html += (
            '<div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-0 group">'
            "<div>"
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" '
            '   class="text-sm font-medium text-red-600 hover:underline">'
            f"{safe_name}</a>"
            f'<p class="text-xs text-gray-400">{safe_lang}{html_escape(stars_text)}</p>'
            "</div>"
            f'<button onclick="deleteRepo({repo.get("id", "")}, {ws_id_js})" '
            '        class="text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100">'
            '<i class="fas fa-trash text-xs"></i></button>'
            "</div>"
        )
    if not repos_html:
        repos_html = '<p class="text-sm text-gray-400 text-center py-4">No repositories added yet.</p>'

    date_joins = {}
    date_commands = {}
    for row in daily_stats:
        d = row.get("date", "")
        et = row.get("event_type", "")
        cnt = row.get("count", 0)
        if et == "Team_Join":
            date_joins[d] = cnt
        elif et == "Command":
            date_commands[d] = cnt

    all_dates = sorted(set(list(date_joins.keys()) + list(date_commands.keys())))
    if not all_dates:
        all_dates = [
            (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(6, -1, -1)
        ]

    chart_labels = json.dumps(all_dates)
    chart_joins = json.dumps([date_joins.get(d, 0) for d in all_dates])
    chart_commands = json.dumps([date_commands.get(d, 0) for d in all_dates])

    dashboard_tabs = ""
    if current_ws:
        ws_q = f"ws={ws_id}" if ws_id else ""
        overview_href = (
            f"/dashboard?{ws_q}&tab=overview" if ws_q else "/dashboard?tab=overview"
        )
        channels_href = (
            f"/dashboard?{ws_q}&tab=channels" if ws_q else "/dashboard?tab=channels"
        )
        overview_active = (
            "bg-red-600 text-white border-red-600"
            if active_tab == "overview"
            else "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
        )
        channels_active = (
            "bg-red-600 text-white border-red-600"
            if active_tab == "channels"
            else "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
        )
        dashboard_tabs = (
            '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-3">'
            '<div class="flex flex-wrap gap-2">'
            f'<a href="{overview_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {overview_active}">'
            '<i class="fas fa-chart-line"></i> Overview</a>'
            f'<a href="{channels_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {channels_active}">'
            '<i class="fas fa-hashtag"></i> Channels</a>'
            "</div></section>"
        )

    if current_ws and active_tab == "channels":
        all_channels_rows = ""
        for idx, ch in enumerate(channels, start=1):
            all_channels_rows += (
                '<tr class="border-b border-gray-100 hover:bg-gray-50">'
                f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{idx}</td>'
                f'<td class="py-3 px-4 text-sm font-medium text-gray-800">#{html_escape(ch.get("channel_name", ""))}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-600">{ch.get("member_count", 0):,}</td>'
                '</tr>'
            )
        if not all_channels_rows:
            all_channels_rows = (
                '<tr><td colspan="3" class="py-6 text-center text-sm text-gray-400">'
                "No channels scanned yet. Use Scan Channels to fetch workspace channels."
                "</td></tr>"
            )
        workspace_section = (
            '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
            '<div class="flex items-center justify-between mb-4">'
            f'<h2 class="text-xl font-bold text-gray-800">Channels - {ws_name}</h2>'
            f'<span class="text-xs text-gray-400">{len(channels)} channel(s)</span>'
            "</div>"
            '<div class="overflow-x-auto">'
            '<table class="w-full text-left">'
            '<thead><tr class="border-b border-gray-200">'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">#</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Channel</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Users</th>'
            "</tr></thead><tbody>"
            f"{all_channels_rows}"
            "</tbody></table></div></section>"
        )
    elif current_ws:
        scan_btn = (
            f'<button onclick="scanChannels({ws_id_js})" '
            '        id="scan-btn" '
            '        class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 '
            '               text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium">'
            '<i class="fas fa-sync-alt"></i> Scan Channels</button>'
            f'<button onclick="sendTestMessage({ws_id_js})" '
            '        id="test-msg-btn" '
            '        class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 border border-red-600 '
            '               text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium">'
            '<i class="fas fa-paper-plane"></i> Send Test Message</button>'
            f'<button onclick="importHistory({ws_id_js})" '
            '        id="import-btn" '
            '        class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 border border-green-600 '
            '               text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium">'
            '<i class="fas fa-file-csv"></i> Upload CSV</button>'
            f'<input id="import-history-file" type="file" accept=".csv,text/csv" class="hidden" '
            f'       onchange="handleImportHistoryFile(event, {ws_id_js})" />'
        )
        workspace_section = _render_template(
            "dashboard_workspace_section.html",
            {
                "WS_NAME": ws_name,
                "APP_EDIT_URL": app_edit_url,
                "SCAN_BTN": scan_btn,
                "TOTAL": f"{total:,}",
                "LAST24": f"{last24:,}",
                "SUCCESS_RATE": f"{success_rate}",
                "WS_COUNT": ws_count,
                "LAST_EVENT_TIME": (
                    last_event_time[:16].replace("T", " ") if last_event_time else "-"
                ),
                "JOINS": f"{joins:,}",
                "COMMANDS": f"{commands:,}",
                "EVENTS_HTML": events_html,
                "CHANNELS_HTML": channels_html,
                "REPOS_HTML": repos_html,
            },
        )
    else:
        workspace_section = (
            '<div class="bg-yellow-50 border border-yellow-200 rounded-xl p-4 '
            'text-sm text-yellow-800">'
            '<i class="fas fa-info-circle mr-2"></i>'
            "Select or add a workspace to view its dashboard.</div>"
        )

    return _render_template(
        "dashboard.html",
        {
            "USER_NAME": user_name,
            "USER_AVATAR": user_avatar_html,
            "WS_COUNT": ws_count,
            "WS_TABS": ws_tabs,
            "DASHBOARD_TABS": dashboard_tabs,
            "WORKSPACE_SECTION": workspace_section,
            "WS_ID_JSON": ws_id_js,
            "CHART_LABELS": chart_labels,
            "CHART_JOINS": chart_joins,
            "CHART_COMMANDS": chart_commands,
        },
    )


def get_homepage_html(user=None):
    """Generate the homepage HTML with project information and live stats."""
    if user:
        auth_button_href = "/dashboard"
        auth_button_text = "Go to Dashboard"
    else:
        auth_button_href = "/login"
        auth_button_text = "Sign in with Slack"

    return _render_template(
        "homepage.html",
        {
            "AUTH_BUTTON_HREF": auth_button_href,
            "AUTH_BUTTON_TEXT": auth_button_text,
        },
    )


def get_status_html(env):
    """Generate the status page HTML showing configuration status."""

    def _status_item(name, description, is_set, required=True):
        """Generate a status item HTML."""
        status_class = "set" if is_set else "missing"
        icon = "✓" if is_set else "✗"
        badge_text = "Required" if required else "Optional"

        # Tailwind classes for styling
        border_color = (
            "border-l-green-500 bg-green-50" if is_set else "border-l-red-500 bg-red-50"
        )
        icon_color = "text-green-600" if is_set else "text-red-600"
        badge_bg = (
            "bg-red-100 text-red-800" if required else "bg-blue-100 text-blue-800"
        )

        return f"""<div class="status-item {status_class} flex items-start p-4 bg-gray-50 rounded-lg border-l-4 {border_color}">
        <div class="status-icon text-2xl mr-4 flex-shrink-0 {icon_color}">{icon}</div>
        <div class="status-details flex-1">
            <div class="status-name font-semibold text-gray-900 mb-1">
                {name} 
                <span class="badge inline-block px-2 py-1 rounded-full text-xs font-semibold uppercase ml-2 {badge_bg}">{badge_text}</span>
            </div>
            <div class="status-desc text-sm text-gray-600">{description}</div>
        </div>
    </div>"""

    # Check which secrets are set
    slack_token = bool(getattr(env, "SLACK_TOKEN", None))
    signing_secret = bool(getattr(env, "SIGNING_SECRET", None))
    slack_client_id = bool(getattr(env, "SLACK_CLIENT_ID", None))
    slack_client_secret = bool(getattr(env, "SLACK_CLIENT_SECRET", None))
    sentry_dsn = bool(getattr(env, "SENTRY_DSN", None))
    base_url = bool(getattr(env, "BASE_URL", None))
    joins_channel = bool(getattr(env, "JOINS_CHANNEL_ID", None))
    contribute_id = bool(getattr(env, "CONTRIBUTE_ID", None))

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
