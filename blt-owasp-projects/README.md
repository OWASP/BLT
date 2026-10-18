# OWASP Projects Dashboard

**Live Site:** [https://projects.owaspblt.org/](https://projects.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-OWASP-Projects](https://git.owaspblt.org/BLT/BLT-OWASP-Projects)

A static dashboard for tracking OWASP project repositories, repository status, and open issues.

## Overview

The hosted site lives in `public/`, served by a small Worker that reads the refreshed JSON data files from Workers KV.

## Project Structure

```text
.
├── public/
│   ├── index.html
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

`public/repo_status.json` contains detailed project and repository statistics.

`public/project_repos_links.json` maps OWASP project names to associated GitHub repositories.

`public/issues.json` contains open OWASP issue data.

## License

This project is part of the OWASP BLT initiative. See `LICENSE`.
