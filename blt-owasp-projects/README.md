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
│   ├── issues.html
│   ├── repo_status.json
│   ├── www_project_repos.json
│   ├── project_repos_links.json
│   ├── issues.json
│   └── known_issue_ids.json
├── scripts/
│   ├── refresh-kv.sh
│   ├── main.py
│   ├── fetch_repo_status.py
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

New issues across the OWASP organization go to Slack the same way: task `new-issues`, hourly at :43,
`worker/new-issues.js` (one GitHub search for the 100 newest issues, state in
`state:new-issue-ids`, the first run only records them). It posts to the `SLACK_NEW_ISSUES_WEBHOOK`
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

`public/www_project_repos.json` contains basic repository information for OWASP `www-project-*` repositories.

`public/repo_status.json` contains detailed project and repository statistics: per project, the
GitHub repository's stars, forks, license, latest release, open issues and open pull requests
(counted exactly; GitHub's own open-issue count includes pull requests), `commits_30d` /
`commits_90d` and `contributors_30d` / `contributors_90d` (distinct human commit authors; at most
300 commits are read, flagged by `activity_capped`), `committers` (all contributors) and
`top_contributors` (up to five, with login, avatar, profile URL and commit count).

`public/project_repos_links.json` maps OWASP project names to associated GitHub repositories.

`public/issues.json` contains open OWASP issue data.

## License

This project is part of the OWASP BLT initiative. See `LICENSE`.
