# BLT GitHub App - Architecture & Flow Documentation

## Overview

This is a **GitHub App** built as a **Cloudflare Worker** (Python) that automates issue/PR management, tracks contributions, and enforces policies for the OWASP BLT project.

## How It Works

### 1. GitHub Connection

- **GitHub App Installation**: Organizations/repos install this as a GitHub App
- **Webhooks**: GitHub sends webhook events to `/api/github/webhooks` endpoint
- **Authentication**: Uses GitHub App credentials (APP_ID, PRIVATE_KEY) to authenticate

### 2. Main Entry Points

```
┌─────────────────────────────────────────────────────────────┐
│                     HTTP Requests                            │
│                                                              │
│  on_fetch(request, env) → Routes incoming requests          │
│                                                              │
│  GET  /              → Landing page                         │
│  GET  /health        → Health check                         │
│  POST /api/github/webhooks → GitHub webhook events          │
│  GET  /callback      → Installation success page            │
│  POST /admin/reset-leaderboard-month → Admin endpoint       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Scheduled Tasks                          │
│                                                              │
│  on_scheduled() → Runs on cron schedule                     │
│  - Checks for stale issue assignments                       │
│  - Auto-unassigns issues after ASSIGNMENT_DURATION_HOURS    │
└─────────────────────────────────────────────────────────────┘
```

---

## Feature Breakdown

### Feature 1: Issue Assignment Commands (`/assign` & `/unassign`)

**Location**: Lines 1856-1982

#### Flow Execution:

```
User posts comment with "/assign" or "/unassign"
              ↓
GitHub sends "issue_comment" webhook event
              ↓
handle_webhook() receives POST to /api/github/webhooks
              ↓
Verifies webhook signature (line 2585)
              ↓
Parses event and extracts installation_id
              ↓
Gets GitHub API token (line 2590)
              ↓
Routes to: handle_issue_comment() (line 1859)
              ↓
Checks if comment author is human (line 1862)
              ↓
_extract_command(body) parses command (line 280)
              ↓
Adds 👀 reaction to acknowledge (line 1879)
              ↓
              ├→ If "/assign": _assign() (line 1908)
              │   - Checks if issue is still open
              │   - Checks if user already assigned
              │   - Checks max assignees limit (MAX_ASSIGNEES = 2)
              │   - Assigns user via GitHub API
              │   - Posts confirmation comment with deadline
              │
              └→ If "/unassign": _unassign() (line 1961)
                  - Checks if user is assigned
                  - Unassigns user via GitHub API
                  - Posts confirmation comment
```

**Key Constants**:

- `ASSIGN_COMMAND = "/assign"` (line 72)
- `UNASSIGN_COMMAND = "/unassign"` (line 73)
- `MAX_ASSIGNEES = 2` (line 79)
- `ASSIGNMENT_DURATION_HOURS = 48` (line 80)

---

### Feature 2: Leaderboard System (`/leaderboard`)

**Location**: Lines 1293-1856

#### Flow Execution:

```
User posts comment with "/leaderboard"
              ↓
handle_issue_comment() receives command
              ↓
Calls: _post_or_update_leaderboard() (line 1598)
              ↓
              ├→ Uses D1 database (Cloudflare's SQL database)
              │  _calculate_leaderboard_stats_from_d1() (line 831)
              │  - Queries monthly stats from DB
              │  - Falls back to API if D1 unavailable
              │
              ├→ Or calculates from GitHub API directly
              │  _calculate_leaderboard_stats() (line 1293)
              │  - Searches across all org repos
              │  - Counts open PRs, merged PRs, reviews, comments
              │  - Scoring: Open +1, Merged +10, Closed -2, Reviews +5
              │
              ↓
_format_leaderboard_comment() (line 1529)
              ↓
Deletes old leaderboard comments (line 1685)
              ↓
Posts new leaderboard comment with user's rank
```

**Scoring System** (line 1499):

