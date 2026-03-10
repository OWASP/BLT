#!/usr/bin/env python3
"""
Generate leaderboard data and pre-render index.html for OWASP BLT Pages.

Fetches all bug-labelled issues from GitHub, builds leaderboard / commenter /
domain / recent-bug statistics, writes ``data/leaderboard.json``, and patches
``index.html`` with server-side-rendered (SSR) content so the page is useful
even when JavaScript is blocked.

Required environment variables:
  GITHUB_TOKEN      – Personal access token or Actions secret
  GITHUB_REPOSITORY – owner/repo  (e.g. OWASP-BLT/BLT-Pages)
  GITHUB_SHA        – Current commit SHA (optional; used in timestamp link)

License: AGPLv3
"""

import json
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse, quote
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "OWASP-BLT/BLT-Pages")
COMMIT_SHA = os.environ.get("GITHUB_SHA", "")

if "/" not in REPOSITORY:
    print(f"ERROR: GITHUB_REPOSITORY must be 'owner/repo', got: {REPOSITORY}", file=sys.stderr)
    sys.exit(1)

OWNER, REPO = REPOSITORY.split("/", 1)
BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "BLT-Pages-leaderboard-generator",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def paginate(url, params=None):
    """Fetch every page of a GitHub list endpoint and return all items."""
    items = []
    page = 1
    while True:
        p = dict(params or {})
        p["per_page"] = 100
        p["page"] = page
        query = "&".join(
            f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}"
            for k, v in p.items()
        )
        paged_url = f"{url}?{query}"
        req = urllib.request.Request(paged_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            print(f"HTTP {exc.code} for {paged_url}: {exc.reason}", file=sys.stderr)
            raise
        if not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
    return items

# ---------------------------------------------------------------------------
# Data-extraction helpers
# ---------------------------------------------------------------------------

def extract_domain(body):
    """Return the hostname from the ``### URL`` field in an issue body."""
    if not body:
        return None
    match = re.search(r"### URL\s*\n\n(\S+)", body)
    if not match:
        return None
    raw_url = match.group(1).strip()
    if raw_url.startswith("//"):
        raw_url = "https:" + raw_url
    elif not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url
    try:
        return urlparse(raw_url).hostname or None
    except Exception:
        return None


def extract_first_image(body):
    """Return the first image URL found in an issue body (Markdown or HTML)."""
    if not body:
        return None
    md = re.search(r"!\[.*?\]\((https?://[^\s)]+)\)", body)
    if md:
        return md.group(1)
    html = re.search(r'<img[^>]+src=["\'](https?://[^\s"\']+)["\']', body, re.IGNORECASE)
    if html:
        return html.group(1)
    return None

# ---------------------------------------------------------------------------
# HTML-rendering helpers
# ---------------------------------------------------------------------------

REACTION_EMOJIS = {
    "+1": "👍", "-1": "👎", "laugh": "😄", "hooray": "🎉",
    "confused": "😕", "heart": "❤️", "rocket": "🚀", "eyes": "👀",
}
RANK_ICONS = ["🥇", "🥈", "🥉"]
SAFE_HOSTNAME_RE = re.compile(
    r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)*$'
)


def _fmt_date(dt):
    """Format a datetime as 'Mon D, YYYY' (no leading zero, cross-platform)."""
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


def _fmt_datetime(dt):
    """Format a datetime as 'Mon D, YYYY, H:MM AM/PM UTC' (cross-platform)."""
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}, {hour}:{dt.strftime('%M')} {ampm} UTC"

