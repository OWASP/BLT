#!/usr/bin/env python3
"""
build_showcase.py
-----------------
Builds the BLT Design Contest showcase pages (index.html, show-all-entries.html and one page per
contest) from:

- open issues of blt-design-contest on git.owaspblt.org, read from the public issue ledger with
  scripts/forkmesh/ledger.py. A submission is attributed to the project (label
  `blt-design-contest` / `project:blt-design-contest`, or title prefix `[blt-design-contest]`) or
  carries a contest label; its contest comes from the contest label (e.g. `logo-submission`), else
  from the contest title prefix (e.g. `[Logo]`). Bodies follow issue-templates/*.md.
- data/gitlab-archive.json: the frozen GitLab-era submissions (gitlab.com/owasp-blt is closed),
  shown with their final GitLab vote counts and marked as archived.

Votes are the forge's native issue votes (signed-in users press Vote on the issue) plus distinct
`+1` comments from other accounts. Issues labelled WINNER_LABEL are pinned first.

Usage:
  python scripts/build_showcase.py [--out DIR] [--offline]
    --out DIR   output directory (default: public/)
    --offline   skip git.owaspblt.org (archive only), for local previews
  FORKMESH_URL overrides the forge instance.
"""

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_DIR, "..", "scripts", "forkmesh"))

import ledger  # noqa: E402  (scripts/forkmesh/ledger.py)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT = "blt-design-contest"
PROJECT_URL = f"{ledger.WEB_URL}/tree/main/{PROJECT}"
ISSUES_URL = f"{ledger.WEB_URL}/issues?label={PROJECT}"
NEW_ISSUE_URL = f"{ledger.WEB_URL}/issues/new"
TEMPLATES_URL = f"{ledger.WEB_URL}/blob/main/{PROJECT}/issue-templates"
ARCHIVE_PATH = os.path.join(PROJECT_DIR, "data", "gitlab-archive.json")

# Label applied to the winning submission(s) in any contest
WINNER_LABEL = "winner"

# All active design contests.  Each entry drives one tab on the showcase page.
CONTESTS = [
    {
        "id": "blt-tshirt",
        "name": "BLT T-Shirt Design Contest",
        "label": "design-submission",
        "title_prefix": "[Design]",
        "template": "design-submission.md",
        "description": "Design a T-shirt or apparel for OWASP BLT.",
        "prize": "$25",
        "deadline": "2026-03-01T00:00:00Z",
        "deadline_display": "March 1, 2026",
        "status": "selecting_winner",
        "icon": "fa-solid fa-shirt",
    },
    {
        "id": "blt-logo",
        "name": "BLT Logo Contest",
        "label": "logo-submission",
        "title_prefix": "[Logo]",
        "template": "logo-submission.md",
        "description": "Design a new logo for OWASP BLT and all its repositories.",
        "prize": "$25",
        "deadline": "2026-04-15T00:00:00Z",
        "deadline_display": "April 15, 2026",
        "icon": "fa-solid fa-brush",
    },
    {
        "id": "blt-homepage",
        "name": "BLT Homepage Design",
        "label": "homepage-submission",
        "title_prefix": "[Homepage]",
        "template": "homepage-submission.md",
        "description": "Design the new homepage for the OWASP BLT website.",
        "prize": "$25",
        "deadline": "2026-04-15T00:00:00Z",
        "deadline_display": "April 15, 2026",
        "icon": "fa-solid fa-house",
    },
    {
        "id": "blt-video-meme",
        "name": "BLT Video Meme",
        "label": "video-meme-submission",
        "title_prefix": "[Video Meme]",
        "template": "video-meme-submission.md",
        "description": "Design a meme video for OWASP BLT.",
        "prize": "$10",
        "deadline": "2026-04-15T00:00:00Z",
        "deadline_display": "April 15, 2026",
        "icon": "fa-solid fa-circle-play",
    },
    {
        "id": "blt-welcome-video",
        "name": "BLT Welcome Video",
        "label": "welcome-video-submission",
        "title_prefix": "[Welcome Video]",
        "template": "welcome-video-submission.md",
        "description": "Design a welcome video for beginners giving a walkthrough explanation of the OWASP BLT ecosystem.",
        "prize": "$20",
        "deadline": "2026-04-15T00:00:00Z",
        "deadline_display": "April 15, 2026",
        "icon": "fa-solid fa-photo-film",
    },
    {
        "id": "appsecil-tshirt",
        "name": "AppSecIL 2026 T-Shirt Design Contest",
        "label": "appsecil-tshirt-submission",
        "title_prefix": "[AppSecIL]",
        "template": "appsecil-tshirt-submission.md",
        "description": "Design a T-shirt for OWASP AppSec Israel — one of the region's leading cybersecurity conferences, bringing together 1,000+ security professionals, developers, and open source contributors.",
        "long_description": (
            "Israel's premier application security event is back! "
            "OWASP AppSec Israel is one of the leading cybersecurity conferences in the region, "
            "bringing together experts, professionals, and enthusiasts from around the world. "
            "Join 1,000+ developers, DevOps engineers, architects, security specialists, product leaders, "
            "and other industry professionals dedicated to advancing the future of application security. "
            "Whether you build, secure, or manage software, this event is designed for you. "
            "Hear from top speakers sharing the latest security insights. "
            "Join hands-on sessions and network with leading industry experts. "
            "A diverse audience awaits you: security and cyber defense professionals, developers, "
            "software engineers, researchers, industry leaders, and executives."
        ),
        "prize": "",
        "deadline": "2026-04-12T00:00:00Z",
        "deadline_display": "April 12, 2026",
        "icon": "fa-solid fa-shirt",
        "google_form_url": "https://docs.google.com/forms/d/e/1FAIpQLSej8eFeNBeUhOyKmDffvv9y0QLIoWCgt6szrFVZjxDaY-8VOw/viewform",
    },
]

# Backward-compatible aliases (used by helpers that pre-date multi-contest support)
LABEL = CONTESTS[0]["label"]
TITLE_PREFIX = CONTESTS[0]["title_prefix"]

PROJECT_PREFIX_RE = re.compile(r"^\s*(?:\[\s*blt-design-contest\s*\]|blt-design-contest\s*:)\s*", re.IGNORECASE)
PLUS_ONE_RE = re.compile(r"^\s*(?:\+1|:\+1:|:thumbsup:|\U0001F44D)\s*$")
IMAGE_EXT_RE = re.compile(r"\.(?:png|jpe?g|gif|webp|svg|avif)(?:\?.*)?$", re.IGNORECASE)
MARKDOWN_IMAGE_RE = re.compile(r"!\[.*?\]\(((?:https?://|/)[^)\s]+)")
HTML_IMAGE_RE = re.compile(r'<img\s[^>]*src="((?:https?://|/)[^"]+)"', re.IGNORECASE)
COMMENT_STRIP_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")
COMMENT_STRIP_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MAX_COMMENT_LENGTH = 120


def absolute_url(url: str) -> str:
    """Forge uploads may be site-relative ("/..."); make them absolute."""
    url = (url or "").strip()
    return f"{ledger.DEFAULT_URL}{url}" if url.startswith("/") and not url.startswith("//") else url


def strip_project_prefix(title: str) -> str:
    return PROJECT_PREFIX_RE.sub("", title or "", count=1).strip()


def contest_for(record: dict) -> dict | None:
    """The contest of an issue record: its contest label, else its contest title prefix."""
    labels = ledger.labels(record)
    for contest in CONTESTS:
        if contest["label"] in labels:
            return contest
    title = strip_project_prefix(record.get("title")).lower()
    for contest in CONTESTS:
        if title.startswith(contest["title_prefix"].lower()):
            return contest
    return None


