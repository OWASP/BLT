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
    installed_apps,
    apps_permission_warning,
    manifest_result,
    join_messages,
    join_message_event_counts,
    can_manage_manifest,
    active_tab="overview",
):
    """Generate the dashboard HTML with workspace statistics and controls."""
    user_name = html_escape((user or {}).get("name") or "User")
    user_slack_id = html_escape((user or {}).get("slack_user_id") or "")
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
    delete_workspace_btn = ""
    if current_ws and can_manage_manifest:
        delete_workspace_btn = (
            f'<button onclick="deleteWorkspace({ws_id})" '
            'class="mt-2 inline-flex w-full justify-center items-center gap-2 px-3 py-2 bg-white text-red-700 border border-red-200 '
            'rounded-lg hover:bg-red-50 transition-colors text-sm font-medium">'
            '<i class="fas fa-trash"></i> Delete Workspace</button>'
        )

    ws_tabs = ""
    for ws in workspaces:
        is_active = ws.get("id") == ws_id
        active = (
            "bg-red-50 text-red-700 border-red-200"
            if is_active
            else "bg-white text-gray-700 border-gray-200 hover:bg-gray-50"
        )
        team_name = str(ws.get("team_name") or "Workspace")
        icon_letter = html_escape(team_name[:1].upper() if team_name else "W")
        icon_url = str(ws.get("icon_url") or "").strip()
        if icon_url:
            workspace_icon_html = (
                f'<img src="{html_escape(icon_url)}" alt="{html_escape(team_name)} icon" '
                'class="w-8 h-8 shrink-0 rounded-lg border border-gray-200 object-cover"/>'
            )
        else:
            workspace_icon_html = (
                '<span class="w-8 h-8 shrink-0 rounded-lg bg-gray-900 text-white inline-flex items-center justify-center text-xs font-bold">'
                f"{icon_letter}</span>"
            )
        team_name_safe = html_escape(team_name)
        ws_tabs += (
            f'<a href="/dashboard?ws={ws["id"]}" '
            f'class="flex items-center gap-3 px-3 py-2 rounded-lg border text-sm font-medium {active} transition-colors">'
            f"{workspace_icon_html}"
            f'<span class="truncate">{team_name_safe}</span>'
            '</a>'
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
        status_label = (
            "Success" if raw_status == "success" else (raw_status.title() or "Unknown")
        )
        ev_type = html_escape(ev.get("event_type", ""))
        raw_user_name = (ev.get("user_name") or "").strip()
        user_name = html_escape(raw_user_name or "Unknown User")
        ev_time = html_escape(ev.get("created_at", "") or "-")
        request_data_raw = str(ev.get("request_data") or "").strip()
        request_data_tooltip = html_escape(request_data_raw)
        request_data_html = (
            '<span class="inline-flex items-center justify-center w-7 h-7 rounded-md border border-gray-200 text-gray-500 hover:text-red-600 hover:border-red-200" '
            f'title="{request_data_tooltip}"><i class="fas fa-code text-xs"></i></span>'
            if request_data_raw
            else '<span class="text-gray-300">-</span>'
        )
        is_verified = int(ev.get("verified") or 0) == 1
        verified_badge = (
            '<span class="inline-flex px-2 py-1 rounded-md text-xs font-semibold bg-green-100 text-green-800">Verified</span>'
            if is_verified
            else '<span class="inline-flex px-2 py-1 rounded-md text-xs font-semibold bg-gray-100 text-gray-600">Unverified</span>'
        )
        raw_channel_name = (ev.get("channel_name") or "").strip()
        if not raw_channel_name:
            event_type_raw = str(ev.get("event_type") or "").strip().lower()
            if event_type_raw == "team_join":
                raw_channel_name = "Workspace"
            elif event_type_raw.startswith("message_"):
                raw_channel_name = "Direct Message"
            elif event_type_raw == "command":
                raw_channel_name = "Slack Command"
            else:
                raw_channel_name = "Unknown Channel"
        channel_name = html_escape(raw_channel_name)
        events_html += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 text-sm text-gray-700">{ev_type}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-700">{user_name}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-500">{channel_name}</td>'
            f'<td class="py-3 px-4 text-sm">{status_dot}{status_label}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-500">{request_data_html}</td>'
            f'<td class="py-3 px-4 text-sm">{verified_badge}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-500" data-timestamp="{ev_time}"><span class="timeago">{ev_time}</span></td>'
            "</tr>"
        )
    if not events_html:
        events_html = (
            '<tr><td colspan="7" class="py-6 text-center text-sm text-gray-400">'
            "No events recorded yet.</td></tr>"
        )

    ws_id_js = _js_literal(ws_id)
    repos_html = ""
    for repo in repos:
        safe_url = html_escape(repo.get("repo_url", "#"))
        safe_name = html_escape(repo.get("repo_name") or repo.get("repo_url", ""))
        safe_lang = html_escape(repo.get("language", ""))
        stars_text = f"  * {repo.get('stars', '')}" if repo.get("stars") else ""
        source_type = html_escape(str(repo.get("source_type") or "repo").upper())
        topics_text = ""
        try:
            metadata = json.loads(repo.get("metadata_json") or "{}")
            topics = metadata.get("topics") if isinstance(metadata, dict) else []
            if isinstance(topics, list) and topics:
                topics_text = "  * " + ", ".join(str(t) for t in topics[:3])
        except Exception:
            topics_text = ""
        repos_html += (
            '<div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-0 group">'
            "<div>"
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" '
            '   class="text-sm font-medium text-red-600 hover:underline">'
            f"{safe_name}</a>"
            f'<p class="text-xs text-gray-400">{safe_lang}{html_escape(stars_text)}  * {source_type}{html_escape(topics_text)}</p>'
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
        repositories_href = (
            f"/dashboard?{ws_q}&tab=repositories"
            if ws_q
            else "/dashboard?tab=repositories"
        )
        apps_href = f"/dashboard?{ws_q}&tab=apps" if ws_q else "/dashboard?tab=apps"
        manifest_href = (
            f"/dashboard?{ws_q}&tab=manifest" if ws_q else "/dashboard?tab=manifest"
        )
        join_messages_href = (
            f"/dashboard?{ws_q}&tab=join-messages"
            if ws_q
            else "/dashboard?tab=join-messages"
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
        repositories_active = (
            "bg-red-600 text-white border-red-600"
            if active_tab == "repositories"
            else "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
        )
        apps_active = (
            "bg-red-600 text-white border-red-600"
            if active_tab == "apps"
            else "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
        )
        manifest_active = (
            "bg-red-600 text-white border-red-600"
            if active_tab == "manifest"
            else "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
        )
        join_messages_active = (
            "bg-red-600 text-white border-red-600"
            if active_tab == "join-messages"
            else "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
        )
        badge_active = "bg-red-500 text-white"
        badge_idle = "bg-gray-100 text-gray-600"

        overview_count_badge = (
            '<span class="inline-flex min-w-5 justify-center rounded-full px-1.5 py-0.5 text-xs font-semibold '
            + (badge_active if active_tab == "overview" else badge_idle)
            + f'">{total}</span>'
        )
        channels_count_badge = (
            '<span class="inline-flex min-w-5 justify-center rounded-full px-1.5 py-0.5 text-xs font-semibold '
            + (badge_active if active_tab == "channels" else badge_idle)
            + f'">{len(channels)}</span>'
        )
        repos_count_badge = (
            '<span class="inline-flex min-w-5 justify-center rounded-full px-1.5 py-0.5 text-xs font-semibold '
            + (badge_active if active_tab == "repositories" else badge_idle)
            + f'">{len(repos)}</span>'
        )
        apps_count_badge = (
            '<span class="inline-flex min-w-5 justify-center rounded-full px-1.5 py-0.5 text-xs font-semibold '
            + (badge_active if active_tab == "apps" else badge_idle)
            + f'">{len(installed_apps or [])}</span>'
        )
        manifest_count_badge = (
            '<span class="inline-flex min-w-5 justify-center rounded-full px-1.5 py-0.5 text-xs font-semibold '
            + (badge_active if active_tab == "manifest" else badge_idle)
            + f'">{len((manifest_result or {}).get("checks") or [])}</span>'
        )
        join_messages_count_badge = (
            '<span class="inline-flex min-w-5 justify-center rounded-full px-1.5 py-0.5 text-xs font-semibold '
            + (badge_active if active_tab == "join-messages" else badge_idle)
            + f'">{len(join_messages or [])}</span>'
        )
        manifest_tab_html = ""
        if can_manage_manifest:
            manifest_tab_html = (
                f'<a href="{manifest_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {manifest_active}">'
                f'<i class="fas fa-clipboard-check"></i> Manifest {manifest_count_badge}</a>'
            )
        join_messages_tab_html = ""
        if can_manage_manifest:
            join_messages_tab_html = (
                f'<a href="{join_messages_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {join_messages_active}">'
                f'<i class="fas fa-message"></i> Join Messages {join_messages_count_badge}</a>'
            )
        dashboard_tabs = (
            '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-3">'
            '<div class="flex flex-wrap gap-2">'
            f'<a href="{overview_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {overview_active}">'
            f'<i class="fas fa-chart-line"></i> Activities {overview_count_badge}</a>'
            f'<a href="{channels_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {channels_active}">'
            f'<i class="fas fa-hashtag"></i> Channels {channels_count_badge}</a>'
            f'<a href="{repositories_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {repositories_active}">'
            f'<i class="fas fa-code-branch"></i> Repositories {repos_count_badge}</a>'
            f'<a href="{apps_href}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium {apps_active}">'
            f'<i class="fas fa-puzzle-piece"></i> Apps {apps_count_badge}</a>'
            f"{manifest_tab_html}"
            f"{join_messages_tab_html}"
            "</div></section>"
        )

    if current_ws and active_tab == "channels":
        join_message_options = '<option value="">None (disabled)</option>'
        for jm in join_messages or []:
            jm_id = int(jm.get("id") or 0)
            jm_name = html_escape(jm.get("name") or f"Message {jm_id}")
            join_message_options += f'<option value="{jm_id}">{jm_name}</option>'

        all_channels_rows = ""
        for idx, ch in enumerate(channels, start=1):
            ch_id = html_escape(ch.get("channel_id", ""))
            current_join_id = str(ch.get("join_message_id") or "")
            delivery_mode = str(ch.get("join_delivery_mode") or "dm").strip().lower()
            if delivery_mode not in ("dm", "ephemeral"):
                delivery_mode = "dm"
            is_configured = bool(current_join_id)
            status_badge = (
                '<span class="inline-flex items-center gap-1 rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-semibold">'
                '<span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>Configured</span>'
                if is_configured
                else '<span class="inline-flex rounded-full bg-gray-100 text-gray-600 px-2 py-0.5 text-xs font-semibold">Not Set</span>'
            )
            sent_count = int(
                (join_message_event_counts or {}).get(ch.get("channel_id"), 0) or 0
            )
            options_html = join_message_options
            if current_join_id:
                options_html = options_html.replace(
                    f'value="{current_join_id}"',
                    f'value="{current_join_id}" selected',
                )
            delivery_options = (
                '<option value="dm">Direct Message</option>'
                '<option value="ephemeral">Channel Ephemeral</option>'
            )
            delivery_options = delivery_options.replace(
                f'value="{delivery_mode}"',
                f'value="{delivery_mode}" selected',
            )
            all_channels_rows += (
                '<tr class="border-b border-gray-100 hover:bg-gray-50">'
                f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{idx}</td>'
                f'<td class="py-3 px-4 text-sm font-medium text-gray-800">#{html_escape(ch.get("channel_name", ""))}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-600">{ch.get("member_count", 0):,}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-600">{status_badge}</td>'
                '<td class="py-3 px-4 text-sm text-gray-600">'
                f'<select id="join-template-{ch_id}" class="w-full rounded-lg border border-gray-200 px-2 py-1 text-sm">{options_html}</select>'
                "</td>"
                '<td class="py-3 px-4 text-sm text-gray-600">'
                f'<select id="join-delivery-{ch_id}" class="w-full rounded-lg border border-gray-200 px-2 py-1 text-sm">{delivery_options}</select>'
                "</td>"
                f'<td class="py-3 px-4 text-sm text-gray-600 font-semibold">{sent_count:,}</td>'
                '<td class="py-3 px-4 text-sm text-gray-600">'
                f'<button onclick="saveChannelJoinConfig({ws_id_js}, &quot;{ch_id}&quot;)" class="px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 text-xs font-medium">Save</button>'
                "</td>"
                '</tr>'
            )
        if not all_channels_rows:
            all_channels_rows = (
                '<tr><td colspan="8" class="py-6 text-center text-sm text-gray-400">'
                "No channels scanned yet. Use Scan Channels to fetch workspace channels."
                "</td></tr>"
            )
        workspace_section = (
            '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
            '<div class="flex items-center justify-between mb-4">'
            f'<h2 class="text-xl font-bold text-gray-800">Channels - {ws_name}</h2>'
            f'<span class="text-xs text-gray-400">{len(channels)} channel(s)</span>'
            "</div>"
            '<div id="channel-config-status" class="hidden mb-4 p-3 rounded-lg"></div>'
            '<p class="text-xs text-gray-400 mb-4">Select a join message to enable auto-send on channel join. Choose "None (disabled)" to turn it off.</p>'
            '<div class="overflow-x-auto">'
            '<table class="w-full text-left">'
            '<thead><tr class="border-b border-gray-200">'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">#</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Channel</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Users</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Join Message</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Delivery</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Messages Sent</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Action</th>'
            "</tr></thead><tbody>"
            f"{all_channels_rows}"
            "</tbody></table></div></section>"
        )
    elif current_ws and active_tab == "repositories":
        workspace_section = (
            '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
            '<h2 class="text-xl font-bold text-gray-800 mb-4">'
            f"Repositories - {ws_name}"
            "</h2>"
            '<p class="text-sm text-gray-500 mb-4">Add a GitHub repository or organization URL. Organization URLs import metadata across repos.</p>'
            '<div id="import-status" class="hidden mb-4 p-3 rounded-lg"></div>'
            '<form id="repo-form" class="flex gap-2 mb-5" onsubmit="addRepo(event)">'
            '<input id="repo-url" type="url" placeholder="https://github.com/owner/repo or https://github.com/org" '
            'class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"/>'
            '<button type="submit" class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium">Add</button>'
            "</form>"
            '<p class="text-xs text-gray-400 mb-4">Organization URLs import all repos and metadata (language, stars, topics, visibility, activity).</p>'
            f'<div id="repos-list">{repos_html}</div>'
            "</section>"
        )
    elif current_ws and active_tab == "apps":
        apps_rows = ""
        slack_apps_home = "https://api.slack.com/apps"
        for app in installed_apps or []:
            app_name = html_escape(app.get("app_name") or "Unknown App")
            app_id = html_escape(app.get("app_id") or "")
            source = html_escape(app.get("source") or "unknown")
            scopes = html_escape(app.get("scopes") or "-")
            distribution = html_escape(app.get("distribution") or "-")
            installed_by = html_escape(app.get("installed_by") or "Unknown")
            status = "Installed" if app.get("is_installed") else "Unknown"
            app_manage_url = (
                f"https://api.slack.com/apps/{app_id}/general"
                if app_id
                else slack_apps_home
            )
            apps_rows += (
                '<tr class="border-b border-gray-100 hover:bg-gray-50">'
                f'<td class="py-3 px-4 text-sm font-medium text-gray-800">{app_name}<a href="{app_manage_url}" target="_blank" rel="noopener noreferrer" class="ml-2 text-xs text-red-600 hover:text-red-700 underline">Manage</a></td>'
                f'<td class="py-3 px-4 text-sm text-gray-500 font-mono">{app_id}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-600">{status}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-600">{installed_by}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-500">{source}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-500">{distribution}</td>'
                f'<td class="py-3 px-4 text-sm text-gray-500">{scopes}</td>'
                "</tr>"
            )
        if not apps_rows:
            apps_rows = (
                '<tr><td colspan="7" class="py-6 text-center text-sm text-gray-400">'
                "No app details available for this workspace token."
                "</td></tr>"
            )

        apps_warning_html = ""
        if apps_permission_warning:
            apps_warning_html = (
                '<div class="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-800 text-sm">'
                '<div class="font-semibold mb-1"><i class="fas fa-triangle-exclamation mr-2"></i>More apps may be hidden</div>'
                f"<div>{html_escape(apps_permission_warning)}</div>"
                "</div>"
            )

        workspace_section = (
            '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
            '<div class="flex items-center justify-between mb-4">'
            f'<h2 class="text-xl font-bold text-gray-800">Installed Apps - {ws_name}</h2>'
            f'<a href="{slack_apps_home}" target="_blank" rel="noopener noreferrer" class="text-xs text-red-600 hover:text-red-700 underline">Open Slack Apps Page</a>'
            "</div>"
            '<p class="text-sm text-gray-500 mb-4">'
            "This tab shows apps visible to your current Slack token. Some workspaces require admin scopes for full app listings."
            "</p>"
            f"{apps_warning_html}"
            '<div class="overflow-x-auto">'
            '<table class="w-full text-left">'
            '<thead><tr class="border-b border-gray-200">'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">App</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">App ID</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Installed By</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Source</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Distribution</th>'
            '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Scopes</th>'
            "</tr></thead><tbody>"
            f"{apps_rows}"
            "</tbody></table></div></section>"
        )
    elif current_ws and active_tab == "join-messages":
        if not can_manage_manifest:
            workspace_section = (
                '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
                '<div class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 text-sm">'
                '<div class="font-semibold mb-1"><i class="fas fa-lock mr-2"></i>Admin Access Required</div>'
                "Only workspace admins/owners can manage join messages."
                "</div></section>"
            )
        else:
            rows = ""
            for jm in join_messages or []:
                jm_id = int(jm.get("id") or 0)
                jm_name = html_escape(jm.get("name") or f"Message {jm_id}")
                jm_text = html_escape(jm.get("message_text") or "")
                rows += (
                    '<tr class="border-b border-gray-100 hover:bg-gray-50">'
                    f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{jm_id}</td>'
                    f'<td class="py-3 px-4 text-sm font-medium text-gray-800">{jm_name}</td>'
                    f'<td class="py-3 px-4 text-sm text-gray-600 whitespace-pre-wrap">{jm_text}</td>'
                    '<td class="py-3 px-4 text-sm text-gray-600">'
                    f'<button onclick="testJoinMessage({ws_id_js}, {jm_id})" class="mr-2 px-3 py-1.5 rounded-lg border border-blue-200 text-blue-700 hover:bg-blue-50 text-xs font-medium">Test</button>'
                    f'<button onclick="deleteJoinMessage({ws_id_js}, {jm_id})" class="px-3 py-1.5 rounded-lg border border-red-200 text-red-700 hover:bg-red-50 text-xs font-medium">Delete</button>'
                    "</td>"
                    "</tr>"
                )
            if not rows:
                rows = (
                    '<tr><td colspan="4" class="py-6 text-center text-sm text-gray-400">'
                    "No join messages yet. Create one below."
                    "</td></tr>"
                )

            workspace_section = (
                '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
                '<div class="flex items-center justify-between mb-4">'
                f'<h2 class="text-xl font-bold text-gray-800">Join Messages - {ws_name}</h2>'
                "</div>"
                '<div id="join-messages-status" class="hidden mb-4 p-3 rounded-lg"></div>'
                '<div class="rounded-lg border border-gray-200 p-4 mb-5">'
                '<h3 class="text-sm font-semibold text-gray-700 mb-3">Create Join Message</h3>'
                '<input id="join-message-name" type="text" placeholder="Welcome DM v1" class="w-full mb-3 rounded-lg border border-gray-200 px-3 py-2 text-sm"/>'
                '<textarea id="join-message-text" rows="6" class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-mono" placeholder="Welcome {user_mention} to #{channel_name} in {workspace_name}!"></textarea>'
                '<p class="text-xs text-gray-400 mt-2">Variables: {user_mention}, {user_id}, {channel_name}, {channel_id}, {workspace_name}, {workspace_id}, {timestamp}</p>'
                f'<button onclick="createJoinMessage({ws_id_js})" class="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium"><i class="fas fa-plus"></i> Save Join Message</button>'
                "</div>"
                '<div class="overflow-x-auto">'
                '<table class="w-full text-left">'
                '<thead><tr class="border-b border-gray-200">'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">ID</th>'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Name</th>'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Message</th>'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Action</th>'
                "</tr></thead><tbody>"
                f"{rows}"
                "</tbody></table></div></section>"
            )
    elif current_ws and active_tab == "manifest":
        if not can_manage_manifest:
            workspace_section = (
                '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
                '<div class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800 text-sm">'
                '<div class="font-semibold mb-1"><i class="fas fa-lock mr-2"></i>Admin Access Required</div>'
                "Only workspace admins/owners can check the app manifest."
                "</div></section>"
            )
        else:
            checks = (manifest_result or {}).get("checks") or []
            check_rows = ""
            for idx, check in enumerate(checks, start=1):
                ok = bool(check.get("ok"))
                badge_class = (
                    "bg-green-100 text-green-800" if ok else "bg-red-100 text-red-800"
                )
                label = "PASS" if ok else "FAIL"
                check_rows += (
                    '<tr class="border-b border-gray-100 hover:bg-gray-50">'
                    f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{idx}</td>'
                    f'<td class="py-3 px-4 text-sm font-medium text-gray-800">{html_escape(check.get("name") or "")}</td>'
                    f'<td class="py-3 px-4 text-sm"><span class="inline-flex px-2 py-1 rounded-md text-xs font-semibold {badge_class}">{label}</span></td>'
                    f'<td class="py-3 px-4 text-sm text-gray-600">{html_escape(check.get("detail") or "")}</td>'
                    "</tr>"
                )
            if not check_rows:
                check_rows = (
                    '<tr><td colspan="4" class="py-6 text-center text-sm text-gray-400">'
                    "No manifest checks available."
                    "</td></tr>"
                )

            summary = html_escape(
                (manifest_result or {}).get("summary") or "No summary"
            )
            manifest_path = html_escape(
                (manifest_result or {}).get("manifest_path") or "manifest.yaml"
            )
            ok = bool((manifest_result or {}).get("ok"))
            summary_class = (
                "text-green-700 bg-green-50 border-green-200"
                if ok
                else "text-red-700 bg-red-50 border-red-200"
            )
            summary_label = "Manifest is valid" if ok else "Manifest has required fixes"

            workspace_section = (
                '<section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">'
                '<div class="flex items-center justify-between mb-4">'
                f'<h2 class="text-xl font-bold text-gray-800">Manifest Checker - {ws_name}</h2>'
                f'<span id="manifest-path" class="text-xs text-gray-400 font-mono">{manifest_path}</span>'
                "</div>"
                '<div class="mb-4">'
                '<label for="manifest-input" class="block text-sm font-medium text-gray-700 mb-2">Paste Manifest YAML</label>'
                '<textarea id="manifest-input" rows="10" '
                'class="w-full rounded-lg border border-gray-200 p-3 text-sm font-mono text-gray-800 focus:outline-none focus:ring-2 focus:ring-red-300" '
                'placeholder="display_information:\n  name: My App\n..."></textarea>'
                f'<button onclick="analyzePastedManifest({ws_id_js})" id="manifest-analyze-btn" '
                'class="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-red-600 border border-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium">'
                '<i class="fas fa-magnifying-glass"></i> Analyze Pasted Manifest</button>'
                "</div>"
                '<div id="manifest-status" class="hidden mb-4 p-3 rounded-lg"></div>'
                f'<div id="manifest-summary-box" class="rounded-lg border p-3 mb-4 {summary_class}">'
                '<div class="flex items-center justify-between gap-3">'
                f'<p id="manifest-summary-label" class="text-sm font-semibold">{summary_label}</p>'
                f'<p id="manifest-summary-text" class="text-xs font-mono">{summary}</p>'
                "</div></div>"
                '<div class="overflow-x-auto">'
                '<table class="w-full text-left">'
                '<thead><tr class="border-b border-gray-200">'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">#</th>'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Requirement</th>'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</th>'
                '<th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Details</th>'
                '</tr></thead><tbody id="manifest-checks-body">'
                f"{check_rows}"
                "</tbody></table></div></section>"
            )
    elif current_ws:
        purge_events_btn = ""
        if can_manage_manifest:
            purge_events_btn = (
                f'<button onclick="purgeRecentActivities({ws_id_js})" '
                '        id="purge-events-btn" '
                '        class="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-red-200 '
                '               text-red-700 rounded-lg hover:bg-red-50 transition-colors text-sm font-medium">'
                '<i class="fas fa-trash"></i> Purge Activities</button>'
            )

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
                "PURGE_EVENTS_BTN": purge_events_btn,
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
            "USER_SLACK_ID": user_slack_id,
            "USER_AVATAR": user_avatar_html,
            "WS_COUNT": ws_count,
            "WS_TABS": ws_tabs,
            "DELETE_WORKSPACE_BTN": delete_workspace_btn,
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


def get_manifest_checker_html(result):
    """Generate HTML page showing manifest requirement validation results."""
    checks = result.get("checks") or []
    rows_html = ""
    for idx, check in enumerate(checks, start=1):
        ok = bool(check.get("ok"))
        badge_class = "bg-green-100 text-green-800" if ok else "bg-red-100 text-red-800"
        status_text = "PASS" if ok else "FAIL"
        icon = (
            "fa-check-circle text-green-600" if ok else "fa-times-circle text-red-600"
        )
        rows_html += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{idx}</td>'
            f'<td class="py-3 px-4 text-sm font-medium text-gray-800">{html_escape(check.get("name") or "")}</td>'
            f'<td class="py-3 px-4 text-sm"><span class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-semibold {badge_class}"><i class="fas {icon}"></i>{status_text}</span></td>'
            f'<td class="py-3 px-4 text-sm text-gray-600">{html_escape(check.get("detail") or "")}</td>'
            '</tr>'
        )

    if not rows_html:
        rows_html = (
            '<tr><td colspan="4" class="py-6 text-center text-sm text-gray-400">'
            "No checks were generated."
            "</td></tr>"
        )

    all_ok = bool(result.get("ok"))
    summary = html_escape(result.get("summary") or "No summary")
    manifest_path = html_escape(result.get("manifest_path") or "manifest.yaml")
    status_class = (
        "text-green-700 bg-green-50 border-green-200"
        if all_ok
        else "text-red-700 bg-red-50 border-red-200"
    )
    status_label = "Manifest is valid" if all_ok else "Manifest has required fixes"

    return _render_template(
        "manifest_checker.html",
        {
            "SUMMARY": summary,
            "MANIFEST_PATH": manifest_path,
            "STATUS_CLASS": status_class,
            "STATUS_LABEL": status_label,
            "CHECK_ROWS": rows_html,
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
