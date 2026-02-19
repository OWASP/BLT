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

We use a local SQLite database for development that mirrors production. The database is managed through **migrations only** - we no longer use a single schema.sql file.

```bash
# Apply all pending migrations to local database
wrangler d1 migrations apply pr-tracker --local
```

The local database is stored in `.wrangler/state/v3/d1/` as a standard SQLite file.

### Production

Production uses Cloudflare's managed D1 service.

```bash
# Apply schema changes to production
wrangler d1 migrations apply pr-tracker --remote
```

Configuration is in `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"                  # Variable name used in code
database_name = "pr_tracker"    # Display name
database_id = "abc-123-xyz"     # Unique identifier
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

Migrations are numbered SQL files in the `migrations/` folder that define your database schema changes over time. Each migration runs once and is tracked by Cloudflare D1.

**Current migrations:**
```
migrations/
  0001_create_prs_table.sql          # PR tracking table
  0002_create_timeline_cache.sql     # Timeline cache table  
  0003_create_indexes.sql            # Performance indexes
```

Each migration runs once and is tracked automatically by D1's migration system.

### Why Migrations?

**Benefits:**
- ✅ **Version Control**: Database schema is tracked in git alongside code
- ✅ **Reproducible**: Same migrations work locally and in production
- ✅ **Team Friendly**: Everyone gets the same database structure
- ✅ **Safe Updates**: Migrations run in order, preventing conflicts
- ✅ **No Manual SQL**: Wrangler handles tracking what's been applied

**Migration-Only Approach:**
- We do NOT use `schema.sql` or runtime schema initialization
- Database structure is ONLY defined through migration files
- Application code assumes migrations have been applied
- Both local and production use the same migration workflow

### Creating a Migration

When you need to change the database structure:

```bash
# Create a new migration file
wrangler d1 migrations create pr-tracker "add_user_column"
```

This creates: `migrations/0004_add_user_column.sql`

### Writing Migration SQL

Edit the generated file with your changes:

```sql
-- Migration: Add user column to prs table
-- Created: 2026-02-19

ALTER TABLE prs ADD COLUMN assigned_user TEXT;
```

**Important patterns:**

```sql
-- Always use IF NOT EXISTS for safety
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL
);

-- Add index safely
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Modify existing data if needed
UPDATE prs SET assigned_user = 'unassigned' WHERE assigned_user IS NULL;
```

### Applying Migrations

**Step 1: Test locally**
```bash
wrangler d1 migrations apply pr-tracker --local
```

**Step 2: Verify it works**
```bash
wrangler dev --port 8787
# Test your endpoints
```

**Step 3: Apply to production**
```bash
wrangler d1 migrations apply pr-tracker --remote
```

**Step 4: Deploy code**
```bash
wrangler deploy
```

### Checking Migration Status

```bash
# See which migrations are applied locally
wrangler d1 migrations list pr-tracker --local

# See which migrations are applied in production
wrangler d1 migrations list pr-tracker --remote
```

## Database Helpers

We provide helper functions in `src/database.py`:

### get_db(env)

Gets the database connection from environment.

```python
from database import get_db

db = get_db(env)
```

This helper tries different binding names ('pr_tracker', 'DB') to ensure compatibility.

### Database Operations

All database operations use the D1 client API directly:

```python
from database import get_db

try:
    db = get_db(env)
    # Your queries here
except Exception as e:
    return error_response(str(e), status=503)
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

### prs table

Main table for tracking GitHub Pull Requests and their readiness analysis.

```sql
CREATE TABLE IF NOT EXISTS prs (
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
    repo_owner_avatar TEXT,
    checks_passed INTEGER DEFAULT 0,
    checks_failed INTEGER DEFAULT 0,
    checks_skipped INTEGER DEFAULT 0,
    commits_count INTEGER DEFAULT 0,
    behind_by INTEGER DEFAULT 0,
    review_status TEXT,
    last_updated_at TEXT,
    last_refreshed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    -- Readiness analysis fields
    overall_score INTEGER,
    ci_score INTEGER,
    review_score INTEGER,
    classification TEXT,
    merge_ready INTEGER DEFAULT 0,
    blockers TEXT,              -- JSON array
    warnings TEXT,              -- JSON array
    recommendations TEXT,       -- JSON array
    review_health_classification TEXT,
    review_health_score INTEGER,
    response_rate REAL,
    total_feedback INTEGER,
    responded_feedback INTEGER,
    stale_feedback_count INTEGER,
    stale_feedback TEXT,        -- JSON array
    readiness_computed_at TEXT,
    is_draft INTEGER DEFAULT 0,
    open_conversations_count INTEGER DEFAULT 0,
    reviewers_json TEXT         -- JSON array
);
```

