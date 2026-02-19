# BLT-Leaf - PR Readiness Checker

A simple one-page application to track and monitor GitHub Pull Request readiness status.

## Quick Deploy

Deploy this application to Cloudflare Workers with one click:

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/OWASP-BLT/BLT-Leaf)

The deploy button will automatically:
- Create a new Cloudflare Workers project
- Provision a D1 database
- Initialize the database schema
- Deploy the application

No manual configuration required!

## Project Structure

```
BLT-Leaf/
├── public/              # Static assets served by Cloudflare Workers
│   └── index.html      # Main frontend application
├── src/                # Backend Python code (modular structure)
│   ├── index.py        # Main entry point and routing
│   ├── handlers.py     # API endpoint handlers
│   ├── utils.py        # Utility functions for PR analysis
│   ├── github_api.py   # GitHub API interactions
│   ├── database.py     # Database operations
│   └── cache.py        # Caching and rate limiting
├── migrations/         # Database migrations for D1
│   ├── 0001_create_prs_table.sql
│   ├── 0002_create_timeline_cache.sql
│   └── 0003_create_indexes.sql
├── wrangler.toml       # Cloudflare Workers configuration
├── package.json        # npm scripts for deployment
├── DEPLOYMENT.md       # Detailed deployment instructions
├── CODE_SPLITTING_SUMMARY.md  # Documentation on code organization
└── README.md          # This file
```

## Features

### Core Functionality
- 📝 **Track Open PRs**: Add GitHub PR URLs to track their readiness (open PRs only)
- 📊 **Sortable Table View**: View PRs in a compact, sortable table with check results, review status, and files changed
- 👥 **Multi-Repo Support**: Track PRs across multiple repositories
- 🔄 **Real-time Updates**: Refresh PR data from GitHub API
- ➕ **Bulk Import**: Import up to 1000 open PRs at once using the plus button next to each repository (prevents timeout on very large repos)
- 🎨 **Clean Interface**: Simple, GitHub-themed UI with dark mode support
- 🔔 **Webhook Integration (NEW)**: Automatically track new PRs when opened via GitHub webhooks

### PR Readiness Analysis (NEW)
- 🎯 **Readiness Scoring**: Data-driven 0-100 score combining CI confidence and review health
- 📈 **Timeline Tracking**: Complete chronological view of commits, reviews, and comments
- 🔍 **Feedback Loop Detection**: Automatically tracks reviewer comments and author responses
- 📊 **Response Rate Analysis**: Measures how quickly and thoroughly authors address feedback
- ⚠️ **Stale Feedback Detection**: Identifies unaddressed comments older than 3 days
- 🚫 **Smart Blocker Detection**: Auto-identifies issues preventing merge (failing checks, merge conflicts, etc.)
- 💬 **Conversation Tracking (NEW)**: Tracks unresolved review conversations; deducts 3 points per conversation from readiness score
- 💡 **Actionable Recommendations**: Context-aware suggestions for next steps

### Performance & Protection
- ⚡ **Response Caching**: 10-minute cache for readiness results with automatic cache headers
- 🔄 **Smart Cache Invalidation**: Auto-clears cache when PRs are manually refreshed
- 🛡️ **Rate Limiting**: Application-level protection (10 req/min per IP) for analysis endpoints
- 📊 **GitHub API Optimization**: Intelligent caching minimizes API usage
- ✅ **Merge Ready Indicator**: Clear verdict on whether PR is safe to merge

## Tech Stack

- **Frontend**: Single HTML page with vanilla JavaScript (no frameworks)
- **Backend**: Python on Cloudflare Workers
- **Database**: Cloudflare D1 (SQLite)
- **Styling**: Embedded CSS with GitHub-inspired theme

## Setup

### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- Cloudflare account

### Installation

1. Clone the repository:
```bash
git clone https://github.com/OWASP-BLT/BLT-Leaf.git
cd BLT-Leaf
```

2. Install Wrangler (if not already installed):
```bash
npm install -g wrangler
```

3. Login to Cloudflare:
```bash
wrangler login
```

