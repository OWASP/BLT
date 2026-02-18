# BLT-API

<p align="center">
  <strong>Full-featured REST API for OWASP BLT running on Cloudflare Workers</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#api-endpoints">API Endpoints</a> •
  <a href="#development">Development</a> •
  <a href="#deployment">Deployment</a>
</p>

<p align="center">
  <a href="https://deploy.workers.cloudflare.com/?url=https://github.com/OWASP-BLT/BLT-API">
    <img src="https://deploy.workers.cloudflare.com/button" alt="Deploy to Cloudflare Workers" />
  </a>
</p>

---

## Overview

BLT-API is a high-performance, edge-deployed REST API that interfaces with all aspects of the [OWASP BLT (Bug Logging Tool)](https://github.com/OWASP-BLT/BLT) project. Built using Python on Cloudflare Workers, it provides efficient, globally-distributed access to BLT's bug bounty platform.

## Features

- 🚀 **Edge-deployed** - Runs on Cloudflare's global network for low latency
- 🐍 **Python-powered** - Built with Python for Cloudflare Workers
- �️ **D1 Database** - Uses Cloudflare D1 (SQLite) for data persistence
- �🔒 **Secure** - CORS enabled, authentication support
- 📊 **Full API Coverage** - Access to bugs, users, domains, organizations, projects, hunts, and more
- 📖 **Well-documented** - Comprehensive API documentation
- ⚡ **Fast** - Optimized for quick cold starts and efficient execution

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

# Start the development server.
wrangler dev --port 8787

# The API will be available at http://localhost:8787
```

For detailed setup instructions, see [CONTRIBUTING.md](CONTRIBUTING.md).

### Running Tests

```bash
# Install test dependencies
uv sync --extra dev

# Run unit tests
uv run pytest

# Run specific test file
uv run pytest tests/test_router.py -v
```

**Note:** Integration tests for bugs endpoints are in development. You can test endpoints manually with the dev server running at `http://localhost:8788`.

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

#### List Bugs - `GET /bugs`

**Query Parameters:**
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 20, max: 100)
- `status` - Filter by status (e.g., `open`, `closed`, `reviewing`)
- `domain` - Filter by domain ID
- `verified` - Filter by verification status (`true` or `false`)

**Example Request:**
```bash
curl "http://localhost:8787/bugs?page=1&per_page=10&status=open&verified=true"
```

