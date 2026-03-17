# BLT-Pool

BLT-Pool is the main product for the OWASP BLT contributor experience.

This repository now serves two connected surfaces:

- `BLT-Pool` as the primary experience, including the mentor directory and contributor onboarding pages.
- The `GitHub App` as a submodule of BLT-Pool, handling issue assignment, leaderboard scoring, review signals, and webhook automation.

## What BLT-Pool Includes

### 1. Mentor Directory

The homepage at `/` is the BLT-Pool mentor directory. It is not a static page anymore: the worker loads mentor data from D1, shows current active mentor assignments, and renders a referral leaderboard based on who invited mentors into the pool.

Mentor-side features currently exposed on the homepage:

- A live mentor list loaded from the D1 `mentors` table
- Per-mentor stats pulled from D1 for homepage display
- An active assignment section backed by the D1 `mentor_assignments` table
- A referral leaderboard built from each mentor's `referred_by` field
- A `Become a Mentor` form that submits directly to `POST /api/mentors`
- A mentor command guide for `/mentor`, `/unmentor`, `/mentor-pause`, `/handoff`, and `/rematch`

### 2. GitHub App Submodule

The GitHub App lives under `/github-app` and powers repository automation for OWASP BLT projects.

Core GitHub automation features:

- `/assign` assigns an issue to the commenter for 8 hours.
- `/unassign` releases the assignment.
- `/leaderboard` shows the contributor's monthly ranking.
- Stale assignments are removed automatically on a cron schedule.
- Bug/security labels are reported to BLT.
- Peer review, workflow approval, and unresolved conversation labels are maintained automatically.
- PR volume protection closes excessive open PRs from the same author.

## Architecture

The app runs as a Python Cloudflare Worker. D1 is used for both the leaderboard system and the mentor pool system.

- `GET /` renders the BLT-Pool mentor directory.
- `GET /github-app` renders the GitHub App landing page.
- `POST /api/mentors` adds a mentor to the D1-backed mentor pool.
- `POST /api/github/webhooks` receives GitHub webhook events.
- `GET /health` returns a health check response.
- `GET /callback` shows the post-installation success page.

### D1 Data Model

The worker creates and uses several D1 tables at runtime:

- `mentors` stores mentor profile records such as name, GitHub username, specialties, timezone, max mentees, and referral source.
- `mentor_assignments` stores active mentor-to-issue assignments so the homepage can show current load.
- `leaderboard_monthly_stats`, `leaderboard_open_prs`, `leaderboard_pr_state`, `leaderboard_review_credits`, and related backfill tables power the GitHub leaderboard.

The mentor pool is seeded on startup with an initial list of mentors using idempotent `INSERT OR IGNORE` statements, so first deploys still show data before new mentors are added through the form.

### Leaderboard Model

Leaderboard scoring is event-driven and stored in D1 for scalability.

- PR opened: open PR count `+1`
- PR merged: merged PR count `+1`, open PR count `-1`
- PR closed unmerged: closed PR count `+1`, open PR count `-1`
- Review submitted: review credit `+1` for the first two unique reviewers per PR/month
- Comment created: comment credit `+1` excluding bots and CodeRabbit pings

### Mentor Pool Flow

The mentor pool is also automated in the worker:

- Mentors are loaded from D1 for homepage display and for runtime assignment logic.
- `POST /api/mentors` validates and inserts mentors directly into D1.
- The homepage form accepts `name`, `github_username`, `specialties`, `max_mentees`, `timezone`, and `referred_by`.
- Slash commands such as `/mentor` and `/unmentor` drive mentor assignment workflows in GitHub.
- Mentor assignment state is stored in D1 so the homepage can reflect active pairings.

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

### Production Secrets

```bash
npx wrangler secret put APP_ID
npx wrangler secret put PRIVATE_KEY
npx wrangler secret put WEBHOOK_SECRET
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
- Ahmed ElSheik
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

- [OWASP BLT](https://github.com/OWASP-BLT/BLT)
- [BLT-API](https://github.com/OWASP-BLT/BLT-API)
- [BLT-Action](https://github.com/OWASP-BLT/BLT-Action)

## License

[AGPL-3.0](LICENSE)
