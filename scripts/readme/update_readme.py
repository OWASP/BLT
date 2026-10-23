#!/usr/bin/env python3
"""Regenerate the generated sections of the root README.md.

Sections are delimited by <!-- NAME-START --> / <!-- NAME-END --> markers:

  PROJECTS      one row per project folder: name, description, live site
  CONTRIBUTORS  everyone with a commit in any project, by commit count (see contributors.py; it also
                writes .forkmesh/contributors/: avatars, contributors.json and a lookup cache)
  WAITING-PRS   open pull requests on git.owaspblt.org, new contributors first (people with no
                commit in any project and no merged pull request); kept as it is when the forge
                can't be read (--offline skips it)
  DEPLOY        one row per Cloudflare deploy, from scripts/deploy/projects.tsv
  BLOG-POSTS    latest posts from dev.to/owaspblt (only with --blog; needs network)

Everything outside the markers is hand-written and kept as it is: edit README.md directly for the intro,
"Using AI", "Contributing and project policies" (links to CONTRIBUTING.md, SECURITY.md and the other root
policy files) and "License".

Run from anywhere inside the repo:  python3 scripts/readme/update_readme.py [--blog] [--offline]
Needs requests and Pillow (pip install requests pillow). --offline skips every network lookup and
download for the contributor wall; cached results and existing avatars are reused.
"""

import html
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # no __pycache__ next to the scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import Counter
from datetime import datetime, timezone

ROOT = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
).stdout.strip()
README = os.path.join(ROOT, "README.md")
ROUTES = os.path.join(ROOT, "scripts", "routing", "projects.tsv")
HOME = "https://git.owaspblt.org/BLT"
SKIP_DIRS = {"scripts", "docs", ".github"}
# For folders whose README has no usable opening paragraph and that have no .forkmesh/info.json
DESCRIPTIONS = {
    "blt-action": "GitHub Action that automates issue and pull request management: self-assignment, unassignment of stale issues and contributor prompts.",
    "blt-autopatch": "Automated patching: proposes fixes for detected security issues.",
    "blt-sammich": "Slack bot for the OWASP BLT community: GitHub activity, contributor stats, reminders and project discovery.",
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


STAMP = re.compile(r"\*Last updated: [^*]*? UTC")


def replace_section(text, name, body):
    """Swap the body between the section markers. A section whose content is unchanged apart from
    its "Last updated" time keeps the old text, so a run with nothing new produces no commit."""
    start, end = f"<!-- {name}-START -->", f"<!-- {name}-END -->"
    pattern = re.compile(re.escape(start) + r"\n?(.*?)\n?" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"README.md is missing the {start} / {end} markers")
    if STAMP.sub("", match.group(1)) == STAMP.sub("", body):
        return text
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text)


def describe(readme_text):
    """First prose paragraph of a project README, as one plain line."""
    for block in re.split(r"\n\s*\n", readme_text):
        kept = [l for l in block.splitlines()
                if not re.match(r"\s*\*\*(Source Code|Live Site|Version)", l)]
        line = " ".join(" ".join(kept).split())
        line = re.sub(r"^>\s*", "", line)
        if (not line or line[0] in "#<![|>`-=" or line.startswith(("* ", "[!"))
                or re.match(r"\*\*[^*]+:\*\*", line)):
            continue
        line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"[*_`]", "", line).strip()
        if len(line) > 20 and not line.endswith(":"):
            return (line[:157] + "...") if len(line) > 160 else line
    return ""


def folder_info(path):
    """{about, website} strings from <folder>/.forkmesh/info.json (the forge's folder About box), or {}."""
    try:
        with open(os.path.join(path, ".forkmesh", "info.json"), encoding="utf-8") as handle:
            info = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(info, dict):
        return {}
    fields = {"about": info.get("about") or info.get("description"),
              "website": info.get("website") or info.get("homepage")}
    return {k: " ".join(v.split()) for k, v in fields.items() if isinstance(v, str) and v.strip()}


