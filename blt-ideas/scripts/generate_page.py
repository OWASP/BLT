#!/usr/bin/env python3
"""Generate a GitHub Pages site for BLT Ideas with overlap analysis,
discussion links, repo links, and interested contributors."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_OWNER = "OWASP-BLT"
REPO_NAME = "BLT-Ideas"
REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
ORG = "OWASP-BLT"

# Maximum number of contributors to display per idea row before truncating
MAX_DISPLAY_CONTRIBUTORS = 10

# Known BLT org repos for each idea (from file content "Repository:" lines and README)
IDEA_REPO_MAP = {
    "A": "OWASP-BLT/BLT",
    "B": "OWASP-BLT/BLT",
    "C": "OWASP-BLT/BLT",
    "D": "OWASP-BLT/BLT",
    "E": "OWASP-BLT/BLT",
    "E.1": "OWASP-BLT/BLT",
    "E.2": "OWASP-BLT/BLT",
    "F": "OWASP-BLT/BLT",
    "G": "OWASP-BLT/BLT-NetGuardian",
    "H": "OWASP-BLT/BLT",
    "I": "OWASP-BLT/BLT",
    "J": "OWASP-BLT/BLT",
    "K": "OWASP-BLT/BLT",
    "L": "OWASP-BLT/BLT",
    "L2": "OWASP-BLT/BLT",
    "M": "OWASP-BLT/BLT",
    "N": "OWASP-BLT/BLT",
    "O": "OWASP-BLT/BLT-Extension",
    "P": "OWASP-BLT/BLT",
    "Q": "OWASP-BLT/BLT",
    "R": "OWASP-BLT/BLT-Flutter",
    "RS": "OWASP-BLT/BLT",
    "S": "OWASP-BLT/BLT-CVE",
    "T": "OWASP-BLT/BLT-NetGuardian",
    "U": "OWASP-BLT/BLT",
    "V": "OWASP-BLT/BLT-API",
    "W": "OWASP-BLT/BLT",
    "X": "OWASP-BLT/BLT",
    "Y": "OWASP-BLT/BLT",
    "Z": "OWASP-BLT/BLT",
}


def github_api_rest(endpoint):
    """Call GitHub REST API."""
    if not GITHUB_TOKEN:
        return None
    url = f"https://api.github.com{endpoint}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "BLT-Ideas-Page-Generator",
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (URLError, HTTPError) as e:
        print(f"  REST API error for {endpoint}: {e}", file=sys.stderr)
        return None


def github_graphql(query):
    """Call GitHub GraphQL API."""
    if not GITHUB_TOKEN:
        return None
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "BLT-Ideas-Page-Generator",
    }
    data = json.dumps({"query": query}).encode()
    try:
        req = Request("https://api.github.com/graphql", data=data, headers=headers)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (URLError, HTTPError) as e:
        print(f"  GraphQL API error: {e}", file=sys.stderr)
        return None


def get_file_contributors(filepath):
    """Get unique contributors for a specific file via git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%ae|||%an", "--follow", "--", filepath],
            capture_output=True,
            text=True,
            cwd=Path(filepath).parent if Path(filepath).is_absolute() else ".",
        )
        contributors = {}
        for line in result.stdout.strip().splitlines():
            if "|||" in line:
                email, name = line.split("|||", 1)
                email = email.strip()
                name = name.strip()
                if email and name:
                    contributors[email] = name
        return list(contributors.values())
    except Exception as e:
        print(f"  git log error for {filepath}: {e}", file=sys.stderr)
        return []


def get_discussion_participants(discussion_num):
    """Fetch participants from an OWASP-BLT org discussion via GraphQL."""
    if not discussion_num or not GITHUB_TOKEN:
        return []

    query = """
    {
      organization(login: "OWASP-BLT") {
        discussion(number: %s) {
          author { login }
          comments(first: 100) {
            nodes {
              author { login }
            }
          }
        }
      }
    }
    """ % discussion_num

    data = github_graphql(query)
    if not data or "data" not in data:
        return []

    participants = set()
    disc = (data.get("data") or {}).get("organization") or {}
    disc = disc.get("discussion") or {}
    if disc.get("author"):
        participants.add(disc["author"]["login"])
    for comment in (disc.get("comments") or {}).get("nodes") or []:
        if comment.get("author"):
            participants.add(comment["author"]["login"])
    return sorted(participants)


