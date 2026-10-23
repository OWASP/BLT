#!/usr/bin/env python3
"""Gold, silver and bronze ratings for the project folders of the BLT monorepo.

Every project is rated against the same checklist (CRITERIA), read from the checkout and from the
folder's row in forge_data.json:

- bronze: the basics. A README that explains the project, a description, a licence and a logo.
- silver: it runs. Tests in CI (scripts/ci/tests.tsv), an automatic deploy (scripts/deploy/projects.tsv),
  a live site that the README links, and README steps to run it locally.
- gold: it is looked after. The shared BLT top bar on its site, a contributing guide, a commit in the
  last 90 days, more than one contributor in the last year, and no open issue left untouched for 60 days.

A project is gold when it meets every criterion that applies to it, silver when it meets every bronze
and silver one, and bronze otherwise. The site criteria (live, readme_live, theme) and deploy apply
only to folders that deploy to Cloudflare (a wrangler.toml in the folder or its deploy directory); NOT_RATED folders get no rating.

generate_forge_data.py adds ``rating`` (and ``gold_issue``, the open issue labelled
``gold-standard`` for the folder) to each row. Run this file to rate an existing forge_data.json in
place, or with --report to print what each project still needs:

    python3 scripts/ratings.py public/forge_data.json
    python3 scripts/ratings.py public/forge_data.json --report
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_sites  # noqa: E402
from datetime import datetime, timedelta, timezone

TIERS = ("bronze", "silver", "gold")
# Repository configuration, not projects: shown on Waypoint without a rating.
NOT_RATED = {"coderabbit"}
GOLD_LABEL = "gold-standard"
STALE_ISSUE_DAYS = 60
ACTIVE_DAYS = 90
README_MIN_CHARS = 1000

CRITERIA = [
    {"id": "readme", "tier": "bronze", "label": "README explains the project",
     "fix": f"Write a README.md of at least {README_MIN_CHARS} characters: what the project is, who it is for, "
            "its live site and where to report issues."},
    {"id": "description", "tier": "bronze", "label": "One-line description",
     "fix": "Add `.forkmesh/info.json` to the folder with a one-line `description` (and `website` if it has one), "
            "so Waypoint and the forge can show what the project is."},
    {"id": "license", "tier": "bronze", "label": "Licence file",
     "fix": "Add a LICENSE file to the folder (most BLT projects are AGPL-3.0; copy the repository root's LICENSE)."},
    {"id": "logo", "tier": "bronze", "label": "Project logo",
     "fix": "Add `logo.svg` (and `logo.png`) to the folder, following the logo guide on design.owaspblt.org."},
    {"id": "tests", "tier": "silver", "label": "Tests run in CI",
     "fix": "Add automated tests and a row for the folder in `scripts/ci/tests.tsv`, so every pull request runs them "
            "(`scripts/ci/test.sh <folder>`)."},
    {"id": "deploy", "tier": "silver", "label": "Deploys automatically",
     "fix": "Add the folder to `scripts/deploy/projects.tsv` with its deploy type, so merging to main deploys it."},
    {"id": "live", "tier": "silver", "label": "Live site", "needs_site": True,
     "fix": "Give the Worker a custom domain under owaspblt.org (a `custom_domain` route in `wrangler.toml`) and "
            "make sure the home page loads."},
    {"id": "readme_live", "tier": "silver", "label": "README links the live site", "needs_site": True,
     "fix": "Put the live site's address near the top of the README (`**Live Site:** https://<name>.owaspblt.org/`)."},
    {"id": "setup", "tier": "silver", "label": "README shows how to run it",
     "fix": "Add a \"Run locally\" (or Install / Getting started) section to the README with the exact commands "
            "in a code block, including how to run the tests."},
    {"id": "theme", "tier": "gold", "label": "Uses the shared BLT top bar", "needs_site": True,
     "fix": "Put the shared top bar first in every page (`<blt-nav project=\"<folder>\" ...>` with "
            "`https://owaspblt.org/_shared/blt-nav.js`) and use the BLT theme: red-600 primary, neutral grays, "
            "light and dark mode, phone-friendly. See design.owaspblt.org and blt-waypoint/public."},
    {"id": "contributing", "tier": "gold", "label": "Contributing guide",
     "fix": "Add CONTRIBUTING.md (or a Contributing section in the README): how to set up, test, and open a pull "
            "request on git.owaspblt.org, linking the root CONTRIBUTING.md and AI_POLICY.md."},
    {"id": "active", "tier": "gold", "label": f"Commit in the last {ACTIVE_DAYS} days",
     "fix": "Land a change: work through this project's open issues, or update its dependencies and docs."},
    {"id": "community", "tier": "gold", "label": "Two or more contributors this year",
     "fix": "Grow the contributors: label a few small issues `good first issue` and link them from the README."},
    {"id": "triage", "tier": "gold", "label": f"No issue untouched for {STALE_ISSUE_DAYS} days",
     "fix": f"Triage the open issues that have had no activity for {STALE_ISSUE_DAYS} days: close, fix or comment "
            "on each."},
]
BY_ID = {c["id"]: c for c in CRITERIA}

SETUP_HEADING = re.compile(r"^#{1,4}\s.*\b(run|running|install|installation|setup|set up|getting started|quick ?start|"
                           r"develop|development|usage|build|local)\b", re.I | re.M)
CONTRIB_HEADING = re.compile(r"^#{1,4}\s.*contribut", re.I | re.M)
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "build", "dist", "__pycache__", ".dart_tool", "target"}
SOURCE_EXT = (".html", ".js", ".mjs", ".jsx", ".ts", ".tsx", ".py", ".jinja", ".j2", ".njk", ".svelte", ".vue")


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _ts(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def tsv_folders(path, want_type=False):
    """Folders listed in a tab-separated scripts/ table (first column), skipping comments."""
    rows = {}
    for line in _read(path).splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        rows[cols[0]] = cols[2] if want_type and len(cols) > 2 else True
    return rows


def uses_top_bar(folder_path):
    """True when any page or script of the folder renders the shared <blt-nav> top bar."""
    for base, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if name.endswith(SOURCE_EXT) and "<blt-nav" in _read(os.path.join(base, name)):
                return True
    return False


def checks(root, row, now, tables):
    """{criterion id: True | False | None (does not apply)} for one forge_data row."""
    folder = row["folder"]
    path = os.path.join(root, folder)
    readme = _read(os.path.join(path, "README.md"))
    files = set(os.listdir(path)) if os.path.isdir(path) else set()
    site = bool(live_sites.wrangler_path(root, folder))
    last = _ts(row.get("last_commit_at"))
    stale = [i for i in row.get("_issues") or []
             if now - (_ts(i.get("updated_at")) or now) > timedelta(days=STALE_ISSUE_DAYS)]
    deploy_type = tables["deploy"].get(folder)
    host = re.sub(r"^https?://(www\.)?", "", str(row.get("live_url") or "")).rstrip("/")
    return {
        "readme": len(readme) >= README_MIN_CHARS,
        "description": bool((row.get("description") or "").strip()),
        "license": any(re.match(r"^(licen[cs]e|copying)(\.|$)", f, re.I) for f in files),
        "logo": "logo.svg" in files,
        "tests": folder in tables["tests"],
        "deploy": (bool(deploy_type) and deploy_type != "-") if site or deploy_type else None,
        "live": bool(row.get("live_url")) if site else None,
        "readme_live": (bool(host) and host in readme) if site and row.get("live_url") else (False if site else None),
        "setup": bool(SETUP_HEADING.search(readme)) and "```" in readme,
        "theme": uses_top_bar(path) if site else None,
        "contributing": "CONTRIBUTING.md" in files or bool(CONTRIB_HEADING.search(readme)),
        "active": bool(last) and now - last <= timedelta(days=ACTIVE_DAYS),
        "community": (row.get("contributor_count") or 0) >= 2,
        "triage": not stale,
    }


def rate(result):
    """The rating dict for a checks() result."""
    met = [k for k, v in result.items() if v is True]
    missing = [k for k, v in result.items() if v is False]
    na = [k for k, v in result.items() if v is None]
    tier = "bronze"
    if not any(BY_ID[k]["tier"] in ("bronze", "silver") for k in missing):
        tier = "silver"
        if not missing:
            tier = "gold"
    applicable = len(met) + len(missing)
    return {"tier": tier, "score": round(100 * len(met) / applicable) if applicable else 0,
            "met": met, "missing": missing, "na": na}


def load_tables(root):
    return {
        "tests": tsv_folders(os.path.join(root, "scripts", "ci", "tests.tsv")),
        "deploy": tsv_folders(os.path.join(root, "scripts", "deploy", "projects.tsv"), want_type=True),
    }


def _labels(issue):
    return [l.get("name") if isinstance(l, dict) else l for l in issue.get("labels") or []]


def gold_issue(issues):
    """URL of the open gold-standard issue among a folder's issue entries, if any."""
    for issue in issues or []:
        if GOLD_LABEL in _labels(issue):
            return issue.get("html_url")
    return None


