#!/usr/bin/env python3
"""
build_showcase.py
-----------------
Fetches all open GitHub issues labelled "design-submission" and generates
a static index.html design-showcase page styled with the BLT brand guide.

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
LABEL = "design-submission"
TITLE_PREFIX = "[Design]"
REACTION_LABELS = {
    "+1": "👍",
    "heart": "❤️",
    "hooray": "🎉",
    "rocket": "🚀",
}

API_BASE = "https://api.github.com"
MARKDOWN_IMAGE_RE = re.compile(r"!\[.*?\]\((https?://[^)]+)\)")
HTML_IMAGE_RE = re.compile(r'<img\s[^>]*src="(https?://[^"]+)"', re.IGNORECASE)


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
    # Strip markdown checkbox noise
    desc = re.sub(r"^[-*]\s+\[[ x]\].*$", "", desc, flags=re.MULTILINE)
    desc = desc.strip()
    if len(desc) > 200:
        desc = desc[:197] + "…"
    return html.escape(desc)


def build_card(issue: dict, reactions: dict) -> str:
    """Return the HTML card markup for a single submission."""
    number = issue["number"]
    title = html.escape(issue.get("title", "Untitled").replace(TITLE_PREFIX + " ", "").strip())
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

    # Reaction pills
    thumbs_count = reactions.get("+1", 0)
    # Always render a clickable thumbs-up button
    reaction_html = (
        f'<button type="button" '
        f'class="inline-flex items-center gap-1 text-sm '
        f'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 '
        f'rounded-full px-2 py-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 '
        f'hover:text-[#E10101] transition-colors cursor-pointer" '
        f'data-thumbs-btn '
        f'aria-label="Thumbs up this design on GitHub">'
        f'👍 <span>{thumbs_count}</span></button>'
    )
    for content, emoji in REACTION_LABELS.items():
        if content == "+1":
            continue
        count = reactions.get(content, 0)
        if count > 0:
            reaction_html += (
                f'<span class="inline-flex items-center gap-1 text-sm '
                f'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 '
                f'rounded-full px-2 py-0.5">'
                f'{emoji} <span>{count}</span></span>'
            )

    # Preview image
    if preview_url:
        preview_block = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'   class="block overflow-hidden aspect-video bg-gray-100 dark:bg-gray-700">'
            f'  <img src="{preview_url}" alt="{title} preview" loading="lazy" '
            f'       class="w-full h-full object-cover transition-transform duration-300 '
            f'              group-hover:scale-105" />'
            f'</a>'
        )
    else:
        preview_block = (
            f'<a href="{issue_url}" target="_blank" rel="noopener" '
            f'   class="flex items-center justify-center aspect-video '
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

    return f"""
    <article class="group bg-white dark:bg-[#1F2937] rounded-2xl shadow-sm border
                    border-[#E5E5E5] dark:border-gray-700 overflow-hidden
                    flex flex-col hover:shadow-md transition-shadow"
             data-thumbs="{thumbs_count}"
             data-issue-url="{issue_url}"
             aria-label="Design submission: {title}">
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


def build_html(cards: list[str], total: int, last_updated: str) -> str:
    """Return the complete index.html as a string."""
    cards_html = "\n".join(cards) if cards else (
        '<div class="col-span-full text-center py-20 text-gray-500 dark:text-gray-400">'
        '<i class="fa-solid fa-palette text-5xl mb-4 block text-[#E10101]" aria-hidden="true"></i>'
        '<p class="text-lg font-medium">No submissions yet — be the first!</p>'
        '<p class="mt-2 text-sm">Click <strong>Submit Your Design</strong> above to get started.</p>'
        '</div>'
    )

    submit_url = f"https://github.com/{REPO}/issues/new?template=design-submission.yml"

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
        <a href="{html.escape(submit_url)}"
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
        Open Design Contest
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
          <strong>$25 prize</strong> for the best design
        </span>
        <span class="hidden sm:block text-[#E10101]/40">|</span>
        <span class="inline-flex items-center gap-1.5">
          <i class="fa-solid fa-calendar-day" aria-hidden="true"></i>
          Contest ends <strong>March 1, 2026</strong>
        </span>
      </div>

      <div class="flex items-center justify-center gap-4 flex-wrap">
        <a href="{html.escape(submit_url)}"
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
          <p class="text-3xl font-black text-[#E10101]">{total}</p>
          <p>Submission{'' if total == 1 else 's'}</p>
        </div>
        <div>
          <p class="text-3xl font-black text-[#E10101]">$25</p>
          <p>Top Prize</p>
        </div>
        <div>
          <p class="text-3xl font-black text-[#E10101]">Mar 1</p>
          <p>Deadline</p>
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
       SHOWCASE GRID
  ══════════════════════════════════════════ -->
  <main id="showcase" class="flex-1">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

      <!-- Section header -->
      <div class="flex items-center justify-between mb-8 gap-4 flex-wrap">
        <div>
          <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Design Entries
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {total} submission{'' if total == 1 else 's'} · last updated {last_updated}
          </p>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          <button id="sort-thumbs" type="button"
                  class="inline-flex items-center gap-2 border border-gray-300 dark:border-gray-600
                         text-gray-700 dark:text-gray-200 hover:border-[#E10101] hover:text-[#E10101]
                         text-sm font-semibold px-4 py-2 rounded-md transition-colors"
                  aria-pressed="false"
                  title="Sort by thumbs up">
            <i class="fa-solid fa-arrow-down-wide-short" aria-hidden="true"></i>
            Sort by 👍
          </button>
          <a href="{html.escape(submit_url)}"
             target="_blank" rel="noopener"
             class="inline-flex items-center gap-2 border border-[#E10101] text-[#E10101]
                    hover:bg-[#E10101] hover:text-white text-sm font-semibold
                    px-4 py-2 rounded-md transition-colors">
            <i class="fa-solid fa-plus" aria-hidden="true"></i>
            Add Entry
          </a>
        </div>
      </div>

      <!-- Cards grid -->
      <div id="cards-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards_html}
      </div>

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

    // Sort by thumbs-up toggle
    const sortBtn = document.getElementById('sort-thumbs');
    const grid = document.getElementById('cards-grid');
    let sortedByThumbs = false;
    let originalOrder = [];

    if (sortBtn && grid) {{
      originalOrder = Array.from(grid.children);
      sortBtn.addEventListener('click', () => {{
        sortedByThumbs = !sortedByThumbs;
        sortBtn.setAttribute('aria-pressed', String(sortedByThumbs));
        sortBtn.classList.toggle('border-[#E10101]', sortedByThumbs);
        sortBtn.classList.toggle('text-[#E10101]', sortedByThumbs);
        sortBtn.classList.toggle('border-gray-300', !sortedByThumbs);
        sortBtn.classList.toggle('dark:border-gray-600', !sortedByThumbs);
        sortBtn.classList.toggle('text-gray-700', !sortedByThumbs);
        sortBtn.classList.toggle('dark:text-gray-200', !sortedByThumbs);

        const cards = sortedByThumbs
          ? [...originalOrder].sort((a, b) =>
              parseInt(b.dataset.thumbs || '0', 10) - parseInt(a.dataset.thumbs || '0', 10))
          : [...originalOrder];

        cards.forEach(card => grid.appendChild(card));
      }});
    }}

    // Thumbs-up click handler
    document.querySelectorAll('[data-thumbs-btn]').forEach(btn => {{
      btn.addEventListener('click', () => {{
        if (btn.disabled) return;
        btn.disabled = true;
        btn.classList.add('text-[#E10101]', 'bg-red-100', 'dark:bg-red-900/30');
        btn.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-200');
        const article = btn.closest('article');
        const issueUrl = article ? article.dataset.issueUrl : null;
        const countEl = btn.querySelector('span');
        if (countEl) {{
          countEl.textContent = parseInt(countEl.textContent || '0', 10) + 1;
        }}
        if (article) {{
          article.dataset.thumbs = parseInt(article.dataset.thumbs || '0', 10) + 1;
        }}
        if (issueUrl) {{
          window.open(issueUrl, '_blank', 'noopener,noreferrer');
        }}
      }});
    }});
  </script>
</body>
</html>"""


def main() -> None:
    print(f"Fetching issues from {REPO} with label '{LABEL}'…")
    issues = github_request(f"/repos/{REPO}/issues?state=open&labels={LABEL}")
    print(f"  Found {len(issues)} labelled submissions.")

    # Also pick up any [Design] issues that may be missing the label
    all_issues = github_request(f"/repos/{REPO}/issues?state=open")
    seen = {i["number"] for i in issues}
    for issue in all_issues:
        if issue["number"] not in seen and issue.get("title", "").startswith(TITLE_PREFIX):
            issues.append(issue)
            seen.add(issue["number"])
            print(f"  Picked up unlabelled issue #{issue['number']}: {issue.get('title', '')[:60]}")

    print(f"  Total submissions: {len(issues)}.")

    cards = []
    for issue in issues:
        number = issue["number"]
        print(f"  Processing issue #{number}: {issue.get('title', '')[:60]}")
        reactions = fetch_reactions(number)
        cards.append(build_card(issue, reactions))

    last_updated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    page_html = build_html(cards, len(cards), last_updated)

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page_html)
    print(f"Written → {out_path}")


if __name__ == "__main__":
    main()