- Open PRs: +1 each
- Merged PRs: +10 each
- Closed (not merged): -2 each
- Reviews: +5 each (first 2 per PR)
- Comments: +2 each (excludes bots)

**D1 Database Tables**:

- `pr_events` - Tracks PR opens/closes/merges
- `review_credits` - Tracks PR reviews
- `comment_credits` - Tracks issue/PR comments
- `backfill_state` - Tracks which repos/months are synced

---

### Feature 3: Auto-Close Excess PRs

**Location**: Lines 1721-1763

#### Flow Execution:

```
User opens a new Pull Request
              ↓
GitHub sends "pull_request.opened" webhook
              ↓
handle_pull_request_opened() (line 2072)
              ↓
_check_and_close_excess_prs() (line 1721)
              ↓
Searches for all open PRs by author
              ↓
If author has >= MAX_OPEN_PRS_PER_AUTHOR (5):
  - Posts warning comment
  - Closes the new PR automatically
  - Stops further processing
```

**Key Constant**:

- `MAX_OPEN_PRS_PER_AUTHOR = 5` (line 81)

---

### Feature 4: Peer Review Enforcement

**Location**: Lines 2262-2419

#### Flow Execution:

```
PR is opened OR review is submitted/dismissed
              ↓
              ├→ handle_pull_request_for_review() (line 2411)
              └→ handle_pull_request_review() (line 2402)
              ↓
check_peer_review_and_comment() (line 2361)
              ↓
get_valid_reviewers() (line 2282)
  - Fetches all reviews for the PR
  - Tracks latest state per reviewer
  - Filters out: bots, PR author, non-approved
              ↓
update_peer_review_labels() (line 2331)
  - Adds "has-peer-review" (green) OR
  - Adds "needs-peer-review" (red)
              ↓
If no valid review:
  - Posts comment asking for peer review
  - Only posts once (checks for marker comment)
```

**Excluded Reviewers** (line 2273):

- Bots like `coderabbitai[bot]`, `dependabot[bot]`
- GitHub Actions bots
- The PR author themselves

---

### Feature 5: Unresolved Conversations Tracking

**Location**: Lines 2169-2260

#### Flow Execution:

```
PR review comment OR review thread event
              ↓
check_unresolved_conversations() (line 2169)
              ↓
Uses GitHub GraphQL API to fetch review threads
              ↓
Counts unresolved threads
              ↓
Removes old "unresolved-conversations" labels
              ↓
Adds label: "unresolved-conversations: X"
  - Red (e74c3c) if any unresolved
  - Green (5cb85c) if all resolved
```

---

### Feature 6: Workflow Approval Labels

**Location**: Lines 2421-2502

#### Flow Execution:

```
GitHub workflow run event occurs
              ↓
handle_workflow_run() (line 2455)
              ↓
Finds PRs associated with the workflow
  - Uses payload's pull_requests array
  - Falls back to searching by head SHA
              ↓
check_workflows_awaiting_approval() (line 2421)
              ↓
Queries GitHub Actions API for runs with status="action_required"
              ↓
Removes old approval labels
              ↓
If workflows awaiting approval > 0:
  - Adds label: "X workflow(s) awaiting approval" (red)
```

---

### Feature 7: BLT API Integration (Bug Reporting)

**Location**: Lines 338-383, 2034-2070

#### Flow Execution:

```
Issue opened with bug label OR bug label added
              ↓
              ├→ handle_issue_opened() (line 2034)
              └→ handle_issue_labeled() (line 2057)
              ↓
Checks if label is in BUG_LABELS (line 2043)
              ↓
report_bug_to_blt() (line 338)
              ↓
POSTs to BLT API endpoint (default: blt-api.owasp-blt.workers.dev)
              ↓
If successful:
  - Posts comment with BLT Bug ID
```

**Bug Labels** (line 76):

- `BUG_LABELS = ["bug", "security", "vulnerability"]`

