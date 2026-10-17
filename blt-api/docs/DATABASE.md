# Cloudflare D1 Database Guide

This project uses Cloudflare D1, a serverless SQLite database that runs at the edge. This guide explains how we use it and how to work with it.

## What is D1?

D1 is Cloudflare's serverless SQL database built on SQLite. It provides:

- **SQLite compatibility** - Standard SQL syntax you already know
- **Edge deployment** - Database runs close to your users
- **Zero configuration** - No servers to manage
- **Local development** - Test with a real SQLite database locally
- **Migrations** - Version-controlled schema changes

## Database Setup

### Local Development

We use a local SQLite database for development that mirrors production.

```bash
# Initialize local database with schema
wrangler d1 migrations apply blt-api --local

# Load sample data for testing
wrangler d1 execute blt-api --local --file=test_data.sql
```

The local database is stored in `.wrangler/state/v3/d1/` as a standard SQLite file.

### Production

Production uses Cloudflare's managed D1 service.

```bash
# Apply schema changes to production
wrangler d1 migrations apply blt-api --remote
```

Configuration is in `wrangler.toml`:

```toml
[[d1_databases]]
binding = "blt_api"           # Variable name used in code
database_name = "blt-api"     # Display name
database_id = "abc-123-xyz"   # Unique identifier
```

## Working with Data

### Querying from Python Code

In your handler functions:

```python
from libs.db import get_db_safe

async def handle_domains(request, env, ...):
    # Get database connection
    db = await get_db_safe(env)
    
    # Execute query
    result = await db.prepare(
        "SELECT * FROM domains WHERE id = ?"
    ).bind(domain_id).first()
    
    # Convert result to Python
    data = result.to_py() if hasattr(result, 'to_py') else result
```

### Query Patterns

**Select multiple rows:**
```python
result = await db.prepare(
    "SELECT * FROM domains LIMIT ? OFFSET ?"
).bind(limit, offset).all()

# Convert results to Python list
from handlers.domains import convert_d1_results
data = convert_d1_results(result.results)
```

**Select single row:**
```python
result = await db.prepare(
    "SELECT * FROM domains WHERE id = ?"
).bind(domain_id).first()

# Returns None if not found, or a row object
if result:
    data = result.to_py() if hasattr(result, 'to_py') else result
```

**Insert data:**
```python
result = await db.prepare(
    "INSERT INTO domains (name, url) VALUES (?, ?)"
).bind(name, url).run()
```

**Count rows:**
```python
result = await db.prepare(
    "SELECT COUNT(*) as total FROM domains"
).first()

total = result['total'] if result else 0
```

### Command Line Queries

For debugging or manual data management:

```bash
# Query local database
wrangler d1 execute blt-api --local --command "SELECT * FROM domains;"

# Query production database
wrangler d1 execute blt-api --remote --command "SELECT * FROM domains;"

# Execute SQL from file
wrangler d1 execute blt-api --local --file=queries.sql
```

## Schema Migrations

### Understanding Migrations

Migrations are numbered SQL files in the `migrations/` folder:

```
migrations/
  0001_init.sql          # Initial schema
  0002_add_users.sql     # Add users table
  0003_modify_domains.sql # Modify domains table
```

Each migration runs once and is tracked in the `d1_migrations` table.

### Creating a Migration

```bash
wrangler d1 migrations create blt-api <description>
```

Example:
```bash
wrangler d1 migrations create blt-api add-description-column
```

This creates: `migrations/0002_add-description-column.sql`

### Writing Migration SQL

Edit the generated file:

```sql
-- Migration number: 0002 	 2026-02-17T10:00:00.000Z

ALTER TABLE domains ADD COLUMN description TEXT;
```

**Important patterns:**

