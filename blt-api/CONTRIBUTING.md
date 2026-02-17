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

The project uses Cloudflare D1 (SQLite) for local development and production.

#### Apply Migrations

```bash
# Apply all migrations to local database
wrangler d1 migrations apply blt-api --local
```

This creates the database schema in `.wrangler/state/v3/d1/`.

#### Insert Test Data

```bash
# Load sample data for development
wrangler d1 execute blt-api --local --file=test_data.sql
```

This creates:
- 3 sample domains
- 5 tags
- Domain-tag relationships

#### Verify Setup

```bash
# List all tables
wrangler d1 execute blt-api --local --command "SELECT name FROM sqlite_master WHERE type='table';"

# View domains
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
python3 test_api.py
```

## Database Migrations

### Understanding Migrations

Migrations are SQL files that modify database schema. They are located in `migrations/` and executed in order.

Current migrations:
- `0001_init.sql` - Initial schema (domains, tags, domain_tags)

### Creating a New Migration

```bash
# Create migration file
wrangler d1 migrations create blt-api <migration-name>
```

This creates a new file: `migrations/XXXX_<migration-name>.sql`

Example migration:
```sql
-- Migration number: 0002
-- Add description column to domains

ALTER TABLE domains ADD COLUMN description TEXT;
```

### Applying Migrations

#### Local Database

```bash
# Apply all pending migrations
wrangler d1 migrations apply blt-api --local

# List migration status
wrangler d1 migrations list blt-api --local
```

#### Remote Database

```bash
# Apply to production
wrangler d1 migrations apply blt-api --remote

# Check status
wrangler d1 migrations list blt-api --remote
```

### Manual Schema Updates

If you need to modify schema directly:

#### Local

```bash
# Execute SQL directly
wrangler d1 execute blt-api --local --command "ALTER TABLE domains ADD COLUMN new_field TEXT;"

# Or from file
wrangler d1 execute blt-api --local --file=my-changes.sql
```

#### Remote

```bash
# Same commands with --remote flag
wrangler d1 execute blt-api --remote --command "..."
wrangler d1 execute blt-api --remote --file=my-changes.sql
```

**Important:** Manual changes should be documented in a migration file for version control.

## Database Management

### Querying Data

```bash
# Local database
wrangler d1 execute blt-api --local --command "SELECT * FROM domains LIMIT 10;"

# Remote database
wrangler d1 execute blt-api --remote --command "SELECT * FROM domains LIMIT 10;"
```

### Resetting Local Database

```bash
# Delete local database
rm -rf .wrangler/state/v3/d1/

# Reapply migrations
wrangler d1 migrations apply blt-api --local

# Reload test data
wrangler d1 execute blt-api --local --file=test_data.sql
```

### Database Location

- Local: `.wrangler/state/v3/d1/`
- Remote: Cloudflare D1 (managed service)

Configuration is in `wrangler.toml`:
```toml
[[d1_databases]]
binding = "blt_api"
database_name = "blt-api"
database_id = "<your-database-id>"
```

## Code Structure

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
python3 test_api.py
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

### Deploy to Cloudflare

```bash
# Deploy to production
wrangler deploy

# Deploy with a specific environment
wrangler deploy --env production
```

### Pre-deployment Checklist

1. Test locally with `wrangler dev`
2. Apply migrations to remote: `wrangler d1 migrations apply blt-api --remote`
3. Verify migrations: `wrangler d1 migrations list blt-api --remote`
4. Deploy: `wrangler deploy`

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