---

### Feature 8: Welcome Messages

**Location**: Lines 2034-2056

#### Flow Execution:

```
New issue opened
              ↓
handle_issue_opened() (line 2034)
              ↓
Posts welcome comment with:
  - How to use /assign command
  - Link to OWASP BLT website
  - Bug tracking info if applicable
```

---

### Feature 9: PR Merge Congratulations

**Location**: Lines 2119-2148

#### Flow Execution:

```
Pull Request merged
              ↓
handle_pull_request_closed() (line 2119)
              ↓
Checks if PR was merged (not just closed)
              ↓
Tracks merge in D1 database (line 2135)
              ↓
Posts congratulations comment
              ↓
Updates leaderboard for the author
```

---

### Feature 10: Stale Assignment Checker (Cron Job)

**Location**: Lines 2858-2950

#### Flow Execution:

```
Cron trigger fires (configured in wrangler.toml)
              ↓
on_scheduled() (line 2906)
              ↓
_run_scheduled() (line 2858)
              ↓
Gets all GitHub App installations
              ↓
For each installation:
  ├→ Gets repos (org or user repos)
  └→ _check_stale_assignments() (line 2914)
      ↓
      Fetches open issues with assignees
      ↓
      For each assigned issue:
        - Checks if assignment is older than 48 hours
        - Checks if assignee has opened a PR for it
        - If stale: auto-unassigns and posts comment
```

**Assignment Deadline**: 48 hours (line 80)

---

## Data Flow Summary

### Webhooks Route Table

| GitHub Event                  | Action        | Handler Function                                                          | Purpose                                             |
| ----------------------------- | ------------- | ------------------------------------------------------------------------- | --------------------------------------------------- |
| `issue_comment`               | `created`     | `handle_issue_comment()`                                                  | Process commands (/assign, /unassign, /leaderboard) |
| `issues`                      | `opened`      | `handle_issue_opened()`                                                   | Welcome message, auto-report bugs                   |
| `issues`                      | `labeled`     | `handle_issue_labeled()`                                                  | Auto-report bugs when labeled                       |
| `pull_request`                | `opened`      | `handle_pull_request_opened()`                                            | Check excess PRs, post leaderboard, peer review     |
| `pull_request`                | `synchronize` | `handle_pull_request_for_review()`                                        | Update peer review status                           |
| `pull_request`                | `reopened`    | `handle_pull_request_for_review()`                                        | Update peer review status                           |
| `pull_request`                | `closed`      | `handle_pull_request_closed()`                                            | Congratulate merge, update leaderboard              |
| `pull_request_review`         | `submitted`   | `handle_pull_request_review_submitted()` + `handle_pull_request_review()` | Track reviews in D1, check peer review              |
| `pull_request_review`         | `dismissed`   | `handle_pull_request_review()`                                            | Update peer review status                           |
| `pull_request_review_comment` | \*            | `check_unresolved_conversations()`                                        | Update unresolved conversation label                |
| `pull_request_review_thread`  | \*            | `check_unresolved_conversations()`                                        | Update unresolved conversation label                |
| `workflow_run`                | \*            | `handle_workflow_run()`                                                   | Update workflow approval labels                     |

---

## Key Helper Functions

### Authentication & API

- `create_github_jwt()` (line 157) - Creates JWT for GitHub App auth
- `get_installation_access_token()` (line 184) - Gets installation token
- `github_api()` (line 233) - Makes authenticated GitHub API calls
- `verify_signature()` (line 289) - Verifies webhook signatures

### Database (D1)

- `_d1_binding()` (line 387) - Gets D1 database binding
- `_track_pr_opened_in_d1()` (line 395) - Tracks PR opens
- `_track_pr_closed_in_d1()` (line 433) - Tracks PR closes/merges
- `_track_review_in_d1()` (line 517) - Tracks PR reviews
- `_track_comment_in_d1()` (line 650) - Tracks comments
- `_calculate_leaderboard_stats_from_d1()` (line 831) - Calculates leaderboard from DB