def get_pr_participants():
    """Fetch recent PR authors/commenters for this repo."""
    prs = github_api_rest(
        f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls?state=all&per_page=100"
    )
    if not prs:
        return {}
    result = {}
    for pr in prs:
        number = pr.get("number")
        login = (pr.get("user") or {}).get("login", "")
        if login:
            result.setdefault(number, set()).add(login)
    return result


def parse_idea_file(path):
    """Parse a single Idea-*.md file and extract metadata."""
    content = path.read_text(encoding="utf-8")
    filename = path.stem  # e.g. "Idea-A"

    # Idea ID from filename
    idea_id = filename.replace("Idea-", "")  # e.g. "A", "B", "E.1", "RS"

    # Extract title from first heading
    title_match = re.search(r"^#+ (.+)", content, re.MULTILINE)
    raw_title = title_match.group(1).strip() if title_match else filename

    # Clean up title: remove leading "Idea X — " / "Idea X – " / "Idea X - " patterns.
    # The character class intentionally covers em dash (—), en dash (–), and hyphen (-).
    title = re.sub(
        r"^Idea\s+[A-Z0-9.]+\s*[—–\-]+\s*", "", raw_title, flags=re.IGNORECASE
    ).strip()
    # If title still starts with "Idea X" pattern, keep it as-is for short filenames
    if not title:
        title = raw_title

    # Extract one-liner
    oneliner = ""
    for pattern in [
        r"\*\*One line:\*\*\s*(.+?)(?:\n|$)",
        r"\*\*One line\*\*:\s*(.+?)(?:\n|$)",
        r"One line[:\s]+(.+?)(?:\n|$)",
    ]:
        m = re.search(pattern, content)
        if m:
            oneliner = m.group(1).strip().strip("*")
            break

    # Extract discussion URL
    disc_match = re.search(
        r"https://github\.com/orgs/OWASP-BLT/discussions/(\d+)", content
    )
    discussion_url = disc_match.group(0) if disc_match else ""
    discussion_num = disc_match.group(1) if disc_match else ""

    # Extract BLT org repo from "Repository:" line, else use known map
    repo_match = re.search(
        r"\*?\*?Repository[:\s]+\*?\*?\s*(OWASP[-/]\S+)", content, re.IGNORECASE
    )
    if repo_match:
        blt_repo = repo_match.group(1).rstrip(")")
        # Normalise OWASP/ → OWASP-BLT/
        blt_repo = re.sub(r"^OWASP/", "OWASP-BLT/", blt_repo)
    else:
        blt_repo = IDEA_REPO_MAP.get(idea_id, f"{REPO_OWNER}/BLT")

    # Find related ideas — any mention of "Idea X" where X is a known idea ID format:
    # single letter (A–Z), two-letter compound (RS), digit-suffixed (E.1, E.2, L2).
    related = set()
    for m in re.finditer(
        r"\bIdea\s+([A-Z]{1,2}[0-9]*(?:\.[0-9]+)?(?:\s*\(Extended\))?)\b", content
    ):
        other = m.group(1).strip()
        # Normalise "(Extended)" suffix
        if "(Extended)" in other:
            other = other.replace("(Extended)", "").strip() + " (Extended)"
        if other != idea_id:
            related.add(other)

    return {
        "id": idea_id,
        "filename": path.name,
        "raw_title": raw_title,
        "title": title,
        "one_liner": oneliner,
        "discussion_url": discussion_url,
        "discussion_num": discussion_num,
        "blt_repo": blt_repo,
        "related": sorted(related),
        "git_contributors": [],
        "discussion_participants": [],
    }


def sort_key(idea_id):
    """Sort ideas: single letters first, then compound IDs."""
    # Map E.1 → E, E.2 → E Extended, RS → after R, L2 → after L
    mapping = {
        "E.1": ("E", 1),
        "E.2": ("E", 2),
        "L2": ("L", 2),
        "RS": ("RS", 0),
    }
    if idea_id in mapping:
        letter, sub = mapping[idea_id]
    elif len(idea_id) == 1:
        letter, sub = idea_id, 0
    else:
        letter, sub = idea_id, 0
    return (letter, sub)


