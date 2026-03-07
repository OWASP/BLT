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
    """Render a template by replacing %%TOKEN%% placeholders."""
    rendered = _load_template(template_name)
    for key, value in replacements.items():
        rendered = rendered.replace(f"%%{key}%%", str(value))
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
    user, workspaces, current_ws, ws_stats, channels, events, daily_stats, repos
):
    """Generate the dashboard HTML with workspace statistics and controls."""
    user_name = html_escape((user or {}).get("name") or "User")
    ws_id = (current_ws or {}).get("id", "")
    ws_name = html_escape((current_ws or {}).get("team_name", "No workspace selected"))
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
        status_label = "Success" if ev.get("status") == "success" else "Failed"
        ev_time = html_escape(ev.get("created_at", "")[:16].replace("T", " "))
        ws_int_id = int(ev.get("workspace_id") or 0)
        events_html += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 text-sm text-gray-700">{html_escape(ev.get("event_type", ""))}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-500">{ev_time}</td>'
            f'<td class="py-3 px-4 text-sm">{status_dot}{status_label}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{ws_int_id}</td>'
            "</tr>"
        )
    if not events_html:
        events_html = (
            '<tr><td colspan="4" class="py-6 text-center text-sm text-gray-400">'
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

    if current_ws:
        scan_btn = (
            f'<button onclick="scanChannels({ws_id_js})" '
            '        id="scan-btn" '
            '        class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 '
            '               text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium">'
            '<i class="fas fa-sync-alt"></i> Scan Channels</button>'
        )
        workspace_section = _render_template(
            "dashboard_workspace_section.html",
            {
                "WS_NAME": ws_name,
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
            "WS_COUNT": ws_count,
            "WS_TABS": ws_tabs,
            "WORKSPACE_SECTION": workspace_section,
            "WS_ID_JSON": ws_id_js,
            "CHART_LABELS": chart_labels,
            "CHART_JOINS": chart_joins,
            "CHART_COMMANDS": chart_commands,
        },
    )


def get_homepage_html():
    """Generate the homepage HTML with project information and live stats."""
    return _load_template("homepage.html")


def get_status_html(env):
    """Generate the status page HTML showing configuration status."""
    
    def _status_item(name, description, is_set, required=True):
        """Generate a status item HTML."""
        status_class = "set" if is_set else "missing"
        icon = "✓" if is_set else "✗"
        badge_class = "required" if required else "optional"
        badge_text = "Required" if required else "Optional"
        
        # Tailwind classes for styling
        border_color = "border-l-green-500 bg-green-50" if is_set else "border-l-red-500 bg-red-50"
        icon_color = "text-green-600" if is_set else "text-red-600"
        badge_bg = "bg-red-100 text-red-800" if required else "bg-blue-100 text-blue-800"
        
        return f'''<div class="status-item {status_class} flex items-start p-4 bg-gray-50 rounded-lg border-l-4 {border_color}">
        <div class="status-icon text-2xl mr-4 flex-shrink-0 {icon_color}">{icon}</div>
        <div class="status-details flex-1">
            <div class="status-name font-semibold text-gray-900 mb-1">
                {name} 
                <span class="badge inline-block px-2 py-1 rounded-full text-xs font-semibold uppercase ml-2 {badge_bg}">{badge_text}</span>
            </div>
            <div class="status-desc text-sm text-gray-600">{description}</div>
        </div>
    </div>'''
    
    # Check which secrets are set
    slack_token = bool(getattr(env, 'SLACK_TOKEN', None))
    signing_secret = bool(getattr(env, 'SIGNING_SECRET', None))
    slack_client_id = bool(getattr(env, 'SLACK_CLIENT_ID', None))
    slack_client_secret = bool(getattr(env, 'SLACK_CLIENT_SECRET', None))
    sentry_dsn = bool(getattr(env, 'SENTRY_DSN', None))
    base_url = bool(getattr(env, 'BASE_URL', None))
    joins_channel = bool(getattr(env, 'JOINS_CHANNEL_ID', None))
    contribute_id = bool(getattr(env, 'CONTRIBUTE_ID', None))
    
    replacements = {
        'SLACK_TOKEN_STATUS': _status_item(
            'SLACK_TOKEN',
            'Slack Bot User OAuth Token (xoxb-...) for API calls',
            slack_token,
            required=True
        ),
        'SIGNING_SECRET_STATUS': _status_item(
            'SIGNING_SECRET',
            'Slack App Signing Secret for webhook verification',
            signing_secret,
            required=True
        ),
        'SLACK_CLIENT_ID_STATUS': _status_item(
            'SLACK_CLIENT_ID',
            'Slack OAuth App Client ID for user authentication',
            slack_client_id,
            required=True
        ),
        'SLACK_CLIENT_SECRET_STATUS': _status_item(
            'SLACK_CLIENT_SECRET',
            'Slack OAuth App Client Secret for token exchange',
            slack_client_secret,
            required=True
        ),
        'SENTRY_DSN_STATUS': _status_item(
            'SENTRY_DSN',
            'Sentry Data Source Name for error tracking',
            sentry_dsn,
            required=False
        ),
        'BASE_URL_STATUS': _status_item(
            'BASE_URL',
            'Base URL for OAuth redirects (e.g., https://lettuce.owaspblt.org)',
            base_url,
            required=False
        ),
        'JOINS_CHANNEL_ID_STATUS': _status_item(
            'JOINS_CHANNEL_ID',
            'Channel ID where join notifications are posted',
            joins_channel,
            required=False
        ),
        'CONTRIBUTE_ID_STATUS': _status_item(
            'CONTRIBUTE_ID',
            'Channel ID for contribution guidelines',
            contribute_id,
            required=False
        ),
    }
    
    return _render_template("status.html", replacements)


def get_404_html():
    """Generate the 404 not found HTML page."""
    return _load_template("404.html")


def get_500_html():
    """Generate the 500 internal server error HTML page."""
    return _load_template("500.html")