**Example Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "url": "https://example.com/page",
      "description": "SQL injection vulnerability",
      "status": "open",
      "verified": 1,
      "score": 85,
      "views": 125,
      "created": "2026-02-17 10:30:00",
      "modified": "2026-02-17 10:30:00",
      "is_hidden": 0,
      "rewarded": 50,
      "cve_id": "CVE-2024-12345",
      "cve_score": 8.5,
      "domain": 1,
      "domain_name": "Example Corp",
      "domain_url": "https://example.com"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "count": 10,
    "total": 150,
    "total_pages": 15
  }
}
```

#### Get Single Bug - `GET /bugs/{id}`

Returns detailed bug information including screenshots and tags.

**Example Request:**
```bash
curl "http://localhost:8787/bugs/5"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": 5,
    "url": "https://example.com/admin",
    "description": "Authentication bypass vulnerability",
    "markdown_description": "# Detailed Description\n\nFound auth bypass...",
    "label": "critical",
    "views": 245,
    "verified": 1,
    "score": 95,
    "status": "open",
    "user_agent": "Mozilla/5.0...",
    "ocr": null,
    "screenshot": "https://cdn.example.com/screenshot.png",
    "closed_date": null,
    "github_url": "https://github.com/example/repo/issues/123",
    "created": "2026-02-17 08:15:00",
    "modified": "2026-02-17 10:30:00",
    "is_hidden": 0,
    "rewarded": 100,
    "reporter_ip_address": null,
    "cve_id": "CVE-2024-67890",
    "cve_score": 9.1,
    "hunt": 3,
    "domain": 1,
    "user": 42,
    "closed_by": null,
    "domain_id": 1,
    "domain_name": "Example Corp",
    "domain_url": "https://example.com",
    "domain_logo": "https://cdn.example.com/logo.png",
    "screenshots": [
      {
        "id": 1,
        "image": "https://cdn.example.com/screenshot1.png",
        "created": "2026-02-17 08:20:00"
      },
      {
        "id": 2,
        "image": "https://cdn.example.com/screenshot2.png",
        "created": "2026-02-17 08:25:00"
      }
    ],
    "tags": [
      {"id": 1, "name": "authentication"},
      {"id": 2, "name": "critical"},
      {"id": 3, "name": "web"}
    ]
  }
}
```

#### Search Bugs - `GET /bugs/search`

Search for bugs by URL or description text.

**Query Parameters:**
- `q` - Search query (required)
- `limit` - Maximum results to return (default: 10, max: 100)

**Example Request:**
```bash
curl "http://localhost:8787/bugs/search?q=sql+injection&limit=20"
```

**Example Response:**
```json
{
  "success": true,
  "query": "sql injection",
  "data": [
    {
      "id": 15,
      "url": "https://example.com/search",
      "description": "SQL injection in search parameter",
      "status": "open",
      "verified": 1,
      "score": 80,
      "views": 89,
      "created": "2026-02-16 14:30:00",
      "modified": "2026-02-16 14:30:00",
      "is_hidden": 0,
      "rewarded": 0,
      "cve_id": null,
      "cve_score": null,
      "domain": 2,
      "domain_name": "Test Site",
      "domain_url": "https://test.example.com"
    }
  ]
}
```

#### Create Bug - `POST /bugs`

Create a new bug report.

**Required Fields:**
- `url` - URL where the bug was found (max 200 characters)
- `description` - Brief description of the bug

**Optional Fields:**
- `markdown_description` - Detailed markdown description
- `label` - Bug label/category
- `views` - View count
- `verified` - Verification status (boolean)
- `score` - Score/severity (integer)
- `status` - Status (default: "open")
- `user_agent` - User agent string
- `ocr` - OCR text
- `screenshot` - Screenshot URL
- `github_url` - Related GitHub issue URL
- `is_hidden` - Hidden status (boolean)
- `rewarded` - Reward amount (integer, default: 0)
- `reporter_ip_address` - Reporter IP
- `cve_id` - CVE identifier
- `cve_score` - CVE score
- `hunt` - Hunt ID
- `domain` - Domain ID
- `user` - User ID
- `closed_by` - User ID who closed

**Example Request:**
```bash
curl -X POST "http://localhost:8787/bugs" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/vulnerable-page",
    "description": "XSS vulnerability in comment field",
    "markdown_description": "# XSS Vulnerability\n\nFound reflected XSS...",
    "status": "open",
    "verified": true,
    "score": 75,
    "domain": 1,
    "user": 42
  }'
```

**Example Response:**
```json
{
  "success": true,
  "message": "Bug created successfully",
  "data": {
    "id": 156,
    "url": "https://example.com/vulnerable-page",
    "description": "XSS vulnerability in comment field",
    "status": "open",
    "verified": 1,
    "score": 75,
    "domain": 1,
    "user": 42,
    "created": "2026-02-18 09:15:00",
    "modified": "2026-02-18 09:15:00"
  }
}
```

Bugs endpoints use Cloudflare D1 database for direct queries. See [docs/DATABASE.md](docs/DATABASE.md) for schema details.

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users (paginated) |
| GET | `/users/{id}` | Get a specific user |
| GET | `/users/{id}/profile` | Get user profile details |

### Domains

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains` | List all domains (paginated) |
| GET | `/domains/{id}` | Get a specific domain |
| GET | `/domains/{id}/tags` | Get tags for a domain |

Domain endpoints use Cloudflare D1 database. See [docs/DATABASE.md](docs/DATABASE.md) for details.

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

**Query Parameters for `/leaderboard/monthly`:**
- `month` - Month number (1-12)
- `year` - Year (e.g., 2024)

### Contributors

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contributors` | List all contributors |
| GET | `/contributors/{id}` | Get a specific contributor |

### Repositories

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/repos` | List repositories |
| GET | `/repos/{id}` | Get a specific repository |

## Response Format

All API responses follow a consistent JSON format:

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "count": 10,
    "total": 100
  }
}
```

### Error Response

```json
{
  "error": true,
  "message": "Error description",
  "status": 400
}
```

## Database

This project uses Cloudflare D1 (SQLite) for data persistence. Some endpoints query the D1 database directly, while others proxy to the BLT backend API.

### D1-Integrated Endpoints

- `/domains` - Domain data stored in D1
- `/domains/{id}/tags` - Domain tags from D1
- `/bugs` - Bugs data stored in D1
- `/bugs/{id}` - Bug details with screenshots and tags from D1

### Database Operations

```bash
# Apply migrations locally
wrangler d1 migrations apply blt-api --local

# Load test data
wrangler d1 execute blt-api --local --file=test_data.sql