```sql
-- Create table (use IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL
);

-- Add index
CREATE INDEX idx_users_username ON users(username);

-- Add auto-update trigger
CREATE TRIGGER update_users_modified 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET modified = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

### Applying Migrations

**Step 1: Test locally**
```bash
wrangler d1 migrations apply blt-api --local
```

**Step 2: Verify it works**
```bash
wrangler dev --port 8787
# Test your endpoints
```

**Step 3: Apply to production**
```bash
wrangler d1 migrations apply blt-api --remote
```

**Step 4: Deploy code**
```bash
wrangler deploy
```

### Checking Migration Status

```bash
# See which migrations are applied
wrangler d1 migrations list blt-api --local
wrangler d1 migrations list blt-api --remote
```

## Database Helpers

We provide helper functions in `src/libs/db.py`:

### get_db(env)

Gets the database connection from environment.

```python
from libs.db import get_db

db = get_db(env)
```

### get_db_safe(env)

Gets database and verifies required tables exist. Use this in handlers.

```python
from libs.db import get_db_safe

try:
    db = await get_db_safe(env)
except Exception as e:
    return error_response(str(e), status=503)
```

### convert_d1_results(results)

Converts D1 JavaScript proxy objects to Python lists.

```python
from handlers.domains import convert_d1_results

result = await db.prepare("SELECT * FROM domains").all()
data = convert_d1_results(result.results)  # List of dicts
```

## Data Type Conversion

D1 returns JavaScript proxy objects that need conversion to Python:

**For lists (all()):**
```python
result = await db.prepare("SELECT * FROM domains").all()
data = convert_d1_results(result.results)
# Returns: [{'id': 1, 'name': 'example'}, ...]
```

**For single row (first()):**
```python
result = await db.prepare("SELECT * FROM domains WHERE id = 1").first()
if result:
    if hasattr(result, 'to_py'):
        data = result.to_py()
    else:
        data = result
# Returns: {'id': 1, 'name': 'example'}
```

**For counts/aggregates:**
```python
result = await db.prepare("SELECT COUNT(*) as total FROM domains").first()
if hasattr(result, 'to_py'):
    result = result.to_py()
    
total = result.get('total', 0) if isinstance(result, dict) else 0
```

## Current Schema

### domains table

Main table for domain information.

```sql
CREATE TABLE domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,              -- Domain name (max 255 chars)
    url TEXT NOT NULL,               -- Domain URL (max 200 chars)
    logo TEXT,                       -- Logo URL
    webshot TEXT,                    -- Screenshot URL
    clicks INTEGER,                  -- Click count
    email_event TEXT,                -- Email event type
    color TEXT,                      -- Display color
    github TEXT,                     -- GitHub username
    email TEXT,                      -- Contact email
    twitter TEXT,                    -- Twitter handle
    facebook TEXT,                   -- Facebook URL
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    has_security_txt BOOLEAN DEFAULT 0,
    security_txt_checked_at TIMESTAMP,
    organization INTEGER             -- Organization ID (no FK yet)
);
```

**Indexes:**
- `idx_domains_organization` - Filter by organization
- `idx_domains_is_active` - Filter active domains
- `idx_domains_created` - Sort by creation date

### tags table

Reusable tags for categorization.

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### domain_tags table

Links domains to tags (many-to-many).

```sql
CREATE TABLE domain_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(domain_id, tag_id)
);
```

**Indexes:**
- `idx_domain_tags_domain` - Get tags for a domain
- `idx_domain_tags_tag` - Get domains with a tag

## Common Patterns

### Pagination

```python
# Get page and per_page from query params
page = int(request.query.get('page', 1))
per_page = min(int(request.query.get('per_page', 20)), 100)

# Calculate offset
offset = (page - 1) * per_page

# Get total count
count_result = await db.prepare("SELECT COUNT(*) as total FROM domains").first()
total = count_result['total'] if count_result else 0

# Get paginated data
result = await db.prepare(
    "SELECT * FROM domains LIMIT ? OFFSET ?"
).bind(per_page, offset).all()

data = convert_d1_results(result.results)

# Return with pagination metadata
return json_response({
    "success": True,
    "data": data,
    "pagination": {
        "page": page,
        "per_page": per_page,
        "count": len(data),
        "total": total,
        "total_pages": (total + per_page - 1) // per_page
    }
})
```

### Filtering

```python
# Build query with conditions
conditions = []
params = []

