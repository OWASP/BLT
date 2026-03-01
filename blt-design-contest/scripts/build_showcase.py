#!/usr/bin/env python3
"""
build_showcase.py
-----------------
Fetches GitHub issues for each configured design contest and generates
a static index.html design-showcase page styled with the BLT brand guide.

Each contest is configured in CONTESTS below with its own label, title
prefix, and issue template.  Issues labelled with WINNER_LABEL are
highlighted at the top of their contest section.

Environment variables
  GITHUB_TOKEN   – optional; increases API rate limit from 60 → 5000/hr
  GITHUB_REPOSITORY – set automatically by GitHub Actions (owner/repo)

Usage:
  python scripts/build_showcase.py
"""

import html
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO = os.environ.get("GITHUB_REPOSITORY", "OWASP-BLT/BLT-Design-Contest")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Label applied to the winning submission(s) in any contest
WINNER_LABEL = "winner"

# All active design contests.  Each entry drives one tab on the showcase page.
CONTESTS = [
    {
        "id": "blt-redesign",
        "name": "BLT App Redesign",
        "label": "design-submission",
        "title_prefix": "[Design]",
        "template": "design-submission.yml",
        "description": "Redesign the OWASP BLT application interface.",
        "prize": "$25",
        "deadline": "2026-06-01T00:00:00Z",
        "deadline_display": "June 1, 2026",
        "icon": "fa-solid fa-palette",
    },
    {
        "id": "blt-logo",
        "name": "BLT Logo Contest",
        "label": "logo-submission",
        "title_prefix": "[Logo]",
        "template": "logo-submission.yml",
        "description": "Design a new logo for OWASP BLT and all its repositories.",
        "prize": "$25",
        "deadline": "2026-06-01T00:00:00Z",
        "deadline_display": "June 1, 2026",
        "icon": "fa-solid fa-brush",
    },
    {
        "id": "blt-homepage",
        "name": "BLT Homepage Design",
        "label": "homepage-submission",
        "title_prefix": "[Homepage]",
        "template": "homepage-submission.yml",
        "description": "Design the new homepage for the OWASP BLT website.",
        "prize": "$25",
        "deadline": "2026-06-01T00:00:00Z",
        "deadline_display": "June 1, 2026",
        "icon": "fa-solid fa-house",
    },
]

# Backward-compatible aliases (used by helpers that pre-date multi-contest support)
LABEL = CONTESTS[0]["label"]
TITLE_PREFIX = CONTESTS[0]["title_prefix"]

REACTION_LABELS = {
    "+1": "👍",
    "-1": "👎",
    "laugh": "😄",
    "hooray": "🎉",
    "confused": "😕",
    "heart": "❤️",
    "rocket": "🚀",
    "eyes": "👀",
}

API_BASE = "https://api.github.com"
MARKDOWN_IMAGE_RE = re.compile(r"!\[.*?\]\((https?://[^)]+)\)")
HTML_IMAGE_RE = re.compile(r'<img\s[^>]*src="(https?://[^"]+)"', re.IGNORECASE)
COMMENT_STRIP_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")
COMMENT_STRIP_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MAX_COMMENT_LENGTH = 120