# Create new migration
wrangler d1 migrations create blt-api <description>

# Apply to production
wrangler d1 migrations apply blt-api --remote
```

For complete database guide including queries, schema, and patterns, see [docs/DATABASE.md](docs/DATABASE.md).

## Development

### Project Structure

```
BLT-API/
├── src/
│   ├── __init__.py         # Package initialization
│   ├── main.py             # Worker entry point
│   ├── router.py           # URL routing
│   ├── utils.py            # Utility functions
│   ├── client.py           # BLT backend HTTP client
│   ├── libs/               # Library modules
│   │   └── db.py           # Database helpers
│   └── handlers/           # Request handlers
│       ├── __init__.py
│       ├── bugs.py
│       ├── users.py
│       ├── domains.py      # D1-integrated.
│       ├── organizations.py
│       ├── projects.py
│       ├── hunts.py
│       ├── stats.py
│       ├── leaderboard.py
│       ├── contributors.py
│       ├── repos.py
│       └── health.py
├── migrations/             # D1 database migrations
│   └── 0001_init.sql
├── docs/                   # Documentation
│   └── DATABASE.md         # D1 database guide
├── tests/                  # Test files
├── test_data.sql           # Sample data for development
├── wrangler.toml           # Cloudflare Workers config
├── pyproject.toml          # Python project config
├── CONTRIBUTING.md         # Contribution guide
└── README.md
```

### Adding New Endpoints

1. Create a new handler in `src/handlers/`
2. Import and export it in `src/handlers/__init__.py`
3. Register the route in `src/main.py`

### Environment Variables

Configure these in `wrangler.toml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `BLT_API_BASE_URL` | BLT backend API URL | `https://blt.owasp.org/api/v1` |
| `BLT_WEBSITE_URL` | BLT website URL | `https://blt.owasp.org` |

## Deployment

### Automatic Deployment with Migrations

The project is configured to automatically run D1 migrations before every deployment using Wrangler's build command. The migrations are defined in `wrangler.toml`:

```toml
[build]
command = "bash scripts/migrate.sh"
```

This means migrations will run automatically whenever you deploy, whether:
- Deploying manually with `wrangler deploy`
- Using Cloudflare's Git integration (automatic deploy on push)
- Running in CI/CD pipelines

### Deploy to Cloudflare Workers

```bash
# Login to Cloudflare (first time only)
wrangler login

# Deploy to production (migrations run automatically)
wrangler deploy

# Deploy to specific environment
wrangler deploy --env production
wrangler deploy --env development
```

### Cloudflare Git Integration (Recommended)

For automatic deployments when code is pushed to your repository:

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages**
2. Connect your GitHub/GitLab repository
3. Configure build settings:
   - **Build command**: (leave empty, wrangler handles it)
   - **Deploy command**: `wrangler deploy`
4. Every push to your main branch will automatically:
   - Run D1 migrations (via build command)
   - Deploy the updated worker

See [Cloudflare Git Integration docs](https://developers.cloudflare.com/workers/ci-cd/builds/git-integration/) for details.

### Manual Migration Control

If you need to run migrations separately:

```bash
# Apply migrations only
wrangler d1 migrations apply blt-api --remote

# Deploy without running build command
wrangler deploy --no-build
```

## Authentication

Some endpoints require authentication. Pass the auth token in the request header:

```bash
curl -H "Authorization: Token YOUR_API_TOKEN" https://your-worker.workers.dev/bugs
```

## Rate Limiting

The API follows Cloudflare Workers' execution limits:
- CPU time: 50ms (free), 30s (paid)
- Memory: 128MB
- Request size: 100MB

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed setup instructions and development guidelines.

Quick start:
1. Fork the repository
2. Setup local environment (see CONTRIBUTING.md)
3. Create a feature branch
4. Make your changes
5. Test locally with `wrangler dev`
6. Submit a pull request

For database changes, see [docs/DATABASE.md](docs/DATABASE.md).

## Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) - Main BLT project
- [BLT Website](https://blt.owasp.org) - Live BLT platform

## License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Support

- 💬 [OWASP Slack](https://owasp.org/slack/invite) - Join #project-blt
- 🐛 [GitHub Issues](https://github.com/OWASP-BLT/BLT-API/issues) - Report bugs
- 📖 [BLT Documentation](https://github.com/OWASP-BLT/BLT/blob/main/README.md)

---

<p align="center">
  Made with ❤️ by the OWASP BLT Community
</p>