4. Create the D1 database:
```bash
wrangler d1 create pr_tracker
```

5. Create `.env` file and populate it with Database ID from previous step:
```bash
cp .env.example .env
```

6. Apply database migrations:
```bash
# For local development
wrangler d1 migrations apply pr-tracker --local

# For production (remote database)
wrangler d1 migrations apply pr-tracker --remote
```

### Development

Run the development server:
```bash
wrangler dev
```

The application will be available at `http://localhost:8787`

### Deployment

Deploy to Cloudflare Workers:
```bash
wrangler deploy
```

### Testing

The application includes comprehensive test suites for rate limiting, caching features, and data display verification.

**Data Display Tests** (verifies project setup and data structure):
```bash
npm test
# or
node test-data-display.js
```

This test suite verifies:
- ✅ HTML structure and data display elements
- ✅ Python API handlers and endpoints
- ✅ Database schema completeness
- ✅ Configuration files (wrangler.toml, package.json)
- ✅ API routing and CORS configuration

**Quick Local Test** (watch wrangler console for logs):
```bash
node test-simple.js
```

**Full Production Test** (requires deployment):
```bash
npm run deploy
node test-production.js https://your-worker.workers.dev
```

For detailed testing instructions and expected behavior, see [TESTING.md](TESTING.md).

**Note**: Local development (`wrangler dev`) may not preserve worker state between requests. For accurate rate limiting and caching tests, deploy to production.

### Continuous Integration

The project includes a comprehensive GitHub Actions workflow that automatically runs on push and pull requests:

**Test Data Display Workflow** (`.github/workflows/test-data-display.yml`):
- Runs on every push to main and pull request
- Sets up Node.js and installs dependencies
- Runs linting and format checks
- Verifies all required source files and configurations exist
- Runs comprehensive data display tests (48+ automated checks)
- Validates HTML structure, API endpoints, and database schema
- Checks Python syntax for all source files
- **Starts live Wrangler dev server** and tests against running application
- **Tests all API endpoints** including refresh functionality
- **Validates refresh button** works correctly to update PR data
- Performs security audit of dependencies

The workflow ensures that:
- The project setup is correct and complete
- All data display components are properly configured
- API endpoints are defined and routed correctly
- Frontend can successfully fetch and display data
- Database schema includes all required fields
- **Refresh functionality works to update PR data from GitHub**
- Code meets quality and security standards

To run the same checks locally:
```bash
npm test
```

## Usage

### Basic Tracking
1. **Add a PR**: Enter a GitHub PR URL in the format `https://github.com/owner/repo/pull/number`
   - Note: Only open PRs can be added. Merged or closed PRs will be rejected.
2. **View Details**: See PRs in a sortable table with:
   - Repository and PR number
   - Author
   - Review status
   - Mergeable state
   - Files changed count
   - Check status (passed/failed/skipped)
   - Open conversations count (unresolved review threads)
   - Last updated time
3. **Sort PRs**: Click any column header to sort by that column
   - Sorting works across all pages (server-side sorting)
   - Click again to toggle ascending/descending order
   - Sorting resets to page 1 for consistent results
4. **Filter by Repo**: Click on a repository in the sidebar to filter PRs
5. **Refresh Data**: Use the refresh button to update PR information from GitHub
   - Note: If a PR has been merged or closed since being added, it will be automatically removed from tracking.

### PR Readiness Analysis
6. **Check Readiness**: Click the "Check Readiness" button on any PR row to analyze:
   - **Overall Score**: 0-100 combining CI confidence (60%) and review health (40%)
   - **Score Breakdown**: See individual CI and review scores
   - **Blockers**: Critical issues preventing merge (failing checks, conflicts, stale feedback)
   - **Warnings**: Non-blocking concerns (awaiting approval, large PR size)
   - **Recommendations**: Specific actionable next steps
   - **Response Metrics**: Author responsiveness and feedback address rate

