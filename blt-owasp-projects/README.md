# OWASP Projects Dashboard

**Live Site:** [https://projects.owaspblt.org/](https://projects.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-OWASP-Projects](https://git.owaspblt.org/BLT/BLT-OWASP-Projects)

A static dashboard for tracking OWASP project repositories, repository status, and open issues.

The home page (`index.html`, `matrix.js`, `matrix.css`) shows one card per OWASP project: its level,
type and pitch, GitHub stars, open issues and pull requests, commits and active people over the last
30 and 90 days, when it was last committed to, and its top five contributors (bots left out with the
rules of `scripts/readme/contributors.py`). Search, filters and sorting run in the browser and are
kept in the URL. It loads no third-party scripts, styles or fonts; only the contributor avatars come
from GitHub.

## Overview

The hosted site lives in `public/`, served by a small Worker that reads the refreshed JSON data files from Workers KV.

## Project Structure

```text
.
├── public/
│   ├── index.html
│   ├── matrix.js
│   ├── matrix.css
│   ├── projects.html
│   ├── open.html
│   ├── issues.html
│   ├── repo_status.json
│   ├── open_issues.json
│   ├── open_prs.json
│   ├── www_project_repos.json
│   ├── project_repos_links.json
│   ├── issues.json
│   └── known_issue_ids.json
├── scripts/
│   ├── refresh-kv.sh
│   ├── main.py
│   ├── fetch_repo_status.py
│   ├── fetch_open_work.py
│   ├── fetch_issues.py
│   ├── scrape_github_links.py
│   └── sweep.py
├── worker/index.js
├── test/worker.test.mjs
├── requirements.txt
└── wrangler.toml
```

## Data refresh (Workers KV)

The workflow `.forkmesh/blt-owasp-projects--refresh-data.yml` runs daily (04:23 UTC) on
git.owaspblt.org. It runs `scripts/refresh-kv.sh`, which seeds `public/` with the live data files,
runs the four generators and writes each data file that is valid, not much smaller than before and
changed into the Worker's KV namespace. It refreshes:

- `www_project_repos.json`
- `repo_status.json`
- `open_issues.json`, `open_prs.json`
- `issues.json`
- `known_issue_ids.json`
- `project_repos_links.json`

Nothing is committed and nothing is redeployed. The Worker (`worker/index.js`) serves those paths
from KV and falls back to the copies committed under `public/` while KV has none. The committed
copies are only that fallback; they are no longer updated.

The workflow needs the Actions secrets `GH_API_TOKEN`, `CLOUDFLARE_API_TOKEN` (Workers KV
Storage: Edit) and `CLOUDFLARE_ACCOUNT_ID`. `.forkmesh/blt-owasp-projects--sweep-repos.yml` is a
manual, notification-only job (`SLACK_WEBHOOK_URL_SWEEP`).

New `www-project-*` repositories are posted to #project-new-projects on Slack by the Worker, not the
workflow: blt-cron calls `POST /__scheduled` (task `new-projects`) hourly at :41, and
`worker/new-projects.js` lists the 100 newest OWASP repositories and posts the ones it has not seen
(ids kept in KV under `state:new-project-ids`; the first run only records them). Worker secrets:
`CRON_SECRET` (the same as blt-cron's), `SLACK_WEBHOOK_URL` and, optionally, `GH_API_TOKEN`.

New issues across every OWASP project go to Slack the same way: task `new-issues`, hourly at :43,
`worker/new-issues.js`. One GitHub search lists the 100 newest issues in the OWASP organization; the
projects whose code lives elsewhere (every `repo_name` in `repo_status.json` outside `OWASP/`, such
as zaproxy/zaproxy, juice-shop/juice-shop or DefectDojo/django-DefectDojo; 63 today) are searched in
batches of 40 with `repo:` qualifiers, and their lines show the owner (`zaproxy/zaproxy#9536`). The
repository list is cached for a day in `state:outside-repos`; seen issues are in
`state:new-issue-ids`, and the first run only records them. It posts to the `SLACK_NEW_ISSUES_WEBHOOK`
Worker secret; without it the task keeps its state current and posts nothing.
`scripts/fetch_issues.py` still builds `issues.json` daily; the workflow gives it no webhook, so it
posts nothing.

## Cloudflare

`wrangler.toml` deploys a Worker (`worker/index.js`) with `public/` as its static assets, and binds
the KV namespace as `DATA`. Deploy with `scripts/deploy.sh blt-owasp-projects` from the repository
root. Tests: `scripts/ci/test.sh blt-owasp-projects` (runs `node --test test/*.test.mjs`).

## Local Development

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run data refresh scripts locally:

```bash
export GITHUB_TOKEN="your_token_here"
python scripts/main.py
python scripts/fetch_repo_status.py
python scripts/fetch_open_work.py
python scripts/fetch_issues.py
python scripts/scrape_github_links.py
```

Open the dashboards from `public/`:

```bash
open public/index.html
open public/projects.html
open public/issues.html
```

## Data Files

`public/www_project_repos.json` contains basic repository information for OWASP `www-project-*`
repositories; `projects.html` (`repos.js`) lists them in a sortable table, matched to their owasp.org
projects through `repo_status.json`.

Each card on the home page has the same cover: a band in the colour of the repository's main
language, a monogram and GitHub's language bar (`languages` in `repo_status.json`: GitHub's language
breakdown and colours, one GraphQL query per 25 repositories). `open_summary.json` holds each
repository's counts for open.html's quick views (good first issues, help wanted, pull requests
needing review, quick reviews of 1 to 50 lines, new contributors' pull requests), shown on the cards
and in the home page's "Find something to work on" strip; `fetch_open_work.py` and `open.js` use the
same label rules.

`public/repo_status.json` lists every project in the [owasp.org inventory](https://owasp.org/projects/)
(its public API, `/api/public/projects/list`), cross-checked with the OWASP organization's
`www-project-*` repositories: an active www-project repository that no inventory project points to is
added with `listed: false` (the matrix tags it "Not on owasp.org"). owasp.github.io's older
`projects.json` fills in the pitch and project-page fields where a project is in both. The card
picture is owasp.org's hero image (`image`) or, without one, a WordPress.com mShots screenshot of the
project's website or repository. Stats come from the
project's code repository (owasp.org's `github_url`, else the `projects.json` code URL, else the
www-project repository). Organizations that require two-factor auth refuse a member's token that
lacks it; those requests are retried without the token. Per project, the
GitHub repository's stars, forks, license, latest release, open issues and open pull requests
(counted exactly; GitHub's own open-issue count includes pull requests), `commits_30d` /
`commits_90d` and `contributors_30d` / `contributors_90d` (distinct human commit authors; at most
300 commits are read, flagged by `activity_capped`), `committers` (all contributors) and
`top_contributors` (up to five, with login, avatar, profile URL and commit count).

`public/project_repos_links.json` maps OWASP project names to associated GitHub repositories.

`public/open_issues.json` and `public/open_prs.json` hold every open issue and pull request in the
repositories of `repo_status.json` (GitHub GraphQL, no 1,000-result cap): title, number, labels,
author (bots flagged), assignees, comments, dates and, for pull requests, draft, review decision and
size. `open.html?kind=issues|prs` shows them in sortable tables; `&repo=owner/name` filters to one
repository (the cards' Open issues / Open PRs link there).

`public/issues.json` contains open issues in the OWASP organization (GitHub search, at most 1,000) for
`issues.html` and the Slack alert.

## License

This project is part of the OWASP BLT initiative. See `LICENSE`.