def submission_contest(record: dict) -> dict | None:
    """The contest of an open submission issue, or None when the issue is not one."""
    if not ledger.is_open(record):
        return None
    contest = contest_for(record)
    if not contest:
        return None
    if contest["label"] in ledger.labels(record) or PROJECT in ledger.issue_projects(record):
        return contest
    return None


def _name(event: dict) -> str:
    return event.get("authorName") or event.get("author") or ""


def plus_one_voters(record: dict) -> list[str]:
    """Distinct accounts (other than the issue author) that commented just `+1`."""
    author = _name(record)
    names = []
    for comment in ledger.comments(record):
        name = _name(comment)
        if name and name != author and name not in names and PLUS_ONE_RE.match(comment.get("body") or ""):
            names.append(name)
    return names


def vote_total(record: dict) -> int:
    """Native forge votes plus `+1` commenters who did not also press Vote."""
    native = ledger.voters(record)
    return ledger.vote_count(record) + len([n for n in plus_one_voters(record) if n not in native])


def avatar_url(name: str) -> str:
    return f"{ledger.DEFAULT_URL}/api/accounts/{name.lower()}/avatar" if name else ""


def attachment_images(record: dict) -> list[str]:
    """Image URLs attached to the issue's opening event (defensive about the record shape)."""
    found = []
    for event in ledger.events(record, "open"):
        for item in event.get("attachments") or []:
            url = item if isinstance(item, str) else (item or {}).get("url") or (item or {}).get("path") or ""
            if isinstance(url, str) and IMAGE_EXT_RE.search(url):
                found.append(absolute_url(url))
    return found


def normalize_forge_issue(record: dict) -> dict:
    """An issue ledger record in the shape the render helpers use."""
    number = int(record.get("number") or 0)
    name = _name(record)
    body = ledger.body(record)
    comments = ledger.comments(record)
    plus_ones = set(plus_one_voters(record))
    talk = [c for c in comments if not (PLUS_ONE_RE.match(c.get("body") or "") and _name(c) in plus_ones)]
    last = talk[-1] if talk else None
    fields = parse_issue_body(body)
    preview = extract_preview_url(fields, body) or next(iter(attachment_images(record)), "")
    return {
        "number": number,
        "title": strip_project_prefix(record.get("title")),
        "body": body,
        "html_url": ledger.issue_url(number),
        "created_at": ledger.ms_to_iso(record.get("createdAt")) or "",
        "comments": len(talk),
        "labels": [{"name": label} for label in ledger.labels(record)],
        "user": {"login": name or "unknown", "html_url": ledger.profile_url(name) or "#",
                 "avatar_url": avatar_url(name)},
        "votes": vote_total(record),
        "last_comment": {
            "body": last.get("body") or "",
            "user": {"login": _name(last), "html_url": ledger.profile_url(_name(last)) or "#",
                     "avatar_url": avatar_url(_name(last))},
        } if last else None,
        "preview_url": preview,
        "design_url": extract_design_url(fields),
        "category": extract_category(fields),
        "description": extract_description(fields),
        "archived": False,
    }