**Indexes:**
- `idx_repo` - Fast filtering by repository (repo_owner, repo_name)
- `idx_pr_number` - Fast lookup by PR number
- `idx_merge_ready` - Sort by merge readiness
- `idx_overall_score` - Sort by overall score
- `idx_ci_score` - Sort by CI score
- `idx_review_score` - Sort by review score
- `idx_response_rate` - Sort by response rate
- `idx_responded_feedback` - Sort by responded feedback count

### timeline_cache table

Cache table to store PR timeline data and reduce GitHub API calls.

```sql
CREATE TABLE IF NOT EXISTS timeline_cache (
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    data TEXT NOT NULL,         -- JSON data
    timestamp TEXT NOT NULL,
    PRIMARY KEY (owner, repo, pr_number)
);
```

**Purpose:** Caches GitHub timeline API responses to minimize rate limit usage.

## Common Patterns

### Pagination

```python
# Get page and per_page from query params
page = int(request.query.get('page', 1))
per_page = min(int(request.query.get('per_page', 30)), 1000)

# Calculate offset
offset = (page - 1) * per_page

# Get total count
count_result = await db.prepare("SELECT COUNT(*) as total FROM prs").first()
if hasattr(count_result, 'to_py'):
    count_result = count_result.to_py()
total = count_result.get('total', 0) if isinstance(count_result, dict) else 0

# Get paginated data
result = await db.prepare(
    "SELECT * FROM prs ORDER BY created_at DESC LIMIT ? OFFSET ?"
).bind(per_page, offset).all()

# Convert D1 results to Python
data = []
if hasattr(result, 'results'):
    for row in result.results:
        row_dict = row.to_py() if hasattr(row, 'to_py') else dict(row)
        data.append(row_dict)

# Return with pagination metadata
return {
    "success": True,
    "data": data,
    "pagination": {
        "page": page,
        "per_page": per_page,
        "count": len(data),
        "total": total,
        "total_pages": (total + per_page - 1) // per_page
    }
}
```

### Filtering by Repository

```python
# Filter PRs by repository
repo_filter = request.query.get('repo')  # Format: "owner/repo"

if repo_filter:
    parts = repo_filter.split('/')
    if len(parts) == 2:
        owner, repo = parts
        result = await db.prepare(
            "SELECT * FROM prs WHERE repo_owner = ? AND repo_name = ?"
        ).bind(owner, repo).all()
else:
    result = await db.prepare("SELECT * FROM prs").all()
```

### Sorting

```python
# Build dynamic sort query
sort_by = request.query.get('sort_by', 'created_at')
sort_dir = request.query.get('sort_dir', 'desc')

# Whitelist allowed sort columns for security
allowed_columns = {
    'created_at', 'updated_at', 'title', 'state',
    'overall_score', 'ci_score', 'review_score',
    'merge_ready', 'response_rate'
}

if sort_by not in allowed_columns:
    sort_by = 'created_at'

if sort_dir.lower() not in ['asc', 'desc']:
    sort_dir = 'desc'

# Build safe query (column name validated against whitelist)
query = f"SELECT * FROM prs ORDER BY {sort_by} {sort_dir}"
result = await db.prepare(query).all()
```

### Upserting PR Data

```python
# Insert or update PR (uses ON CONFLICT)
current_timestamp = datetime.now(timezone.utc).isoformat()

stmt = db.prepare('''
    INSERT INTO prs (pr_url, repo_owner, repo_name, pr_number, title, state, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(pr_url) DO UPDATE SET
        title = excluded.title,
        state = excluded.state,
        updated_at = excluded.updated_at
''').bind(pr_url, owner, repo, pr_number, title, state, current_timestamp)

await stmt.run()
```

### Storing JSON Data

```python
import json

# Store readiness analysis as JSON
blockers_json = json.dumps(['Failing CI checks', 'Merge conflicts'])
warnings_json = json.dumps(['No reviewers assigned'])

await db.prepare('''
    UPDATE prs SET 
        blockers = ?,
        warnings = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
''').bind(blockers_json, warnings_json, pr_id).run()

# Read and parse JSON
result = await db.prepare("SELECT blockers FROM prs WHERE id = ?").bind(pr_id).first()
if result:
    row = result.to_py() if hasattr(result, 'to_py') else dict(result)
    blockers = json.loads(row.get('blockers', '[]'))
```

