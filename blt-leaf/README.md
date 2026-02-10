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
├── src/                # Backend Python code
│   └── index.py        # Cloudflare Worker main handler
├── schema.sql          # Database schema for D1
├── wrangler.toml       # Cloudflare Workers configuration
├── package.json        # npm scripts for deployment
├── DEPLOYMENT.md       # Detailed deployment instructions
└── README.md          # This file
```

## Features

- 📝 **Track PRs**: Add GitHub PR URLs to track their status
- 📊 **Detailed Metrics**: View merge status, files changed, check results, and review status
- 👥 **Multi-Repo Support**: Track PRs across multiple repositories
- 🔄 **Real-time Updates**: Refresh PR data from GitHub API
- 🎨 **Clean Interface**: Simple, GitHub-themed UI with no external frameworks

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
wrangler d1 create pr-tracker
```

5. Update `wrangler.toml` with your database ID from the previous step.

6. Initialize the database schema:
```bash
wrangler d1 execute pr-tracker --file=./schema.sql
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

## Usage

1. **Add a PR**: Enter a GitHub PR URL in the format `https://github.com/owner/repo/pull/number`
2. **View Details**: See comprehensive PR information including:
   - Current state (Open/Closed/Merged)
   - Merge readiness
   - Files changed count
   - Check status (passed/failed/skipped)
   - Review approval status
   - Time since last update
   - Author information
3. **Filter by Repo**: Click on a repository in the sidebar to filter PRs
4. **Refresh Data**: Use the refresh button to update PR information from GitHub

## API Endpoints

- `GET /` - Serves the HTML interface
- `GET /api/repos` - List all repositories with PRs
- `GET /api/prs` - List all PRs (optional `?repo=owner/name` filter)
- `POST /api/prs` - Add a new PR (body: `{"pr_url": "..."}`)
- `POST /api/refresh` - Refresh a PR's data (body: `{"pr_id": 123}`)

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

## GitHub API

The application uses the GitHub REST API to fetch PR information. No authentication is required for public repositories, but rate limits apply (60 requests per hour for unauthenticated requests).

For private repositories or higher rate limits, you can add a GitHub token to the worker environment variables.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is part of the OWASP Bug Logging Tool (BLT) project. 
