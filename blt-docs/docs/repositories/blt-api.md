# BLT-API

**Full-featured REST API for OWASP BLT running on Cloudflare Workers**

- **Repository**: [OWASP-BLT/BLT-API](https://github.com/OWASP-BLT/BLT-API)
- **Language**: Python
- **License**: AGPL-3.0

---

## Overview

BLT-API is a high-performance, edge-deployed REST API that interfaces with all aspects of the [OWASP BLT](https://github.com/OWASP-BLT/BLT) project. Built using Python on Cloudflare Workers, it provides efficient, globally-distributed access to BLT's bug bounty platform data.

## Key Features

- 🚀 **Edge-deployed** — Runs on Cloudflare's global network for low latency
- 🐍 **Python-powered** — Built with Python for Cloudflare Workers
- 🗄️ **D1 Database** — Uses Cloudflare D1 (SQLite) for data persistence
- 🔒 **Secure** — CORS enabled, authentication support
- 📊 **Full API Coverage** — Access to bugs, users, domains, organizations, projects, hunts, and more
- 📖 **Well-documented** — Comprehensive API documentation
- ⚡ **Fast** — Optimized for quick cold starts and efficient execution

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Wrangler](https://developers.cloudflare.com/workers/cli-wrangler/) (Cloudflare Workers CLI)

### Installation

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-API.git
cd BLT-API

# Install dependencies
uv sync

# Install workers-py
uv tool install workers-py
```

### Local Development

```bash
# Setup local database
wrangler d1 migrations apply blt-api --local
wrangler d1 execute blt-api --local --file=test_data.sql

# Start the development server
wrangler dev --port 8787
# The API will be available at http://localhost:8787
```

### Running Tests

```bash
# Install test dependencies
uv sync --extra dev

# Run unit tests
uv run pytest

# Run specific test file
uv run pytest tests/test_router.py -v
```

---

## API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API status and available endpoints |
| GET | `/health` | Health check endpoint |

### Bugs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bugs` | List all bugs (paginated) |
| GET | `/bugs/{id}` | Get a specific bug with screenshots and tags |
| POST | `/bugs` | Create a new bug |
| GET | `/bugs/search?q={query}` | Search bugs by URL or description |

**Query Parameters for `GET /bugs`:**

- `page` — Page number (default: 1)
- `per_page` — Items per page (default: 20, max: 100)
- `status` — Filter by status (e.g., `open`, `closed`, `reviewing`)
- `domain` — Filter by domain ID
- `verified` — Filter by verification status (`true` or `false`)

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users (paginated) |
| GET | `/users/{id}` | Get a specific user |
| GET | `/users/{id}/profile` | Get user profile with statistics |
| GET | `/users/{id}/bugs` | Get bugs reported by user |
| GET | `/users/{id}/domains` | Get domains submitted by user |
| GET | `/users/{id}/followers` | Get users following this user |
| GET | `/users/{id}/following` | Get users this user follows |

### Domains

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains` | List all domains (paginated) |
| GET | `/domains/{id}` | Get a specific domain |
| GET | `/domains/{id}/tags` | Get tags for a domain |

### Organizations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/organizations` | List all organizations (paginated) |
| GET | `/organizations/{id}` | Get a specific organization |
| GET | `/organizations/{id}/repos` | Get organization repositories |
| GET | `/organizations/{id}/projects` | Get organization projects |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects` | List all projects (paginated) |
| GET | `/projects/{id}` | Get a specific project |
| GET | `/projects/{id}/contributors` | Get project contributors |

### Bug Hunts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/hunts` | List all bug hunts |
| GET | `/hunts/{id}` | Get a specific hunt |
| GET | `/hunts/active` | Get currently active hunts |
| GET | `/hunts/previous` | Get past hunts |
| GET | `/hunts/upcoming` | Get upcoming hunts |

### Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | Get platform statistics |

### Leaderboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/leaderboard` | Get global leaderboard |
| GET | `/leaderboard/monthly` | Get monthly leaderboard |
| GET | `/leaderboard/organizations` | Get organization leaderboard |

### Contributors & Repositories

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contributors` | List all contributors |
| GET | `/contributors/{id}` | Get a specific contributor |
| GET | `/repos` | List repositories |
| GET | `/repos/{id}` | Get a specific repository |

---

## Response Format

All API responses follow a consistent JSON format:

**Success Response:**
```json
{
  "success": true,
  "data": { "..." : "..." },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "count": 10,
    "total": 100
  }
}
```

**Error Response:**
```json
{
  "error": true,
  "message": "Error description",
  "status": 400
}
```

---

## Database

This project uses Cloudflare D1 (SQLite) for data persistence. Some endpoints query the D1 database directly, while others proxy to the BLT backend API.

**D1-Integrated Endpoints:** `/domains`, `/domains/{id}/tags`, `/bugs`, `/bugs/{id}`

```bash
# Apply migrations locally
wrangler d1 migrations apply blt-api --local

# Load test data
wrangler d1 execute blt-api --local --file=test_data.sql

# Apply to production
wrangler d1 migrations apply blt-api --remote
```

---

## Project Structure

```
BLT-API/
├── src/
│   ├── main.py             # Worker entry point
│   ├── router.py           # URL routing
│   ├── utils.py            # Utility functions
│   ├── client.py           # BLT backend HTTP client
│   ├── libs/
│   │   └── db.py           # Database helpers
│   └── handlers/           # Request handlers
│       ├── bugs.py
│       ├── users.py
│       ├── domains.py
│       ├── organizations.py
│       ├── projects.py
│       ├── hunts.py
│       ├── stats.py
│       ├── leaderboard.py
│       ├── contributors.py
│       ├── repos.py
│       └── health.py
├── migrations/             # D1 database migrations
├── docs/
│   └── DATABASE.md         # D1 database guide
├── tests/
├── test_data.sql           # Sample data for development
├── wrangler.toml           # Cloudflare Workers config
└── pyproject.toml          # Python project config
```

---

## Environment Variables

Configure these in `wrangler.toml`:

| Variable | Description |
|----------|-------------|
| `BLT_API_BASE_URL` | BLT backend API URL |
| `BLT_WEBSITE_URL` | BLT website URL |
| `JWT_SECRET` | Secret key for JWT tokens |
| `MAILGUN_API_KEY` | Mailgun API key for email |
| `MAILGUN_DOMAIN` | Mailgun domain |

---

## Deployment

```bash
# Login to Cloudflare (first time only)
wrangler login

# Deploy to production (migrations run automatically)
wrangler deploy
```

The project is configured to automatically run D1 migrations before every deployment via the build command in `wrangler.toml`.

---

## Authentication

Some endpoints require authentication. Pass the auth token in the request header:

```bash
curl -H "Authorization: Token YOUR_API_TOKEN" https://your-worker.workers.dev/bugs
```

---

## Contributing

See [CONTRIBUTING.md](https://github.com/OWASP-BLT/BLT-API/blob/main/CONTRIBUTING.md) for detailed setup instructions and development guidelines.

## Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) — Main BLT project
- [BLT Website](https://blt.owasp.org) — Live BLT platform
