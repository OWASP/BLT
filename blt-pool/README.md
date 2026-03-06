# BLT-GitHub-App

A GitHub App that integrates [OWASP BLT](https://owaspblt.org) services into GitHub repositories.

## Features

- **`/assign` command** — Comment `/assign` on any issue to be automatically assigned to it. Assignments expire after 8 hours if no linked PR is submitted.
- **`/unassign` command** — Comment `/unassign` to release an issue assignment so others can pick it up.
- **Automatic unassignment** — A cron task runs every 2 hours to automatically unassign issues where the 8-hour deadline has passed without a linked pull request.
- **`/leaderboard` command** — Comment `/leaderboard` on any issue or PR to see your rank in the monthly leaderboard.
- **Monthly leaderboard** — Uses D1-backed event counters for accurate, scalable org-wide ranking (no per-request repo scanning). Automatically posted on PRs (when opened or merged) showing contributor rankings based on:
  - Open PRs (+1 each)
  - Merged PRs (+10)
  - Closed PRs without merge (−2)
  - PR Reviews (+5; sampled from recent merged PRs)
- **Auto-close excess PRs** — PRs are automatically closed if the author has 50+ open PRs in the repository.
- **Rank improvement congratulations** — When a PR is merged and the author's rank improves on the 6-month leaderboard, they receive a congratulatory message.
- **BLT bug reporting** — When an issue is labeled as `bug`, `vulnerability`, or `security`, it is automatically reported to the [BLT API](https://github.com/OWASP-BLT/BLT-API).
- **Welcome messages** — New issues and pull requests receive helpful onboarding messages with contribution tips.
- **Merge congratulations** — Merged PRs receive an acknowledgement message celebrating the contributor's work.

## Setup

### Prerequisites

- [Cloudflare Workers](https://workers.cloudflare.com/) account
- A GitHub App

### Configuration

Copy `.dev.vars.example` to `.dev.vars` and fill in your credentials:

```bash
cp .dev.vars.example .dev.vars
```
## Architecture Notes

### Leaderboard Scalability

The leaderboard uses an **event-driven D1 model**:
- Webhook events increment persistent counters in D1.
- `/leaderboard` reads precomputed counters from D1.
- This avoids per-request org scans and scales to very large orgs.

**Tracked by webhook events:**
- `pull_request` opened: open PR counter (+1)
- `pull_request` closed merged: merged PRs (+1), open PR counter (-1)
- `pull_request` closed unmerged: closed PRs (+1), open PR counter (-1)
- `pull_request_review` submitted: reviews (+1, first two unique reviewers per PR/month)
- `issue_comment` created: comments (+1, excludes bots and CodeRabbit pings)

### D1 Setup

1. Create database:

```bash
npx wrangler d1 create blt-leaderboard
```

2. Copy returned `database_id` into `wrangler.toml` under `[[d1_databases]]`.

3. Deploy worker:

```bash
npx wrangler deploy
```


| Variable | Description |
|---|---|
| `APP_ID` | GitHub App numeric ID |
| `PRIVATE_KEY` | GitHub App private key (PEM, PKCS#1 or PKCS#8) |
| `WEBHOOK_SECRET` | GitHub App webhook secret |
| `GITHUB_APP_SLUG` | GitHub App URL slug (e.g. `blt-github-app`) |
| `BLT_API_URL` | BLT API base URL (default: `https://blt-api.owasp-blt.workers.dev`) |
| `GITHUB_CLIENT_ID` | OAuth client ID (optional) |
| `GITHUB_CLIENT_SECRET` | OAuth client secret (optional) |

### Running

```bash
cp .dev.vars.example .dev.vars   # fill in your credentials
npx wrangler dev                 # local dev server
npx wrangler deploy              # deploy to Cloudflare
```

**Note:** The `public/` directory contains static assets (logo, HTML files) that are automatically served by Cloudflare Workers when the `[site]` bucket is configured in `wrangler.toml`.

Set secrets securely for production:
```bash
npx wrangler secret put APP_ID
npx wrangler secret put PRIVATE_KEY
npx wrangler secret put WEBHOOK_SECRET
```

Bulk upload from `.env.production` with Worker verification:
```bash
chmod +x scripts/upload-production-vars.sh
./scripts/upload-production-vars.sh
```

The script verifies `CLOUDFLARE_WORKER_NAME` in `.env.production` matches
`name` in `wrangler.toml` before uploading any secrets.

### Testing

```bash
pip install pytest
pytest test_worker.py -v
```

## GitHub App Permissions

The app requires the following repository permissions:

| Permission | Access |
|---|---|
| Issues | Read & Write |
| Pull Requests | Read & Write |
| Metadata | Read |

And listens for these webhook events: `issue_comment`, `issues`, `pull_request`, `pull_request_review`.

## Usage

### Issue Assignment

In any issue, comment:

```
/assign
```

You will be assigned to the issue with an 8-hour deadline to submit a pull request.

To release an issue:

```
/unassign
```

### Bug Reporting

When an issue is labeled with `bug`, `vulnerability`, or `security`, the app automatically creates a corresponding entry in the BLT platform and posts the Bug ID as a comment.

## Cloudflare Worker

This app runs as a [Cloudflare Workers](https://workers.cloudflare.com/) Python Worker
and includes a **landing homepage** where users can view the app status and
install it on their own GitHub organization.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/health` | JSON health check |
| `POST` | `/api/github/webhooks` | GitHub webhook receiver |
| `GET` | `/callback` | Post-installation success page |

## Project Structure

```
├── worker.py                     # Python Cloudflare Worker (all handlers + landing page)
├── wrangler.toml                 # Cloudflare Worker configuration
├── .dev.vars.example             # Local dev environment variables template
├── test_worker.py                # pytest unit tests for pure-Python utilities
├── app.yml                       # GitHub App manifest
└── LICENSE
```

## Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) — Main bug logging platform
- [BLT-Action](https://github.com/OWASP-BLT/BLT-Action) — GitHub Action for issue assignment
- [BLT-API](https://github.com/OWASP-BLT/BLT-API) — REST API for BLT

## License

[AGPL-3.0](LICENSE)