def esc(s):
    """Escape HTML special characters."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def fmt(n):
    """Format an integer with a k-suffix when >= 1000."""
    n = int(n)
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def ssr_reactions(reactions):
    """Render a reactions dict as inline HTML badges."""
    if not reactions:
        return ""
    parts = []
    for rtype, count in reactions.items():
        if not count:
            continue
        emoji = REACTION_EMOJIS.get(rtype, "❓")
        label = f"{rtype}: {count}"
        parts.append(
            f'<span class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gray-100 '
            f'dark:bg-gray-700 rounded-full text-xs text-gray-700 dark:text-gray-300 '
            f'hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors align-middle" '
            f'title="{label}" aria-label="{label}">'
            f'<span aria-hidden="true">{emoji}</span>'
            f'<span class="font-medium">{count}</span></span>'
        )
    return " ".join(parts)


def _rank_cell(rank):
    if rank <= 3:
        return f'<span class="text-xl" aria-label="Rank {rank}">{RANK_ICONS[rank - 1]}</span>'
    return f'<span class="font-bold text-gray-500 dark:text-gray-400">#{rank}</span>'


def _row_class(rank):
    return "bg-active-bg dark:bg-red-900/10" if rank <= 3 else "hover:bg-gray-50 dark:hover:bg-gray-800/50"


def render_leaderboard_rows(leaderboard):
    if not leaderboard:
        return (
            '<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">'
            '<svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true">'
            '<use href="#fa-trophy"></use></svg>'
            'No reports yet. Be the first to '
            '<a href="https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml" '
            'class="text-primary underline hover:no-underline">report a bug</a>!'
            '</td></tr>'
        )
    max_lb = leaderboard[0]["count"] or 1
    rows = []
    for entry in leaderboard:
        rank = entry["rank"]
        pct = min(100.0, entry["count"] / max_lb * 100)
        profile_url = esc(entry.get("profile_url") or f"https://github.com/{entry['login']}")
        avatar_url = esc(entry.get("avatar_url") or f"https://github.com/{entry['login']}.png")
        login = esc(entry["login"])
        rows.append(
            f'<tr class="{_row_class(rank)} transition-colors">'
            f'<td class="px-4 py-3 text-center w-12">{_rank_cell(rank)}</td>'
            f'<td class="px-4 py-3">'
            f'<a href="{profile_url}" target="_blank" rel="noopener noreferrer" '
            f'class="flex items-center gap-3 group min-w-0">'
            f'<img src="{avatar_url}" alt="{login}&#039;s avatar" '
            f'class="w-8 h-8 rounded-full border border-neutral-border dark:border-gray-700 flex-shrink-0" '
            f'loading="lazy" onerror="this.src=&#039;https://github.com/identicons/{login}.png&#039;" />'
            f'<span class="font-medium text-gray-900 dark:text-white group-hover:text-primary '
            f'transition-colors truncate min-w-0 flex-1">{login}</span></a>'
            f'<div class="flex sm:hidden items-center gap-2 mt-1 pl-11">'
            f'<span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">'
            f'<svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-bug"></use></svg>'
            f'{fmt(entry["count"])}</span>'
            f'<div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 flex-1 overflow-hidden">'
            f'<div class="bg-primary h-1.5 rounded-full" style="width:{pct:.1f}%"></div></div></div>'
            f'</td>'
            f'<td class="hidden px-4 py-3 text-right sm:table-cell">'
            f'<span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">'
            f'<svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-bug"></use></svg>'
            f'{fmt(entry["count"])}</span></td>'
            f'<td class="px-4 py-3 hidden sm:table-cell">'
            f'<div class="flex justify-end">'
            f'<div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">'
            f'<div class="bg-primary h-2 rounded-full" style="width:{pct:.1f}%"></div>'
            f'</div></div></td></tr>'
        )
    return "".join(rows)


def render_commenters_rows(commenters):
    if not commenters:
        return (
            '<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">'
            '<svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true">'
            '<use href="#fa-comment"></use></svg>'
            'No comments yet. Start a conversation on a '
            '<a href="https://github.com/OWASP-BLT/BLT-Pages/issues" '
            'class="text-primary underline hover:no-underline" '
            'target="_blank" rel="noopener noreferrer">bug report</a>!'
            '</td></tr>'
        )
    max_cm = commenters[0]["count"] or 1
    rows = []
    for entry in commenters:
        rank = entry["rank"]
        pct = min(100.0, entry["count"] / max_cm * 100)
        profile_url = esc(entry.get("profile_url") or f"https://github.com/{entry['login']}")
        avatar_url = esc(entry.get("avatar_url") or f"https://github.com/{entry['login']}.png")
        login = esc(entry["login"])
        rows.append(
            f'<tr class="{_row_class(rank)} transition-colors">'
            f'<td class="px-4 py-3 text-center w-12">{_rank_cell(rank)}</td>'
            f'<td class="px-4 py-3">'
            f'<a href="{profile_url}" target="_blank" rel="noopener noreferrer" '
            f'class="flex items-center gap-3 group min-w-0">'
            f'<img src="{avatar_url}" alt="{login}&#039;s avatar" '
            f'class="w-8 h-8 rounded-full border border-neutral-border dark:border-gray-700 flex-shrink-0" '
            f'loading="lazy" onerror="this.src=&#039;https://github.com/identicons/{login}.png&#039;" />'
            f'<span class="font-medium text-gray-900 dark:text-white group-hover:text-primary '
            f'transition-colors truncate min-w-0 flex-1">{login}</span></a>'
            f'<div class="flex sm:hidden items-center gap-2 mt-1 pl-11">'
            f'<span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">'
            f'<svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-comment"></use></svg>'
            f'{fmt(entry["count"])}</span>'
            f'<div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 flex-1 overflow-hidden">'
            f'<div class="bg-primary h-1.5 rounded-full" style="width:{pct:.1f}%"></div></div></div>'
            f'</td>'
            f'<td class="hidden px-4 py-3 text-right sm:table-cell">'
            f'<span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">'
            f'<svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-comment"></use></svg>'
            f'{fmt(entry["count"])}</span></td>'
            f'<td class="px-4 py-3 hidden sm:table-cell">'
            f'<div class="flex justify-end">'
            f'<div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">'
            f'<div class="bg-primary h-2 rounded-full" style="width:{pct:.1f}%"></div>'
            f'</div></div></td></tr>'
        )
    return "".join(rows)


def render_domains_rows(domains):
    if not domains:
        return (
            '<tr><td colspan="4" class="text-center py-12 text-gray-500 dark:text-gray-400">'
            '<svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true">'
            '<use href="#fa-globe"></use></svg>'
            'No domain data yet. '
            '<a href="https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml" '
            'class="text-primary underline hover:no-underline">Be the first to report a bug!</a>'
            '</td></tr>'
        )
    max_dm = domains[0]["count"] or 1
    rows = []
    for entry in domains:
        rank = entry["rank"]
        pct = min(100.0, entry["count"] / max_dm * 100)
        domain = esc(entry["domain"])
        safe_href = f"https://{domain}" if SAFE_HOSTNAME_RE.match(entry["domain"]) else "#"
        favicon_url = esc(f"https://www.google.com/s2/favicons?domain={quote(entry['domain'])}&sz=32")
        rows.append(
            f'<tr class="{_row_class(rank)} transition-colors">'
            f'<td class="px-4 py-3 text-center w-12">{_rank_cell(rank)}</td>'
            f'<td class="px-4 py-3">'
            f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer" '
            f'class="flex items-center gap-3 group min-w-0">'
            f'<img src="{favicon_url}" alt="{domain} favicon" '
            f'class="w-5 h-5 rounded flex-shrink-0" loading="lazy" '
            f"onerror=\"this.outerHTML='<svg class=\\'fa-icon text-gray-400 w-5 h-5 flex-shrink-0\\' "
            f"aria-hidden=\\'true\\'><use href=\\'#fa-globe\\'></use></svg>'\" />"
            f'<span class="font-medium text-gray-900 dark:text-white group-hover:text-primary '
            f'transition-colors truncate min-w-0 flex-1">{domain}</span></a>'
            f'<div class="flex sm:hidden items-center gap-2 mt-1 pl-8">'
            f'<span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white text-xs">'
            f'<svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-bug"></use></svg>'
            f'{fmt(entry["count"])}</span>'
            f'<div class="bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 flex-1 overflow-hidden">'
            f'<div class="bg-primary h-1.5 rounded-full" style="width:{pct:.1f}%"></div></div></div>'
            f'</td>'
            f'<td class="hidden px-4 py-3 text-right sm:table-cell">'
            f'<span class="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">'
            f'<svg class="fa-icon text-primary text-xs" aria-hidden="true"><use href="#fa-bug"></use></svg>'
            f'{fmt(entry["count"])}</span></td>'
            f'<td class="px-4 py-3 hidden sm:table-cell">'
            f'<div class="flex justify-end">'
            f'<div class="bg-gray-100 dark:bg-gray-700 rounded-full h-2 w-24 overflow-hidden">'
            f'<div class="bg-primary h-2 rounded-full" style="width:{pct:.1f}%"></div>'
            f'</div></div></td></tr>'
        )
    return "".join(rows)


def render_recent_bugs(bugs):
    if not bugs:
        return (
            '<div class="col-span-3 text-center py-12 text-gray-400 dark:text-gray-500">'
            '<svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3" aria-hidden="true">'
            '<use href="#fa-bug"></use></svg>'
            'No bug reports yet. '
            '<a href="https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml" '
            'class="text-primary hover:underline">Be the first to report!</a></div>'
        )
    cards = []
    for bug in bugs:
        if bug.get("image_url"):
            img_html = (
                f'<div class="aspect-video bg-gray-100 dark:bg-gray-800 rounded-xl mb-4 '
                f'overflow-hidden flex-shrink-0">'
                f'<img src="{esc(bug["image_url"])}" alt="Bug screenshot" '
                f'class="w-full h-full object-cover" loading="lazy" '
                f"onerror=\"this.parentElement.classList.add('hidden')\" /></div>"
            )
        else:
            img_html = (
                f'<div class="aspect-video bg-gray-100 dark:bg-gray-800 rounded-xl mb-4 '
                f'flex items-center justify-center flex-shrink-0">'
                f'<svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600" aria-hidden="true">'
                f'<use href="#fa-bug"></use></svg></div>'
            )

        dt = datetime.fromisoformat(bug["created_at"].replace("Z", "+00:00"))
        date = _fmt_date(dt)
        avatar_url = esc(bug["user"].get("avatar_url") or f"https://github.com/{bug['user']['login']}.png")
        profile_url = esc(bug["user"].get("profile_url") or f"https://github.com/{bug['user']['login']}")
        login = esc(bug["user"]["login"])
        reactions_html = ssr_reactions(bug.get("reactions"))

        if bug.get("domain"):
            favicon_src = esc(f"https://www.google.com/s2/favicons?domain={quote(bug['domain'])}&sz=32")
            favicon_html = (
                f'<img src="{favicon_src}" '
                f'alt="{esc(bug["domain"])} favicon" '
                f'class="w-4 h-4 rounded flex-shrink-0 inline-block align-middle mr-1" '
                f'loading="lazy" referrerpolicy="no-referrer" '
                f"onerror=\"this.outerHTML='<svg class=\\'fa-icon text-gray-400 w-4 h-4\\' "
                f"aria-hidden=\\'true\\'><use href=\\'#fa-globe\\'></use></svg>'\" />"
            )
        else:
            favicon_html = ""

        comment_count = bug.get("comment_count", 0)
        comment_html = ""
        if isinstance(comment_count, int) and comment_count > 0 and bug.get("latest_comment"):
            c = bug["latest_comment"]["user"]
            c_avatar = esc(c.get("avatar_url") or f"https://github.com/{c['login']}.png")
            c_profile = esc(c.get("profile_url") or f"https://github.com/{c['login']}")
            c_login = esc(c["login"])
            c_body = esc(re.sub(r"\s+", " ", (bug["latest_comment"].get("body") or "")).strip())
            c_label = "1 comment" if comment_count == 1 else f"{fmt(comment_count)} comments"
            comment_html = (
                f'<div class="mt-3 pt-3 border-t border-neutral-border dark:border-gray-700">'
                f'<div class="flex items-start gap-2">'
                f'<a href="{c_profile}" target="_blank" rel="noopener noreferrer" class="flex-shrink-0">'
                f'<img src="{c_avatar}" alt="{c_login}&#039;s avatar" '
                f'class="w-6 h-6 rounded-full border border-neutral-border dark:border-gray-700" '
                f'loading="lazy" onerror="this.src=&#039;https://github.com/identicons/{c_login}.png&#039;" /></a>'
                f'<div class="min-w-0 flex-1">'
                f'<p class="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">{c_body}</p>'
                f'<a href="{esc(bug["html_url"])}" target="_blank" rel="noopener noreferrer" '
                f'class="inline-flex items-center gap-1 mt-1 text-xs text-gray-400 hover:text-primary transition-colors">'
                f'<svg class="fa-icon text-xs" aria-hidden="true"><use href="#fa-comment"></use></svg>'
                f'{c_label}</a></div></div></div>'
            )
        elif isinstance(comment_count, int) and comment_count == 0:
            comment_html = (
                f'<div class="mt-3 pt-3 border-t border-neutral-border dark:border-gray-700">'
                f'<a href="{esc(bug["html_url"])}" target="_blank" rel="noopener noreferrer" '
                f'class="inline-flex items-center gap-1 text-xs text-primary hover:underline">'
                f'<svg class="fa-icon text-xs" aria-hidden="true"><use href="#fa-comment"></use></svg>'
                f'Be the first to comment</a></div>'
            )

        cards.append(
            f'<div class="bg-white dark:bg-dark-base border border-neutral-border dark:border-gray-700 '
            f'rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col">'
            f'{img_html}'
            f'<h3 class="font-semibold text-gray-900 dark:text-white mb-3 line-clamp-2 flex-1">'
            f'<a href="{esc(bug["html_url"])}" target="_blank" rel="noopener noreferrer" '
            f'class="hover:text-primary transition-colors">{favicon_html}{esc(bug["title"])}</a></h3>'
            f'<div class="flex items-center justify-between gap-3 mt-auto pt-3 '
            f'border-t border-neutral-border dark:border-gray-700 flex-wrap">'
            f'<div class="flex items-center gap-3">'
            f'<a href="{profile_url}" target="_blank" rel="noopener noreferrer" '
            f'class="flex items-center gap-2 group">'
            f'<img src="{avatar_url}" alt="{login}&#039;s avatar" '
            f'class="w-7 h-7 rounded-full border border-neutral-border dark:border-gray-700" '
            f'loading="lazy" onerror="this.src=&#039;https://github.com/identicons/{login}.png&#039;" />'
            f'<span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-primary transition-colors">'
            f'{login}</span></a>{reactions_html}</div>'
            f'<span class="text-xs text-gray-400 dark:text-gray-500">{date}</span></div>'
            f'{comment_html}</div>'
        )
    return "".join(cards)

# ---------------------------------------------------------------------------
# HTML-patching helpers
# ---------------------------------------------------------------------------

def patch_html(html, payload):
    """Apply all SSR patches to the HTML string and return the result."""

    # ── Inline JSON data ─────────────────────────────────────────────────────
    inline_json = re.sub(r'</script>', r'<\\/script>', json.dumps(payload, ensure_ascii=True), flags=re.IGNORECASE)
    inline_script = (
        f'<script id="leaderboard-inline-data">'
        f'window.__BLT_LEADERBOARD__ = {inline_json};</script>'
    )
    html = re.sub(
        r'<script id="leaderboard-inline-data">[\s\S]*?</script>',
        lambda _: inline_script,
        html,
    )

    # ── Stat numbers ─────────────────────────────────────────────────────────
    html = re.sub(
        r'(<dd id="stat-total-bugs"[^>]*>)[^<]*',
        lambda m: m.group(1) + fmt(payload["total_bugs"]),
        html,
    )
    html = re.sub(
        r'(<dd id="stat-domains"[^>]*>)[^<]*',
        lambda m: m.group(1) + (fmt(payload["total_domains"]) if payload["total_domains"] is not None else "-"),
        html,
    )
    html = re.sub(
        r'(<dd id="stat-reporters"[^>]*>)[^<]*',
        lambda m: m.group(1) + fmt(len(payload["leaderboard"])),
        html,
    )

    # ── Header bug counts ─────────────────────────────────────────────────────
    html = re.sub(
        r'(<span id="header-stat-total"[^>]*>)[^<]*',
        lambda m: m.group(1) + fmt(payload["total_bugs"]),
        html,
    )
    html = re.sub(
        r'(<span id="header-stat-open"[^>]*>)[^<]*',
        lambda m: m.group(1) + fmt(payload["open_bugs"]),
        html,
    )
    html = re.sub(
        r'(<span id="header-stat-closed"[^>]*>)[^<]*',
        lambda m: m.group(1) + fmt(payload["closed_bugs"]),
        html,
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    if payload.get("updated_at"):
        dt = datetime.fromisoformat(payload["updated_at"].replace("Z", "+00:00"))

        updated_date = _fmt_date(dt)
        html = re.sub(
            r'(<p id="leaderboard-updated")([^>]*>)[\s\S]*?(</p>)',
            lambda m: f'{m.group(1)}{m.group(2)}Updated {esc(updated_date)}{m.group(3)}',
            html,
        )

        updated_full = _fmt_datetime(dt)
        sha = payload.get("commit_sha", "")
        homepage_ts = f"Last updated: {esc(updated_full)}"
        if sha and re.match(r"^[0-9a-f]{7,40}$", sha, re.I):
            commit_url = f"https://github.com/{REPOSITORY}/commit/{sha}"
            homepage_ts += (
                f' &mdash; <a href="{esc(commit_url)}" target="_blank" '
                f'rel="noopener noreferrer" class="hover:underline">{esc(sha[:7])}</a>'
            )
        _homepage_ts = homepage_ts
        html = re.sub(
            r'(<p id="homepage-updated")([^>]*>)[\s\S]*?(</p>)',
            lambda m: f'{m.group(1)}{m.group(2)}{_homepage_ts}{m.group(3)}',
            html,
        )

    # ── Leaderboard rows ──────────────────────────────────────────────────────
    lb_html = render_leaderboard_rows(payload["leaderboard"])
    _lb = f'<!-- SSR:leaderboard-rows -->{lb_html}<!-- /SSR:leaderboard-rows -->'
    html = re.sub(
        r'<!-- SSR:leaderboard-rows -->[\s\S]*?<!-- /SSR:leaderboard-rows -->',
        lambda _: _lb,
        html,
    )
    html = re.sub(
        r'(<tbody id="leaderboard-rows")(?:\s+data-pre-rendered="true")?([^>]*>)',
        lambda m: f'{m.group(1)} data-pre-rendered="true"{m.group(2)}',
        html,
    )

    # ── Commenters rows ───────────────────────────────────────────────────────
    cm_html = render_commenters_rows(payload["top_commenters"])
    _cm = f'<!-- SSR:commenters-rows -->{cm_html}<!-- /SSR:commenters-rows -->'
    html = re.sub(
        r'<!-- SSR:commenters-rows -->[\s\S]*?<!-- /SSR:commenters-rows -->',
        lambda _: _cm,
        html,
    )
    html = re.sub(
        r'(<tbody id="commenters-rows")(?:\s+data-pre-rendered="true")?([^>]*>)',
        lambda m: f'{m.group(1)} data-pre-rendered="true"{m.group(2)}',
        html,
    )

    # ── Domains rows ──────────────────────────────────────────────────────────
    dm_html = render_domains_rows(payload["top_domains"])
    _dm = f'<!-- SSR:domains-rows -->{dm_html}<!-- /SSR:domains-rows -->'
    html = re.sub(
        r'<!-- SSR:domains-rows -->[\s\S]*?<!-- /SSR:domains-rows -->',
        lambda _: _dm,
        html,
    )
    html = re.sub(
        r'(<tbody id="domains-rows")(?:\s+data-pre-rendered="true")?([^>]*>)',
        lambda m: f'{m.group(1)} data-pre-rendered="true"{m.group(2)}',
        html,
    )

    # ── Recent bugs grid ──────────────────────────────────────────────────────
    rb_html = render_recent_bugs(payload["recent_bugs"])
    _rb = f'<!-- SSR:recent-bugs -->{rb_html}<!-- /SSR:recent-bugs -->'
    html = re.sub(
        r'<!-- SSR:recent-bugs -->[\s\S]*?<!-- /SSR:recent-bugs -->',
        lambda _: _rb,
        html,
    )
    html = re.sub(
        r'(<div id="recent-bugs-grid")(?:\s+data-pre-rendered="true")?([^>]*>)',
        lambda m: f'{m.group(1)} data-pre-rendered="true"{m.group(2)}',
        html,
    )

    return html

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Fetching issues for {OWNER}/{REPO} …")

    # Fetch all bug-labelled issues (all states)
    all_issues = paginate(f"{BASE_URL}/issues", {"state": "all", "labels": "bug"})
    bug_issues = [i for i in all_issues if not i.get("pull_request")]
    print(f"  {len(bug_issues)} bug issues found")

    # ── Leaderboard ──────────────────────────────────────────────────────────
    counts = {}
    org_set = set()
    for issue in bug_issues:
        login = issue["user"]["login"]
        if login not in counts:
            counts[login] = {
                "count": 0,
                "avatar_url": issue["user"]["avatar_url"],
                "profile_url": issue["user"]["html_url"],
            }
        counts[login]["count"] += 1
        if issue.get("body"):
            m = re.search(r"### Organization Name.*?\n\n(.+)", issue["body"], re.DOTALL)
            if m:
                org_set.add(m.group(1).strip().split("\n")[0])

    leaderboard = [
        {"rank": i + 1, "login": login, **data}
        for i, (login, data) in enumerate(
            sorted(counts.items(), key=lambda x: x[1]["count"], reverse=True)[:50]
        )
    ]

    # ── Top domains ───────────────────────────────────────────────────────────
    domain_counts = {}
    for issue in bug_issues:
        domain = extract_domain(issue.get("body"))
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

    top_domains = [
        {"rank": i + 1, "domain": domain, "count": count}
        for i, (domain, count) in enumerate(
            sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        )
    ]

    # ── Top commenters & comment map ─────────────────────────────────────────
    print("  Fetching comments …")

    issues_needing_comments = [i for i in bug_issues if i["comments"] > 0]

    def fetch_comments(issue):
        return issue["number"], paginate(f"{BASE_URL}/issues/{issue['number']}/comments")

    issue_comments_map = {i["number"]: [] for i in bug_issues}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_comments, issue): issue for issue in issues_needing_comments}
        for future in as_completed(futures):
            number, comments = future.result()
            issue_comments_map[number] = comments

    comment_counts = {}
    for comments in issue_comments_map.values():
        for comment in comments:
            c_login = comment["user"]["login"]
            if c_login.endswith("[bot]"):
                continue
            if c_login not in comment_counts:
                comment_counts[c_login] = {
                    "count": 0,
                    "avatar_url": comment["user"]["avatar_url"],
                    "profile_url": comment["user"]["html_url"],
                }
            comment_counts[c_login]["count"] += 1

    top_commenters = [
        {"rank": i + 1, "login": login, **data}
        for i, (login, data) in enumerate(
            sorted(comment_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:20]
        )
    ]

    # ── Recent bugs ───────────────────────────────────────────────────────────
    open_bugs = sorted(
        [i for i in bug_issues if i["state"] == "open"],
        key=lambda x: x["created_at"],
        reverse=True,
    )
    recent_bugs = []
    for issue in open_bugs[:3]:
        comments = issue_comments_map.get(issue["number"], [])
        latest_comment = comments[-1] if comments else None
        reactions = {
            k: v
            for k, v in (issue.get("reactions") or {}).items()
            if k in ("+1", "-1", "laugh", "hooray", "confused", "heart", "rocket", "eyes")
            and v > 0
        }
        recent_bugs.append({
            "number": issue["number"],
            "title": issue["title"],
            "html_url": issue["html_url"],
            "created_at": issue["created_at"],
            "comment_count": issue["comments"],
            "user": {
                "login": issue["user"]["login"],
                "avatar_url": issue["user"]["avatar_url"],
                "profile_url": issue["user"]["html_url"],
            },
            "image_url": extract_first_image(issue.get("body")),
            "domain": extract_domain(issue.get("body")),
            "reactions": reactions,
            "latest_comment": {
                "body": latest_comment["body"],
                "created_at": latest_comment["created_at"],
                "html_url": latest_comment["html_url"],
                "user": {
                    "login": latest_comment["user"]["login"],
                    "avatar_url": latest_comment["user"]["avatar_url"],
                    "profile_url": latest_comment["user"]["html_url"],
                },
            } if latest_comment else None,
        })

    # ── Assemble payload ──────────────────────────────────────────────────────
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "commit_sha": COMMIT_SHA,
        "total_bugs": len(bug_issues),
        "open_bugs": sum(1 for i in bug_issues if i["state"] == "open"),
        "closed_bugs": sum(1 for i in bug_issues if i["state"] == "closed"),
        "total_domains": len(domain_counts),
        "total_orgs": len(org_set),
        "leaderboard": leaderboard,
        "top_commenters": top_commenters,
        "top_domains": top_domains,
        "recent_bugs": recent_bugs,
    }

    # ── Write JSON ────────────────────────────────────────────────────────────
    os.makedirs("data", exist_ok=True)
    with open("data/leaderboard.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("  Wrote data/leaderboard.json")

    # ── Patch index.html ──────────────────────────────────────────────────────
    with open("index.html", encoding="utf-8") as fh:
        html = fh.read()

    html = patch_html(html, payload)

    with open("index.html", "w", encoding="utf-8") as fh:
        fh.write(html)
    print("  Patched index.html")

    print(
        f"Done: {len(bug_issues)} bugs, {len(leaderboard)} reporters, "
        f"{len(org_set)} orgs, {len(top_commenters)} commenters, "
        f"{len(domain_counts)} domains"
    )


if __name__ == "__main__":
    main()
