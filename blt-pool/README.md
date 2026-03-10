# BLT GitHub App

> A GitHub App that automates contribution tracking, PR health enforcement, and issue management for [OWASP BLT](https://owaspblt.org) repositories — running as a Python [Cloudflare Worker](https://workers.cloudflare.com/).

---

## Table of Contents

- [Features](#features)
  - [Issue Management](#-issue-management)
  - [Pull Request Automation](#-pull-request-automation)
  - [Contribution Leaderboard](#-contribution-leaderboard)
  - [Bug Reporting](#-bug-reporting)
  - [Landing Page & Status](#-landing-page--status)
- [Architecture](#architecture)
- [Setup](#setup)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [D1 Database](#d1-database)
  - [Running Locally](#running-locally)
  - [Deploying to Production](#deploying-to-production)
  - [Testing](#testing)
- [GitHub App Permissions](#github-app-permissions)
- [Endpoints](#endpoints)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Related Projects](#related-projects)
- [License](#license)

---

## Features

### 🗂 Issue Management

| Feature | Description |
|---|---|
| **`/assign` command** | Comment `/assign` on any issue to self-assign it. An 8-hour deadline is set — if no linked PR is submitted in time, you are automatically unassigned. |
| **`/unassign` command** | Comment `/unassign` to release your assignment so other contributors can pick it up. |
| **Stale assignment cleanup** | A cron job runs every 2 hours and automatically unassigns issues where the 8-hour window has expired with no linked PR. |
| **Welcome message** | New issues receive an onboarding comment with instructions on how to get assigned and contribute. |

### 🔀 Pull Request Automation

| Feature | Description |
|---|---|
| **Welcome message** | New PRs receive a checklist comment (code style, tests, commit messages, linked issue). |
| **Merge congratulations** | A celebratory comment is posted when a PR is merged, crediting the author. |
| **Auto-close excess PRs** | If an author has more than **50 open PRs** in the repository, the new PR is automatically closed with an explanatory message. |
| **Peer review enforcement** | PRs are labeled `needs-peer-review` or `has-peer-review` based on whether a valid (non-bot, non-author) approval exists. A reminder comment is posted when a review is missing. |
| **Unresolved conversations label** | Every PR is labeled `unresolved-conversations: N` (🔴 red if any are open, 🟢 green if all resolved), updated automatically whenever the PR is opened or a review thread changes. |

### 🏆 Contribution Leaderboard

The leaderboard is **event-driven and backed by Cloudflare D1** — no per-request repo scanning, scalable to large orgs.

**How points are scored:**

| Event | Points |
|---|---|
| PR opened | +1 to open PR counter |
| PR merged | +10 merged PRs, −1 open PR counter |
| PR closed without merge | −2 closed PRs, −1 open PR counter |
| PR review submitted | +5 (first two unique reviewers per PR per month only) |
| Issue comment created | +1 (bots and CodeRabbit pings excluded) |

**Commands & automation:**

| Feature | Description |
|---|---|
| **`/leaderboard` command** | Comment `/leaderboard` on any issue or PR to see the current monthly ranking for your org. The triggering command comment is deleted to keep threads clean. |
| **Auto-posted leaderboard** | The leaderboard is automatically posted (or updated in-place) when a PR is opened or merged. |
| **D1 backfill** | Historical data from repos is incrementally backfilled into D1 on scheduled runs so rankings are accurate from day one. |

### 🐛 Bug Reporting

When an issue is labeled with `bug`, `vulnerability`, or `security` — either at creation time or by adding the label later — the app automatically:
1. Reports the issue to the [BLT platform](https://owaspblt.org) via the BLT API.
2. Posts a comment with the assigned BLT Bug ID for cross-referencing.

Duplicate reports are prevented: if a bug label is already present from a prior event, the report is skipped.

### 🌐 Landing Page & Status

The Worker serves a branded landing page at `/` where anyone can:
- View the app description and install it on their GitHub organization.
- See the live status of all required secret variables (`APP_ID`, `PRIVATE_KEY`, `WEBHOOK_SECRET`).

A post-installation success page is served at `/callback`.

---

## Architecture

```
GitHub Webhook
      │
      ▼
Cloudflare Worker (src/worker.py)
      │
      ├── Webhook signature verification (HMAC-SHA256)
      ├── Event routing → handler functions
      │
      ├── Issue handlers
      │   ├── handle_issue_comment   (/assign, /unassign, /leaderboard)
      │   ├── handle_issue_opened    (welcome message, bug report)
      │   └── handle_issue_labeled   (bug report on label add)
      │
      ├── PR handlers
      │   ├── handle_pull_request_opened   (welcome, leaderboard, excess-PR check, unresolved-conversations)
      │   ├── handle_pull_request_closed   (merge congrats, leaderboard, D1 tracking)
      │   ├── handle_pull_request_review_submitted  (D1 review tracking)
      │   ├── handle_pull_request_for_review         (peer review label + comment)
      │   └── handle_pull_request_review             (peer review label update on dismiss)
      │
      ├── Leaderboard engine
      │   ├── D1-backed event counters (open/merged/closed PRs, reviews, comments)
      │   ├── Incremental D1 backfill from GitHub REST API
      │   └── Formatted leaderboard comment builder
      │
      └── Cron scheduler (every 2 hours)
          └── _check_stale_assignments → auto-unassign expired issues
```

### Leaderboard Scalability

The leaderboard uses an **event-driven D1 model**:
- Webhook events atomically increment counters in Cloudflare D1 (SQLite at the edge).
- `/leaderboard` reads precomputed counters — no repo scanning on demand.
- Scales to orgs with hundreds of repos and thousands of contributors.

---

## Setup

### Prerequisites

- A [Cloudflare Workers](https://workers.cloudflare.com/) account with Workers Paid plan (required for D1)
- A registered [GitHub App](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/about-creating-github-apps)
- [Node.js](https://nodejs.org/) ≥ 18 (for Wrangler CLI)
- [Python](https://python.org/) ≥ 3.11 (for running tests locally)

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `APP_ID` | ✅ | GitHub App numeric ID |
| `PRIVATE_KEY` | ✅ | GitHub App RSA private key (full PEM, PKCS#1 or PKCS#8) |
| `WEBHOOK_SECRET` | ✅ | GitHub App webhook secret |
| `GITHUB_APP_SLUG` | ✅ | App URL slug shown in GitHub App URLs (e.g. `blt-github-app`) |
| `BLT_API_URL` | ✅ | BLT API base URL (default: `https://github-app.owaspblt.org`) |
| `GITHUB_CLIENT_ID` | ⬜ | OAuth client ID (optional, for OAuth flow) |
| `GITHUB_CLIENT_SECRET` | ⬜ | OAuth client secret (optional, for OAuth flow) |

Non-secret variables (`BLT_API_URL`, `GITHUB_APP_SLUG`) are committed to `wrangler.toml`. Secrets must be set via Wrangler.

### D1 Database

The leaderboard requires a Cloudflare D1 database.

**1. Create the database:**
```bash
npx wrangler d1 create blt-leaderboard
```

**2. Copy the returned `database_id` into `wrangler.toml`:**
```toml
[[d1_databases]]
binding = "LEADERBOARD_DB"
database_name = "blt-leaderboard"
database_id = "<your-database-id>"
```

The schema is auto-created on first webhook event — no manual migration needed.

### Running Locally

```bash
# 1. Copy the example env file and fill in your credentials
cp .dev.vars.example .dev.vars

# 2. Start the local dev server
npx wrangler dev
```

The local server listens at `http://localhost:8787`. Use a tool like [ngrok](https://ngrok.com/) to expose it for GitHub webhook delivery.

### Deploying to Production

```bash
# Set required secrets (one-time setup)
npx wrangler secret put APP_ID
npx wrangler secret put PRIVATE_KEY
npx wrangler secret put WEBHOOK_SECRET

# Deploy the Worker
npx wrangler deploy
```

**Bulk secret upload** from an `.env.production` file (with pre-flight Worker name verification):
```bash
chmod +x scripts/upload-production-vars.sh
./scripts/upload-production-vars.sh
```

The script verifies that `CLOUDFLARE_WORKER_NAME` in `.env.production` matches `name` in `wrangler.toml` before uploading any secrets.

> **Static assets:** The `public/` directory (landing page HTML, logo) is automatically served by the Worker via the `[site]` bucket configured in `wrangler.toml`.

### Testing

```bash
pip install pytest
pytest test_worker.py -v
```

---

## GitHub App Permissions

| Permission | Access | Why |
|---|---|---|
| Issues | Read & Write | Assignment, comments, bug reporting |
| Pull Requests | Read & Write | PR automation, leaderboard, peer review |
| Metadata | Read | Repository info |

**Subscribed webhook events:** `issue_comment`, `issues`, `pull_request`, `pull_request_review`, `pull_request_review_comment`, `pull_request_review_thread`

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Branded landing page with install button and secret variable status |
| `GET` | `/health` | JSON health check (`{"status": "ok"}`) |
| `POST` | `/api/github/webhooks` | GitHub webhook receiver (HMAC-verified) |
| `GET` | `/callback` | Post-installation success page |

---

## Project Structure

```
BLT-GitHub-App/
├── src/
│   ├── worker.py              # Main Cloudflare Worker — all webhook handlers, leaderboard engine, landing page
│   └── index_template.py      # Landing page HTML template
├── public/
│   ├── index.html             # Landing page source
│   └── callback.html          # Post-installation page
├── scripts/
│   └── upload-production-vars.sh  # Bulk secret upload script
├── test_worker.py             # pytest unit tests
├── wrangler.toml              # Cloudflare Worker configuration
├── app.yml                    # GitHub App manifest
└── LICENSE
```

---

## Roadmap

The following features are actively being developed in open branches. Once reviewed and merged, they will be reflected here.

### 🔧 In Progress

| Feature | Branch | Description |
|---|---|---|
| **PR Automation Labels** | `feat/pr-labels-and-checks` | Auto-labels PRs by files changed (`files-changed: N`), detects Django migration files (`migrations`), validates linked issue in PR body (`linked-issue`), detects merge conflicts, and exposes feature toggles for all automation. |
| **GitHub Checks API — Console Statement Scanner** | `feature/ci-checks` | Creates a GitHub Check Run that scans changed JS/TS files for `console.*` calls and annotates offending lines directly in the PR diff. |
| **PR Automation Labels (extended)** | `feature/pr-automation` | Extends label automation with additional feature toggles and rate-limiting improvements. |
| **PR Summary Comment** | `feature/pr-summary-comments` | Posts a rich summary comment on every PR with file stats, estimated contribution points, a pre-merge checklist, and the contributor's current leaderboard rank. |

### 📋 Planned

The items below are defined in the [Implementation Blueprint](BLT%20GitHub%20App%20Implementation%20Blueprint.md) and are targeted for future development.

| Feature | Description |
|---|---|
| **Security scanning checks** | GitHub Checks API integration for Gitleaks (secrets), Semgrep (SAST), Checkov (IaC), and CodeQL — results posted as inline PR annotations and SARIF uploaded to GitHub Code Scanning. |
| **Python linting check** | Ruff linting and formatting check surfaced as a GitHub Check Run with per-line annotations. |
| **Auto-fix commits** | Automatically commit Ruff / isort / djLint fixes to the PR branch when linting issues are detected; includes loop detection and rate limiting. |
| **Quality labels** | Mutual-exclusion labels (`quality: high`, `quality: medium`, `quality: low`) applied based on review feedback. |
| **Test result labels** | `tests: passing` / `tests: failing` labels and failure summary comments driven by CI status checks. |
| **Comment count label** | Label tracking PR discussion activity, updated on each new comment. |
| **Last-active label** | Marks PRs that have been inactive for a configurable time window to surface stale work. |
| **Bounty payout integration** | When a PR merges and closes an issue carrying a `$amount` label, trigger the BLT bounty payout API automatically. |
| **Reviewer suggestions** | Suggest relevant reviewers based on file ownership and past contribution patterns. |

---

## Related Projects

| Project | Description |
|---|---|
| [OWASP BLT](https://github.com/OWASP-BLT/BLT) | Main bug logging and bounty platform |
| [BLT-Action](https://github.com/OWASP-BLT/BLT-Action) | GitHub Action for issue assignment (predecessor) |
| [BLT-API](https://github.com/OWASP-BLT/BLT-API) | REST API powering BLT services |

---

## License

[AGPL-3.0](LICENSE)