## Debugging

### View Database Contents

```bash
# List all tables
wrangler d1 execute pr-tracker --local --command \
  "SELECT name FROM sqlite_master WHERE type='table';"

# View table structure
wrangler d1 execute pr-tracker --local --command \
  "PRAGMA table_info(prs);"

# View sample PR data
wrangler d1 execute pr-tracker --local --command \
  "SELECT id, pr_number, title, state, overall_score FROM prs LIMIT 5;"

# Check migration status
wrangler d1 migrations list pr-tracker --local
```

### Reset Local Database

```bash
# Delete local database
rm -rf .wrangler/state/v3/d1/

# Reapply all migrations
wrangler d1 migrations apply pr-tracker --local
```

### Check Query Performance

```bash
# Use EXPLAIN to see query plan
wrangler d1 execute pr-tracker --local --command \
  "EXPLAIN QUERY PLAN SELECT * FROM prs WHERE repo_owner = 'OWASP-BLT' AND repo_name = 'BLT';"
```

### Common Issues

**Issue: "no such table: prs"**
```bash
# Migrations not applied - run:
wrangler d1 migrations apply pr-tracker --local
```

**Issue: "column doesn't exist"**
```bash
# Check if all migrations are applied:
wrangler d1 migrations list pr-tracker --local

# If missing, apply migrations:
wrangler d1 migrations apply pr-tracker --local
```

**Issue: Different schema in local vs production**
```bash
# Check both environments
wrangler d1 migrations list pr-tracker --local
wrangler d1 migrations list pr-tracker --remote

# Apply missing migrations
wrangler d1 migrations apply pr-tracker --local
wrangler d1 migrations apply pr-tracker --remote
```

## Best Practices

### Always Use Parameterized Queries

**Good:**
```python
result = await db.prepare(
    "SELECT * FROM prs WHERE id = ?"
).bind(pr_id).all()
```

**Bad (SQL injection risk):**
```python
result = await db.prepare(
    f"SELECT * FROM prs WHERE id = {pr_id}"
).all()
```

### Convert D1 Results to Python

D1 returns JavaScript proxy objects that need conversion:

```python
# For single row (first())
result = await db.prepare("SELECT * FROM prs WHERE id = ?").bind(pr_id).first()
if result:
    row = result.to_py() if hasattr(result, 'to_py') else dict(result)
    
# For multiple rows (all())
result = await db.prepare("SELECT * FROM prs").all()
data = []
if hasattr(result, 'results'):
    for row in result.results:
        row_dict = row.to_py() if hasattr(row, 'to_py') else dict(row)
        data.append(row_dict)
```

### Handle Errors Gracefully

```python
from database import get_db

try:
    db = get_db(env)
    result = await db.prepare("SELECT * FROM prs").all()
    # Process results...
    return success_response(data)
except Exception as e:
    print(f"Database error: {str(e)}")
    return error_response(f"Database error: {str(e)}", status=500)
```

### Use Migrations, Not Runtime Schema Creation

**Do this:**
```bash
# Create migration file
wrangler d1 migrations create pr-tracker "add_new_column"

# Edit migrations/0004_add_new_column.sql
# ALTER TABLE prs ADD COLUMN new_field TEXT;

# Apply migration
wrangler d1 migrations apply pr-tracker --local
wrangler d1 migrations apply pr-tracker --remote
```

**Don't do this:**
```python
# ❌ Don't create tables at runtime
async def init_schema(env):
    db = get_db(env)
    await db.prepare("CREATE TABLE IF NOT EXISTS...").run()
```

### Test Locally Before Production

Always test database changes locally before applying to production:

1. Create migration file
2. Apply migration locally: `wrangler d1 migrations apply pr-tracker --local`
3. Test with `wrangler dev`
4. Verify data with command line queries
5. Apply to remote: `wrangler d1 migrations apply pr-tracker --remote`
6. Deploy code: `wrangler deploy`

### Whitelist Sort Columns

When building dynamic queries, always validate column names:

```python
# Whitelist allowed columns
allowed_columns = {'created_at', 'updated_at', 'title', 'overall_score'}

sort_by = request.query.get('sort_by', 'created_at')
if sort_by not in allowed_columns:
    sort_by = 'created_at'

# Now safe to use in query
query = f"SELECT * FROM prs ORDER BY {sort_by}"
```

