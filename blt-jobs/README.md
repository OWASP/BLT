# BLT Jobs

**Live Site:** [https://jobs.owaspblt.org/](https://jobs.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/tree/main/blt-jobs](https://git.owaspblt.org/BLT/tree/main/blt-jobs)

<p align="center"><img src="logo.png" alt="blt-jobs logo" width="160" height="160"></p>

BLT Jobs is a Git-native job platform for the [OWASP BLT](https://owasp.org/www-project-bug-logging-tool/) ecosystem. Jobs and seeker profiles live as Markdown-backed open data in this repository, so the source of truth is public, reviewable, forkable, and auditable through Git history.

**Live site:** [jobs.owaspblt.org](https://jobs.owaspblt.org)

## Architecture

See [docs/git-native-architecture.md](docs/git-native-architecture.md) for the Git-native product contract, submission workflow, future provider abstraction points, public-data boundaries, maintainer review model, and issue/MR -> Markdown -> JSON -> static site flow.

## How It Works

- Job listings live in `jobs/*.md`.
- Seeker profiles live in `seekers/*.md`.
- `npm run build:jobs` turns the Markdown sources into `public/data/jobs.json` and `public/data/seekers.json`.
- Cloudflare Workers serves the committed static site files directly and excludes repository internals with `.assetsignore`.
- Contributors submit jobs and profiles as issues on [git.owaspblt.org](https://git.owaspblt.org/BLT/issues), using the bodies in `issue-templates/`. The `.forkmesh/blt-jobs--process-submissions.yml` workflow processes each issue when it is opened, edited or labelled, commits the Markdown file, comments, and closes the issue.
- Seeker profiles can link to GitHub, GitLab, LinkedIn, a portfolio, or any combination of those services.

## Contribute

Use the [Contribute page](https://jobs.owaspblt.org/add.html) or [open an issue](https://git.owaspblt.org/BLT/issues/new) and paste one of the templates in `issue-templates/` into its body (the forge has no issue templates, so the page links to them):

- `job-posting-from-link`: paste a public job URL so maintainers can generate a reviewable Markdown draft.
- `job-posting`: enter a job manually.
- `job-seeker`: create a transparent public seeker profile.
- `flag-job-posting`: report a listing that should be removed (title starting with `[FLAG]`).

`scripts/actions/process-submission.mjs` recognizes the labels `job-posting`, `job-posting-from-link`, `job-seeker` and `flag-job-posting`, and also the template headings, so submissions work for users who cannot apply labels. The conversion itself is `createFromIssue()` in `scripts/submissions.js`.

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
npm run test:worker
npm run validate:jobs
npm run list:jobs
npm run expire:jobs
npm run discover:candidates
npm run build:worker
```

`npm run discover:candidates` writes candidate URLs for maintainer review only. It does not publish jobs and is not part of the canonical submission path.

## Automation

The workflows are `.forkmesh/blt-jobs--process-submissions.yml` (issue events) and `.forkmesh/blt-jobs--expire-jobs.yml` (by hand only). See [docs/workflows.md](../docs/workflows.md); they need no GitLab secrets.

Expired jobs do not need that job to disappear from the site: the Worker serves `/data/jobs.json` and drops every job whose `effective_expires_at` (`expires_at`, else the posted/created date + 60 days) has passed. `npm run expire:jobs` only deletes the expired Markdown files, as optional cleanup.

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

For local deployment, use `npm run deploy:worker` to regenerate JSON first. `.forkmesh/deploy.yml` deploys the Worker on each push to `main`.

Configure `jobs.owaspblt.org` as a Cloudflare custom domain for the `blt-jobs` Worker.

## Repository Layout

```text
.
├── issue-templates/
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
