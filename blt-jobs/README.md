# BLT Jobs

BLT Jobs is an open source job board for the [OWASP BLT](https://owasp.org/www-project-bug-logging-tool/) ecosystem. Jobs and seeker profiles live in Markdown files in this GitLab repository, so the underlying data is public and reviewable.

**Live site:** [jobs.owaspblt.org](https://jobs.owaspblt.org)

## How It Works

- Job listings live in `jobs/*.md`.
- Seeker profiles live in `seekers/*.md`.
- `npm run build:jobs` turns the Markdown sources into `data/jobs.json` and `data/seekers.json`.
- The static site is packaged with `npm run build:worker` and deployed to Cloudflare Workers.
- Contributors submit jobs and profiles through GitLab issue templates. A scheduled or manually started GitLab pipeline processes labeled issues, commits the Markdown file, and closes the issue.
- Seeker profiles can link to GitHub, GitLab, LinkedIn, a portfolio, or any combination of those services.

## Contribute

Use the [Contribute page](https://jobs.owaspblt.org/add.html) or open a GitLab issue with one of the templates in `.gitlab/issue_templates/`:

- `job-posting-from-link`: paste a job URL for automatic scraping.
- `job-posting`: enter a job manually.
- `job-seeker`: create a transparent public seeker profile.
- `flag-job-posting`: report a listing that should be removed.

GitLab labels each template through a quick action. The `process_submissions` CI job reads open issues through the GitLab API and recognizes both labels and template headings, so submissions also work for users who cannot apply labels.

## Local Development

```bash
npm ci
npm run build:jobs
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

Use Node.js 22 or newer for Cloudflare Wrangler deployment commands.

Useful commands:

```bash
npm run build:jobs
npm run validate:jobs
npm run list:jobs
npm run expire:jobs
npm run build:worker
```

## GitLab CI Setup

The pipeline is defined in `.gitlab-ci.yml`. Add these masked CI/CD variables in GitLab:

| Variable | Purpose |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | Deploy the static asset Worker |
| `CLOUDFLARE_ACCOUNT_ID` | Select the Cloudflare account |
| `GITLAB_TOKEN` | Read, comment on, and close GitLab issues |
| `GITLAB_PUSH_TOKEN` | Push generated Markdown and JSON commits to `main` |

`GITLAB_TOKEN` and `GITLAB_PUSH_TOKEN` can be the same project access token with API and repository write access. As an alternative to `GITLAB_PUSH_TOKEN`, enable GitLab's **Allow Git push requests to the repository** setting for CI job tokens.

Create a GitLab pipeline schedule for periodic submission processing and stale job expiry. The same maintenance jobs can also be started manually from the GitLab pipeline UI.

## Cloudflare Workers

`wrangler.toml` serves `.worker-assets/` as static assets with `404.html` handling. Run:

```bash
npm run deploy:worker
```

Configure `jobs.owaspblt.org` as a Cloudflare custom domain for the `blt-jobs` Worker.

## Repository Layout

```text
.
├── .gitlab-ci.yml
├── .gitlab/issue_templates/
├── assets/
├── data/
├── jobs/
├── seekers/
├── scripts/
├── wrangler.toml
└── *.html
```