def github_request(path: str) -> list | dict:
    """Perform a paginated GET against the GitHub REST API."""
    url = f"{API_BASE}{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    results = []
    page = 1
    while True:
        paged_url = f"{url}{'&' if '?' in url else '?'}per_page=100&page={page}"
        req = urllib.request.Request(paged_url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            print(f"GitHub API error {exc.code} for {paged_url}: {exc.reason}",
                  file=sys.stderr)
            break
        if isinstance(data, list):
            results.extend(data)
            if len(data) < 100:
                break
            page += 1
        else:
            return data
    return results


def fetch_reactions(issue_number: int) -> dict:
    """Return reaction totals for an issue as {emoji: count}."""
    data = github_request(
        f"/repos/{REPO}/issues/{issue_number}/reactions"
    )
    totals: dict[str, int] = {}
    for item in data:
        content = item.get("content", "")
        if content in REACTION_LABELS:
            totals[content] = totals.get(content, 0) + 1
    return totals


def fetch_last_comment(issue_number: int) -> dict | None:
    """Return the last comment on an issue, or None if there are none."""
    data = github_request(
        f"/repos/{REPO}/issues/{issue_number}/comments"
    )
    if isinstance(data, list) and data:
        return data[-1]
    return None


def parse_issue_body(body: str) -> dict:
    """
    Extract structured fields from a GitHub issue-form body.
    Issue forms render as markdown with ### headings above each answer.
    """
    fields: dict[str, str] = {}
    if not body:
        return fields

    # GitHub issue form renders sections as:
    #   ### Field Label\n\nanswer text
    sections = re.split(r"\n###\s+", "\n" + body)
    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue
        heading = lines[0].strip()
        value = "\n".join(lines[1:]).strip()
        # Normalise key
        key = heading.lower().replace("/", " ").replace(" ", "_").strip("_")
        fields[key] = value
    return fields


def extract_preview_url(fields: dict, body: str) -> str:
    """Find the preview image URL from parsed fields or raw body."""
    # Check known field keys (including legacy keys for backward compatibility)
    for key in ("preview_image_url", "preview_url", "preview_image"):
        val = fields.get(key, "").strip()
        if val and val.startswith("http"):
            return val
        # Handle markdown image syntax: ![alt](url) or HTML <img src="url">
        if val:
            m = MARKDOWN_IMAGE_RE.search(val)
            if m:
                return m.group(1)
            m = HTML_IMAGE_RE.search(val)
            if m:
                return m.group(1)

    # Fallback: first markdown image in body  ![alt](url)
    m = MARKDOWN_IMAGE_RE.search(body or "")
    if m:
        return m.group(1)

    # Fallback: HTML <img src="url"> in body
    m = HTML_IMAGE_RE.search(body or "")
    if m:
        return m.group(1)

    # Fallback: first bare URL ending in image extension
    m = re.search(r"(https?://\S+\.(?:png|jpg|jpeg|gif|webp|svg))", body or "",
                  re.IGNORECASE)
    if m:
        return m.group(1)

    return ""


def extract_design_url(fields: dict) -> str:
    for key in ("design_prototype_link", "design_url", "prototype_link"):
        val = fields.get(key, "").strip()
        if val and val.startswith("http"):
            return val
    return ""


def extract_category(fields: dict) -> str:
    return fields.get("design_category", fields.get("category", "Other")).strip()


def extract_description(fields: dict) -> str:
    desc = fields.get("description", "").strip()
    # Strip matched markdown code fences (e.g. ```markdown ... ```)
    desc = re.sub(r"^```[^\n]*\n(.*?)^```\s*$", r"\1", desc, flags=re.DOTALL | re.MULTILINE)
    # Strip any remaining lone opening/closing fence markers (unmatched fences)
    desc = re.sub(r"^```\w*\s*$", "", desc, flags=re.MULTILINE)
    # Strip markdown checkbox noise
    desc = re.sub(r"^[-*]\s+\[[ x]\].*$", "", desc, flags=re.MULTILINE)
    desc = desc.strip()
    if len(desc) > 200:
        desc = desc[:197] + "…"
    return html.escape(desc)


def build_card(issue: dict, reactions: dict, last_comment: dict | None = None,
               is_winner: bool = False, title_prefix: str = TITLE_PREFIX) -> str:
    """Return the HTML card markup for a single submission."""
    number = issue["number"]
    title = html.escape(issue.get("title", "Untitled").replace(title_prefix + " ", "").strip())
    issue_url = html.escape(issue.get("html_url", "#"))
    created = issue.get("created_at", "")[:10]
    user = issue.get("user", {})
    author_login = html.escape(user.get("login", "unknown"))
    author_url = html.escape(user.get("html_url", "#"))
    author_avatar = html.escape(user.get("avatar_url", ""))

    body = issue.get("body", "") or ""
    fields = parse_issue_body(body)

    designer_name = html.escape(author_login)
    preview_url = html.escape(extract_preview_url(fields, body))
    design_url = html.escape(extract_design_url(fields))
    category = html.escape(extract_category(fields))
    description = extract_description(fields)
    comment_count = issue.get("comments", 0)

    # Last comment snippet
    comment_block = ""
    if last_comment:
        c_user = last_comment.get("user", {})
        c_login = html.escape(c_user.get("login", "unknown"))
        c_url = html.escape(c_user.get("html_url", "#"))
        c_avatar = html.escape(c_user.get("avatar_url", ""))
        c_body = (last_comment.get("body", "") or "").strip()
        # Strip markdown images and links for the snippet
        c_body = COMMENT_STRIP_IMAGE_RE.sub("", c_body)
        c_body = COMMENT_STRIP_LINK_RE.sub(r"\1", c_body)
        c_body = c_body.strip()
        if len(c_body) > MAX_COMMENT_LENGTH:
            c_body = c_body[:MAX_COMMENT_LENGTH - 3] + "…"
        c_body_escaped = html.escape(c_body)
        if c_body:
            c_avatar_img = (
                f'<img src="{c_avatar}" alt="{c_login}\'s avatar" class="w-5 h-5 rounded-full shrink-0" />'
                if c_avatar else
                '<i class="fa-solid fa-user-circle text-base shrink-0" aria-hidden="true"></i>'
            )
            count_label = f'{comment_count} comment{"s" if comment_count != 1 else ""} · ' if comment_count > 0 else ''
            comment_block = (
                f'<div class="flex items-start gap-1.5 text-xs text-gray-400 dark:text-gray-500">'
                f'{c_avatar_img}'
                f'<span>'
                f'<a href="{issue_url}" target="_blank" rel="noopener" '
                f'class="hover:text-[#E10101] transition-colors">{count_label}</a>'
                f'<a href="{c_url}" target="_blank" rel="noopener" '
                f'class="font-medium text-gray-500 dark:text-gray-400 hover:text-[#E10101] transition-colors">'
                f'{c_login}</a>: {c_body_escaped}</span>'
                f'</div>'
            )
    if not comment_block:
        comment_block = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'class="inline-flex items-center gap-1.5 text-xs '
            f'text-gray-400 dark:text-gray-500 hover:text-[#E10101] '
            f'dark:hover:text-[#E10101] transition-colors" '
            f'aria-label="Be the first to comment on GitHub">'
            f'<i class="fa-regular fa-comment" aria-hidden="true"></i>'
            f'Be the first to comment!</a>'
        )

    # Reaction pills
    thumbs_count = reactions.get("+1", 0)
    total_reactions = sum(reactions.get(c, 0) for c in REACTION_LABELS)

    if total_reactions > 0:
        reaction_html = ""
        for content, emoji in REACTION_LABELS.items():
            count = reactions.get(content, 0)
            if count == 0:
                continue
            if content == "+1":
                reaction_html += (
                    f'<button type="button" '
                    f'class="inline-flex items-center gap-1 text-sm '
                    f'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 '
                    f'rounded-full px-2 py-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 '
                    f'hover:text-[#E10101] transition-colors cursor-pointer" '
                    f'data-thumbs-btn '
                    f'aria-label="Thumbs up this design on GitHub">'
                    f'{emoji} <span>{count}</span></button>'
                )
            else:
                reaction_html += (
                    f'<span class="inline-flex items-center gap-1 text-sm '
                    f'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 '
                    f'rounded-full px-2 py-0.5">'
                    f'{emoji} <span>{count}</span></span>'
                )
    else:
        reaction_html = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'class="inline-flex items-center gap-1.5 text-xs '
            f'text-gray-400 dark:text-gray-500 hover:text-[#E10101] '
            f'dark:hover:text-[#E10101] transition-colors" '
            f'aria-label="Be the first to react on GitHub">'
            f'<i class="fa-regular fa-face-smile" aria-hidden="true"></i>'
            f'Be the first to react!</a>'
        )

    # Preview image
    if preview_url:
        preview_block = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'   class="block overflow-hidden aspect-square bg-gray-100 dark:bg-gray-700">'
            f'  <img src="{preview_url}" alt="{title} preview" loading="lazy" '
            f'       class="w-full h-full object-cover transition-transform duration-300 '
            f'              group-hover:scale-105" />'
            f'</a>'
        )
    else:
        preview_block = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'   class="flex items-center justify-center aspect-square '
            f'          bg-gray-100 dark:bg-gray-700 text-gray-400">'
            f'  <i class="fa-solid fa-image text-4xl" aria-hidden="true"></i>'
            f'</a>'
        )

    design_link = ""
    if design_url:
        design_link = (
            f'<a href="{design_url}" target="_blank" rel="noopener" '
            f'   class="text-[#E10101] hover:underline text-sm inline-flex items-center gap-1">'
            f'  <i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i>'
            f'  View Design</a>'
        )

    # Category badge colour
    cat_colour = {
        "UI / Website Redesign": "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
        "Logo / Brand Identity": "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200",
        "Banner / Marketing": "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-200",
        "Icon Set": "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200",
        "Mobile App": "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200",
        "T-Shirt / Apparel Design": "bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-200",
    }.get(category, "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200")

    # Winner badge and extra styling
    winner_badge = ""
    winner_ring = ""
    winner_attr = ""
    if is_winner:
        winner_badge = (
            '<div class="absolute top-2 left-2 z-10 flex items-center gap-1.5 '
            'bg-amber-400 text-amber-900 text-xs font-bold px-2.5 py-1 '
            'rounded-full shadow-md pointer-events-none">'
            '<i class="fa-solid fa-trophy" aria-hidden="true"></i> Winner</div>'
        )
        winner_ring = " ring-2 ring-amber-400 ring-offset-2 dark:ring-offset-[#111827]"
        winner_attr = ' data-winner="true"'

    return f"""
    <article class="group relative bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm border
                    border-[#E5E5E5] dark:border-gray-700 overflow-hidden
                    flex flex-col hover:shadow-md transition-shadow{winner_ring}"
             data-thumbs="{thumbs_count}"
             data-total-reactions="{total_reactions}"
             data-issue-url="{issue_url}"{winner_attr}
             aria-label="Contest submission: {title}">
      {winner_badge}
      {preview_block}
      <div class="p-5 flex flex-col gap-3 flex-1">
        <!-- Category + issue number -->
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <span class="text-xs font-medium px-2 py-0.5 rounded-full {cat_colour}">{category}</span>
          <span class="text-xs text-gray-400 dark:text-gray-500">#{number} · {created}</span>
        </div>

        <!-- Title -->
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 leading-snug">
          <a href="{issue_url}" target="_blank" rel="noopener"
             class="hover:text-[#E10101] transition-colors">{title}</a>
        </h2>

        <!-- Description -->
        <p class="text-sm text-gray-600 dark:text-gray-300 flex-1">{description or "No description provided."}</p>

        <!-- Designer -->
        <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          {'<img src="' + author_avatar + '" alt="" class="w-6 h-6 rounded-full" aria-hidden="true" />' if author_avatar else '<i class="fa-solid fa-user-circle text-lg" aria-hidden="true"></i>'}
          <a href="{author_url}" target="_blank" rel="noopener"
             class="text-[#E10101] hover:underline font-medium">{designer_name}</a>
        </div>
        <!-- Last comment -->
        {comment_block}
        <!-- Footer: reactions + design link -->
        <div class="flex items-center justify-between gap-2 flex-wrap pt-2
                    border-t border-[#E5E5E5] dark:border-gray-700">
          <div class="flex items-center gap-1 flex-wrap" aria-label="Reactions">
            {reaction_html}
          </div>
          <div class="flex items-center gap-3">
            {design_link}
            <a href="{issue_url}" target="_blank" rel="noopener"
               class="inline-flex items-center gap-1 text-sm font-medium
                      border border-[#E10101] text-[#E10101] rounded-md px-3 py-1
                      hover:bg-[#E10101] hover:text-white transition-colors"
               aria-label="View issue #{number}">
              <i class="fa-brands fa-github" aria-hidden="true"></i> Issue
            </a>
          </div>
        </div>
      </div>
    </article>"""


