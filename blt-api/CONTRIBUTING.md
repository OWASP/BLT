# Contributing to BLT API

This guide covers setting up the development environment, working with the database, and contributing code.

## Prerequisites

- Node.js 18+ (for Wrangler CLI)
- Python 3.11+
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
git clone <repository-url>
cd BLT-API
```

## Local Development

### Database Setup

The project uses Cloudflare D1 (SQLite) for data persistence. See [docs/DATABASE.md](docs/DATABASE.md) for detailed database documentation.

#### Quick Setup

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
# List domains
curl http://localhost:8787/domains

# Get specific domain
curl http://localhost:8787/domains/1

# Get domain tags
curl http://localhost:8787/domains/1/tags

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

## Code Structure

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

Use curl or the provided test script:

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
pytest tests/
```

## Deployment

### Automated Deployment (CI/CD)

The project uses GitHub Actions for continuous deployment. When you push to the `main` branch:

1. Database migrations are automatically applied
2. Worker code is automatically deployed to Cloudflare

This means **you don't need to manually run migrations or deploy** for changes merged to `main`.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for CI/CD setup and configuration details.

### Manual Deployment

For manual deployments or testing:

```bash
# Apply migrations first
wrangler d1 migrations apply blt-api --remote

# Deploy to production
wrangler deploy

# Deploy with a specific environment
wrangler deploy --env production
```

### Pre-deployment Checklist (for PRs)

1. Test locally with `wrangler dev`
2. Apply migrations locally: `wrangler d1 migrations apply blt-api --local`
3. Verify migrations work correctly
4. Run tests: `uv run pytest`
5. Once merged to `main`, CI/CD handles the rest!

## Common Tasks

### Add a New Endpoint

1. Create handler in `src/handlers/`
2. Register route in `src/main.py`
3. Test locally
4. Submit PR

### Add a New Table

1. Create migration: `wrangler d1 migrations create blt-api add-<table-name>`
2. Write SQL in generated migration file
3. Apply locally: `wrangler d1 migrations apply blt-api --local`
4. Test with sample data
5. Commit migration file

### Modify Existing Table

1. Create migration: `wrangler d1 migrations create blt-api modify-<table-name>`
2. Write ALTER TABLE statements
3. Test locally first
4. Document any breaking changes
5. Apply to remote before deployment

See [docs/DATABASE.md](docs/DATABASE.md) for migration examples and patterns.

## Troubleshooting

### "Database not configured" Error

Ensure `wrangler.toml` has correct D1 binding:
```toml
[[d1_databases]]
binding = "blt_api"
```

And code uses correct binding name:
```python
db = get_db(env)  # Looks for 'blt_api' binding
```

### "Missing tables" Error

Apply migrations:
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
- Validate input parameters
- Handle errors with appropriate HTTP status codes
- Convert D1 results to Python types
- Use parameterized queries (never string interpolation)
- Add pagination to list endpoints
- Document new endpoints in PR

## Resources

- [Cloudflare D1 Documentation](https://developers.cloudflare.com/d1/)
- [Wrangler CLI Documentation](https://developers.cloudflare.com/workers/wrangler/)
- [Python Workers Documentation](https://developers.cloudflare.com/workers/languages/python/)

## Getting Help

- Check existing issues
- Review closed PRs for similar changes
- Ask in discussions section
- Read Cloudflare Workers documentation