if domain_filter:
    conditions.append("domain_id = ?")
    params.append(domain_filter)

if is_active is not None:
    conditions.append("is_active = ?")
    params.append(1 if is_active else 0)

where_clause = " AND ".join(conditions) if conditions else "1=1"

# Execute query
result = await db.prepare(
    f"SELECT * FROM domains WHERE {where_clause}"
).bind(*params).all()
```

### Joins

```python
# Get domains with their tags
result = await db.prepare("""
    SELECT 
        d.id,
        d.name,
        d.url,
        GROUP_CONCAT(t.name) as tags
    FROM domains d
    LEFT JOIN domain_tags dt ON d.id = dt.domain_id
    LEFT JOIN tags t ON dt.tag_id = t.id
    GROUP BY d.id
""").all()

data = convert_d1_results(result.results)
```

## Debugging

### View Database Contents

```bash
# List all tables
wrangler d1 execute blt-api --local --command \
  "SELECT name FROM sqlite_master WHERE type='table';"

# View table structure
wrangler d1 execute blt-api --local --command \
  "PRAGMA table_info(domains);"

# View sample data
wrangler d1 execute blt-api --local --command \
  "SELECT * FROM domains LIMIT 5;"
```

### Reset Local Database

```bash
# Delete local database
rm -rf .wrangler/state/v3/d1/

# Reapply migrations
wrangler d1 migrations apply blt-api --local

# Reload test data
wrangler d1 execute blt-api --local --file=test_data.sql
```

### Check Query Performance

```bash
# Use EXPLAIN to see query plan
wrangler d1 execute blt-api --local --command \
  "EXPLAIN QUERY PLAN SELECT * FROM domains WHERE is_active = 1;"
```

## Best Practices

### Always Use Parameterized Queries

**Good:**
```python
result = await db.prepare(
    "SELECT * FROM domains WHERE id = ?"
).bind(domain_id).all()
```

**Bad (SQL injection risk):**
```python
result = await db.prepare(
    f"SELECT * FROM domains WHERE id = {domain_id}"
).all()
```

### Convert Results Immediately

```python
# Always convert D1 results to Python types
result = await db.prepare("SELECT * FROM domains").all()
data = convert_d1_results(result.results)  # Do this
```

### Handle Errors Gracefully

```python
try:
    db = await get_db_safe(env)
    result = await db.prepare("SELECT * FROM domains").all()
    data = convert_d1_results(result.results)
    return json_response({"success": True, "data": data})
except Exception as e:
    return error_response(f"Database error: {str(e)}", status=500)
```

### Test Locally First

Always test database changes locally before applying to production:

1. Apply migration locally
2. Test with `wrangler dev`
3. Verify data with command line queries
4. Then apply to remote

## Limits and Constraints

### D1 Limits

- **Database size:** 100MB per database (free plan)
- **Query execution:** 30 seconds max
- **Rows per query:** No hard limit, but be reasonable
- **Concurrent operations:** D1 handles this automatically

### SQLite Constraints

- **TEXT max length:** No limit in SQLite
- **INTEGER range:** -9223372036854775808 to 9223372036854775807
- **BLOB max size:** 1GB (theoretical), 10MB (practical)

We add application-level constraints using CHECK:

```sql
CREATE TABLE domains (
    name TEXT CHECK(LENGTH(name) >= 1 AND LENGTH(name) <= 255),
    url TEXT CHECK(LENGTH(url) >= 1 AND LENGTH(url) <= 200)
);
```

## Resources

All information in this guide is based on Cloudflare's official documentation:

- [Cloudflare D1 Documentation](https://developers.cloudflare.com/d1/)
- [D1 Client API Reference](https://developers.cloudflare.com/d1/client-api/)
- [Wrangler D1 Commands](https://developers.cloudflare.com/workers/wrangler/commands/#d1)
- [SQLite SQL Reference](https://www.sqlite.org/lang.html)
- [Python Workers with D1](https://developers.cloudflare.com/workers/languages/python/)

For specific implementation details not covered here, refer to the official Cloudflare D1 documentation.