### Readiness Classifications
- ✅ **READY_TO_MERGE** (70-100): No blockers, all key metrics passing
- 🟡 **NEARLY_READY** (60-69): Minor issues, mostly ready
- 🟠 **NEEDS_WORK** (40-59): Significant issues need attention
- 🔴 **NOT_READY** (<40): Major problems, not safe to merge

### Review Health States
- **APPROVED** (90-100): Reviews approved, ready to go
- **ACTIVE** (70-85): Good progress with responsive author
- **AWAITING_REVIEWER** (60-80): Author responded, waiting on reviewers
- **AWAITING_AUTHOR** (35-55): Author needs to address feedback
- **STALLED** (10-30): Unaddressed feedback >3 days old
- **NO_ACTIVITY** (50): No reviews or feedback yet

## API Endpoints

### Core Endpoints
- `GET /` - Serves the HTML interface
- `GET /api/repos` - List all repositories with open PRs
- `GET /api/prs` - List all open PRs with pagination and sorting
  - Query parameters:
    - `?repo=owner/name` - Filter by repository (optional)
    - `?page=N` - Page number (default: 1)
    - `?sort_by=column` - Sort column (default: `last_updated_at`)
    - `?sort_dir=asc|desc` - Sort direction (default: `desc`)
  - Supported sort columns: `title`, `author_login`, `pr_number`, `files_changed`, `checks_passed`, `checks_failed`, `checks_skipped`, `review_status`, `mergeable_state`, `commits_count`, `behind_by`, `ready` (merge_ready flag: 0/1), `ready_score` (overall_score: 0-100), `overall` (alias for ready_score), `ci_score`, `review_score`, `response_score`, `feedback_score`, `last_updated_at`
- `POST /api/prs` - Add a new PR (body: `{"pr_url": "..."}`)
  - Returns 400 error if PR is merged or closed
- `POST /api/refresh` - Refresh a PR's data (body: `{"pr_id": 123}`)
  - Automatically removes PR if it has been merged or closed
- `GET /api/rate-limit` - Check GitHub API rate limit status
- `GET /api/status` - Check database configuration status