def apply(payload, root, now=None):
    """Add rating and gold_issue to every row of a forge_data payload (in place)."""
    now = now or datetime.now(timezone.utc)
    tables = load_tables(root)
    folders = {r["folder"] for r in payload.get("repos") or []}
    by_folder = {}
    for issue in payload.get("open_issues") or []:
        for folder in {issue.get("folder"), *_labels(issue)} & folders:
            by_folder.setdefault(folder, []).append(issue)
    for row in payload.get("repos") or []:
        if row["folder"] in NOT_RATED:
            row["rating"], row["gold_issue"] = None, None
            continue
        issues = by_folder.get(row["folder"], [])
        row["rating"] = rate(checks(root, {**row, "_issues": issues}, now, tables))
        row["gold_issue"] = gold_issue(issues)
    payload["rating_criteria"] = [{k: c[k] for k in ("id", "tier", "label", "fix")} for c in CRITERIA]
    payload.setdefault("cumulative", {})["ratings"] = {
        t: sum(1 for r in payload.get("repos") or [] if (r["rating"] or {}).get("tier") == t) for t in TIERS}
    return payload


def report(payload):
    for row in sorted((r for r in payload["repos"] if r["rating"]),
                      key=lambda r: (TIERS.index(r["rating"]["tier"]), r["folder"])):
        rating = row["rating"]
        need = ", ".join(rating["missing"]) or "-"
        print(f"{rating['tier']:<7} {rating['score']:>3}%  {row['folder']:<24} needs: {need}")
    print(json.dumps(payload["cumulative"]["ratings"]))


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[-2].strip(), file=sys.stderr)
        return 2
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    with open(argv[0], encoding="utf-8") as handle:
        payload = json.load(handle)
    apply(payload, root)
    if "--report" in argv:
        report(payload)
        return 0
    with open(argv[0], "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), ensure_ascii=False)
        handle.write("\n")
    print(f"ratings: {json.dumps(payload['cumulative']['ratings'])} -> {argv[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