def build_overlap_matrix(ideas):
    """Build a symmetric overlap/dependency matrix."""
    idea_ids = [i["id"] for i in ideas]
    # Matrix: overlap[i][j] = True if idea i references idea j or vice-versa
    matrix = {a: {b: False for b in idea_ids} for a in idea_ids}

    for idea in ideas:
        for rel in idea["related"]:
            # Normalise: map "E (Extended)" → E.2, plain letters to their IDs
            target = rel
            if target in idea_ids:
                matrix[idea["id"]][target] = True
                matrix[target][idea["id"]] = True
            else:
                # Try to find partial match
                for other_id in idea_ids:
                    if target.startswith(other_id) or other_id.startswith(target):
                        matrix[idea["id"]][other_id] = True
                        matrix[other_id][idea["id"]] = True

    return matrix


def html_escape(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_html(ideas, overlap_matrix):
    """Generate a complete HTML page with sortable table and overlap analysis."""

    # Prepare table rows
    rows_html = []
    for idea in ideas:
        idea_id = idea["id"]
        title = html_escape(idea["title"])
        one_liner = html_escape(
            idea["one_liner"][:120] + ("…" if len(idea["one_liner"]) > 120 else "")
        )

        # Idea file link (in this repo)
        file_url = f"{REPO_URL}/blob/main/{idea['filename']}"
        idea_link = f'<a href="{file_url}" title="{html_escape(idea["raw_title"])}" target="_blank">Idea&nbsp;{html_escape(idea_id)}</a>'

        # BLT org repo link
        blt_repo = idea["blt_repo"]
        repo_url = f"https://github.com/{blt_repo}"
        repo_link = f'<a href="{repo_url}" target="_blank">{html_escape(blt_repo.split("/")[-1])}</a>'

        # Discussion link
        if idea["discussion_url"]:
            disc_link = f'<a href="{idea["discussion_url"]}" target="_blank">#{idea["discussion_num"]}</a>'
        else:
            disc_link = '<span class="muted">—</span>'

        # Related ideas
        related_links = []
        for rel in idea["related"]:
            # Find the idea with this ID to get its file URL
            rel_idea = next((i for i in ideas if i["id"] == rel), None)
            if rel_idea:
                rel_file_url = f"{REPO_URL}/blob/main/{rel_idea['filename']}"
                related_links.append(
                    f'<a href="{rel_file_url}" target="_blank" class="badge">Idea&nbsp;{html_escape(rel)}</a>'
                )
            else:
                related_links.append(
                    f'<span class="badge">Idea&nbsp;{html_escape(rel)}</span>'
                )
        related_html = " ".join(related_links) if related_links else '<span class="muted">—</span>'

        # Interested contributors (git + discussion)
        all_contributors = sorted(
            set(idea["git_contributors"] + idea["discussion_participants"])
        )
        if all_contributors:
            contrib_html = ", ".join(
                html_escape(c) for c in all_contributors[:MAX_DISPLAY_CONTRIBUTORS]
            )
            if len(all_contributors) > MAX_DISPLAY_CONTRIBUTORS:
                contrib_html += f' <small>(+{len(all_contributors) - MAX_DISPLAY_CONTRIBUTORS} more)</small>'
        else:
            contrib_html = '<span class="muted">—</span>'

        # Overlap count for sorting
        overlap_count = sum(
            1 for other_id, v in overlap_matrix.get(idea_id, {}).items() if v and other_id != idea_id
        )

        rows_html.append(
            f"""      <tr>
        <td data-sort="{html_escape(idea_id)}">{idea_link}</td>
        <td data-sort="{title}">{title}</td>
        <td class="oneliner" data-sort="{html_escape(idea["one_liner"])}">{one_liner}</td>
        <td data-sort="{html_escape(blt_repo)}">{repo_link}</td>
        <td data-sort="{(idea.get('discussion_num') or '0').zfill(6)}">{disc_link}</td>
        <td data-sort="{overlap_count:03d}">{related_html}</td>
        <td data-sort="{len(all_contributors):03d}">{contrib_html}</td>
      </tr>"""
        )

    # Overlap matrix HTML
    all_ids = [i["id"] for i in ideas]
    matrix_headers = "".join(
        f'<th class="matrix-head" title="Idea {html_escape(i)}">{html_escape(i)}</th>'
        for i in all_ids
    )
    matrix_rows = []
    for row_idea in ideas:
        rid = row_idea["id"]
        file_url = f"{REPO_URL}/blob/main/{row_idea['filename']}"
        cells = f'<td class="matrix-label"><a href="{file_url}" target="_blank">{html_escape(rid)}</a></td>'
        for col_id in all_ids:
            if col_id == rid:
                cells += '<td class="matrix-self">·</td>'
            elif overlap_matrix.get(rid, {}).get(col_id):
                cells += f'<td class="matrix-yes" title="Idea {html_escape(rid)} ↔ Idea {html_escape(col_id)}">✓</td>'
            else:
                cells += '<td class="matrix-no"></td>'
        matrix_rows.append(f"<tr>{cells}</tr>")

    table_rows = "\n".join(rows_html)
    matrix_rows_html = "\n".join(matrix_rows)
    total_ideas = len(ideas)

    # Ideas with the most connections
    top_connected = sorted(
        ideas,
        key=lambda i: sum(1 for v in overlap_matrix.get(i["id"], {}).values() if v),
        reverse=True,
    )[:5]
    top_connected_html = "".join(
        f'<li><strong>Idea {html_escape(i["id"])}</strong> — {html_escape(i["title"])} '
        f'({sum(1 for v in overlap_matrix.get(i["id"], {}).values() if v)} connections)</li>'
        for i in top_connected
    )

    html = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT Ideas | OWASP BLT</title>
  <meta name="description" content="BLT Ideas landing page with searchable idea catalog, overlap matrix, and contributor context for OWASP BLT." />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            primary: '#E10101',
            'primary-hover': '#b91c1c',
            'neutral-border': '#E5E5E5',
            'dark-base': '#111827',
            'dark-surface': '#1F2937'
          }},
          fontFamily: {{
            sans: ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif']
          }}
        }}
      }}
    }};
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <link
    rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
    integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA=="
    crossorigin="anonymous"
    referrerpolicy="no-referrer"
  />
  <style>
    :root {{
      --blt-primary: #E10101;
      --blt-primary-hover: #b91c1c;
      --blt-neutral-border: #E5E5E5;
      --blt-dark-base: #111827;
      --blt-dark-surface: #1F2937;
    }}
    body {{
      background:
        radial-gradient(circle at 5% 0%, rgba(225, 1, 1, 0.08), transparent 24%),
        radial-gradient(circle at 95% 8%, rgba(225, 1, 1, 0.06), transparent 20%),
        #ffffff;
      color: #111827;
    }}
    a {{
      color: #dc2626;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .btn-link:hover {{
      text-decoration: none;
    }}
    .input-core {{
      border: 1px solid #9ca3af;
      border-radius: 0.375rem;
      padding: 0.5rem 1rem;
      background: #ffffff;
    }}
    .input-core:focus {{
      outline: none;
      border-color: #dc2626;
      box-shadow: 0 0 0 1px #dc2626;
    }}
    .table-wrap {{
      border: 1px solid var(--blt-neutral-border);
      border-radius: 0.75rem;
      overflow-x: auto;
      background: #ffffff;
    }}
    #ideas-table thead th {{
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }}
    #ideas-table td {{
      padding: 0.75rem;
      vertical-align: top;
    }}
    #ideas-table thead th.sorted-asc::after {{
      content: " ↑";
      color: #E10101;
    }}
    #ideas-table thead th.sorted-desc::after {{
      content: " ↓";
      color: #E10101;
    }}
    #ideas-table tbody tr:hover {{
      background: #fff7f7;
    }}
    td.oneliner {{
      max-width: 300px;
      color: #4b5563;
      line-height: 1.45;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border: 1px solid #fecaca;
      background: #fff1f2;
      color: #b91c1c;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: 600;
      margin: 2px 3px 2px 0;
      white-space: nowrap;
    }}
    .muted {{
      color: #6b7280;
    }}
    .matrix-wrap {{
      overflow-x: auto;
      border: 1px solid var(--blt-neutral-border);
      border-radius: 0.75rem;
      background: #ffffff;
    }}
    .matrix-wrap table {{
      width: auto;
      border-collapse: collapse;
    }}
    .matrix-wrap th, .matrix-wrap td {{
      border: 1px solid #f3f4f6;
      text-align: center;
      font-size: 11px;
      padding: 0.3rem 0.35rem;
    }}
    .matrix-head {{
      background: #f9fafb;
      color: #374151;
      font-weight: 700;
      writing-mode: vertical-rl;
      white-space: nowrap;
    }}
    .matrix-label {{
      background: #f9fafb;
      color: #374151;
      font-weight: 700;
      text-align: left;
      padding: 0.35rem 0.5rem;
      white-space: nowrap;
    }}
    .matrix-yes {{
      background: #fee2e2;
      color: #b91c1c;
      font-weight: 700;
    }}
    .matrix-no {{
      background: #ffffff;
    }}
    .matrix-self {{
      background: #f9fafb;
      color: #9ca3af;
      font-weight: 700;
    }}
    .top-list {{
      list-style: none;
    }}
    .top-list li {{
      border-bottom: 1px solid #f3f4f6;
      padding: 0.65rem 0;
      font-size: 0.95rem;
      color: #374151;
    }}
    .top-list li:last-child {{
      border-bottom: none;
    }}
  </style>
