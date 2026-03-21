# Contributing to BLT API

This guide covers setting up the development environment, working with the database, and contributing code.

## Prerequisites

- Node.js 18+ (for Wrangler CLI)
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Cloudflare account (for remote deployment)

## Initial Setup

### 1. Install Wrangler CLI

```bash
npm install -g wrangler
```

### 2. Authenticate with Cloudflare

```bash
wrangler login
```

This opens a browser for authentication. Required for remote database operations.

### 3. Clone and Install

```bash
git clone https://github.com/OWASP-BLT/BLT-API.git
cd BLT-API

# Install Python dependencies
uv sync

# Install workers-py
uv tool install workers-py
```

## Local Development

### Database Setup

The project uses Cloudflare D1 (SQLite) for data persistence. See [docs/DATABASE.md](docs/DATABASE.md) for detailed database documentation.

#### Quick Setup (Recommended)

Use the automated setup script:

```bash
# Setup local database with migrations and test data
bash scripts/setup_local_db.sh
```

This script will:
- Apply all migrations to the local database
- List all tables to verify setup
- Provide next steps for loading test data

#### Manual Setup

If you prefer manual control:

```bash
# Apply schema to local database
wrangler d1 migrations apply blt-api --local

# Load sample data
wrangler d1 execute blt-api --local --file=test_data.sql

# Verify setup
wrangler d1 execute blt-api --local --command "SELECT * FROM domains;"
```

### Start Development Server

```bash
wrangler dev --port 8787
```

The API will be available at `http://localhost:8787`.

Hot reload is enabled - code changes trigger automatic restart.

### Test Endpoints

```bash
# Visit the interactive API homepage
open http://localhost:8787

# Health check
curl http://localhost:8787/health

# List domains
curl http://localhost:8787/domains

# Get specific domain
curl http://localhost:8787/domains/1

# Get domain tags
curl http://localhost:8787/domains/1/tags

# List bugs
curl http://localhost:8787/bugs

# Get stats
curl http://localhost:8787/stats

# Or use the test script
python3 tests/test_domain.py
```

## Database Migrations

Migrations are SQL files that define schema changes. See [docs/DATABASE.md](docs/DATABASE.md) for complete guide.

### Quick Reference

```bash
# Create migration
wrangler d1 migrations create blt-api <description>

# Apply locally
wrangler d1 migrations apply blt-api --local

# Apply to production
wrangler d1 migrations apply blt-api --remote

# Check status
wrangler d1 migrations list blt-api --local
```

## Database Management

For querying data, resetting database, and other database operations, see [docs/DATABASE.md](docs/DATABASE.md).

Quick commands:

```bash
# Query data
wrangler d1 execute blt-api --local --command "SELECT * FROM domains LIMIT 10;"

# Reset local database
rm -rf .wrangler/state/v3/d1/
wrangler d1 migrations apply blt-api --local
wrangler d1 execute blt-api --local --file=test_data.sql
```

## Environment Configuration

Configure environment variables using `.env.sample`:

```bash
cp .env.sample .env
```

Then configure Wrangler runtime values/secrets per environment (for example with `wrangler secret put ...`).

To load all production variables from `.env.production` automatically:

```bash
bash scripts/load_env_production.sh
```

Or provide a custom path:

```bash
bash scripts/load_env_production.sh path/to/.env.production
```

### Email Service Setup

The API uses Mailgun for sending emails (verification, password reset, welcome emails):

1. **Create a Mailgun account** at https://www.mailgun.com
2. **Get your API key** from Settings → API Keys
3. **Choose a domain:**
   - **Sandbox domain** (testing): Free, limited to 5 authorized recipients
   - **Custom domain** (production): Requires DNS setup, can send to anyone
4. **Add configuration** from `.env.sample` and set Wrangler secrets for deployment

### JWT Authentication

For authentication endpoints (`/auth/signup`, `/auth/signin`), configure:

```toml
[vars]
JWT_SECRET = "your-very-secure-random-string-here"
```

Generate a secure secret:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Code Structure

### Project Organization

- `src/handlers/` - HTTP request handlers (bugs, users, domains, auth, etc.)
- `src/services/` - Service modules (email service, templates)
- `src/libs/` - Shared libraries (database, JWT, constants)
- `src/pages/` - Static HTML pages (API homepage)
- `scripts/` - Utility scripts (database setup, migrations)
- `migrations/` - D1 database migrations
- `tests/` - Test files

### Database Code Patterns

See [docs/DATABASE.md](docs/DATABASE.md) for detailed examples of querying, pagination, and data conversion.

### Database Helpers

`src/libs/db.py` provides database utilities:

```python
from libs.db import get_db_safe

async def my_handler(request, env, ...):
    db = await get_db_safe(env)  # Validates DB is initialized
    result = await db.prepare("SELECT * FROM domains").all()
    data = convert_d1_results(result.results)
```

### D1 Result Conversion

D1 returns JavaScript proxy objects. Convert them to Python:

```python
from handlers.domains import convert_d1_results

result = await db.prepare("SELECT * FROM table").all()
data = convert_d1_results(result.results)  # List of dicts
```

Or for single row:

```python
result = await db.prepare("SELECT * FROM table WHERE id = ?").bind(1).first()
if result:
    data = result.to_py() if hasattr(result, 'to_py') else result
```

### Response Handling

Use the standard response helpers:

```python
from utils import json_response, error_response

# Success
return json_response({
    "success": True,
    "data": data
})

# Error
return error_response("Not found", status=404)
```