def display_names():
    """Folder -> URL name (e.g. blt-leaf -> BLT-Leaf), from scripts/routing/projects.tsv."""
    names = {}
    for line in open(ROUTES, encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            folder, display = line.rstrip("\n").split("\t")[:2]
            if folder != "-":
                names[folder] = display
    return names


def projects_section():
    names = display_names()
    rows = ["| Project | What it is | Live site |", "|---|---|---|"]
    for slug in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, slug)
        if slug.startswith(".") or slug in SKIP_DIRS or not os.path.isdir(path):
            continue
        text = ""
        for name in ("README.md", "readme.md", "README"):
            if os.path.exists(os.path.join(path, name)):
                text = open(os.path.join(path, name), encoding="utf-8", errors="replace").read()
                break
        info = folder_info(path)
        live = re.search(r"\*\*Live Site:\*\*\s*\[(https://[^\]]+)\]", text)
        site = live.group(1) if live else info.get("website", "")
        live_cell = f"[{site.split('//')[1].rstrip('/')}]({site})" if site.startswith("https://") else ""
        desc = (info.get("about") or DESCRIPTIONS.get(slug) or describe(text)).replace("|", "\\|")
        rows.append(f"| [{names.get(slug, slug)}]({HOME}/{names.get(slug, slug)}) | {desc} | {live_cell} |")
    return "## 📦 Projects\n\n" + "\n".join(rows)