## Limits and Constraints

### D1 Limits

- **Database size:** Up to 100MB per database (free plan), 10GB (paid)
- **Query execution:** 30 seconds max per query
- **Rows per query:** No hard limit, but be reasonable with pagination
- **Concurrent operations:** D1 handles this automatically
- **API calls:** 50,000 reads/day, 100,000 writes/day (free tier)

### SQLite Constraints

- **TEXT max length:** No limit in SQLite (practical limit ~1GB)
- **INTEGER range:** -9223372036854775808 to 9223372036854775807
- **BLOB max size:** 1GB (theoretical), 10MB (practical)

### Application Constraints

We rely on application-level validation rather than database constraints:

```sql
-- No CHECK constraints in our tables
-- Validation happens in Python code before insert/update
```

**Example validation:**
```python
# Validate data before database insert
if not pr_url or not pr_url.startswith('https://github.com/'):
    raise ValueError("Invalid PR URL")

if per_page < 10 or per_page > 1000:
    per_page = 30  # Use default
```

## Performance Tips

### Index Usage

Our indexes are designed for common query patterns:

- **Filtering by repo**: Uses `idx_repo` (repo_owner, repo_name)
- **Sorting by score**: Uses `idx_overall_score`, `idx_ci_score`, etc.
- **Finding merge-ready PRs**: Uses `idx_merge_ready`

### Query Optimization

```python
# Good: Specific columns, indexed where clause
result = await db.prepare(
    "SELECT id, title, overall_score FROM prs WHERE repo_owner = ? ORDER BY overall_score DESC"
).bind(owner).all()

# Avoid: SELECT * without WHERE clause on large tables
result = await db.prepare("SELECT * FROM prs").all()
```

### Caching Strategy

We cache timeline data to reduce GitHub API calls:

```python
# Check cache first
cached_data, timestamp = await load_timeline_from_db(env, owner, repo, pr_number)

if cached_data and (time.time() - timestamp) < 600:  # 10 min cache
    return cached_data

# If cache miss, fetch from GitHub and cache
data = await fetch_from_github(...)
await save_timeline_to_db(env, owner, repo, pr_number, data)
```

## Quick Reference

### NPM Scripts

```bash
# Apply migrations locally
npm run db:migrate:local

# Apply migrations to production
npm run db:migrate:remote

# List migrations
npm run db:migrations:list
```

### Common Commands

```bash
# Check which migrations are applied
wrangler d1 migrations list pr-tracker --local
wrangler d1 migrations list pr-tracker --remote

# Create new migration
wrangler d1 migrations create pr-tracker "description"

# Apply migrations
wrangler d1 migrations apply pr-tracker --local
wrangler d1 migrations apply pr-tracker --remote

# Execute query for debugging
wrangler d1 execute pr-tracker --local --command "SELECT COUNT(*) FROM prs;"

# Reset local database (delete and reapply migrations)
rm -rf .wrangler/state/v3/d1/ && wrangler d1 migrations apply pr-tracker --local
```

## Resources

All information in this guide is based on:

- [Cloudflare D1 Documentation](https://developers.cloudflare.com/d1/)
- [D1 Client API Reference](https://developers.cloudflare.com/d1/client-api/)
- [D1 Migrations Guide](https://developers.cloudflare.com/d1/migrations/)
- [Wrangler D1 Commands](https://developers.cloudflare.com/workers/wrangler/commands/#d1)
- [SQLite SQL Reference](https://www.sqlite.org/lang.html)
- [Python Workers with D1](https://developers.cloudflare.com/workers/languages/python/)

For specific implementation details not covered here, refer to the official Cloudflare D1 documentation.

## Summary

**Key Points:**
- ✅ Database is managed through **migrations only** (no schema.sql)
- ✅ Migrations work identically for `--local` and `--remote`
- ✅ Always test migrations locally before applying to production
- ✅ Use parameterized queries to prevent SQL injection
- ✅ Convert D1 results to Python with `.to_py()` or `dict()`
- ✅ Migrations are tracked automatically - run once and only once
- ✅ All schema changes must be in migration files

**Workflow:**
1. Create migration: `wrangler d1 migrations create pr-tracker "description"`
2. Edit SQL file in `migrations/` folder
3. Test locally: `wrangler d1 migrations apply pr-tracker --local`
4. Verify with `wrangler dev`
5. Apply to prod: `wrangler d1 migrations apply pr-tracker --remote`
6. Deploy code: `wrangler deploy`
