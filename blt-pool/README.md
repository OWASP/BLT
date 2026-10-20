# BLT-Pool

**Live Site:** [https://pool.owaspblt.org/](https://pool.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Pool](https://git.owaspblt.org/BLT/BLT-Pool)

A GitHub App that integrates [OWASP BLT](https://owaspblt.org) services into GitHub repositories.

This repository now serves two connected surfaces:

- **`/assign` command** — Comment `/assign` on any issue to be automatically assigned to it. Assignments expire after 8 hours if no linked PR is submitted.
- **`/unassign` command** — Comment `/unassign` to release an issue assignment so others can pick it up.
- **Automatic unassignment** — A cron task runs every 2 hours to automatically unassign issues where the 8-hour deadline has passed without a linked pull request. The schedule (`0 */2 * * *`) now runs from the [blt-cron](../blt-cron) dispatcher Worker, which calls `POST /__scheduled` with the shared `CRON_SECRET` (set it with `wrangler secret put CRON_SECRET`); this Worker has no cron trigger of its own.
- **`/leaderboard` command** — Comment `/leaderboard` on any issue or PR to see your rank in the monthly leaderboard.
- **Monthly leaderboard** — Uses D1-backed event counters for accurate, scalable org-wide ranking (no per-request repo scanning). Automatically posted on PRs (when opened or merged) showing contributor rankings based on:
  - Open PRs (+1 each)
  - Merged PRs (+10)
  - Closed PRs without merge (−2)
  - PR Reviews (+5; sampled from recent merged PRs)
- **Auto-close excess PRs** — PRs are automatically closed if the author has 50+ open PRs in the repository.
- **Rank improvement congratulations** — When a PR is merged and the author's rank improves on the 6-month leaderboard, they receive a congratulatory message.
- **BLT bug reporting** — When an issue is labeled as `bug`, `vulnerability`, or `security`, it is automatically reported to the [BLT API](https://git.owaspblt.org/BLT/BLT-API).
- **Welcome messages** — New issues and pull requests receive helpful onboarding messages with contribution tips.
- **Merge congratulations** — Merged PRs receive an acknowledgement message celebrating the contributor's work.

## Setup

### Prerequisites

- [Cloudflare Workers](https://workers.cloudflare.com/)
- A GitHub App installation
- Python for tests

### Local Configuration

```bash
cp .dev.vars.example .dev.vars
```

Fill in:

| Variable | Description |
|---|---|
| `APP_ID` | GitHub App numeric ID |
| `PRIVATE_KEY` | GitHub App private key |
| `WEBHOOK_SECRET` | GitHub App webhook secret |
| `GITHUB_APP_SLUG` | Current GitHub App slug |
| `BLT_API_URL` | BLT API base URL |
| `GITHUB_CLIENT_ID` | Optional OAuth client ID |
| `GITHUB_CLIENT_SECRET` | Optional OAuth client secret |
| `GITHUB_ORG` | Optional org used for homepage mentor stats, defaults to `OWASP-BLT` |
| `ADMIN_BASIC_AUTH_USERNAME` | Required username for `/admin` HTTP Basic Auth |
| `ADMIN_BASIC_AUTH_PASSWORD` | Required password for `/admin` HTTP Basic Auth |
| `ADMIN_PATH` | Optional custom admin route path, defaults to `/admin` |

### D1 Setup

```bash
npx wrangler d1 create blt-leaderboard
```

Copy the returned `database_id` into `wrangler.toml` under `[[d1_databases]]`.

The same D1 binding is used for both:

- GitHub leaderboard/event tracking
- Mentor pool storage and mentor assignment state

### Run Locally

```bash
npx wrangler dev
```

### Deploy

```bash
npx wrangler deploy
```

Apply pending D1 migrations first with `bash scripts/run-migrations.sh` (it is not run by `wrangler deploy`).

### Production Secrets

```bash
npx wrangler secret put APP_ID
npx wrangler secret put PRIVATE_KEY
npx wrangler secret put WEBHOOK_SECRET
npx wrangler secret put ADMIN_BASIC_AUTH_USERNAME
npx wrangler secret put ADMIN_BASIC_AUTH_PASSWORD
```

Bulk upload is supported with:

```bash
chmod +x scripts/upload-production-vars.sh
./scripts/upload-production-vars.sh
```

## Testing

```bash
pip install pytest
pytest test_worker.py -v
```

## Current Naming Note

The product name is now `BLT-Pool`, but some deployment identifiers still use legacy GitHub App naming for continuity.

Examples:

- `wrangler.toml` worker name
- `GITHUB_APP_SLUG`

Those can be migrated separately when production deployment and GitHub App settings are ready.

## GitHub App Permissions

Required permissions:

| Permission | Access |
|---|---|
| Issues | Read & Write |
| Pull Requests | Read & Write |
| Metadata | Read |
| Checks | Read |
| Actions | Read |

Webhook events currently handled:

- `issue_comment`
- `issues`
- `pull_request`
- `pull_request_review`
- `check_run`
- `workflow_run`

## Mentor API

The mentor signup form on `/` submits to `POST /api/mentors`.

Accepted payload fields:

- `name` required
- `github_username` required
- `specialties` optional list or comma-separated string
- `max_mentees` optional, clamped to `1..10`
- `timezone` optional
- `referred_by` optional GitHub username

Validation implemented in `worker.py`:

- GitHub usernames must match GitHub's normal username shape
- Specialty tags are validated before insert
- Invalid payloads return `400`
- Successful inserts return `201`

## Seeded Mentors

The worker currently seeds an initial mentor pool in code so the homepage is populated on first run. This seeded list includes mentors such as:

- Rinkit Adhana
- Raj Gupta
- Shriyash Soni
- Mohammed Faiyaz Shaikh
- Vinamra Vaswani
- Carla Voorhees
- Akshay Behl
- Kunal Kashyap
- Rudra Bhaskar
- Sanidhya Shishodia
- Vedant Anand
- Rishab Kumar Jha
- Aryan Jain
- Ramansh Saxena

## Project Structure

```text
.
├── README.md
├── app.yml
├── wrangler.toml
├── .dev.vars.example
├── public/
├── scripts/
├── src/
│   ├── worker.py
│   └── index_template.py
├── templates/
│   ├── index.html
│   └── callback.html
└── test_worker.py
```

## Related Projects

- [OWASP BLT](https://git.owaspblt.org/BLT/BLT-Core) — Main bug logging platform
- [BLT-Action](https://git.owaspblt.org/BLT/BLT-Action) — GitHub Action for issue assignment
- [BLT-API](https://git.owaspblt.org/BLT/BLT-API) — REST API for BLT

## License

[AGPL-3.0](LICENSE)
