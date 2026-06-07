# OWASP Projects Dashboard

A static dashboard for tracking OWASP project repositories, repository status, and open issues.

## Overview

The hosted site lives in `public/` so Cloudflare can serve it directly. GitLab CI validates that deployable folder and can refresh the JSON data files that power the dashboards.

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
│   ├── main.py
│   ├── fetch_repo_status.py
│   ├── fetch_issues.py
│   ├── scrape_github_links.py
│   └── sweep.py
├── .gitlab-ci.yml
├── requirements.txt
└── wrangler.toml
```

## GitLab CI

`validate_static` runs on normal pipelines and checks that `public/` contains the hosted pages plus valid JSON.

`refresh_data` runs from scheduled pipelines or as a manual job from a web pipeline. It refreshes:

- `public/www_project_repos.json`
- `public/repo_status.json`
- `public/issues.json`
- `public/known_issue_ids.json`
- `public/project_repos_links.json`

When those files change, the job commits them back to the default branch. Cloudflare can then auto-deploy the checked-in `public/` folder.

`sweep_repos` is manual and notification-only.

Set these GitLab CI/CD variables as needed:

- `GITHUB_TOKEN`
- `ACCESS_TOKEN`
- `SLACK_WEBHOOK_URL`
- `SLACK_NEW_ISSUES_WEBHOOK`
- `SLACK_WEBHOOK_URL_SWEEP`
- `CI_PUSH_TOKEN` if the default branch does not allow `CI_JOB_TOKEN` pushes

## Cloudflare

`wrangler.toml` points at `./public`:

```toml
pages_build_output_dir = "./public"

[assets]
directory = "./public"
```

Use `public` as the Cloudflare Pages build output directory. No Cloudflare-side build command is required.

## Local Development

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run data refresh scripts locally:

```bash
export GITHUB_TOKEN="your_token_here"
export ACCESS_TOKEN="your_token_here"
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