def build_contest_section(contest: dict, cards: list[str], total: int,
                          winner_count: int = 0) -> str:
    """Return the HTML panel for one contest tab (without wrapping <main>)."""
    cid = html.escape(contest["id"])
    name = html.escape(contest["name"])
    description = html.escape(contest["description"])
    prize = html.escape(contest["prize"])
    deadline_display = html.escape(contest["deadline_display"])
    submit_url = html.escape(
        f"https://github.com/{REPO}/issues/new?template={contest['template']}"
    )
    icon = contest["icon"]

    if cards:
        cards_html = "\n".join(cards)
    else:
        cards_html = (
            '<div class="col-span-full text-center py-20 text-gray-500 dark:text-gray-400">'
            f'<i class="{icon} text-5xl mb-4 block text-[#E10101]" aria-hidden="true"></i>'
            '<p class="text-lg font-medium">No submissions yet — be the first!</p>'
            '<p class="mt-2 text-sm">Click <strong>Add Entry</strong> to get started.</p>'
            '</div>'
        )

    winner_banner = ""
    if winner_count:
        s = "s" if winner_count > 1 else ""
        are = "are" if winner_count > 1 else "is"
        winner_banner = f"""
      <!-- Winner announcement banner -->
      <div class="mb-6 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-600
                  rounded-xl px-5 py-4 flex items-center gap-3">
        <i class="fa-solid fa-trophy text-2xl text-amber-500" aria-hidden="true"></i>
        <div>
          <p class="font-semibold text-amber-800 dark:text-amber-300">Winner{s} Selected!</p>
          <p class="text-sm text-amber-700 dark:text-amber-400">
            {winner_count} winning design{s} {are} highlighted below.
          </p>
        </div>
      </div>"""

    return f"""
    <div id="contest-{cid}" class="contest-panel" role="tabpanel" aria-labelledby="tab-{cid}">

      <!-- Contest info bar -->
      <div class="mb-6 p-5 bg-white dark:bg-[#1F2937] rounded-xl border border-[#E5E5E5] dark:border-gray-700">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <i class="{icon} text-[#E10101]" aria-hidden="true"></i>
              {name}
            </h2>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</p>
            <div class="mt-2 flex items-center gap-4 text-sm font-medium flex-wrap">
              <span class="inline-flex items-center gap-1 text-[#E10101]">
                <i class="fa-solid fa-trophy" aria-hidden="true"></i> {prize} prize
              </span>
              <span class="inline-flex items-center gap-1 text-[#E10101]">
                <i class="fa-solid fa-calendar-day" aria-hidden="true"></i> Ends {deadline_display}
              </span>
              <span class="inline-flex items-center gap-1 text-gray-500 dark:text-gray-400">
                <i class="fa-solid fa-images" aria-hidden="true"></i>
                {total} submission{'' if total == 1 else 's'}
              </span>
            </div>
          </div>
          <a href="{submit_url}"
             target="_blank" rel="noopener"
             class="inline-flex items-center gap-2 bg-[#E10101] hover:bg-red-700
                    text-white text-sm font-semibold px-4 py-2 rounded-md
                    transition-colors shrink-0">
            <i class="fa-solid fa-plus" aria-hidden="true"></i>
            Add Entry
          </a>
        </div>
      </div>
      {winner_banner}
      <!-- Sort controls -->
      <div class="flex items-center gap-3 flex-wrap mb-6">
        <span class="text-sm text-gray-500 dark:text-gray-400 mr-1">Sort:</span>
        <button id="sort-thumbs-{cid}" type="button"
                class="inline-flex items-center gap-2 border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-200 hover:border-[#E10101] hover:text-[#E10101]
                       text-sm font-semibold px-4 py-2 rounded-md transition-colors"
                aria-pressed="false"
                data-sort="thumbs" data-contest="{cid}">
          <i class="fa-solid fa-arrow-down-wide-short" aria-hidden="true"></i>
          By 👍
        </button>
        <button id="sort-reactions-{cid}" type="button"
                class="inline-flex items-center gap-2 border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-200 hover:border-[#E10101] hover:text-[#E10101]
                       text-sm font-semibold px-4 py-2 rounded-md transition-colors"
                aria-pressed="false"
                data-sort="reactions" data-contest="{cid}">
          <i class="fa-solid fa-arrow-down-wide-short" aria-hidden="true"></i>
          By all reactions
        </button>
      </div>

      <!-- Cards grid -->
      <div id="cards-grid-{cid}"
           class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards_html}
      </div>

    </div>"""