def load_archive(path: str = ARCHIVE_PATH) -> list[dict]:
    """The frozen GitLab-era entries (data/gitlab-archive.json), or [] when the file is absent."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle).get("entries") or []
    except FileNotFoundError:
        return []


def normalize_archive_entry(entry: dict) -> dict:
    author = entry.get("author") or {}
    last = entry.get("last_comment")
    return {
        "number": int(entry.get("number") or 0),
        "title": entry.get("title") or "Untitled",
        "body": "",
        "html_url": "",
        "created_at": entry.get("created_at") or "",
        "comments": int(entry.get("comments") or 0),
        "labels": [{"name": WINNER_LABEL}] if entry.get("winner") else [],
        "user": {"login": author.get("login") or "unknown", "html_url": author.get("url") or "#",
                 "avatar_url": author.get("avatar") or ""},
        "votes": int(entry.get("votes") or 0),
        "last_comment": {
            "body": last.get("body") or "",
            "user": {"login": last.get("login") or "unknown", "html_url": last.get("url") or "#",
                     "avatar_url": last.get("avatar") or ""},
        } if last else None,
        "preview_url": entry.get("preview_url") or "",
        "design_url": entry.get("design_url") or "",
        "category": entry.get("category") or "Other",
        "description": entry.get("description") or "",
        "archived": True,
    }


def issue_template_url(template: str | None = None) -> str:
    """The issue body to copy (the forge has no issue templates or prefill)."""
    return f"{TEMPLATES_URL}/{template}" if template else f"{TEMPLATES_URL}/README.md"


def is_winner(issue: dict) -> bool:
    return WINNER_LABEL in [label["name"] for label in issue.get("labels", [])]


def display_title(issue: dict, title_prefix: str) -> str:
    title = (issue.get("title") or "").strip()
    if title_prefix and title.lower().startswith(title_prefix.lower()):
        title = title[len(title_prefix):].strip()
    return title or "Untitled submission"


def entry_link(issue: dict, fallback: str = "#") -> str:
    """Where a card links: the forge issue, else (archived) the preview, else ``fallback``."""
    return issue.get("html_url") or issue.get("preview_url") or fallback

def strip_comments(body: str) -> str:
    return re.sub(r"<!--.*?-->", "", (body or "").replace("\r\n", "\n"), flags=re.DOTALL)


def parse_issue_body(body: str) -> dict:
    """
    Extract the fields of an issue body written from issue-templates/*.md: each answer sits below
    a `### Field Label` heading (`##` also works). HTML comments (template hints) are dropped.
    Keys are the lower-cased labels with runs of other characters turned into `_`
    (`Design / Prototype Link` -> `design_prototype_link`).
    """
    fields: dict[str, str] = {}
    if not body:
        return fields
    body = strip_comments(body)
    for section in re.split(r"\n#{2,3}[ \t]+", "\n" + body):
        lines = section.strip().splitlines()
        if not lines:
            continue
        key = re.sub(r"[^a-z0-9]+", "_", lines[0].strip().lower()).strip("_")
        if key:
            fields[key] = "\n".join(lines[1:]).strip()
    return fields


def extract_preview_url(fields: dict, body: str) -> str:
    """Find the preview image URL from parsed fields or the body (template hints ignored)."""
    body = strip_comments(body)
    for key in ("preview_image", "preview_image_url", "preview_url"):
        val = fields.get(key, "").strip()
        if not val:
            continue
        for regex in (MARKDOWN_IMAGE_RE, HTML_IMAGE_RE):
            m = regex.search(val)
            if m:
                return absolute_url(m.group(1))
        m = re.search(r"https?://\S+", val)
        if m:
            return m.group(0)

    for regex in (MARKDOWN_IMAGE_RE, HTML_IMAGE_RE):
        m = regex.search(body or "")
        if m:
            return absolute_url(m.group(1))

    # Fallback: first bare URL ending in an image extension
    m = re.search(r"(https?://\S+\.(?:png|jpg|jpeg|gif|webp|svg))", body or "", re.IGNORECASE)
    return m.group(1) if m else ""


def extract_design_url(fields: dict) -> str:
    for key in ("design_prototype_link", "design_source_file_link", "design_url", "prototype_link"):
        m = re.search(r"https?://[^\s)>\]]+", fields.get(key, ""))
        if m and m.group(0) not in ("https://", "http://"):
            return m.group(0)
    return ""


def extract_category(fields: dict) -> str:
    value = fields.get("design_category") or fields.get("category") or next(
        (v for k, v in fields.items() if k.endswith("_category") and v), "")
    for line in value.splitlines():
        line = re.sub(r"^[-*]\s+(?:\[[ xX]\]\s*)?", "", line.strip()).strip()
        if line:
            return line
    return "Other"


def extract_description(fields: dict) -> str:
    """The description as plain text (not escaped), at most 200 characters."""
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
    return desc
def build_card(issue: dict, title_prefix: str = TITLE_PREFIX) -> str:
    """Return the HTML card markup for a single submission (forge issue or archived entry)."""
    number = issue["number"]
    archived = bool(issue.get("archived"))
    winner = is_winner(issue)
    title = html.escape(display_title(issue, title_prefix))
    issue_url = html.escape(issue.get("html_url") or "")
    link = html.escape(entry_link(issue))
    created_at_iso = html.escape(issue.get("created_at", ""))
    created = created_at_iso[:10]  # UTC date used as static fallback
    user = issue.get("user", {})
    author_login = html.escape(user.get("login", "unknown"))
    author_url = html.escape(user.get("html_url", "#"))
    author_avatar = html.escape(user.get("avatar_url", ""))

    preview_url = html.escape(issue.get("preview_url", ""))
    design_url = html.escape(issue.get("design_url", ""))
    category = html.escape(issue.get("category") or "Other")
    description = html.escape(issue.get("description", ""))
    comment_count = int(issue.get("comments", 0) or 0)
    votes = int(issue.get("votes", 0) or 0)

    # Last comment snippet
    comment_block = ""
    last_comment = issue.get("last_comment")
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
            count_text = f'{comment_count} comment{"s" if comment_count != 1 else ""} · ' if comment_count > 0 else ''
            count_label = (
                f'<a href="{issue_url}" target="_blank" rel="noopener" '
                f'class="hover:text-[#E10101] transition-colors">{count_text}</a>'
                if issue_url else count_text
            )
            comment_block = (
                f'<div class="flex items-start gap-1.5 text-xs text-gray-400 dark:text-gray-500">'
                f'{c_avatar_img}'
                f'<span>{count_label}'
                f'<a href="{c_url}" target="_blank" rel="noopener" '
                f'class="font-medium text-gray-500 dark:text-gray-400 hover:text-[#E10101] transition-colors">'
                f'{c_login}</a>: {c_body_escaped}</span>'
                f'</div>'
            )
    if not comment_block and not archived:
        comment_block = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'class="inline-flex items-center gap-1.5 text-xs '
            f'text-gray-400 dark:text-gray-500 hover:text-[#E10101] '
            f'dark:hover:text-[#E10101] transition-colors" '
            f'aria-label="Be the first to comment on the issue">'
            f'<i class="fa-regular fa-comment" aria-hidden="true"></i>'
            f'Be the first to comment!</a>'
        )

    # Votes: generated counts; voting happens on the forge issue
    vote_word = f'vote{"" if votes == 1 else "s"}'
    pill = ('inline-flex items-center gap-1 text-sm bg-gray-100 dark:bg-gray-700 '
            'text-gray-700 dark:text-gray-200 rounded-full px-2 py-0.5')
    if archived:
        vote_html = (
            f'<span class="{pill}" title="Final GitLab vote count (archived)">'
            f'<i class="fa-solid fa-thumbs-up" aria-hidden="true"></i> <span>{votes}</span>'
            f'<span class="sr-only"> {vote_word}</span></span>'
            f'<span class="inline-flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">'
            f'<i class="fa-solid fa-box-archive" aria-hidden="true"></i> GitLab archive</span>'
        )
    else:
        vote_html = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'class="{pill} hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-[#E10101] transition-colors" '
            f'aria-label="{votes} {vote_word}. Vote on the issue">'
            f'<i class="fa-solid fa-thumbs-up" aria-hidden="true"></i> <span>{votes}</span></a>'
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'class="text-xs text-gray-400 dark:text-gray-500 hover:text-[#E10101] transition-colors">'
            f'Vote on the issue</a>'
        )

    # Preview image
    if preview_url:
        preview_block = (
            f'<a href="{link}" target="_blank" rel="noopener" '
            f'   class="block overflow-hidden aspect-square bg-gray-100 dark:bg-gray-700">'
            f'  <img src="{preview_url}" alt="{title} preview" loading="lazy" '
            f'       class="w-full h-full object-cover transition-transform duration-300 '
            f'              group-hover:scale-105" />'
            f'</a>'
        )
    else:
        preview_block = (
            f'<a href="{link}" target="_blank" rel="noopener" '
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

    if archived:
        issue_button = ""  # the GitLab issue is gone; the header shows its number
        title_html = title
    else:
        issue_button = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'class="inline-flex items-center gap-1 text-sm font-medium '
            f'border border-[#E10101] text-[#E10101] rounded-md px-3 py-1 '
            f'hover:bg-[#E10101] hover:text-white transition-colors" '
            f'aria-label="View issue #{number}">'
            f'<i class="fa-solid fa-code-branch" aria-hidden="true"></i> Issue</a>'
        )
        title_html = (f'<a href="{issue_url}" target="_blank" rel="noopener" '
                      f'class="hover:text-[#E10101] transition-colors">{title}</a>')

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
    if winner:
        winner_badge = (
            '<div class="absolute top-2 left-2 z-10 flex items-center gap-1.5 '
            'bg-amber-400 text-amber-900 text-xs font-bold px-2.5 py-1 '
            'rounded-full shadow-md pointer-events-none">'
            '<i class="fa-solid fa-trophy" aria-hidden="true"></i> Winner</div>'
        )
        winner_ring = " ring-2 ring-amber-400 ring-offset-2 dark:ring-offset-[#111827]"
        winner_attr = ' data-winner="true"'
    archived_attr = ' data-archived="true"' if archived else ""
    number_label = f"GitLab #{number}" if archived else f"#{number}"

    return f"""
    <article class="group relative bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm border
                    border-[#E5E5E5] dark:border-gray-700 overflow-hidden
                    flex flex-col hover:shadow-md transition-shadow{winner_ring}"
             data-votes="{votes}"
             data-comments="{comment_count}"
             data-issue-url="{issue_url}"{winner_attr}{archived_attr}
             aria-label="Contest submission: {title}">
      {winner_badge}
      {preview_block}
      <div class="p-5 flex flex-col gap-3 flex-1">
        <!-- Category + issue number -->
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <span class="text-xs font-medium px-2 py-0.5 rounded-full {cat_colour}">{category}</span>
          <span class="text-xs text-gray-400 dark:text-gray-500">{number_label} · <time class="sub-date" datetime="{created_at_iso}">{created}</time></span>
        </div>

        <!-- Title -->
        <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100 leading-snug">
          {title_html}
        </h2>

        <!-- Description -->
        <p class="text-sm text-gray-600 dark:text-gray-300 flex-1">{description or "No description provided."}</p>

        <!-- Designer -->
        <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          {'<img src="' + author_avatar + '" alt="" class="w-6 h-6 rounded-full" aria-hidden="true" />' if author_avatar else '<i class="fa-solid fa-user-circle text-lg" aria-hidden="true"></i>'}
          <a href="{author_url}" target="_blank" rel="noopener"
             class="text-[#E10101] hover:underline font-medium">{author_login}</a>
        </div>
        <!-- Last comment -->
        {comment_block}
        <!-- Footer: votes + design link -->
        <div class="flex items-center justify-between gap-2 flex-wrap pt-2
                    border-t border-[#E5E5E5] dark:border-gray-700">
          <div class="flex items-center gap-2 flex-wrap" aria-label="Votes">
            {vote_html}
          </div>
          <div class="flex items-center gap-3">
            {design_link}
            {issue_button}
          </div>
        </div>
      </div>
    </article>"""


def build_contest_section(contest: dict, cards: list[str], total: int,
                          winner_count: int = 0) -> str:
    """Return the HTML panel for one contest tab (without wrapping <main>)."""
    cid = html.escape(contest["id"])
    name = html.escape(contest["name"])
    description = html.escape(contest.get("long_description") or contest["description"])
    prize = html.escape(contest["prize"])
    deadline_display = html.escape(contest["deadline_display"])
    submit_url = html.escape(issue_template_url(contest["template"]))
    title_prefix = html.escape(contest["title_prefix"])
    icon = contest["icon"]
    cstatus = contest.get("status", "active")
    ends_label = "Ended" if cstatus == "selecting_winner" else "Ends"
    google_form_url = html.escape(contest.get("google_form_url", ""))

    prize_html = (
        f'<span class="inline-flex items-center gap-1 text-[#E10101]">'
        f'<i class="fa-solid fa-trophy" aria-hidden="true"></i> {prize} prize</span>'
        if prize else ""
    )
    google_form_html = (
        f'<div class="mt-3 text-sm text-gray-500 dark:text-gray-400">'
        f'Submit via BLT below, or use the '
        f'<a href="{google_form_url}" target="_blank" rel="noopener"'
        f' class="text-[#E10101] hover:underline font-medium">official Google Form</a>'
        f" as an alternative.</div>"
        if google_form_url else ""
    )

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
              {prize_html}
              <span class="inline-flex items-center gap-1 text-[#E10101]">
                <i class="fa-solid fa-calendar-day" aria-hidden="true"></i> {ends_label} {deadline_display}
              </span>
              <span class="inline-flex items-center gap-1 text-gray-500 dark:text-gray-400">
                <i class="fa-solid fa-images" aria-hidden="true"></i>
                {total} submission{'' if total == 1 else 's'}
              </span>
            </div>
            <p class="mt-3 text-sm text-gray-500 dark:text-gray-400">
              To enter, copy the <a href="{submit_url}" target="_blank" rel="noopener"
              class="text-[#E10101] hover:underline font-medium">submission template</a> into a
              <a href="{NEW_ISSUE_URL}" target="_blank" rel="noopener"
              class="text-[#E10101] hover:underline font-medium">new issue</a> on git.owaspblt.org
              titled <code>[blt-design-contest] {title_prefix} ...</code>. To vote, open a submission's
              issue and press Vote (signed in), or comment <code>+1</code>.
            </p>
            {google_form_html}
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
        <button id="sort-votes-{cid}" type="button"
                class="inline-flex items-center gap-2 border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-200 hover:border-[#E10101] hover:text-[#E10101]
                       text-sm font-semibold px-4 py-2 rounded-md transition-colors"
                aria-pressed="false"
                data-sort="votes" data-contest="{cid}">
          <i class="fa-solid fa-arrow-down-wide-short" aria-hidden="true"></i>
          By votes
        </button>
        <button id="sort-comments-{cid}" type="button"
                class="inline-flex items-center gap-2 border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-200 hover:border-[#E10101] hover:text-[#E10101]
                       text-sm font-semibold px-4 py-2 rounded-md transition-colors"
                aria-pressed="false"
                data-sort="comments" data-contest="{cid}">
          <i class="fa-solid fa-arrow-down-wide-short" aria-hidden="true"></i>
          By comments
        </button>
      </div>

      <!-- Cards grid -->
      <div id="cards-grid-{cid}"
           class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards_html}
      </div>

    </div>"""



def entry_summaries(contests_data: list[dict]) -> list[dict]:
    """Every submission of every contest (escaped for HTML), newest first."""
    entries = []
    for d in contests_data:
        c = d["config"]
        contest_page = f'{c["id"]}.html'
        for issue in d.get("issues", []):
            created_at = issue.get("created_at", "")
            try:
                submitted_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            archived = bool(issue.get("archived"))
            entries.append({
                "contest_id": html.escape(c["id"]),
                "contest_name": html.escape(c["name"]),
                "contest_url": html.escape(contest_page),
                "title": html.escape(display_title(issue, c.get("title_prefix", ""))),
                "link": html.escape(entry_link(issue, contest_page)),
                "issue_url": html.escape(issue.get("html_url") or ""),
                "archived": archived,
                "number": issue.get("number"),
                "preview_url": html.escape(issue.get("preview_url", "")),
                "submitted_iso": html.escape(created_at),
                "submitted_fallback": html.escape(created_at[:10]),
                "submitted_dt": submitted_dt,
            })
    entries.sort(key=lambda item: item["submitted_dt"], reverse=True)
    return entries


def summary_card(item: dict, aspect: str = "aspect-square") -> str:
    """A compact card (homepage "Recent Submissions" and show-all-entries.html)."""
    if item["preview_url"]:
        preview_block = (
            f'<a href="{item["link"]}" target="_blank" rel="noopener" '
            f'   class="block overflow-hidden {aspect} bg-gray-100 dark:bg-gray-700">'
            f'  <img src="{item["preview_url"]}" alt="{item["title"]} preview" loading="lazy" '
            f'       class="w-full h-full object-cover transition-transform duration-300 '
            f'              group-hover:scale-105" />'
            f'</a>'
        )
    else:
        preview_block = (
            f'<a href="{item["link"]}" target="_blank" rel="noopener" '
            f'   class="flex items-center justify-center {aspect} '
            f'          bg-gray-100 dark:bg-gray-700 text-gray-400">'
            f'  <i class="fa-solid fa-image text-3xl" aria-hidden="true"></i>'
            f'</a>'
        )
    if item["archived"]:
        issue_button = (
            f'<span class="inline-flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">'
            f'<i class="fa-solid fa-box-archive" aria-hidden="true"></i> GitLab #{item["number"]} (archived)</span>'
        )
    else:
        issue_button = (
            f'<a href="{item["issue_url"]}" target="_blank" rel="noopener" '
            f'class="inline-flex items-center gap-1 text-sm font-medium '
            f'border border-[#E10101] text-[#E10101] rounded-md px-3 py-1 '
            f'hover:bg-[#E10101] hover:text-white transition-colors">'
            f'<i class="fa-solid fa-code-branch" aria-hidden="true"></i> Issue</a>'
        )
    return f"""
        <article class="group bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm border
                       border-[#E5E5E5] dark:border-gray-700 overflow-hidden
                       hover:shadow-lg hover:border-[#E10101] transition-all duration-200"
                 data-contest="{item["contest_id"]}">
          <div class="h-1.5 bg-gradient-to-r from-[#E10101] to-red-400"></div>
          {preview_block}
          <div class="p-5 flex flex-col gap-3">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <span class="text-xs font-medium px-2 py-0.5 rounded-full bg-[#feeae9] dark:bg-red-900/30 text-[#E10101]">{item["contest_name"]}</span>
              <span class="text-xs text-gray-400 dark:text-gray-500">
                <time class="sub-date" datetime="{item["submitted_iso"]}">{item["submitted_fallback"]}</time>
              </span>
            </div>
            <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100 leading-snug">
              <a href="{item["link"]}" target="_blank" rel="noopener"
                 class="hover:text-[#E10101] transition-colors">{item["title"]}</a>
            </h3>
            <div class="flex items-center justify-between gap-3 pt-2
                        border-t border-[#E5E5E5] dark:border-gray-700">
              <a href="{item["contest_url"]}"
                 class="text-sm text-gray-500 dark:text-gray-400 hover:text-[#E10101] transition-colors">
                Open Contest
              </a>
              {issue_button}
            </div>
          </div>
        </article>"""


def build_html(contests_data: list[dict], last_updated: str) -> str:
    """Return the complete index.html (homepage) as a string.

    ``contests_data`` is a list of dicts, each with keys:
      - ``config``  – the CONTESTS entry dict
      - ``cards``   – list of card HTML strings (winners first)
      - ``total``   – submission count for that contest
      - ``issues``  – raw issue payloads for that contest
    """
    total_all = sum(d["total"] for d in contests_data)

    # Build contest summary cards for the homepage
    contest_cards_html = ""
    for d in contests_data:
        c = d["config"]
        cid = html.escape(c["id"])
        cname = html.escape(c["name"])
        cdesc = html.escape(c["description"])
        cprize = html.escape(c["prize"])
        cdeadline = html.escape(c["deadline_display"])
        ctotal = d["total"]
        icon = c["icon"]
        page_url = f"{cid}.html"
        cstatus = c.get("status", "active")
        if cstatus == "selecting_winner":
            status_badge = (
                '<span class="inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full'
                ' bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">'
                'Ended \u2013 Selecting Winner'
                '</span>'
            )
            ends_text = f"Ended {cdeadline}"
        else:
            status_badge = (
                '<span class="inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full'
                ' bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">'
                'Active'
                '</span>'
            )
            ends_text = f"Ends {cdeadline}"

        contest_cards_html += f"""
        <a href="{page_url}"
           class="group block bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm
                  border border-[#E5E5E5] dark:border-gray-700 overflow-hidden
                  hover:shadow-lg hover:border-[#E10101] transition-all duration-200">
          <div class="h-1.5 bg-gradient-to-r from-[#E10101] to-red-400"></div>
          <div class="p-6 sm:p-7">
            <div class="flex items-start gap-4 mb-4">
              <div class="w-14 h-14 rounded-xl bg-[#feeae9] dark:bg-red-900/30
                          flex items-center justify-center shrink-0">
                <i class="{icon} text-2xl text-[#E10101]" aria-hidden="true"></i>
              </div>
              <div class="min-w-0">
                <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100 leading-snug">{cname}</h3>
                {status_badge}
              </div>
            </div>
            <p class="text-sm text-gray-600 dark:text-gray-300 mb-5 leading-relaxed">{cdesc}</p>
            <div class="flex items-center gap-4 text-sm font-medium mb-5 flex-wrap">
              {'<span class="inline-flex items-center gap-1.5 text-[#E10101]"><i class="fa-solid fa-trophy" aria-hidden="true"></i> ' + cprize + ' prize</span>' if cprize else ''}
              <span class="inline-flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
                <i class="fa-solid fa-calendar-day" aria-hidden="true"></i> {ends_text}
              </span>
            </div>
            <div class="flex items-center justify-between pt-4
                        border-t border-[#E5E5E5] dark:border-gray-700">
              <div>
                <p class="text-2xl font-black text-[#E10101]">{ctotal}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  submission{'' if ctotal == 1 else 's'}
                </p>
              </div>
              <span class="inline-flex items-center gap-1.5 text-[#E10101] font-semibold text-sm
                           group-hover:gap-2.5 transition-all duration-200">
                View Entries <i class="fa-solid fa-arrow-right" aria-hidden="true"></i>
              </span>
            </div>
          </div>
        </a>"""

    latest_three = entry_summaries(contests_data)[:3]
    if latest_three:
        recent_cards_html = "".join(summary_card(item, "aspect-video") for item in latest_three)
    else:
        recent_cards_html = (
            '<div class="md:col-span-3 bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm '
            'border border-[#E5E5E5] dark:border-gray-700 p-6 text-center '
            'text-sm text-gray-500 dark:text-gray-400">'
            'No recent submissions available.'
            '</div>'
        )

    # For the hero submit URL, use the first contest
    first_submit_url = html.escape(issue_template_url())

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <meta name="description" content="BLT Design Contest — open design showcases for BLT and the broader open source security community. Browse entries, vote for your favourites, and submit your own!" />
  <title>BLT Design Contests</title>

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
  <a href="#contests"
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
        <a href="index.html" class="flex items-center gap-2 shrink-0 group" aria-label="BLT Design Contests home">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-md
                       bg-[#E10101] text-white font-black text-sm select-none">BLT</span>
          <span class="font-semibold text-gray-900 dark:text-gray-100 hidden sm:block">
            Design Contests
          </span>
        </a>

        <!-- Centre nav links -->
        <div class="hidden md:flex items-center gap-6 text-sm font-medium">
          <a href="#contests"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors">
            Contests
          </a>
          <a href="#how-it-works"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors">
            How it works
          </a>
          <a href="{ISSUES_URL}" target="_blank" rel="noopener"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors
                    inline-flex items-center gap-1">
            <i class="fa-solid fa-list-check" aria-hidden="true"></i> Issues
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
        Open to Everyone
      </span>
      <h1 class="text-4xl sm:text-5xl font-black text-gray-900 dark:text-gray-50 leading-tight mb-4">
        BLT Design Contests
      </h1>
      <p class="max-w-2xl mx-auto text-lg text-gray-600 dark:text-gray-300 mb-8">
        Anyone passionate about BLT, open source, and application security is welcome to participate.
        Browse entries, vote for your favourites on git.owaspblt.org, and submit your own design.
      </p>
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
          <h3 class="font-semibold text-gray-900 dark:text-gray-100">Submit your design</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Open a new issue on git.owaspblt.org and paste the contest's
            <a href="{TEMPLATES_URL}/README.md" target="_blank" rel="noopener" class="text-[#E10101] hover:underline">submission template</a>
            into it — no prior experience needed. Add a preview image, a short description, and a link to your design.
          </p>
        </li>
        <li class="flex flex-col items-center text-center gap-3">
          <span class="w-12 h-12 rounded-full bg-[#feeae9] dark:bg-red-900/30 text-[#E10101]
                       flex items-center justify-center text-xl font-black">2</span>
          <h3 class="font-semibold text-gray-900 dark:text-gray-100">Everyone votes</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Anyone — from seasoned security pros to open source newcomers — can sign in and press
            Vote on a submission's issue (or comment <code>+1</code>). The showcase shows the counts from its last update.
          </p>
        </li>
        <li class="flex flex-col items-center text-center gap-3">
          <span class="w-12 h-12 rounded-full bg-[#feeae9] dark:bg-red-900/30 text-[#E10101]
                       flex items-center justify-center text-xl font-black">3</span>
          <h3 class="font-semibold text-gray-900 dark:text-gray-100">Showcase updates</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            The showcase is rebuilt whenever a submission issue is opened, edited, labelled or closed,
            and once a day for new votes.
          </p>
        </li>
      </ol>
    </div>
  </section>

  <!-- ══════════════════════════════════════════
       CONTESTS OVERVIEW
  ══════════════════════════════════════════ -->
  <section id="contests" class="bg-white dark:bg-[#1F2937] border-t border-[#E5E5E5] dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-10">
        <div>
          <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Active Contests</h2>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Pick a contest to browse submissions and vote for your favourites.
          </p>
        </div>
        <p class="text-xs text-gray-400 dark:text-gray-500 shrink-0">
          Last updated {last_updated}
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
        {contest_cards_html}
      </div>

    </div>
  </section>

  <!-- ══════════════════════════════════════════
       RECENT SUBMISSIONS
  ══════════════════════════════════════════ -->
  <section id="recent-submissions" class="bg-gray-50 dark:bg-[#111827] border-t border-[#E5E5E5] dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
      <div class="flex items-center justify-between gap-4 mb-8">
        <div>
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-8">
            <h2 class="text-xl sm:text-2xl font-bold text-gray-900 dark:text-gray-100">Recent Submissions</h2>
            <a href="show-all-entries.html"
              class="inline-flex items-center gap-1.5 text-[#E10101] font-semibold text-sm
                      self-start sm:self-auto whitespace-nowrap
                      hover:gap-2.5 transition-all duration-200">
              View Entries <i class="fa-solid fa-arrow-right" aria-hidden="true"></i>
            </a>
          </div>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Latest 3 entries sorted by submitted time.
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
        {recent_cards_html}
      </div>
    </div>
  </section>

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
        <a href="{PROJECT_URL}" target="_blank" rel="noopener"
           class="hover:text-[#E10101] transition-colors inline-flex items-center gap-1">
          <i class="fa-solid fa-code" aria-hidden="true"></i> Source
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

    // Format submission dates in user's local timezone; cap any future dates to today
    (function () {{
      var now = new Date();
      document.querySelectorAll('time.sub-date').forEach(function (el) {{
        var raw = el.getAttribute('datetime');
        if (!raw) return;
        var d = new Date(raw);
        if (isNaN(d.getTime())) return;
        if (d > now) d = now;
        el.textContent = d.toLocaleDateString(undefined, {{
          year: 'numeric', month: 'short', day: 'numeric'
        }});
      }});
    }})();
  </script>
</body>
</html>"""


def build_show_all_entries_html(contests_data: list[dict], last_updated: str) -> str:
    """Return a standalone page with all submissions in a simple card layout."""
    entries = entry_summaries(contests_data)

    if entries:
        cards = [summary_card(item) for item in entries]
        cards_html = "\n".join(cards)
    else:
        cards_html = (
            '<div class="sm:col-span-2 lg:col-span-3 bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm '
            'border border-[#E5E5E5] dark:border-gray-700 p-6 text-center text-sm '
            'text-gray-500 dark:text-gray-400">No entries available right now.</div>'
        )

    filter_buttons = [
        '<button type="button" data-filter="all" '
        'class="filter-btn inline-flex items-center gap-2 border text-sm font-semibold px-4 py-2 rounded-md transition-colors" '
        'aria-pressed="true">All Contests</button>'
    ]
    for c in CONTESTS:
        filter_buttons.append(
            f'<button type="button" data-filter="{html.escape(c["id"])}" '
            f'class="filter-btn inline-flex items-center gap-2 border text-sm font-semibold px-4 py-2 rounded-md transition-colors" '
            f'aria-pressed="false">{html.escape(c["name"])}</button>'
        )
    filter_buttons_html = "\n        ".join(filter_buttons)

    first_submit_url = html.escape(issue_template_url())

    return f"""<!DOCTYPE html>
    <html lang="en" class="scroll-smooth">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />
    <meta name="description" content="All BLT Design Contest submissions in one place." />
    <title>All Entries - BLT Design Contests</title>

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

    <link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
      integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA=="
      crossorigin="anonymous" referrerpolicy="no-referrer" />

    <style>
    :root {{ --brand: #E10101; }}
    *:focus-visible {{
      outline: 2px solid var(--brand);
      outline-offset: 2px;
    }}
    </style>
    </head>

    <body class="bg-gray-50 dark:bg-[#111827] text-gray-900 dark:text-gray-100 min-h-screen flex flex-col font-sans antialiased">
    <a href="#all-entries"
     class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-[#E10101] focus:text-white focus:rounded-md focus:font-medium">
    Skip to content
    </a>

    <header class="bg-white dark:bg-[#1F2937] border-b border-[#E5E5E5] dark:border-gray-700 sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <nav class="flex items-center justify-between h-16 gap-4" aria-label="Primary navigation">
      <a href="index.html" class="flex items-center gap-2 shrink-0 group" aria-label="BLT Design Contests home">
      <span class="inline-flex items-center justify-center w-8 h-8 rounded-md bg-[#E10101] text-white font-black text-sm select-none">BLT</span>
      <span class="font-semibold text-gray-900 dark:text-gray-100 hidden sm:block">Design Contests</span>
      </a>

      <div class="hidden md:flex items-center gap-6 text-sm font-medium">
      <a href="index.html" class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors inline-flex items-center gap-1.5">
      <i class="fa-solid fa-arrow-left" aria-hidden="true"></i> All Contests
      </a>
      <a href="show-all-entries.html"
       class="text-[#E10101] font-semibold inline-flex items-center gap-1.5"
       aria-current="page">
      <i class="fa-solid fa-images" aria-hidden="true"></i> All Entries
      </a>
      <a href="{ISSUES_URL}" target="_blank" rel="noopener"
       class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors inline-flex items-center gap-1">
      <i class="fa-solid fa-list-check" aria-hidden="true"></i> Issues
      </a>
      </div>

      <a href="index.html#contests"
       class="inline-flex items-center gap-2 bg-[#E10101] hover:bg-red-700 text-white text-sm font-semibold px-4 py-2 rounded-md transition-colors shrink-0">
      <i class="fa-solid fa-plus" aria-hidden="true"></i>
      <span>Choose Contest</span>
      </a>

      <button id="theme-toggle" type="button"
      class="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      aria-label="Toggle dark mode">
      <i class="fa-solid fa-moon dark:hidden" aria-hidden="true"></i>
      <i class="fa-solid fa-sun hidden dark:inline" aria-hidden="true"></i>
      </button>
      </nav>
    </div>
    </header>

    <section class="bg-white dark:bg-[#1F2937] border-b border-[#E5E5E5] dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
      <span class="inline-block mb-4 bg-[#feeae9] dark:bg-red-900/30 text-[#E10101] text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wide">
      Unified Showcase
      </span>
      <h1 class="text-3xl sm:text-4xl font-black text-gray-900 dark:text-gray-50 leading-tight mb-3">
      All Contest Entries
      </h1>
      <p class="max-w-2xl mx-auto text-base sm:text-lg text-gray-600 dark:text-gray-300">
      Browse every current submission from all BLT design contests in one page.
      </p>
      <p class="mt-3 text-xs text-gray-400 dark:text-gray-500">Last updated {last_updated}</p>
    </div>
    </section>

    <main id="all-entries" class="flex-1 bg-gray-50 dark:bg-[#111827] border-t border-[#E5E5E5] dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div class="mb-6">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Entries</h2>
      <p id="entries-status" class="mt-1 text-sm text-gray-500 dark:text-gray-400">Loading entries...</p>
      </div>

      <div class="flex flex-wrap items-center gap-2 mb-8" id="contest-filters" aria-label="Contest filters">
      {filter_buttons_html}
      </div>

      <div id="all-entries-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" aria-live="polite">
      {cards_html}
      <div id="no-filter-results" class="hidden sm:col-span-2 lg:col-span-3 bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm border border-[#E5E5E5] dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400">No entries found for this filter.</div>
      </div>
    </div>
    </main>

    <footer class="bg-white dark:bg-[#1F2937] border-t border-[#E5E5E5] dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500 dark:text-gray-400">
      <p>
      &copy; {datetime.now(timezone.utc).year}
      <a href="https://owasp.org/www-project-blt/" target="_blank" rel="noopener" class="text-[#E10101] hover:underline font-medium">OWASP BLT</a>.
      Content licensed under
      <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener" class="text-[#E10101] hover:underline">CC BY 4.0</a>.
      </p>
      <div class="flex items-center gap-4">
      <a href="index.html" class="hover:text-[#E10101] transition-colors inline-flex items-center gap-1">
      <i class="fa-solid fa-arrow-left" aria-hidden="true"></i> All Contests
      </a>
      <a href="{PROJECT_URL}" target="_blank" rel="noopener" class="hover:text-[#E10101] transition-colors inline-flex items-center gap-1">
      <i class="fa-solid fa-code" aria-hidden="true"></i> Source
      </a>
      </div>
    </div>
    </footer>

    <script>
    const toggle = document.getElementById('theme-toggle');
    const html = document.documentElement;

    if (localStorage.theme === 'dark' ||
      (!('theme' in localStorage) &&
       window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
      html.classList.add('dark');
    }}

    toggle.addEventListener('click', () => {{
      html.classList.toggle('dark');
      localStorage.theme = html.classList.contains('dark') ? 'dark' : 'light';
    }});

    const baseBtn = ['border-gray-300', 'dark:border-gray-600', 'text-gray-700', 'dark:text-gray-200'];
    const activeBtn = ['border-[#E10101]', 'text-[#E10101]', 'bg-red-50', 'dark:bg-red-900/20', 'dark:text-red-300'];

    let activeFilter = 'all';
    const statusEl = document.getElementById('entries-status');
    const allCards = Array.from(document.querySelectorAll('#all-entries-grid > article[data-contest]'));
    const noFilterResults = document.getElementById('no-filter-results');

    function setButtonState(button, active) {{
      button.classList.remove(...baseBtn, ...activeBtn);
      if (active) {{
      button.classList.add(...activeBtn);
      }} else {{
      button.classList.add(...baseBtn);
      }}
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    }}

    function updateFilterButtons() {{
      document.querySelectorAll('.filter-btn').forEach((btn) => {{
      setButtonState(btn, btn.dataset.filter === activeFilter);
      }});
    }}

    function formatDates() {{
      const now = new Date();
      document.querySelectorAll('time.sub-date').forEach((el) => {{
      const raw = el.getAttribute('datetime');
      if (!raw) return;
      let d = new Date(raw);
      if (isNaN(d.getTime())) return;
      if (d > now) d = now;
      el.textContent = d.toLocaleDateString(undefined, {{
      year: 'numeric', month: 'short', day: 'numeric'
      }});
      }});
    }}

    function applyFilter() {{
      if (!allCards.length) {{
      statusEl.textContent = 'No entries available right now.';
      return;
      }}

      let visibleCount = 0;
      allCards.forEach((card) => {{
      const show = activeFilter === 'all' || card.dataset.contest === activeFilter;
      card.classList.toggle('hidden', !show);
      if (show) visibleCount += 1;
      }});

      if (noFilterResults) {{
      noFilterResults.classList.toggle('hidden', visibleCount !== 0);
      }}

      statusEl.textContent = 'Showing ' + visibleCount + ' entr' + (visibleCount === 1 ? 'y' : 'ies') + ' from all contests.';
      formatDates();
    }}

    document.querySelectorAll('.filter-btn').forEach((btn) => {{
      btn.addEventListener('click', () => {{
      activeFilter = btn.dataset.filter;
      updateFilterButtons();
      applyFilter();
      }});
    }});

    updateFilterButtons();
    applyFilter();
    </script>
    </body>
    </html>"""


def build_winner_showcase(winner_issues: list, title_prefix: str) -> str:
    """Return a prominent winner-showcase hero section for a contest page.

    Displayed at the top of the main content area when one or more winners
    have been selected.  Each winner gets their design image, avatar,
    username, and a link back to the winning submission.
    """
    if not winner_issues:
        return ""

    entry_blocks: list[str] = []
    for i, issue in enumerate(winner_issues):
        number = issue["number"]
        title = html.escape(display_title(issue, title_prefix))
        issue_url = html.escape(issue.get("html_url") or "")
        user = issue.get("user", {})
        author_login = html.escape(user.get("login", "unknown"))
        author_url = html.escape(user.get("html_url", "#"))
        author_avatar = html.escape(user.get("avatar_url", ""))

        preview_url = html.escape(issue.get("preview_url", ""))

        avatar_img = (
            f'<img src="{author_avatar}" alt="{author_login}\'s avatar" '
            f'class="w-12 h-12 rounded-full border-2 border-amber-400 shadow-sm" />'
            if author_avatar
            else (
                '<span class="inline-flex items-center justify-center w-12 h-12 '
                "rounded-full bg-amber-200 dark:bg-amber-800\">"
                '<i class="fa-solid fa-user text-amber-700 dark:text-amber-300"'
                ' aria-hidden="true"></i></span>'
            )
        )

        preview_html = (
            f'<a href="{html.escape(entry_link(issue))}" target="_blank" rel="noopener"'
            f'   class="block w-full md:w-1/2 lg:w-2/5 shrink-0 rounded-xl'
            f"          overflow-hidden shadow-lg border-2 border-amber-300"
            f'          dark:border-amber-600">'
            f'  <img src="{preview_url}" alt="{title} - winning design"'
            f'       class="w-full object-cover" style="max-height:20rem" />'
            f"</a>"
        ) if preview_url else ""

        if issue_url:
            submission_link = (
                f'<a href="{issue_url}" target="_blank" rel="noopener" '
                f'class="inline-flex items-center gap-2 bg-amber-400 hover:bg-amber-500 '
                f'text-amber-900 font-semibold text-sm px-4 py-2 rounded-md transition-colors w-fit">'
                f'<i class="fa-solid fa-code-branch" aria-hidden="true"></i> View Winning Submission #{number}</a>'
            )
        else:
            submission_link = (
                f'<span class="inline-flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">'
                f'<i class="fa-solid fa-box-archive" aria-hidden="true"></i> GitLab submission #{number} (archived)</span>'
            )
        sep = (
            '<hr class="border-amber-200 dark:border-amber-700" />'
            if i > 0
            else ""
        )
        entry_blocks.append(f"""
        {sep}
        <div class="flex flex-col md:flex-row gap-6 items-center">
          <div class="flex-1 min-w-0 flex flex-col gap-4">
            <div class="flex items-center gap-3">
              {avatar_img}
              <div class="min-w-0">
                <a href="{author_url}" target="_blank" rel="noopener"
                   class="text-lg font-bold text-amber-800 dark:text-amber-300 hover:underline">
                  @{author_login}
                </a>
                <p class="text-xs text-amber-600 dark:text-amber-500">
                  <i class="fa-solid fa-trophy" aria-hidden="true"></i> Contest Winner
                </p>
              </div>
            </div>
            <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 leading-snug">
              {title}
            </h3>
            {submission_link}
          </div>
          {preview_html}
        </div>""")

    count = len(winner_issues)
    s = "s" if count > 1 else ""
    have = "have" if count > 1 else "has"
    entries_combined = "\n".join(entry_blocks)

    return f"""
    <!-- ══════════════════════════════════════════
         WINNER SHOWCASE HERO
    ══════════════════════════════════════════ -->
    <section aria-label="Contest winner showcase"
             class="mb-8 bg-gradient-to-br from-amber-50 via-yellow-50 to-amber-50
                    dark:from-amber-900/25 dark:via-yellow-900/15 dark:to-amber-900/25
                    border border-amber-300 dark:border-amber-600
                    rounded-2xl overflow-hidden shadow-sm">
      <div class="px-6 py-4 border-b border-amber-200 dark:border-amber-700
                  flex items-center gap-3">
        <span class="inline-flex items-center justify-center w-10 h-10 rounded-full
                     bg-amber-400 text-amber-900 text-xl">
          <i class="fa-solid fa-trophy" aria-hidden="true"></i>
        </span>
        <div>
          <h2 class="text-lg font-bold text-amber-800 dark:text-amber-300">
            Winner{s} Announced!
          </h2>
          <p class="text-sm text-amber-600 dark:text-amber-500">
            The following design{s} {have} been selected as the winner{s} of this contest.
          </p>
        </div>
      </div>
      <div class="p-6 flex flex-col gap-6">
        {entries_combined}
      </div>
    </section>"""


def build_contest_page_html(contest_data: dict, last_updated: str) -> str:
    """Return a complete standalone HTML page for a single contest."""
    c = contest_data["config"]
    cid = html.escape(c["id"])
    cname = html.escape(c["name"])
    icon = c["icon"]
    submit_url = html.escape(issue_template_url(c["template"]))
    deadline = c["deadline"]

    # Build winner showcase from issues carrying the winner label
    winner_issues = [issue for issue in contest_data.get("issues", []) if is_winner(issue)]
    winner_showcase = build_winner_showcase(winner_issues, c["title_prefix"])
    archive_note = (
        '<p class="mb-6 text-sm text-gray-500 dark:text-gray-400">'
        '<i class="fa-solid fa-box-archive" aria-hidden="true"></i> '
        'Entries marked <strong>GitLab archive</strong> were submitted on gitlab.com before the BLT '
        'GitLab group closed; their vote counts are final. New entries and votes live on '
        f'<a href="{html.escape(ISSUES_URL)}" target="_blank" rel="noopener" '
        'class="text-[#E10101] hover:underline">git.owaspblt.org</a>.</p>'
        if any(i.get("archived") for i in contest_data.get("issues", [])) else ""
    )

    # The contest content (info bar + winner banner + sort controls + cards grid)
    contest_section = build_contest_section(
        contest_data["config"],
        contest_data["cards"],
        contest_data["total"],
        winner_count=contest_data.get("winner_count", 0),
    )

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <meta name="description" content="{cname} — open design showcase for BLT and the broader open source security community. Browse entries, vote for your favourites, and submit your own!" />
  <title>{cname} — BLT Design Contests</title>

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
  <a href="#contest-{cid}"
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
        <a href="index.html" class="flex items-center gap-2 shrink-0 group" aria-label="BLT Design Contests home">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-md
                       bg-[#E10101] text-white font-black text-sm select-none">BLT</span>
          <span class="font-semibold text-gray-900 dark:text-gray-100 hidden sm:block">
            Design Contests
          </span>
        </a>

        <!-- Centre nav links -->
        <div class="hidden md:flex items-center gap-6 text-sm font-medium">
          <a href="index.html"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors
                    inline-flex items-center gap-1.5">
            <i class="fa-solid fa-arrow-left" aria-hidden="true"></i> All Contests
          </a>
          <span class="text-gray-300 dark:text-gray-600">|</span>
          <span class="inline-flex items-center gap-1.5 text-[#E10101] font-semibold">
            <i class="{icon}" aria-hidden="true"></i> {cname}
          </span>
          <a href="{ISSUES_URL}" target="_blank" rel="noopener"
             class="text-gray-600 dark:text-gray-300 hover:text-[#E10101] transition-colors
                    inline-flex items-center gap-1">
            <i class="fa-solid fa-list-check" aria-hidden="true"></i> Issues
          </a>
        </div>

        <!-- CTA -->
        <a href="{submit_url}"
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
       CONTEST CONTENT
  ══════════════════════════════════════════ -->
  <main class="flex-1">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

      <!-- Last updated note -->
      <p class="text-xs text-gray-400 dark:text-gray-500 mb-4 text-right">
        Last updated {last_updated}
      </p>

      {winner_showcase}
      {archive_note}
      {contest_section}

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
        <a href="index.html"
           class="hover:text-[#E10101] transition-colors inline-flex items-center gap-1">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i> All Contests
        </a>
        <a href="{PROJECT_URL}" target="_blank" rel="noopener"
           class="hover:text-[#E10101] transition-colors inline-flex items-center gap-1">
          <i class="fa-solid fa-code" aria-hidden="true"></i> Source
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

        if (!sortState[cid]) sortState[cid] = {{ votes: false, comments: false, originalOrder: null }};
        if (!sortState[cid].originalOrder) sortState[cid].originalOrder = Array.from(grid.children);

        const otherType = sortType === 'votes' ? 'comments' : 'votes';
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

        const dataKey = sortType; // data-votes / data-comments
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

    // Format submission dates in user's local timezone; cap any future dates to today
    (function () {{
      var now = new Date();
      document.querySelectorAll('time.sub-date').forEach(function (el) {{
        var raw = el.getAttribute('datetime');
        if (!raw) return;
        var d = new Date(raw);
        if (isNaN(d.getTime())) return;
        if (d > now) d = now;
        el.textContent = d.toLocaleDateString(undefined, {{
          year: 'numeric', month: 'short', day: 'numeric'
        }});
      }});
    }})();
  </script>
</body>
</html>"""


def group_submissions(records: list[dict], archive: list[dict]) -> list[dict]:
    """contests_data: per contest, its open forge submissions (newest first), then its archived
    GitLab entries; winners first. ``records`` are issue ledger records."""
    live: dict[str, list[dict]] = {c["id"]: [] for c in CONTESTS}
    for record in sorted(records, key=lambda r: int(r.get("number") or 0), reverse=True):
        contest = submission_contest(record)
        if contest:
            live[contest["id"]].append(normalize_forge_issue(record))
    archived: dict[str, list[dict]] = {c["id"]: [] for c in CONTESTS}
    for entry in archive:
        if entry.get("contest") in archived:
            archived[entry["contest"]].append(normalize_archive_entry(entry))

    contests_data = []
    for contest in CONTESTS:
        issues = live[contest["id"]] + archived[contest["id"]]
        issues = [i for i in issues if is_winner(i)] + [i for i in issues if not is_winner(i)]
        cards = [build_card(issue, title_prefix=contest["title_prefix"]) for issue in issues]
        contests_data.append({
            "config": contest,
            "cards": cards,
            "issues": issues,
            "total": len(cards),
            "winner_count": sum(1 for i in issues if is_winner(i)),
            "live": len(live[contest["id"]]),
        })
    return contests_data


def write_pages(contests_data: list[dict], output_dir: str, last_updated: str) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    pages = {"index.html": build_html(contests_data, last_updated),
             "show-all-entries.html": build_show_all_entries_html(contests_data, last_updated)}
    for contest_data in contests_data:
        pages[f'{contest_data["config"]["id"]}.html'] = build_contest_page_html(contest_data, last_updated)
    written = []
    for name, page_html in pages.items():
        path = os.path.join(output_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page_html)
        written.append(path)
        print(f"Written -> {path}")
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=os.path.join(PROJECT_DIR, "public"), help="output directory")
    parser.add_argument("--offline", action="store_true", help="skip git.owaspblt.org (archive only)")
    args = parser.parse_args(argv)
    last_updated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    records: list[dict] = []
    if not args.offline:
        client = ledger.client()
        print(f"Reading issues from {ledger.WEB_URL}/issues ...")
        records = ledger.issues(client)  # a failure stops the run, so no empty pages are published
        print(f"  {len(records)} issues ({client.requests} requests).")
    archive = load_archive()
    contests_data = group_submissions(records, archive)
    for d in contests_data:
        print(f'  {d["config"]["id"]}: {d["live"]} open submissions, {d["total"] - d["live"]} archived')
    write_pages(contests_data, args.out, last_updated)


if __name__ == "__main__":
    main()
