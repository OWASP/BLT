# BLT Jobs

BLT Jobs is a Git-native job platform for the [OWASP BLT](https://owasp.org/www-project-bug-logging-tool/) ecosystem. Jobs and seeker profiles live as Markdown-backed open data in this repository, so the source of truth is public, reviewable, forkable, and auditable through Git history.

**Live site:** [jobs.owaspblt.org](https://jobs.owaspblt.org)

## Architecture

See [docs/git-native-architecture.md](docs/git-native-architecture.md) for the Git-native product contract, current GitLab workflow, future provider abstraction points, public-data boundaries, maintainer review model, and issue/MR -> Markdown -> JSON -> static site flow.

## How It Works

- Job listings live in `jobs/*.md`.
- Seeker profiles live in `seekers/*.md`.
- `npm run build:jobs` turns the Markdown sources into `public/data/jobs.json` and `public/data/seekers.json`.
- Cloudflare Workers serves the committed static site files directly and excludes repository internals with `.assetsignore`.
- Contributors submit jobs and profiles through GitLab issue templates. A scheduled or manually started GitLab pipeline processes labeled issues, commits the Markdown file, and closes the issue.
- Seeker profiles can link to GitHub, GitLab, LinkedIn, a portfolio, or any combination of those services.

## Contribute

Use the [Contribute page](https://jobs.owaspblt.org/add.html) or open a GitLab issue with one of the templates in `.gitlab/issue_templates/`:

- `job-posting-from-link`: paste a public job URL so maintainers can generate a reviewable Markdown draft.
- `job-posting`: enter a job manually.
- `job-seeker`: create a transparent public seeker profile.
- `flag-job-posting`: report a listing that should be removed.

GitLab labels each template through a quick action. The `process_submissions` CI job reads open issues through the GitLab API and recognizes both labels and template headings, so submissions also work for users who cannot apply labels.

Accepted submissions become public Markdown in this repository. Do not submit private applicant notes, private phone numbers, identity documents, secrets, or contact routes that should not be public Git history.

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
npm test
npm run validate:jobs
npm run list:jobs
npm run expire:jobs
npm run discover:candidates
npm run build:worker
```

`npm run discover:candidates` writes candidate URLs for maintainer review only. It does not publish jobs and is not part of the canonical submission path.

## GitLab CI Setup

The pipeline is defined in `.gitlab-ci.yml`. Add these masked CI/CD variables in GitLab:

| Variable | Purpose |
| --- | --- |
| `GITLAB_TOKEN` | Read, comment on, and close GitLab issues |
| `GITLAB_PUSH_TOKEN` | Push generated Markdown and JSON commits to `main` |

`GITLAB_TOKEN` and `GITLAB_PUSH_TOKEN` can be the same project access token with API and repository write access. As an alternative to `GITLAB_PUSH_TOKEN`, enable GitLab's **Allow Git push requests to the repository** setting for CI job tokens.

Create a GitLab pipeline schedule for periodic submission processing and stale job expiry. The same maintenance jobs can also be started manually from the GitLab pipeline UI.

If `GITLAB_TOKEN` is not configured or is not exposed to a pipeline, GitLab skips the `process_submissions` job. The `expire_jobs` maintenance job can still run on the schedule.

## Cloudflare Workers

`wrangler.toml` serves the committed static site assets with `404.html` handling. Run:

```bash
npm run deploy:worker
```

For Cloudflare Workers Builds, the default deploy command is enough:

| Setting | Value |
| --- | --- |
| Build command | Leave blank |
| Deploy command | `npx wrangler@4 deploy` |

For local deployment, use `npm run deploy:worker` to regenerate JSON first. GitLab CI does not deploy the Worker.

Configure `jobs.owaspblt.org` as a Cloudflare custom domain for the `blt-jobs` Worker.

## Repository Layout

```text
.
├── .gitlab-ci.yml
├── .gitlab/issue_templates/
├── .assetsignore
├── assets/
├── docs/
├── jobs/
├── public/
├── seekers/
├── scripts/
├── wrangler.toml
└── package.json
```