</head>
<body class="font-sans antialiased">
  <header class="border-b border-neutral-border bg-white/95 backdrop-blur">
    <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
      <a href="{REPO_URL}" target="_blank" class="btn-link flex items-center gap-3" aria-label="BLT Ideas repository">
        <span class="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-white shadow-sm">
          <i class="fa-solid fa-lightbulb" aria-hidden="true"></i>
        </span>
        <span class="block">
          <span class="block text-base font-extrabold text-gray-900">BLT Ideas</span>
          <span class="block text-xs font-medium text-gray-500">OWASP BLT Extension Planning Hub</span>
        </span>
      </a>
      <div class="flex items-center gap-2 sm:gap-3">
        <a
          href="{REPO_URL}"
          target="_blank"
          class="btn-link inline-flex items-center gap-2 rounded-md border border-[var(--blt-primary)] px-4 py-2 text-sm font-semibold text-[var(--blt-primary)] transition hover:bg-[var(--blt-primary)] hover:text-white"
        >
          <i class="fa-brands fa-github" aria-hidden="true"></i>
          <span>Repository</span>
        </a>
        <a
          href="#ideas-overview"
          class="btn-link inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
        >
          <i class="fa-solid fa-list-check" aria-hidden="true"></i>
          <span>Explore Ideas</span>
        </a>
      </div>
    </div>
  </header>

  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <div class="grid gap-8 lg:grid-cols-12">
      <aside class="lg:col-span-3">
        <div class="sticky top-6 space-y-4">
          <nav class="rounded-xl border border-neutral-border bg-white p-4" aria-label="Page navigation">
            <p class="mb-2 text-xs font-bold uppercase tracking-wide text-gray-500">Navigate</p>
            <ul class="space-y-1 text-sm font-semibold">
              <li><a href="#landing" class="btn-link block rounded-md bg-[#feeae9] px-3 py-2 text-[#E10101]">Overview</a></li>
              <li><a href="#ideas-overview" class="btn-link block rounded-md px-3 py-2 text-gray-700 hover:bg-gray-50">Feature Catalog</a></li>
              <li><a href="#overlap-matrix" class="btn-link block rounded-md px-3 py-2 text-gray-700 hover:bg-gray-50">Overlap Matrix</a></li>
              <li><a href="#top-ideas" class="btn-link block rounded-md px-3 py-2 text-gray-700 hover:bg-gray-50">Most Connected</a></li>
            </ul>
          </nav>
          <section class="rounded-xl border border-neutral-border bg-white p-4">
            <p class="text-sm font-bold text-gray-900">How It Is Used</p>
            <ul class="mt-3 space-y-3 text-sm text-gray-600">
              <li class="flex gap-3">
                <i class="fa-solid fa-magnifying-glass mt-1 text-primary" aria-hidden="true"></i>
                <span>Discover scoped ideas quickly with searchable metadata.</span>
              </li>
              <li class="flex gap-3">
                <i class="fa-solid fa-diagram-project mt-1 text-primary" aria-hidden="true"></i>
                <span>Track dependencies using the overlap matrix before implementation.</span>
              </li>
              <li class="flex gap-3">
                <i class="fa-solid fa-users mt-1 text-primary" aria-hidden="true"></i>
                <span>Identify active contributors and discussion context for each idea.</span>
              </li>
            </ul>
          </section>
        </div>
      </aside>

      <div class="space-y-8 lg:col-span-9">
        <section id="landing" class="rounded-2xl border border-neutral-border bg-white p-6 shadow-sm sm:p-8">
          <div class="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div class="max-w-2xl">
              <p class="mb-3 inline-flex items-center gap-2 rounded-full bg-red-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-red-700">
                <i class="fa-solid fa-shield-halved" aria-hidden="true"></i>
                BLT Official Ideas Board
              </p>
              <h1 class="text-3xl font-extrabold leading-tight text-gray-900 sm:text-4xl">
                Plan Better OWASP BLT Extensions With Clear, Actionable Ideas
              </h1>
              <p class="mt-4 text-base leading-relaxed text-gray-600">
                This landing page brings all proposal specs, dependencies, and contributor signals into one practical workspace. Teams can evaluate why an idea matters, how it integrates with BLT, and where collaboration already exists.
              </p>
              <div class="mt-5 flex flex-wrap gap-2 text-sm font-semibold text-gray-600">
                <span class="rounded-full border border-neutral-border bg-gray-50 px-3 py-1">Feature list visibility</span>
                <span class="rounded-full border border-neutral-border bg-gray-50 px-3 py-1">Usage guidance</span>
                <span class="rounded-full border border-neutral-border bg-gray-50 px-3 py-1">Cross-idea dependencies</span>
              </div>
            </div>
            <div class="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:w-80">
              <div class="rounded-xl border border-neutral-border bg-gradient-to-b from-white to-red-50 p-4">
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Total Ideas</p>
                <p class="mt-2 text-3xl font-extrabold text-primary">{total_ideas}</p>
              </div>
              <div class="rounded-xl border border-neutral-border bg-gradient-to-b from-white to-gray-50 p-4">
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Repository</p>
                <p class="mt-2 text-sm font-bold text-gray-900">OWASP-BLT/BLT-Ideas</p>
              </div>
            </div>
          </div>
        </section>

        <section aria-label="Feature highlights" class="grid gap-4 sm:grid-cols-3">
          <article class="rounded-xl border border-neutral-border bg-white p-4 shadow-sm">
            <div class="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-red-50 text-primary">
              <i class="fa-solid fa-table-list" aria-hidden="true"></i>
            </div>
            <h2 class="text-base font-bold text-gray-900">Complete Feature List</h2>
            <p class="mt-2 text-sm text-gray-600">Every idea is indexed with title, one-liner, linked repo, discussions, and contributors.</p>
          </article>
          <article class="rounded-xl border border-neutral-border bg-white p-4 shadow-sm">
            <div class="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-red-50 text-primary">
              <i class="fa-solid fa-link" aria-hidden="true"></i>
            </div>
            <h2 class="text-base font-bold text-gray-900">Why It Matters</h2>
            <p class="mt-2 text-sm text-gray-600">Overlap mapping clarifies integration points early, reducing duplicated effort.</p>
          </article>
          <article class="rounded-xl border border-neutral-border bg-white p-4 shadow-sm">
            <div class="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-red-50 text-primary">
              <i class="fa-solid fa-route" aria-hidden="true"></i>
            </div>
            <h2 class="text-base font-bold text-gray-900">How Teams Use It</h2>
            <p class="mt-2 text-sm text-gray-600">Filter ideas by repo, inspect discussions, then prioritize the best-connected roadmap items.</p>
          </article>
        </section>

        <section id="stats" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Idea statistics">
          <article class="rounded-xl border border-neutral-border bg-white p-5 shadow-sm">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Total Ideas</p>
            <p class="mt-2 text-3xl font-extrabold text-primary" id="stat-total">{total_ideas}</p>
          </article>
          <article class="rounded-xl border border-neutral-border bg-white p-5 shadow-sm">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">With Discussion Post</p>
            <p class="mt-2 text-3xl font-extrabold text-primary" id="stat-with-discussion">0</p>
          </article>
          <article class="rounded-xl border border-neutral-border bg-white p-5 shadow-sm">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">With Overlaps</p>
            <p class="mt-2 text-3xl font-extrabold text-primary" id="stat-with-overlaps">0</p>
          </article>
          <article class="rounded-xl border border-neutral-border bg-white p-5 shadow-sm">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Unique Contributors</p>
            <p class="mt-2 text-3xl font-extrabold text-primary" id="stat-contributors">0</p>
          </article>
        </section>

        <section id="ideas-overview" class="rounded-2xl border border-neutral-border bg-white p-5 shadow-sm sm:p-6">
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 class="flex items-center gap-2 text-xl font-extrabold text-gray-900">
              <i class="fa-solid fa-clipboard-list text-primary" aria-hidden="true"></i>
              Ideas Overview
            </h2>
            <span class="text-sm font-medium text-gray-500">Sortable columns + repo filter</span>
          </div>
          <div class="toolbar mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <label for="search" class="sr-only">Search ideas</label>
            <div class="relative w-full sm:max-w-sm">
              <span class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-primary">
                <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
              </span>
              <input
                type="text"
                id="search"
                placeholder="Search ideas, titles, contributors..."
                class="input-core w-full border-gray-400 pl-11 text-sm text-gray-900 placeholder-gray-400"
              />
            </div>
            <label for="filter-repo" class="text-sm font-semibold text-gray-700">Filter repo</label>
            <select id="filter-repo" class="input-core border-gray-400 text-sm text-gray-900">
              <option value="">All repos</option>
            </select>
          </div>
          <div class="table-wrap">
            <table id="ideas-table" class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-gray-50 text-xs uppercase tracking-wide text-gray-600">
                <tr>
                  <th data-col="0" class="px-3 py-3 text-left font-bold">Idea</th>
                  <th data-col="1" class="px-3 py-3 text-left font-bold">Title</th>
                  <th data-col="2" class="px-3 py-3 text-left font-bold">One-Liner</th>
                  <th data-col="3" class="px-3 py-3 text-left font-bold">BLT Repo</th>
                  <th data-col="4" class="px-3 py-3 text-left font-bold">Discussion</th>
                  <th data-col="5" class="px-3 py-3 text-left font-bold">Overlapping Ideas</th>
                  <th data-col="6" class="px-3 py-3 text-left font-bold">Interested Contributors</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 bg-white text-gray-700">
{table_rows}
              </tbody>
            </table>
          </div>
        </section>

        <section id="overlap-matrix" class="rounded-2xl border border-neutral-border bg-white p-5 shadow-sm sm:p-6">
          <h2 class="flex items-center gap-2 text-xl font-extrabold text-gray-900">
            <i class="fa-solid fa-diagram-project text-primary" aria-hidden="true"></i>
            Idea Overlap Matrix
          </h2>
          <p class="mt-2 text-sm text-gray-600">
            <span class="font-semibold text-gray-800">✓</span> means two ideas reference each other as cross-cutting integration points.
            Click an idea ID to open its full specification.
          </p>
          <div class="matrix-wrap mt-4">
            <table>
              <thead>
                <tr>
                  <th class="matrix-label"></th>
                  {matrix_headers}
                </tr>
              </thead>
              <tbody>
{matrix_rows_html}
              </tbody>
            </table>
          </div>
        </section>

        <section id="top-ideas" class="rounded-2xl border border-neutral-border bg-white p-5 shadow-sm sm:p-6">
          <h3 class="flex items-center gap-2 text-xl font-extrabold text-gray-900">
            <i class="fa-solid fa-ranking-star text-primary" aria-hidden="true"></i>
            Most-Connected Ideas
          </h3>
          <ul class="top-list mt-3">
{top_connected_html}
          </ul>
        </section>
      </div>
    </div>
  </main>

  <footer class="mt-10 border-t border-neutral-border bg-white">
    <div class="mx-auto max-w-7xl px-4 py-7 text-center text-sm text-gray-500 sm:px-6 lg:px-8">
      Generated by
      <a href="{REPO_URL}/blob/main/.github/workflows/pages.yml" target="_blank">BLT Ideas Pages workflow</a>
      with data from GitHub APIs and repository commit history.
    </div>
  </footer>

  <script>
  (function() {{
    // ── Sorting ────────────────────────────────────────────────────────────
    const table = document.getElementById('ideas-table');
    const tbody = table.querySelector('tbody');
    let sortCol = 0, sortDir = 1;

    function getVal(row, col) {{
      const td = row.cells[col];
      return (td.dataset.sort || td.textContent).trim().toLowerCase();
    }}

    function sortTable(col) {{
      if (sortCol === col) sortDir = -sortDir;
      else {{ sortCol = col; sortDir = 1; }}
      const rows = Array.from(tbody.rows);
      rows.sort((a, b) => getVal(a, col) < getVal(b, col) ? -sortDir : sortDir);
      rows.forEach(r => tbody.appendChild(r));
      document.querySelectorAll('thead th').forEach((th, i) => {{
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (i === col) th.classList.add(sortDir === 1 ? 'sorted-asc' : 'sorted-desc');
      }});
    }}

    document.querySelectorAll('thead th[data-col]').forEach(th => {{
      th.addEventListener('click', () => sortTable(parseInt(th.dataset.col)));
    }});
    sortTable(0); // default sort by idea ID

    // ── Search / filter ──────────────────────────────────────────────────
    const searchInput = document.getElementById('search');
    const repoFilter = document.getElementById('filter-repo');

    // Populate repo dropdown
    const repos = [...new Set(
      Array.from(tbody.rows).map(r => r.cells[3].textContent.trim())
    )].sort();
    repos.forEach(r => {{
      const opt = document.createElement('option');
      opt.value = r; opt.textContent = r;
      repoFilter.appendChild(opt);
    }});

    function applyFilter() {{
      const q = searchInput.value.toLowerCase();
      const repo = repoFilter.value.toLowerCase();
      let visible = 0;
      Array.from(tbody.rows).forEach(row => {{
        const text = row.textContent.toLowerCase();
        const rowRepo = row.cells[3].textContent.trim().toLowerCase();
        const show = (!q || text.includes(q)) && (!repo || rowRepo === repo);
        row.style.display = show ? '' : 'none';
        if (show) visible++;
      }});
    }}

    searchInput.addEventListener('input', applyFilter);
    repoFilter.addEventListener('change', applyFilter);

    // ── Stats ────────────────────────────────────────────────────────────
    const rows = Array.from(tbody.rows);
    document.getElementById('stat-with-discussion').textContent =
      rows.filter(r => r.cells[4].textContent.trim() !== '—').length;
    document.getElementById('stat-with-overlaps').textContent =
      rows.filter(r => r.cells[5].textContent.trim() !== '—').length;

    const allContribs = new Set();
    rows.forEach(r => {{
      r.cells[6].textContent.split(',').forEach(c => {{
        const t = c.trim();
        if (t && t !== '—') allContribs.add(t);
      }});
    }});
    document.getElementById('stat-contributors').textContent = allContribs.size;
  }})();
  </script>