## Testing

### Manual Testing

Use the interactive API homepage:
```bash
# Start dev server
wrangler dev --port 8787

# Open in browser
open http://localhost:8787
```

Or use curl:
```bash
python3 tests/test_domain.py
```

### Writing Tests

Add tests to `tests/` directory:

```python
import pytest
from handlers.domains import handle_domains

async def test_list_domains():
    # Test implementation
    pass
```

Run tests:

```bash
# Install test dependencies first
uv sync --extra dev

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_router.py -v
```

## Deployment

### Deploy to Cloudflare

Migrations run automatically during deployment thanks to the `[build]` command in `wrangler.toml`:

```bash
# Deploy to production (migrations run automatically)
wrangler deploy

# Deploy to specific environment
wrangler deploy --env production
wrangler deploy --env development
```

The build process automatically runs `scripts/migrate.sh` which applies D1 migrations before the worker is deployed.

### Automatic Deployment from Git

The recommended approach is to use Cloudflare's Git integration:

1. Connect your repository in the Cloudflare dashboard
2. Pushes to `main` automatically trigger deployment
3. Migrations run as part of the build process

See the [README.md](README.md#cloudflare-git-integration-recommended) for setup instructions.

### Pre-deployment Checklist

1. Test locally with `wrangler dev`
2. Test migrations locally: `wrangler d1 migrations apply blt-api --local`
3. Run tests: `uv run pytest`
4. Deploy: `wrangler deploy` (migrations run automatically)

## Common Tasks

### Add a New Endpoint

1. Create handler in `src/handlers/` (e.g., `new_feature.py`)
2. Export handler in `src/handlers/__init__.py`
3. Register route in `src/main.py`:
   ```python
   from handlers import handle_new_feature
   router.add_route("GET", "/new-feature", handle_new_feature)
   ```
4. Test locally with `wrangler dev`
5. Add tests in `tests/`
6. Update API documentation in homepage template if needed
7. Submit PR

### Add a New Table

1. Create migration: `wrangler d1 migrations create blt-api add-<table-name>`
2. Write SQL in generated migration file (in `migrations/` folder)
3. Apply locally:
   ```bash
   wrangler d1 migrations apply blt-api --local
   # Or use the script
   bash scripts/setup_local_db.sh
   ```
4. Test with sample data
5. Update `test_data.sql` if needed
6. Commit migration file

### Modify Existing Table

1. Create migration: `wrangler d1 migrations create blt-api modify-<table-name>`
2. Write ALTER TABLE statements
3. Test locally first
4. Document any breaking changes
5. Apply to remote before deployment

See [docs/DATABASE.md](docs/DATABASE.md) for migration examples and patterns.

### Add Email Template

1. Create HTML template in `src/services/templates/`
2. Use `[[placeholder]]` syntax for dynamic values (consistent with base template)
3. Extend base template or create standalone
4. Add rendering function in `src/services/email_templates.py`:
   ```python
   def render_my_template(data: dict) -> str:
       template = Path(__file__).parent / "templates/my_template.html"
       content = template.read_text()
       # Replace placeholders
       content = content.replace("[[value]]", data["value"])
       return content
   ```
5. Use with EmailService in handlers:
   ```python
   from services.email_service import EmailService
   from services.email_templates import render_my_template
   
   email_html = render_my_template({"value": "data"})
   await EmailService.send(env, to="user@example.com", subject="...", html=email_html)
   ```

## Troubleshooting

### "Database not configured" Error

Ensure `wrangler.toml` has correct D1 binding:
```toml
[[d1_databases]]
binding = "blt_api"
database_name = "blt-api"
database_id = "your-database-id"
```

And code uses correct binding name:
```python
from libs.db import get_db_safe
db = await get_db_safe(env)  # Looks for 'blt_api' binding
```

### "Missing tables" Error

Apply migrations using the setup script:
```bash
bash scripts/setup_local_db.sh
```

Or manually:
```bash
wrangler d1 migrations apply blt-api --local
```

### JsProxy Errors

Always convert D1 results:
```python
data = convert_d1_results(result.results)
```

Or use `.to_py()`:
```python
data = result.to_py() if hasattr(result, 'to_py') else result
```

### Hot Reload Not Working

Restart dev server:
```bash
# Stop with Ctrl+C
wrangler dev --port 8787
```

## Code Standards

- Use async/await for database operations
- Validate input parameters with `check_required_fields()` utility
- Handle errors with appropriate HTTP status codes using `error_response()`
- Convert D1 results to Python types using `convert_d1_results()` or `.to_py()`
- Use parameterized queries (never string interpolation) with `.bind()`
- Add pagination to list endpoints with consistent parameters (`page`, `per_page`)
- Use `[[placeholder]]` syntax in HTML templates (not `{{placeholder}}`)
- Follow JWT authentication patterns from `libs/jwt_utils.py`
- Use EmailService for sending emails, not direct API calls
- Document new endpoints in PR and update homepage template if public-facing

## Resources

- [Cloudflare D1 Documentation](https://developers.cloudflare.com/d1/)
- [Wrangler CLI Documentation](https://developers.cloudflare.com/workers/wrangler/)
- [Python Workers Documentation](https://developers.cloudflare.com/workers/languages/python/)

## Getting Help

- Check existing issues
- Review closed PRs for similar changes
- Ask in discussions section
- Read Cloudflare Workers documentation
