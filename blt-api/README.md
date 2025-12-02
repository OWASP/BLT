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

---

## Overview

BLT-API is a high-performance, edge-deployed REST API that interfaces with all aspects of the [OWASP BLT (Bug Logging Tool)](https://github.com/OWASP-BLT/BLT) project. Built using Python on Cloudflare Workers, it provides efficient, globally-distributed access to BLT's bug bounty platform.

## Features

- 🚀 **Edge-deployed** - Runs on Cloudflare's global network for low latency
- 🐍 **Python-powered** - Built with Python for Cloudflare Workers
- 🔒 **Secure** - CORS enabled, authentication support
- 📊 **Full API Coverage** - Access to issues, users, domains, organizations, projects, hunts, and more
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
# Start the development server
uv run pywrangler dev

# The API will be available at http://localhost:8787
```

### Running Tests

```bash
# Install test dependencies
uv sync --extra dev

# Run tests
uv run pytest
```

## API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API status and available endpoints |
| GET | `/health` | Health check endpoint |

### Issues

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/issues` | List all issues (paginated) |
| GET | `/issues/{id}` | Get a specific issue |
| POST | `/issues` | Create a new issue |
| GET | `/issues/search?q={query}` | Search issues |

**Query Parameters for `/issues`:**
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 20, max: 100)
- `status` - Filter by status (open, closed)
- `domain` - Filter by domain URL

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
| GET | `/domains/{id}/issues` | Get issues for a domain |

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
│   └── handlers/           # Request handlers
│       ├── __init__.py
│       ├── issues.py
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
├── tests/                  # Test files
├── wrangler.toml           # Cloudflare Workers config
├── pyproject.toml          # Python project config
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

### Deploy to Cloudflare Workers

```bash
# Login to Cloudflare
wrangler login

# Deploy to production
uv run pywrangler deploy
```

### Environment-specific Deployment

```bash
# Deploy to development
uv run pywrangler deploy --env development

# Deploy to production
uv run pywrangler deploy --env production
```

## Authentication

Some endpoints require authentication. Pass the auth token in the request header:

```bash
curl -H "Authorization: Token YOUR_API_TOKEN" https://your-worker.workers.dev/issues
```

## Rate Limiting

The API follows Cloudflare Workers' execution limits:
- CPU time: 50ms (free), 30s (paid)
- Memory: 128MB
- Request size: 100MB

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

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