def deploy_section():
    import json
    import tomllib

    table = os.path.join(ROOT, "scripts", "deploy", "projects.tsv")
    rows = ["| Project | Folder | Deploy type | Cloudflare name | Crons |", "|---|---|---|---|---|"]
    for line in open(table, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        project, folder, kind, args, _ = (line.rstrip("\n").split("\t") + ["-"] * 5)[:5]
        name, crons = "", []
        for cfg in ("wrangler.toml", "wrangler.jsonc"):
            path = os.path.join(ROOT, folder, cfg)
            if os.path.exists(path):
                if cfg.endswith(".toml"):
                    conf = tomllib.load(open(path, "rb"))
                else:
                    conf = json.loads(re.sub(r"(?m)^\s*//.*$", "", open(path, encoding="utf-8").read()))
                name = conf.get("name", "")
                crons = (conf.get("triggers") or {}).get("crons") or []
                break
        detail = kind + (f" `{args}`" if args != "-" else "")
        rows.append(f"| {project} | `{folder}/` | {detail} | {name} | {', '.join(f'`{c}`' for c in crons)} |")
    return (
        "## 🚀 Deploying\n\n"
        "Every Cloudflare project deploys from its own folder. Set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, then:\n\n"
        "```bash\nscripts/deploy.sh blt-leaf            # one project\nscripts/deploy.sh blt-leaf blt-api    # several\n"
        "scripts/deploy.sh --all               # everything\nscripts/deploy.sh --all --dry-run     # build and validate only\n```\n\n"
        "Secrets are set per Worker with `wrangler secret put` (see each project's README).\n\n" + "\n".join(rows)
    )


def contributors_section(offline=False):
    import contributors

    people = contributors.build(offline=offline)
    sources = Counter(p["source"] for p in people)
    cells = []
    for p in people:
        handle = f" (@{p['login']})" if p["login"] and p["login"].lower() != p["name"].lower() else ""
        label = html.escape(f"{p['name']}{handle}: {p['commits']} commit{'s' if p['commits'] != 1 else ''}", quote=True)
        img = f'<img src="{p["avatar"]}" width="50" height="50" alt="{html.escape(p["name"], quote=True)}"'
        cells.append(f'<a href="{p["profile"]}" title="{label}">{img}></a>' if p["profile"] else f'{img} title="{label}">')
    accounts = ", ".join(f"{sources[k]} {label}" for k, label in
                         (("instance", "on git.owaspblt.org"), ("github", "on GitHub"),
                          ("git", "by commit name only")) if sources[k])
    return (
        f"## 👥 Contributors ({len(people)} total)\n\n"
        f"*Last updated: {now()} — everyone with a commit in any BLT project, authors and co-authors, bots excluded"
        f" ({accounts}). Avatars and the full list live in"
        f" [`.forkmesh/contributors`](.forkmesh/contributors/contributors.json).*\n\n"
        + " ".join(cells)
    )


def waiting_section(people):
    """Open pull requests on the forge, grouped by author, new contributors first. None when the
    forge can't be read, so the old section is kept."""
    sys.path.insert(0, os.path.join(ROOT, "scripts", "forkmesh"))
    import ledger

    try:
        pulls = ledger.pulls(ledger.client(seconds=60))
    except Exception as error:  # network or ledger trouble: keep the previous section
        print(f"waiting pull requests: {error}", file=sys.stderr)
        return None
    known = {str(v).lower() for p in people for v in (p.get("login"), p.get("name"), p.get("github")) if v}
    merged = {str(p.get("authorName") or "").lower() for p in pulls if str(p.get("status")).lower() == "merged"}
    authors = {}
    for pull in pulls:
        if str(pull.get("status") or "open").lower() == "open":
            authors.setdefault(str(pull.get("authorName") or "unknown"), []).append(pull)
    if not authors:
        return ("## ⏳ Pull Requests Waiting for Review\n\n"
                f"*Last updated: {now()} — no open pull requests on git.owaspblt.org.*")

    def shorten(text, n):
        return text if len(text) <= n else text[:n - 1].rstrip() + "…"

    def is_new(name):
        return name.lower() not in known and name.lower() not in merged

    order = sorted(authors, key=lambda a: (not is_new(a), -len(authors[a]), a.lower()))
    rows = ["| Contributor | Waiting | Pull requests |", "|---|---|---|"]
    for name in order:
        prs = sorted(authors[name], key=lambda p: int(p.get("number") or 0))
        who = f"[{name}]({ledger.profile_url(name)})" + (" 🌱 **new contributor**" if is_new(name) else "")
        links = "<br>".join(
            f"[#{p['number']}]({ledger.DEFAULT_URL}/BLT/pull/{p['number']}) "
            + html.escape(shorten(str(p.get("title") or "").replace("|", "/"), 90))
            for p in prs)
        rows.append(f"| {who} | {len(prs)} | {links} |")
    total = sum(len(v) for v in authors.values())
    new = [a for a in order if is_new(a)]
    return (
        f"## ⏳ Pull Requests Waiting for Review ({total} open, {len(new)} new contributor{'s' if len(new) != 1 else ''})\n\n"
        f"*Last updated: {now()} — open pull requests on [git.owaspblt.org](https://git.owaspblt.org/BLT/pulls),"
        " people making their first BLT contribution first. Reviews help them most.*\n\n" + "\n".join(rows)
    )


def blog_section():
    import requests  # only needed for --blog

    resp = requests.get("https://dev.to/api/articles?username=owaspblt&per_page=10", timeout=15)
    resp.raise_for_status()
    posts = sorted((a for a in resp.json() if a.get("published_at")),
                   key=lambda a: a["published_at"], reverse=True)[:2]
    cells = "".join(
        f"<td align='center' width='50%'><a href='{p['url']}'><img src='{p.get('cover_image') or p.get('social_image') or ''}' width='100%'><br><b>{html.escape(p['title'])}</b></a></td>"
        for p in posts
    )
    return (f"## 📝 Latest Blog Posts\n\n*Last updated: {now()} — from [dev.to/owaspblt](https://dev.to/owaspblt)*\n\n"
            f"<table><tr>{cells}</tr></table>")


def main():
    text = open(README, encoding="utf-8").read()
    text = replace_section(text, "PROJECTS", projects_section())
    offline = "--offline" in sys.argv
    text = replace_section(text, "CONTRIBUTORS", contributors_section(offline=offline))
    if not offline:
        with open(os.path.join(ROOT, ".forkmesh", "contributors", "contributors.json"), encoding="utf-8") as f:
            people = json.load(f).get("contributors") or []
        waiting = waiting_section(people)
        if waiting is not None:
            text = replace_section(text, "WAITING-PRS", waiting)
    text = replace_section(text, "DEPLOY", deploy_section())
    if "--blog" in sys.argv:
        text = replace_section(text, "BLOG-POSTS", blog_section())
    open(README, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