### Utilities

- `_is_human()` (line 305) - Checks if user is human (not bot)
- `_is_bot()` (line 314) - Explicitly checks if user is bot
- `_extract_command()` (line 280) - Extracts commands from comments
- `create_comment()` (line 322) - Posts GitHub comments
- `create_reaction()` (line 331) - Adds emoji reactions

---

## Configuration (Environment Variables)

**Required**:

- `APP_ID` - GitHub App ID
- `PRIVATE_KEY` - GitHub App private key (RSA)
- `WEBHOOK_SECRET` - Secret for webhook signature verification

**Optional**:

- `GITHUB_APP_SLUG` - App slug for installation URL
- `BLT_API_URL` - BLT API endpoint (default: https://blt-api.owasp-blt.workers.dev)
- `ADMIN_SECRET` - Secret for admin endpoints
- `DB` - D1 database binding (configured in wrangler.toml)

**Optional OAuth** (not actively used):

- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                         GitHub                                 │
│  (Issues, PRs, Comments, Reviews, Workflows)                   │
└────────────────┬───────────────────────────────────────────────┘
                 │ Webhooks (JSON payloads)
                 ↓
┌────────────────────────────────────────────────────────────────┐
│              Cloudflare Worker (Python)                        │
│                                                                │
│  on_fetch() ──→ handle_webhook() ──→ Event Handlers           │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Event Handlers:                                         │ │
│  │  • handle_issue_comment()     → Commands                 │ │
│  │  • handle_issue_opened()      → Welcome                  │ │
│  │  • handle_pull_request_*()    → PR automation            │ │
│  │  • handle_workflow_run()      → Workflow labels          │ │
│  │  • check_unresolved_conversations() → Thread tracking    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  on_scheduled() ──→ _run_scheduled() ──→ Stale assignments    │
└────────┬───────────────────────────────────────────┬──────────┘
         │                                            │
         │ API Calls                                  │ Database Queries
         ↓                                            ↓
┌──────────────────┐                      ┌──────────────────────┐
│   GitHub API     │                      │  Cloudflare D1 DB    │
│  (REST + GraphQL)│                      │  (SQLite)            │
│                  │                      │                      │
│  • Issues API    │                      │  • pr_events         │
│  • PRs API       │                      │  • review_credits    │
│  • Search API    │                      │  • comment_credits   │
│  • Actions API   │                      │  • backfill_state    │
│  • GraphQL       │                      │                      │
└──────────────────┘                      └──────────────────────┘
         │
         │ Optionally
         ↓
┌──────────────────┐
│   BLT API        │
│  (Bug Reporting) │
└──────────────────┘
```

---

## Testing Locally

1. Install dependencies: `pip install -r requirements.txt`
2. Set up wrangler: `npx wrangler@latest`
3. Configure secrets: `npx wrangler secret put APP_ID`
4. Run locally: `npx wrangler dev`
5. Use GitHub webhook forwarding tool (e.g., smee.io)

---

## Deployment

```bash
# Deploy to Cloudflare
npx wrangler deploy

# Upload secrets
./scripts/upload-production-vars.sh
```

---

## Summary

This GitHub App is NOT just handling GitHub Actions - it's a **webhook-driven automation bot** that:

1. **Listens** to GitHub webhook events (issue comments, PRs, reviews, etc.)
2. **Processes** commands and events in real-time
3. **Responds** by posting comments, adding labels, closing PRs, etc.
4. **Tracks** contributions in a database for leaderboard
5. **Enforces** policies (max PRs, peer review, stale assignments)
6. **Runs** scheduled jobs to clean up stale assignments

Every action is triggered by either:

- A webhook from GitHub (real-time events)
- A cron schedule (periodic cleanup)

The code is **event-driven** and **serverless** (runs on Cloudflare Workers).