def build_html(contests_data: list[dict], last_updated: str) -> str:
    """Return the complete index.html as a string.

    ``contests_data`` is a list of dicts, each with keys:
      - ``config``  – the CONTESTS entry dict
      - ``cards``   – list of card HTML strings (winners first)
      - ``total``   – submission count for that contest
    """
    total_all = sum(d["total"] for d in contests_data)

    # Build tab buttons
    tab_buttons_html = ""
    for d in contests_data:
        c = d["config"]
        cid = html.escape(c["id"])
        cname = html.escape(c["name"])
        icon = c["icon"]
        tab_buttons_html += (
            f'<button role="tab" id="tab-{cid}" data-tab="{cid}"'
            f' aria-selected="false" aria-controls="contest-{cid}"'
            f' class="contest-tab inline-flex items-center gap-2 px-4 py-3 text-sm font-medium'
            f' border-b-2 border-transparent text-gray-600 dark:text-gray-300'
            f' hover:text-[#E10101] hover:border-[#E10101] transition-colors whitespace-nowrap">'
            f'<i class="{icon}" aria-hidden="true"></i>'
            f' {cname}'
            f' <span class="ml-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-500'
            f' dark:text-gray-400 rounded-full px-1.5 py-0.5">{d["total"]}</span>'
            f'</button>'
        )

    # Build contest panels
    contest_panels_html = ""
    for d in contests_data:
        contest_panels_html += build_contest_section(
            d["config"], d["cards"], d["total"], winner_count=d.get("winner_count", 0)
        )

    # For the hero submit URL, use the first contest
    first_submit_url = html.escape(
        f"https://github.com/{REPO}/issues/new?template={contests_data[0]['config']['template']}"
        if contests_data else f"https://github.com/{REPO}/issues/new"
    )

    # Earliest deadline across all contests (used for the countdown timer)
    earliest_deadline = min(
        (d["config"]["deadline"] for d in contests_data),
        default="2026-06-01T00:00:00Z",
    )

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="BLT Design Contest — community showcase of design submissions. Rate your favourites with a thumbs up!" />
  <title>BLT Design Contest — Showcase</title>

  <!-- Tailwind CSS (CDN) -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          colors: {{
            brand: '#E10101',
          }},
        }},
      }},
    }};
  </script>

  <!-- Font Awesome 6 (CDN) -->
  <link rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
        integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA=="
        crossorigin="anonymous" referrerpolicy="no-referrer" />

  <!-- Minimal custom overrides -->
  <style>
    :root {{ --brand: #E10101; }}
    *:focus-visible {{
      outline: 2px solid var(--brand);
      outline-offset: 2px;
    }}
  </style>
</head>

<body class="bg-gray-50 dark:bg-[#111827] text-gray-900 dark:text-gray-100 min-h-screen
             flex flex-col font-sans antialiased">

  <!-- ── Skip to content ── -->
  <a href="#showcase"
     class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2
            focus:z-50 focus:px-4 focus:py-2 focus:bg-[#E10101] focus:text-white
            focus:rounded-md focus:font-medium">
    Skip to content
  </a>

  <!-- ══════════════════════════════════════════
       HEADER / NAV
  ══════════════════════════════════════════ -->
  <header class="bg-white dark:bg-[#1F2937] border-b border-[#E5E5E5] dark:border-gray-700
                 sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <nav class="flex items-center justify-between h-16 gap-4" aria-label="Primary navigation">

        <!-- Logo / Brand -->
        <a href="/" class="flex items-center gap-2 shrink-0 group" aria-label="BLT Design Contest home">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-md
                       bg-[#E10101] text-white font-black text-sm select-none">BLT</span>
          <span class="font-semibold text-gray-900 dark:text-gray-100 hidden sm:block">
            Design Contest
          </span>
        </a>

        <!-- Centre nav links -->
        <div class="hidden md:flex items-center gap-6 text-sm font-medium">
          <a href="#showcase"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors">
            Showcase
          </a>
          <a href="#how-it-works"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors">
            How it works
          </a>
          <a href="https://github.com/{REPO}" target="_blank" rel="noopener"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors
                    inline-flex items-center gap-1">
            <i class="fa-brands fa-github" aria-hidden="true"></i> GitHub
          </a>
        </div>

        <!-- CTA -->
        <a href="{first_submit_url}"
           target="_blank" rel="noopener"
           class="inline-flex items-center gap-2 bg-[#E10101] hover:bg-red-700
                  text-white text-sm font-semibold px-4 py-2 rounded-md
                  transition-colors shrink-0">
          <i class="fa-solid fa-plus" aria-hidden="true"></i>
          <span>Submit Design</span>
        </a>

        <!-- Dark-mode toggle -->
        <button id="theme-toggle" type="button"
                class="p-2 rounded-md text-gray-500 dark:text-gray-400
                       hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                aria-label="Toggle dark mode">
          <i class="fa-solid fa-moon dark:hidden" aria-hidden="true"></i>
          <i class="fa-solid fa-sun hidden dark:inline" aria-hidden="true"></i>
        </button>

      </nav>
    </div>
  </header>

  <!-- ══════════════════════════════════════════
       HERO
  ══════════════════════════════════════════ -->
  <section class="bg-white dark:bg-[#1F2937] border-b border-[#E5E5E5] dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
      <span class="inline-block mb-4 bg-[#feeae9] dark:bg-red-900/30 text-[#E10101]
                   text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wide">
        Open Design Contests
      </span>
      <h1 class="text-4xl sm:text-5xl font-black text-gray-900 dark:text-gray-50 leading-tight mb-4">
        BLT Design Showcase
      </h1>
      <p class="max-w-2xl mx-auto text-lg text-gray-600 dark:text-gray-300 mb-4">
        Community-driven design submissions for OWASP BLT.
        Browse entries, react with 👍 on GitHub, and submit your own work.
      </p>

      <!-- Prize & deadline banner -->
      <div class="inline-flex flex-wrap items-center justify-center gap-4 mb-8
                  bg-[#feeae9] dark:bg-red-900/30 border border-[#E10101]/20
                  rounded-xl px-6 py-3 text-sm font-medium text-[#E10101]">
        <span class="inline-flex items-center gap-1.5">
          <i class="fa-solid fa-trophy" aria-hidden="true"></i>
          <strong>$25 prize</strong> per contest
        </span>
        <span class="hidden sm:block text-[#E10101]/40">|</span>
        <span class="inline-flex items-center gap-1.5">
          <i class="fa-solid fa-calendar-day" aria-hidden="true"></i>
          Contests end <strong>June 1, 2026</strong>
        </span>
      </div>

      <div class="flex items-center justify-center gap-4 flex-wrap">
        <a href="{first_submit_url}"
           target="_blank" rel="noopener"
           class="inline-flex items-center gap-2 bg-[#E10101] hover:bg-red-700
                  text-white font-semibold px-6 py-3 rounded-md transition-colors">
          <i class="fa-solid fa-pen-ruler" aria-hidden="true"></i>
          Submit Your Design
        </a>
        <a href="#showcase"
           class="inline-flex items-center gap-2 border border-[#E10101] text-[#E10101]
                  hover:bg-[#E10101] hover:text-white font-semibold px-6 py-3
                  rounded-md transition-colors">
          <i class="fa-solid fa-images" aria-hidden="true"></i>
          Browse Entries
        </a>
      </div>

      <!-- Stats bar -->
      <div class="mt-12 grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-2xl mx-auto
                  text-center text-sm text-gray-500 dark:text-gray-400">
        <div>
          <p class="text-3xl font-black text-[#E10101]">{total_all}</p>
          <p>Submission{'' if total_all == 1 else 's'}</p>
        </div>
        <div>
          <p class="text-3xl font-black text-[#E10101]">{len(contests_data)}</p>
          <p>Contest{'' if len(contests_data) == 1 else 's'}</p>
        </div>
        <div class="col-span-2 sm:col-span-1">
          <div id="countdown" class="flex justify-center gap-3 text-[#E10101]">
            <span class="flex flex-col items-center">
              <span id="cd-days" class="text-3xl font-black">--</span>
              <span class="text-xs">days</span>
            </span>
            <span class="text-3xl font-black leading-none self-start pt-1">:</span>
            <span class="flex flex-col items-center">
              <span id="cd-hours" class="text-3xl font-black">--</span>
              <span class="text-xs">hrs</span>
            </span>
            <span class="text-3xl font-black leading-none self-start pt-1">:</span>
            <span class="flex flex-col items-center">
              <span id="cd-mins" class="text-3xl font-black">--</span>
              <span class="text-xs">min</span>
            </span>
            <span class="text-3xl font-black leading-none self-start pt-1">:</span>
            <span class="flex flex-col items-center">
              <span id="cd-secs" class="text-3xl font-black">--</span>
              <span class="text-xs">sec</span>
            </span>
          </div>
          <p>Until Deadline</p>
        </div>
        <div class="col-span-2 sm:col-span-1">
          <p class="text-3xl font-black text-[#E10101]">∞</p>
          <p>Creativity</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ══════════════════════════════════════════
       HOW IT WORKS
  ══════════════════════════════════════════ -->
  <section id="how-it-works" class="bg-gray-50 dark:bg-[#111827]">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
      <h2 class="text-2xl font-bold text-center text-gray-900 dark:text-gray-100 mb-10">
        How it works
      </h2>
      <ol class="grid sm:grid-cols-3 gap-8" role="list">
        <li class="flex flex-col items-center text-center gap-3">
          <span class="w-12 h-12 rounded-full bg-[#feeae9] dark:bg-red-900/30 text-[#E10101]
                       flex items-center justify-center text-xl font-black">1</span>
          <h3 class="font-semibold text-gray-900 dark:text-gray-100">Submit via GitHub</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Open a new issue using the <em>Design Submission</em> template.
            Upload your preview image, add a description and a link to your design.
          </p>
        </li>
        <li class="flex flex-col items-center text-center gap-3">
          <span class="w-12 h-12 rounded-full bg-[#feeae9] dark:bg-red-900/30 text-[#E10101]
                       flex items-center justify-center text-xl font-black">2</span>
          <h3 class="font-semibold text-gray-900 dark:text-gray-100">Community rates it</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Anyone can leave a 👍 reaction on your issue to show appreciation.
            The showcase automatically reflects the current reaction counts.
          </p>
        </li>
        <li class="flex flex-col items-center text-center gap-3">
          <span class="w-12 h-12 rounded-full bg-[#feeae9] dark:bg-red-900/30 text-[#E10101]
                       flex items-center justify-center text-xl font-black">3</span>
          <h3 class="font-semibold text-gray-900 dark:text-gray-100">Showcase updates</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            GitHub Actions rebuilds this page whenever a submission issue is
            opened or edited, keeping the showcase always up to date.
          </p>
        </li>
      </ol>
    </div>
  </section>

  <!-- ══════════════════════════════════════════
       SHOWCASE (TABBED MULTI-CONTEST)
  ══════════════════════════════════════════ -->
  <main id="showcase" class="flex-1">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

      <!-- Last updated note -->
      <p class="text-xs text-gray-400 dark:text-gray-500 mb-4 text-right">
        Last updated {last_updated}
      </p>

      <!-- Contest tab strip -->
      <div class="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <div class="border-b border-[#E5E5E5] dark:border-gray-700 mb-8 flex gap-1 min-w-max"
             role="tablist" aria-label="Design contests">
          {tab_buttons_html}
        </div>
      </div>

      <!-- Contest panels (one per contest, shown/hidden via JS) -->
      {contest_panels_html}

    </div>
  </main>

  <!-- ══════════════════════════════════════════
       FOOTER
  ══════════════════════════════════════════ -->
  <footer class="bg-white dark:bg-[#1F2937] border-t border-[#E5E5E5] dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8
                flex flex-col sm:flex-row items-center justify-between gap-4 text-sm
                text-gray-500 dark:text-gray-400">
      <p>
        &copy; {datetime.now(timezone.utc).year}
        <a href="https://owasp.org/www-project-blt/" target="_blank" rel="noopener"
           class="text-[#E10101] hover:underline font-medium">OWASP BLT</a>.
        Content licensed under
        <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener"
           class="text-[#E10101] hover:underline">CC BY 4.0</a>.
      </p>
      <div class="flex items-center gap-4">
        <a href="https://github.com/{REPO}" target="_blank" rel="noopener"
           class="hover:text-[#E10101] transition-colors inline-flex items-center gap-1">
          <i class="fa-brands fa-github" aria-hidden="true"></i> Source
        </a>
        <a href="https://owasp.org/www-project-blt/" target="_blank" rel="noopener"
           class="hover:text-[#E10101] transition-colors">OWASP BLT</a>
      </div>
    </div>
  </footer>

  <!-- ══════════════════════════════════════════
       SCRIPTS
  ══════════════════════════════════════════ -->
  <script>
    // Dark-mode toggle
    const toggle = document.getElementById('theme-toggle');
    const html = document.documentElement;

    // Initialise from localStorage or system preference
    if (localStorage.theme === 'dark' ||
        (!('theme' in localStorage) &&
         window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
      html.classList.add('dark');
    }}

    toggle.addEventListener('click', () => {{
      html.classList.toggle('dark');
      localStorage.theme = html.classList.contains('dark') ? 'dark' : 'light';
    }});

    // Sort buttons — work independently per contest panel
    const sortState = {{}};

    function resetSortBtn(btn) {{
      if (!btn) return;
      btn.setAttribute('aria-pressed', 'false');
      btn.classList.remove('border-[#E10101]', 'text-[#E10101]');
      btn.classList.add('border-gray-300', 'dark:border-gray-600', 'text-gray-700', 'dark:text-gray-200');
    }}

    document.querySelectorAll('[data-sort][data-contest]').forEach(btn => {{
      btn.addEventListener('click', () => {{
        const cid = btn.dataset.contest;
        const sortType = btn.dataset.sort;
        const grid = document.getElementById(`cards-grid-${{cid}}`);
        if (!grid) return;

        if (!sortState[cid]) sortState[cid] = {{ thumbs: false, reactions: false, originalOrder: null }};
        if (!sortState[cid].originalOrder) sortState[cid].originalOrder = Array.from(grid.children);

        const otherType = sortType === 'thumbs' ? 'reactions' : 'thumbs';
        const otherBtn = document.querySelector(`[data-sort="${{otherType}}"][data-contest="${{cid}}"]`);
        const isActive = sortState[cid][sortType];

        sortState[cid][sortType] = !isActive;
        sortState[cid][otherType] = false;
        resetSortBtn(otherBtn);

        btn.setAttribute('aria-pressed', String(!isActive));
        btn.classList.toggle('border-[#E10101]', !isActive);
        btn.classList.toggle('text-[#E10101]', !isActive);
        btn.classList.toggle('border-gray-300', isActive);
        btn.classList.toggle('dark:border-gray-600', isActive);
        btn.classList.toggle('text-gray-700', isActive);
        btn.classList.toggle('dark:text-gray-200', isActive);

        const dataKey = sortType === 'thumbs' ? 'thumbs' : 'totalReactions';
        // Preserve winner pinning: keep winner cards at the top, only sort within non-winners.
        const allCards = [...sortState[cid].originalOrder];
        const winnerCards = allCards.filter(card => card.dataset.winner === 'true');
        const nonWinnerCards = allCards.filter(card => card.dataset.winner !== 'true');
        const sortedNonWinners = !isActive
          ? [...nonWinnerCards].sort((a, b) =>
              parseInt(b.dataset[dataKey] || '0', 10) - parseInt(a.dataset[dataKey] || '0', 10))
          : nonWinnerCards;
        const cards = [...winnerCards, ...sortedNonWinners];

        cards.forEach(card => grid.appendChild(card));
      }});
    }});

    // Thumbs-up click handler — opens the GitHub issue so the user can react there
    // Uses event delegation so it works for both static and live-updated buttons
    document.addEventListener('click', (e) => {{
      const btn = e.target.closest('[data-thumbs-btn]');
      if (!btn) return;
      const issueUrl = btn.closest('article')?.dataset.issueUrl;
      if (issueUrl) {{
        window.open(issueUrl, '_blank', 'noopener,noreferrer');
      }}
    }});

    // Live-update reaction counts from the GitHub API on page load
    (async function () {{
      const REACTION_LABELS = [
        ['+1',      '\U0001F44D'],
        ['-1',      '\U0001F44E'],
        ['laugh',   '\U0001F604'],
        ['hooray',  '\U0001F389'],
        ['confused','\U0001F615'],
        ['heart',   '\u2764\uFE0F'],
        ['rocket',  '\U0001F680'],
        ['eyes',    '\U0001F440'],
      ];
      const PILL = 'inline-flex items-center gap-1 text-sm bg-gray-100 dark:bg-gray-700 '
                 + 'text-gray-700 dark:text-gray-200 rounded-full px-2 py-0.5';
      const THUMBS_PILL = PILL + ' hover:bg-red-100 dark:hover:bg-red-900/30 '
                        + 'hover:text-[#E10101] transition-colors cursor-pointer';
      const ETAG_KEY   = 'bltDesignIssuesEtag';
      const CACHE_KEY  = 'bltDesignIssuesCache';
      const BASE_URL   = 'https://api.github.com/repos/{REPO}/issues?state=open&per_page=100';
      const API_HEADERS = {{ 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' }};

      const cards = Array.from(document.querySelectorAll('article[data-issue-url]'));
      if (!cards.length) return;

      // Load cached data from localStorage
      let cachedEtag = null;
      let issues = null;
      try {{
        cachedEtag = localStorage.getItem(ETAG_KEY);
        const raw = localStorage.getItem(CACHE_KEY);
        if (raw) issues = JSON.parse(raw);
      }} catch (_) {{}}

      // Fetch fresh data, using a conditional request when we have a cached ETag
      try {{
        const firstPageHeaders = cachedEtag
          ? {{ ...API_HEADERS, 'If-None-Match': cachedEtag }}
          : {{ ...API_HEADERS }};
        const resp = await fetch(`${{BASE_URL}}&page=1`, {{ headers: firstPageHeaders }});

        if (resp.status === 304) {{
          // Not modified — reuse cached issues, no rate-limit hit
        }} else if (resp.ok) {{
          const allIssues = await resp.json();
          const newEtag = resp.headers.get('ETag');
          let page = 2;
          while (true) {{
            const next = await fetch(`${{BASE_URL}}&page=${{page}}`, {{ headers: API_HEADERS }});
            if (!next.ok) break;
            const batch = await next.json();
            if (!Array.isArray(batch) || !batch.length) break;
            allIssues.push(...batch);
            if (batch.length < 100) break;
            page++;
          }}
          issues = allIssues;
          try {{
            if (newEtag) localStorage.setItem(ETAG_KEY, newEtag);
            localStorage.setItem(CACHE_KEY, JSON.stringify(issues));
          }} catch (_) {{}}
        }} else {{
          console.error('Failed to fetch live reaction counts:', resp.status, resp.statusText);
        }}
      }} catch (err) {{
        console.error('Failed to fetch live reaction counts:', err);
      }}

      if (!issues) return;

      const byUrl = {{}};
      for (const issue of issues) byUrl[issue.html_url] = issue.reactions || {{}};

      for (const card of cards) {{
        const reactions = byUrl[card.dataset.issueUrl];
        if (!reactions) continue;

        const thumbsCount = parseInt(reactions['+1'], 10) || 0;
        card.dataset.thumbs = thumbsCount;
        const totalReactions = REACTION_LABELS.reduce((sum, [c]) => sum + (parseInt(reactions[c], 10) || 0), 0);
        card.dataset.totalReactions = totalReactions;

        const container = card.querySelector('[aria-label="Reactions"]');
        if (!container) continue;

        let html = '';
        let total = 0;
        for (const [content, emoji] of REACTION_LABELS) {{
          const count = parseInt(reactions[content], 10) || 0;
          if (!count) continue;
          total++;
          if (content === '+1') {{
            html += `<button type="button" class="${{THUMBS_PILL}}" data-thumbs-btn `
                  + `aria-label="Thumbs up this design on GitHub">${{emoji}} <span>${{count}}</span></button>`;
          }} else {{
            html += `<span class="${{PILL}}">${{emoji}} <span>${{count}}</span></span>`;
          }}
        }}
        if (!total) {{
          html = `<a href="${{card.dataset.issueUrl}}" target="_blank" rel="noopener" `
               + `class="inline-flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 `
               + `hover:text-[#E10101] dark:hover:text-[#E10101] transition-colors" `
               + `aria-label="Be the first to react on GitHub">`
               + `<i class="fa-regular fa-face-smile" aria-hidden="true"></i>Be the first to react!</a>`;
        }}
        container.innerHTML = html;
      }}
    }})();

    // Contest tab navigation
    (function () {{
      const tabs = document.querySelectorAll('[role="tab"][data-tab]');
      const panels = document.querySelectorAll('.contest-panel');

      function switchTab(targetId) {{
        panels.forEach(panel => {{ panel.hidden = panel.id !== `contest-${{targetId}}`; }});
        tabs.forEach(tab => {{
          const isActive = tab.dataset.tab === targetId;
          tab.setAttribute('aria-selected', String(isActive));
          tab.classList.toggle('border-[#E10101]', isActive);
          tab.classList.toggle('text-[#E10101]', isActive);
          tab.classList.toggle('font-semibold', isActive);
          tab.classList.toggle('border-transparent', !isActive);
          tab.classList.toggle('text-gray-600', !isActive);
          tab.classList.toggle('dark:text-gray-300', !isActive);
        }});
      }}

      tabs.forEach(tab => {{ tab.addEventListener('click', () => switchTab(tab.dataset.tab)); }});
      if (tabs.length) switchTab(tabs[0].dataset.tab);
    }})();

    // Countdown timer to nearest contest deadline
    (function () {{
      const deadline = new Date('{earliest_deadline}').getTime();
      const els = {{
        days:  document.getElementById('cd-days'),
        hours: document.getElementById('cd-hours'),
        mins:  document.getElementById('cd-mins'),
        secs:  document.getElementById('cd-secs'),
      }};
      if (!els.days) return;
      function pad(n) {{ return String(n).padStart(2, '0'); }}
      function tick() {{
        const diff = deadline - Date.now();
        if (diff <= 0) {{
          els.days.textContent = '00';
          els.hours.textContent = '00';
          els.mins.textContent  = '00';
          els.secs.textContent  = '00';
          clearInterval(intervalId);
          return;
        }}
        const d = Math.floor(diff / 86400000);
        const h = Math.floor((diff % 86400000) / 3600000);
        const m = Math.floor((diff % 3600000)  /   60000);
        const s = Math.floor((diff %   60000)  /    1000);
        els.days.textContent  = pad(d);
        els.hours.textContent = pad(h);
        els.mins.textContent  = pad(m);
        els.secs.textContent  = pad(s);
      }}
      tick();
      const intervalId = setInterval(tick, 1000);
    }})();
  </script>
</body>
</html>"""


def main() -> None:
    last_updated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    contests_data = []

    # Fetch all open issues once to use for the title-prefix fallback across all contests
    print(f"Fetching all open issues from {REPO}…")
    all_issues = github_request(f"/repos/{REPO}/issues?state=open")
    print(f"  Found {len(all_issues)} open issues total.")

    for contest in CONTESTS:
        label = contest["label"]
        title_prefix = contest["title_prefix"]
        print(f"\nFetching issues for contest '{contest['name']}' (label: {label})…")

        issues = github_request(f"/repos/{REPO}/issues?state=open&labels={label}")
        print(f"  Found {len(issues)} labelled submissions.")

        # Also pick up issues with the correct title prefix that may be missing the label
        seen = {i["number"] for i in issues}
        for issue in all_issues:
            if issue["number"] not in seen and issue.get("title", "").startswith(title_prefix):
                issues.append(issue)
                seen.add(issue["number"])
                print(f"  Picked up unlabelled issue #{issue['number']}: {issue.get('title', '')[:60]}")

        print(f"  Total submissions: {len(issues)}.")

        winner_cards = []
        non_winner_cards = []
        for issue in issues:
            number = issue["number"]
            print(f"  Processing issue #{number}: {issue.get('title', '')[:60]}")
            reactions = fetch_reactions(number)
            last_comment = fetch_last_comment(number)
            label_names = [lb["name"] for lb in issue.get("labels", [])]
            is_winner = WINNER_LABEL in label_names
            card_html = build_card(issue, reactions, last_comment,
                                   is_winner=is_winner, title_prefix=title_prefix)
            if is_winner:
                winner_cards.append(card_html)
            else:
                non_winner_cards.append(card_html)

        # Winners always appear first
        cards = winner_cards + non_winner_cards
        contests_data.append({
            "config": contest,
            "cards": cards,
            "total": len(cards),
            "winner_count": len(winner_cards),
        })

    page_html = build_html(contests_data, last_updated)

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page_html)
    print(f"\nWritten → {out_path}")


if __name__ == "__main__":
    main()