### Webhook Endpoints
- `POST /api/github/webhook` - Receive GitHub webhook events
  - Automatically updates tracked PRs based on GitHub events
  - Verifies signature using `GITHUB_WEBHOOK_SECRET`
  - Fully supported: `pull_request` | Acknowledged: `pull_request_review`, `check_run`, `check_suite`
  - See [Webhook Integration](#webhook-integration) section for setup details

### Analysis Endpoints (NEW)
- `GET /api/prs/{id}/timeline` - Get complete PR event timeline
  - Returns chronological list of commits, reviews, and comments
  - Includes parsed timestamps and event metadata
  
- `GET /api/prs/{id}/review-analysis` - Analyze review feedback loops
  - Detects reviewer feedback and author responses
  - Calculates response rates and timing
  - Identifies stale unaddressed feedback
  - Returns review health classification and score
  
- `GET /api/prs/{id}/readiness` - Get comprehensive PR readiness analysis
  - Combines CI confidence and review health scores
  - Detects blockers (failing checks, conflicts, stale feedback)
  - Provides actionable recommendations
  - Returns merge-ready verdict with detailed breakdown

### Webhook Endpoint (NEW)
- `POST /api/github/webhook` - GitHub webhook integration for automatic PR tracking
  - Automatically adds new PRs to tracking when they are opened
  - Updates existing PRs when they are modified (synchronize, edited, reviews, checks)
  - Removes PRs from tracking when they are closed or merged
  - Supported webhook events:
    - `pull_request.opened` - Automatically adds PR to tracking
    - `pull_request.closed` - Removes PR from tracking
    - `pull_request.reopened` - Re-adds PR to tracking
    - `pull_request.synchronize` - Updates PR when new commits are pushed
    - `pull_request.edited` - Updates PR when details change
    - `pull_request_review.*` - Updates PR data including behind_by and mergeable_state
    - `check_run.*` - Updates PR data including behind_by and mergeable_state
    - `check_suite.*` - Updates PR data including behind_by and mergeable_state
  - Security: Verifies GitHub webhook signatures using `GITHUB_WEBHOOK_SECRET`

#### Setting Up GitHub Webhooks
To enable automatic PR tracking:

1. Go to your repository settings → Webhooks → Add webhook
2. Set Payload URL to: `https://your-worker.workers.dev/api/github/webhook`
3. Set Content type to: `application/json`
4. Set Secret to a secure random string
5. Select events to send:
   - ✓ Pull requests
   - ✓ Pull request reviews (optional)
   - ✓ Check runs (optional)
6. Add the webhook secret to your Cloudflare Worker environment:
   ```bash
   wrangler secret put GITHUB_WEBHOOK_SECRET
   ```

Once configured, new PRs will be automatically added to tracking when opened!

### Response Examples

#### Timeline Response
```json
{
  "pr": { "id": 1, "title": "...", "author": "..." },
  "timeline": [
    {
      "type": "commit",
      "timestamp": "2024-01-15T10:30:00Z",
      "author": "username",
      "data": { "sha": "abc1234", "message": "Fix bug" }
    },
    {
      "type": "review_comment",
      "timestamp": "2024-01-15T11:00:00Z",
      "author": "reviewer",
      "data": { "body": "Please add tests", "path": "src/main.py" }
    }
  ],
  "event_count": 15
}
```

#### Readiness Response
```json
{
  "pr": { "id": 1, "title": "...", "state": "open" },
  "readiness": {
    "overall_score": 78,
    "overall_score_display": "78%",
    "ci_score": 100,
    "ci_score_display": "100%",
    "review_score": 70,
    "review_score_display": "70%",
    "classification": "READY_TO_MERGE",
    "merge_ready": true,
    "blockers": [],
    "warnings": ["Awaiting reviewer approval"],
    "recommendations": ["Ping reviewers for re-review"]
  },
  "review_health": {
    "classification": "AWAITING_REVIEWER",
    "score": 70,
    "score_display": "70%",
    "response_rate": 1.0,
    "response_rate_display": "100%",
    "total_feedback": 3,
    "responded_feedback": 3
  },
  "ci_checks": {
    "passed": 5,
    "failed": 0,
    "skipped": 0
  }
}
```

## Database Schema

The application uses a single table:

```sql
CREATE TABLE prs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_url TEXT NOT NULL UNIQUE,
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    title TEXT,
    state TEXT,
    is_merged INTEGER DEFAULT 0,
    mergeable_state TEXT,
    files_changed INTEGER DEFAULT 0,
    author_login TEXT,
    author_avatar TEXT,
    checks_passed INTEGER DEFAULT 0,
    checks_failed INTEGER DEFAULT 0,
    checks_skipped INTEGER DEFAULT 0,
    review_status TEXT,
    last_updated_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## Readiness Scoring Algorithm

### Overall Score Calculation
```
Base Score = (CI Confidence × 45%) + (Review Health × 55%)

Apply Multipliers:
- Draft PR: Score = 0
- Merge Conflicts: Score × 0.67
- Changes Requested: Score × 0.5

Final Score = max(0, Score - (3 × open_conversations_count))
```

### Conversation Score Impact (NEW)
- **Open Conversations**: Unresolved review threads/conversations
- **Score Deduction**: -3 points per unresolved conversation
- **Detection**: Uses GitHub GraphQL API to fetch `reviewThreads` with `isResolved` status
- **Minimum Score**: 0 (score cannot go negative)

### CI Confidence Score (0-100)
- **All passing**: 100 points
- **Any failing**: Heavily penalized (0 points if all fail)
- **Skipped checks**: Minor penalty (−20% per skipped)
- **Pass rate**: `(passed / total) × 100 - (failed / total) × 80 - (skipped / total) × 20`

### Review Health Score (0-100)
Based on review state and responsiveness:
- **APPROVED**: 95 points (reviews approved)
- **ACTIVE**: 70-85 points (good back-and-forth, responsive author)
- **AWAITING_REVIEWER**: 60-80 points (author responded, waiting on reviewers)
- **AWAITING_AUTHOR**: 35-55 points (needs author response)
- **STALLED**: 10-30 points (unaddressed feedback >3 days)
- **NO_ACTIVITY**: 50 points (no reviews yet)

### Feedback Loop Detection
The system tracks reviewer-author interaction cycles:
1. **Reviewer Action**: Review submission or comment
2. **Author Response**: Commit, reply, or code change
3. **Response Tracking**: Measures time between feedback and response
4. **Staleness Detection**: Flags feedback >3 days without response

### Automatic Blocker Detection
- ❌ Failing CI checks
- ❌ Merge conflicts (dirty mergeable state)
- ❌ PR closed or already merged
- ❌ Stale unaddressed feedback (>3 days)
- ❌ Awaiting author response to change requests

### Warnings
- ⚠️ Unresolved review conversations
- ⚠️ Large PR (>30 files)
- ⚠️ Skipped CI checks
- ⚠️ No review activity yet

### Smart Recommendations
Context-aware suggestions based on PR state:
- Fix specific failing checks
- Address reviewer comments
- Resolve merge conflicts
- Resolve open review conversations
- Ping reviewers for approval
- Split large PRs (>30 files)
- Re-run flaky checks

## GitHub API

The application uses the GitHub REST API to fetch PR information. No authentication is required for public repositories, but rate limits apply (60 requests per hour for unauthenticated requests).

For private repositories or higher rate limits, you can add a GitHub token to the worker environment variables.

## Webhook Integration

BLT-Leaf supports GitHub webhooks for automatic PR updates, eliminating the need for manual refreshes.

### What is the Webhook?

The webhook endpoint (`POST /api/github/webhook`) receives real-time notifications from GitHub when events occur on your tracked pull requests. This keeps your PR tracking data automatically synchronized with GitHub.

### Which Events Would You Like to Trigger This Webhook?

When setting up the webhook in your GitHub repository, select the following events:

**Recommended Events:**
- ✅ **Pull requests** - Automatically updates PR data when PRs are:
  - `closed` - Removes closed/merged PRs from tracking
  - `reopened` - Re-adds reopened PRs to tracking
  - `synchronize` - Updates PR when new commits are pushed
  - `edited` - Updates PR metadata (title, description, etc.)

**Optional Events** (for future enhancements):
- ⚪ **Pull request reviews** - Detects when reviews are submitted, edited, or dismissed
- ⚪ **Check runs** - Monitors CI/CD check completions
- ⚪ **Check suites** - Tracks overall check suite status

> **Note:** Currently, only the `pull_request` event is fully processed. Other events are acknowledged but do not trigger updates yet.

### Webhook Setup

1. **Configure the webhook secret** (required for production):
   ```bash
   # Generate a secure random secret
   openssl rand -hex 32
   
   # Add to your Cloudflare Worker secrets
   wrangler secret put GITHUB_WEBHOOK_SECRET
   # You will be prompted to paste the secret generated above
   ```

2. **Add the webhook to your GitHub repository:**
   - Go to your repository settings → Webhooks → Add webhook
   - **Payload URL**: `https://your-worker.workers.dev/api/github/webhook`
   - **Content type**: `application/json`
   - **Secret**: Enter the same secret you configured in step 1
   - **Which events would you like to trigger this webhook?**
     - Select "Let me select individual events"
     - Check: ✅ Pull requests
     - Optionally check: Pull request reviews, Check runs, Check suites
   - **Active**: ✅ Checked
   - Click "Add webhook"

3. **Verify the webhook is working:**
   - Make a change to a tracked PR (e.g., add a commit or close it)
   - Check the webhook delivery logs in GitHub to ensure it was successfully delivered
   - Verify that your PR tracker updates automatically

### Security

The webhook endpoint verifies GitHub's signature using HMAC SHA-256 to ensure requests are authentic. Always configure `GITHUB_WEBHOOK_SECRET` in production to prevent unauthorized access.

**Development Mode:** If `GITHUB_WEBHOOK_SECRET` is not set, signature verification is skipped (use only for local testing).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is part of the OWASP Bug Logging Tool (BLT) project. 
