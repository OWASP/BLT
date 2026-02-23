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
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT Ideas — Analysis Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #c9d1d9;
      font-size: 14px;
      line-height: 1.5;
    }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    header {{
      background: linear-gradient(135deg, #161b22 0%, #1f2937 100%);
      border-bottom: 1px solid #30363d;
      padding: 24px 32px;
    }}
    header h1 {{ font-size: 24px; color: #f0f6fc; font-weight: 700; }}
    header p {{ color: #8b949e; margin-top: 6px; font-size: 13px; }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 16px; }}
    .stats {{
      display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px;
    }}
    .stat-card {{
      background: #161b22; border: 1px solid #30363d; border-radius: 8px;
      padding: 16px 20px; flex: 1; min-width: 140px;
    }}
    .stat-card .num {{ font-size: 28px; font-weight: 700; color: #58a6ff; }}
    .stat-card .label {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}

    /* Filter / search */
    .toolbar {{
      display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; align-items: center;
    }}
    .toolbar input {{
      background: #161b22; border: 1px solid #30363d; border-radius: 6px;
      color: #c9d1d9; padding: 7px 12px; font-size: 13px; width: 260px;
    }}
    .toolbar input:focus {{ outline: none; border-color: #58a6ff; }}
    .toolbar select {{
      background: #161b22; border: 1px solid #30363d; border-radius: 6px;
      color: #c9d1d9; padding: 7px 10px; font-size: 13px;
    }}
    .toolbar label {{ font-size: 13px; color: #8b949e; }}

    /* Table */
    .table-wrap {{ overflow-x: auto; border: 1px solid #30363d; border-radius: 8px; }}
    table {{
      width: 100%; border-collapse: collapse; background: #161b22;
    }}
    thead th {{
      background: #21262d; color: #8b949e; font-size: 12px; font-weight: 600;
      text-transform: uppercase; letter-spacing: .5px;
      padding: 10px 12px; border-bottom: 1px solid #30363d;
      cursor: pointer; user-select: none; white-space: nowrap;
    }}
    thead th:hover {{ background: #2d333b; color: #c9d1d9; }}
    thead th.sorted-asc::after {{ content: " ↑"; color: #58a6ff; }}
    thead th.sorted-desc::after {{ content: " ↓"; color: #58a6ff; }}
    tbody tr {{ border-bottom: 1px solid #21262d; transition: background .1s; }}
    tbody tr:last-child {{ border-bottom: none; }}
    tbody tr:hover {{ background: #1c2128; }}
    td {{
      padding: 9px 12px; vertical-align: top; font-size: 13px;
    }}
    td.oneliner {{ max-width: 280px; color: #8b949e; }}
    .muted {{ color: #484f58; }}
    .badge {{
      display: inline-block; background: #1f3a5f; color: #79c0ff;
      border-radius: 4px; padding: 1px 6px; font-size: 11px;
      margin: 1px; white-space: nowrap;
    }}

    /* Section headings */
    h2 {{
      font-size: 18px; font-weight: 600; color: #f0f6fc;
      margin: 32px 0 12px; border-bottom: 1px solid #30363d; padding-bottom: 8px;
    }}
    h3 {{ font-size: 15px; font-weight: 600; color: #c9d1d9; margin: 24px 0 8px; }}

    /* Overlap matrix */
    .matrix-wrap {{ overflow-x: auto; margin-bottom: 24px; }}
    .matrix-wrap table {{
      width: auto; background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    }}
    .matrix-wrap th, .matrix-wrap td {{
      padding: 4px 6px; text-align: center; font-size: 11px; border: 1px solid #21262d;
    }}
    .matrix-head {{ background: #21262d; color: #8b949e; font-weight: 600; writing-mode: vertical-rl; white-space: nowrap; }}
    .matrix-label {{ background: #21262d; color: #8b949e; font-weight: 600; text-align: left; padding: 4px 8px; white-space: nowrap; }}
    .matrix-yes {{ background: #1a4a2e; color: #3fb950; font-weight: 700; }}
    .matrix-no {{ background: #161b22; }}
    .matrix-self {{ background: #21262d; color: #484f58; }}

    /* Top connected */
    .top-list {{ list-style: none; }}
    .top-list li {{ padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 13px; }}
    .top-list li:last-child {{ border-bottom: none; }}

    footer {{
      text-align: center; color: #484f58; font-size: 12px;
      padding: 32px 16px; border-top: 1px solid #21262d; margin-top: 40px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>🔍 BLT Ideas — Analysis Dashboard</h1>
    <p>
      Auto-generated from
      <a href="{REPO_URL}" target="_blank">OWASP-BLT/BLT-Ideas</a>
      · {total_ideas} ideas · Sortable table · Overlap analysis · Discussion board links
    </p>
  </header>

  <div class="container">
    <!-- Stats -->
    <div class="stats" id="stats">
      <div class="stat-card">
        <div class="num" id="stat-total">{total_ideas}</div>
        <div class="label">Total Ideas</div>
      </div>
      <div class="stat-card">
        <div class="num" id="stat-with-discussion">0</div>
        <div class="label">With Discussion Post</div>
      </div>
      <div class="stat-card">
        <div class="num" id="stat-with-overlaps">0</div>
        <div class="label">With Overlapping Ideas</div>
      </div>
      <div class="stat-card">
        <div class="num" id="stat-contributors">0</div>
        <div class="label">Unique Contributors</div>
      </div>
    </div>

    <!-- Main sortable table -->
    <h2>📋 Ideas Overview</h2>
    <div class="toolbar">
      <input type="text" id="search" placeholder="Search ideas…" />
      <label>Filter repo:
        <select id="filter-repo">
          <option value="">All repos</option>
        </select>
      </label>
    </div>
    <div class="table-wrap">
      <table id="ideas-table">
        <thead>
          <tr>
            <th data-col="0">Idea</th>
            <th data-col="1">Title</th>
            <th data-col="2">One-Liner</th>
            <th data-col="3">BLT Repo</th>
            <th data-col="4">Discussion</th>
            <th data-col="5">Overlapping Ideas</th>
            <th data-col="6">Interested Contributors</th>
          </tr>
        </thead>
        <tbody>
{table_rows}
        </tbody>
      </table>
    </div>

    <!-- Overlap Analysis -->
    <h2>🔗 Idea Overlap Matrix</h2>
    <p style="color:#8b949e; font-size:13px; margin-bottom:12px;">
      ✓ = ideas reference each other (cross-cutting dependencies / integration points).
      Click any idea ID to view its full spec.
    </p>
    <div class="matrix-wrap">
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

    <h3>🏆 Most-Connected Ideas</h3>
    <ul class="top-list">
{top_connected_html}
    </ul>
  </div>

  <footer>
    Generated by the
    <a href="{REPO_URL}/blob/main/.github/workflows/pages.yml" target="_blank">BLT Ideas Pages workflow</a>
    · Data sourced from GitHub API and repository commit history
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