</body>
</html>
"""
    return html


def main():
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    os.chdir(repo_root)

    if not GITHUB_TOKEN:
        print(
            "Warning: GITHUB_TOKEN is not set. "
            "Discussion participant data will be unavailable. "
            "Set the GITHUB_TOKEN environment variable for full API access.",
            file=sys.stderr,
        )

    print("Parsing idea files…")
    idea_files = sorted(repo_root.glob("Idea-*.md"), key=lambda p: sort_key(p.stem.replace("Idea-", "")))
    ideas = [parse_idea_file(p) for p in idea_files]
    print(f"  Found {len(ideas)} idea files")

    print("Fetching git contributors…")
    for idea in ideas:
        idea["git_contributors"] = get_file_contributors(idea["filename"])
        if idea["git_contributors"]:
            print(f"  {idea['filename']}: {idea['git_contributors']}")

    print("Fetching discussion participants…")
    for idea in ideas:
        if idea["discussion_num"]:
            print(f"  Fetching discussion #{idea['discussion_num']} for Idea {idea['id']}…")
            idea["discussion_participants"] = get_discussion_participants(
                idea["discussion_num"]
            )
            if idea["discussion_participants"]:
                print(f"    Participants: {idea['discussion_participants']}")

    print("Building overlap matrix…")
    overlap_matrix = build_overlap_matrix(ideas)

    print("Generating HTML…")
    html = generate_html(ideas, overlap_matrix)

    # Write output
    out_dir = repo_root / "docs"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"  Written to {out_file}")

    # Write a minimal _config.yml so GitHub Pages serves docs/
    config_file = repo_root / "docs" / "_config.yml"
    if not config_file.exists():
        config_file.write_text("# GitHub Pages configuration\n", encoding="utf-8")

    print("Done.")


if __name__ == "__main__":
    main()
