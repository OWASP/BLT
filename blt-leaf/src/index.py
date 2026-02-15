from js import Response, fetch, Headers, URL, Object, Date
from pyodide.ffi import to_js
import json
import re
import asyncio
from datetime import datetime, timezone

# Track if schema initialization has been attempted in this worker instance
# This is safe in Cloudflare Workers Python as each isolate runs single-threaded
_schema_init_attempted = False

# In-memory cache for rate limit data (per worker isolate)
_rate_limit_cache = {
    'data': None,
    'timestamp': 0
}
# Cache TTL in seconds (5 minutes)
_RATE_LIMIT_CACHE_TTL = 300

# Application-level rate limiting for readiness endpoints
# Tracks requests per IP address with sliding window
_readiness_rate_limit = {
    # Structure: {'ip_address': {'count': int, 'window_start': float}}
}
# Rate limit: 10 requests per minute per IP for readiness endpoints
_READINESS_RATE_LIMIT = 10
_READINESS_RATE_WINDOW = 60  # seconds

# In-memory cache for readiness results
# Invalidated when PR is manually refreshed
_readiness_cache = {
    # Structure: {pr_id: {'data': dict, 'timestamp': float}}
}
# Cache TTL in seconds (10 minutes)
_READINESS_CACHE_TTL = 600

# In-memory cache for timeline data
# Reduces redundant API calls across timeline/review-analysis/readiness endpoints
_timeline_cache = {
    # Structure: {cache_key: {'data': dict, 'timestamp': float}}
    # cache_key format: "{owner}/{repo}/{pr_number}"
}
# Cache TTL in seconds (30 minutes - timeline data changes less frequently)
_TIMELINE_CACHE_TTL = 1800

def parse_pr_url(pr_url):
    """
    Parse GitHub PR URL to extract owner, repo, and PR number.
    
    Security Hardening (Issue #45):
    - Type validation to prevent type confusion attacks
    - Anchored regex pattern to block malformed URLs with trailing junk
    - Raises ValueError instead of returning None for better error handling
    """
    # FIX Issue #45: Type validation
    if not isinstance(pr_url, str):
        raise ValueError("PR URL must be a string")
    
    if not pr_url:
        raise ValueError("PR URL is required")
    
    pr_url = pr_url.strip().rstrip('/')
    
    # FIX Issue #45: Anchored regex - must match EXACTLY, no trailing junk allowed
    pattern = r'^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)$'
    match = re.match(pattern, pr_url)
    
    if not match:
        # FIX Issue #45: Raise error instead of returning None
        raise ValueError("Invalid GitHub PR URL. Format: https://github.com/OWNER/REPO/pull/NUMBER")
    
    return {
        'owner': match.group(1),
        'repo': match.group(2),
        'pr_number': int(match.group(3))
    }

def check_rate_limit(ip_address):
    """Check if request from IP is within rate limit for readiness endpoints.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        Tuple of (allowed: bool, retry_after: int)
        - allowed: True if request is allowed, False if rate limited
        - retry_after: Seconds to wait before retrying (0 if allowed)
    """
    global _readiness_rate_limit
    
    current_time = Date.now() / 1000  # Convert milliseconds to seconds
    
    if ip_address not in _readiness_rate_limit:
        _readiness_rate_limit[ip_address] = {
            'count': 1,
            'window_start': current_time
        }
        print(f"Rate limit: New IP {ip_address} - count: 1")
        return (True, 0)
    
    rate_data = _readiness_rate_limit[ip_address]
    window_elapsed = current_time - rate_data['window_start']
    
    # Reset window if expired
    if window_elapsed >= _READINESS_RATE_WINDOW:
        _readiness_rate_limit[ip_address] = {
            'count': 1,
            'window_start': current_time
        }
        print(f"Rate limit: Window reset for {ip_address} - count: 1")
        return (True, 0)
    
    # Check if within limit
    if rate_data['count'] < _READINESS_RATE_LIMIT:
        rate_data['count'] += 1
        print(f"Rate limit: {ip_address} - count: {rate_data['count']}/{_READINESS_RATE_LIMIT}")
        return (True, 0)
    
    # Rate limited - calculate retry_after
    retry_after = int(_READINESS_RATE_WINDOW - window_elapsed) + 1
    print(f"Rate limit: EXCEEDED for {ip_address} - retry after {retry_after}s")
    return (False, retry_after)

async def get_readiness_cache(env, pr_id):
    """Get cached readiness result for a PR if still valid.
    
    First checks in-memory cache, then falls back to database if not found.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        
    Returns:
        Cached data dict if valid, None if expired or not found
    """
    global _readiness_cache
    
    # Check in-memory cache first
    if pr_id in _readiness_cache:
        cache_entry = _readiness_cache[pr_id]
        current_time = Date.now() / 1000
        
        # Check if cache is still valid
        if (current_time - cache_entry['timestamp']) < _READINESS_CACHE_TTL:
            age = int(current_time - cache_entry['timestamp'])
            print(f"Cache: HIT (memory) for PR {pr_id} (age: {age}s)")
            return cache_entry['data']
        
        # Cache expired - remove it
        del _readiness_cache[pr_id]
        print(f"Cache: MISS (memory expired) for PR {pr_id}")
    else:
        print(f"Cache: MISS (memory) for PR {pr_id}")
    
    # Fall back to database
    db_data = await load_readiness_from_db(env, pr_id)
    if db_data:
        # Store in memory cache for faster subsequent access
        current_time = Date.now() / 1000
        _readiness_cache[pr_id] = {
            'data': db_data,
            'timestamp': current_time
        }
        print(f"Cache: HIT (database) for PR {pr_id} - loaded into memory")
        return db_data
    
    print(f"Cache: MISS (database) for PR {pr_id}")
    return None

async def set_readiness_cache(env, pr_id, data):
    """Cache readiness result for a PR in both memory and database.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        data: Readiness data to cache
    """
    global _readiness_cache
    
    # Store in memory cache
    current_time = Date.now() / 1000
    _readiness_cache[pr_id] = {
        'data': data,
        'timestamp': current_time
    }
    print(f"Cache: Stored result (memory) for PR {pr_id}")
    
    # Also save to database for persistence
    await save_readiness_to_db(env, pr_id, data)

async def invalidate_readiness_cache(env, pr_id):
    """Invalidate cached readiness result for a PR in both memory and database.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
    """
    global _readiness_cache
    
    # Remove from memory cache
    if pr_id in _readiness_cache:
        del _readiness_cache[pr_id]
        print(f"Cache: Invalidated (memory) for PR {pr_id}")
    
    # Also remove from database
    await delete_readiness_from_db(env, pr_id)

async def save_readiness_to_db(env, pr_id, readiness_data):
    """Save readiness analysis results to database in the prs table.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        readiness_data: Dictionary containing readiness analysis results
    """
    try:
        db = get_db(env)
        
        # Extract data from the response structure
        readiness = readiness_data.get('readiness', {})
        review_health = readiness_data.get('review_health', {})
        
        # Convert lists to JSON strings for storage
        blockers_json = json.dumps(readiness.get('blockers', []))
        warnings_json = json.dumps(readiness.get('warnings', []))
        recommendations_json = json.dumps(readiness.get('recommendations', []))
        
        # Update the existing PR row with readiness data
        stmt = db.prepare('''
            UPDATE prs SET
                overall_score = ?,
                ci_score = ?,
                review_score = ?,
                classification = ?,
                merge_ready = ?,
                blockers = ?,
                warnings = ?,
                recommendations = ?,
                review_health_classification = ?,
                review_health_score = ?,
                response_rate = ?,
                total_feedback = ?,
                responded_feedback = ?,
                readiness_computed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''')
        
        await stmt.bind(
            readiness.get('overall_score'),
            readiness.get('ci_score'),
            readiness.get('review_score'),
            readiness.get('classification'),
            1 if readiness.get('merge_ready') else 0,
            blockers_json,
            warnings_json,
            recommendations_json,
            review_health.get('classification'),
            review_health.get('score'),
            review_health.get('response_rate'),
            review_health.get('total_feedback'),
            review_health.get('responded_feedback'),
            pr_id
        ).run()
        
        print(f"Database: Saved readiness data for PR {pr_id}")
    except Exception as e:
        print(f"Error saving readiness to database for PR {pr_id}: {str(e)}")
        # Don't raise - we can continue with in-memory cache only

async def load_readiness_from_db(env, pr_id):
    """Load readiness analysis results from database (prs table).
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        
    Returns:
        Dictionary with complete response data including PR info and readiness, or None if not found
    """
    try:
        db = get_db(env)
        
        # Load PR data with readiness fields - explicitly select needed columns
        stmt = db.prepare('''
            SELECT id, title, author_login, repo_owner, repo_name, pr_number, 
                   state, is_merged, mergeable_state, files_changed,
                   checks_passed, checks_failed, checks_skipped,
                   overall_score, ci_score, review_score, classification, 
                   merge_ready, blockers, warnings, recommendations,
                   review_health_classification, review_health_score, 
                   response_rate, total_feedback, responded_feedback,
                   readiness_computed_at
            FROM prs WHERE id = ?
        ''')
        result = await stmt.bind(pr_id).first()
        
        if not result:
            print(f"Database: PR {pr_id} not found")
            return None
        
        # Convert result to Python dict
        pr = result.to_py() if hasattr(result, 'to_py') else dict(result)
        
        # Check if readiness data exists (overall_score will be None if never computed)
        if pr.get('overall_score') is None:
            print(f"Database: No readiness data found for PR {pr_id}")
            return None
        
        # Parse JSON strings back to lists - with error handling
        try:
            blockers = json.loads(pr.get('blockers', '[]'))
        except Exception as e:
            print(f"Failed to parse blockers JSON for PR {pr_id}: {str(e)}")
            return None
        
        try:
            warnings = json.loads(pr.get('warnings', '[]'))
        except Exception as e:
            print(f"Failed to parse warnings JSON for PR {pr_id}: {str(e)}")
            return None
        
        try:
            recommendations = json.loads(pr.get('recommendations', '[]'))
        except Exception as e:
            print(f"Failed to parse recommendations JSON for PR {pr_id}: {str(e)}")
            return None
        
        # Get numeric values for display formatting
        overall_score = pr.get('overall_score', 0)
        ci_score = pr.get('ci_score', 0)
        review_score = pr.get('review_score', 0)
        response_rate = pr.get('response_rate', 0.0)
        
        # Reconstruct the complete response structure with PR info and display fields
        readiness_data = {
            'pr': {
                'id': pr['id'],
                'title': pr.get('title'),
                'author': pr.get('author_login'),
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number'],
                'state': pr.get('state'),
                'is_merged': pr.get('is_merged') == 1,
                'mergeable_state': pr.get('mergeable_state'),
                'files_changed': pr.get('files_changed')
            },
            'readiness': {
                'overall_score': overall_score,
                'overall_score_display': f"{overall_score}%",
                'ci_score': ci_score,
                'ci_score_display': f"{ci_score}%",
                'review_score': review_score,
                'review_score_display': f"{review_score}%",
                'classification': row.get('classification'),
                'merge_ready': bool(row.get('merge_ready')),
                'blockers': blockers,
                'warnings': warnings,
                'recommendations': recommendations
            },
            'review_health': {
                'classification': pr.get('review_health_classification'),
                'score': pr.get('review_health_score'),
                'score_display': f"{pr.get('review_health_score', 0)}%",
                'response_rate': response_rate,
                'response_rate_display': f"{int(response_rate * 100)}%",
                'total_feedback': pr.get('total_feedback'),
                'responded_feedback': pr.get('responded_feedback')
            },
            'ci_checks': {
                'passed': pr.get('checks_passed'),
                'failed': pr.get('checks_failed'),
                'skipped': pr.get('checks_skipped')
            }
        }
        
        print(f"Database: Loaded readiness data for PR {pr_id}")
        return readiness_data
    except Exception as e:
        print(f"Error loading readiness from database for PR {pr_id}: {str(e)}")
        return None

async def delete_readiness_from_db(env, pr_id):
    """Clear readiness analysis results from database (prs table).
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
    """
    try:
        db = get_db(env)
        
        # Clear readiness fields in the prs table
        stmt = db.prepare('''
            UPDATE prs SET
                overall_score = NULL,
                ci_score = NULL,
                review_score = NULL,
                classification = NULL,
                merge_ready = NULL,
                blockers = NULL,
                warnings = NULL,
                recommendations = NULL,
                review_health_classification = NULL,
                review_health_score = NULL,
                response_rate = NULL,
                total_feedback = NULL,
                responded_feedback = NULL,
                readiness_computed_at = NULL
            WHERE id = ?
        ''')
        await stmt.bind(pr_id).run()
        
        print(f"Database: Cleared readiness data for PR {pr_id}")
    except Exception as e:
        print(f"Error clearing readiness from database for PR {pr_id}: {str(e)}")
        # Don't raise - cache invalidation is already done

def get_timeline_cache_key(owner, repo, pr_number):
    """Generate cache key for timeline data"""
    return f"{owner}/{repo}/{pr_number}"

def get_timeline_cache(owner, repo, pr_number):
    """Get cached timeline data if still valid.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        
    Returns:
        Cached timeline data dict if valid, None if expired or not found
    """
    global _timeline_cache
    
    cache_key = get_timeline_cache_key(owner, repo, pr_number)
    
    if cache_key in _timeline_cache:
        cache_entry = _timeline_cache[cache_key]
        current_time = Date.now() / 1000
        
        # Check if cache is still valid
        if (current_time - cache_entry['timestamp']) < _TIMELINE_CACHE_TTL:
            age = int(current_time - cache_entry['timestamp'])
            print(f"Timeline Cache: HIT for {cache_key} (age: {age}s)")
            return cache_entry['data']
        
        # Cache expired - remove it
        del _timeline_cache[cache_key]
        print(f"Timeline Cache: MISS (expired) for {cache_key}")
    else:
        print(f"Timeline Cache: MISS for {cache_key}")
    
    return None

def set_timeline_cache(owner, repo, pr_number, data):
    """Cache timeline data.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        data: Timeline data to cache
    """
    global _timeline_cache
    
    cache_key = get_timeline_cache_key(owner, repo, pr_number)
    current_time = Date.now() / 1000
    
    _timeline_cache[cache_key] = {
        'data': data,
        'timestamp': current_time
    }
    print(f"Timeline Cache: Stored for {cache_key}")

def invalidate_timeline_cache(owner, repo, pr_number):
    """Invalidate cached timeline data for a PR.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
    """
    global _timeline_cache
    
    cache_key = get_timeline_cache_key(owner, repo, pr_number)
    
    if cache_key in _timeline_cache:
        del _timeline_cache[cache_key]
        print(f"Timeline Cache: Invalidated for {cache_key}")

def parse_repo_url(url):
    """Parse GitHub Repo URL to extract owner and repo name"""
    if not url: return None
    url = url.strip().rstrip('/')
    pattern = r'https?://github\.com/([^/]+)/([^/]+)(?:/.*)?$'
    match = re.match(pattern, url)
    if match:
        return {
            'owner': match.group(1),
            'repo': match.group(2)
        }
    return None

def get_db(env):
    """Helper to get DB binding from env, handling different env types.
    
    Raises an exception if database is not configured.
    """
    # Try common binding names
    for name in ['pr_tracker', 'DB']:
        # Try attribute access
        if hasattr(env, name):
            return getattr(env, name)
        # Try dict access
        if hasattr(env, '__getitem__'):
            try:
                return env[name]
            except (KeyError, TypeError):
                pass
    
    # Database not configured - raise error
    print(f"DEBUG: env attributes: {dir(env)}")
    raise Exception("Database binding 'pr_tracker' or 'DB' not found in env. Please configure a D1 database.")

async def init_database_schema(env):
    """Initialize database schema if it doesn't exist.
    
    This function is idempotent and safe to call multiple times.
    Uses CREATE TABLE IF NOT EXISTS to avoid errors on existing tables.
    Includes migration logic to add missing columns to existing tables.
    A module-level flag prevents redundant calls within the same worker instance.
    """
    global _schema_init_attempted
    
    # Skip if already attempted in this worker instance
    if _schema_init_attempted:
        return
    
    _schema_init_attempted = True
    
    try:
        db = get_db(env)
        
        # Create the prs table (idempotent with IF NOT EXISTS)
        create_table = db.prepare('''
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
                checks_passed INTEGER DEFAULT 0,
                checks_failed INTEGER DEFAULT 0,
                checks_skipped INTEGER DEFAULT 0,
                review_status TEXT,
                last_updated_at TEXT,
                last_refreshed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                overall_score INTEGER,
                ci_score INTEGER,
                review_score INTEGER,
                classification TEXT,
                merge_ready INTEGER DEFAULT 0,
                blockers TEXT,
                warnings TEXT,
                recommendations TEXT,
                review_health_classification TEXT,
                review_health_score INTEGER,
                response_rate REAL,
                total_feedback INTEGER,
                responded_feedback INTEGER,
                readiness_computed_at TEXT
            )
        ''')
        await create_table.run()
        
        # Migration: Add columns if they don't exist
        # Check if columns exist by querying PRAGMA table_info
        try:
            pragma_result = db.prepare('PRAGMA table_info(prs)')
            columns_result = await pragma_result.all()
            columns = columns_result.results.to_py() if hasattr(columns_result, 'results') else []
            
            column_names = [col['name'] for col in columns if isinstance(col, dict)]
            
            # List of new columns to add for readiness data
            # SECURITY: These are hardcoded and validated - safe for f-string SQL construction
            new_columns = [
                ('last_refreshed_at', 'TEXT'),
                ('overall_score', 'INTEGER'),
                ('ci_score', 'INTEGER'),
                ('review_score', 'INTEGER'),
                ('classification', 'TEXT'),
                ('merge_ready', 'INTEGER DEFAULT 0'),
                ('blockers', 'TEXT'),
                ('warnings', 'TEXT'),
                ('recommendations', 'TEXT'),
                ('review_health_classification', 'TEXT'),
                ('review_health_score', 'INTEGER'),
                ('response_rate', 'REAL'),
                ('total_feedback', 'INTEGER'),
                ('responded_feedback', 'INTEGER'),
                ('readiness_computed_at', 'TEXT')
            ]
            
            # Whitelist of allowed column names for security
            allowed_columns = {name for name, _ in new_columns}
            
            for col_name, col_type in new_columns:
                if col_name not in column_names:
                    # Double-check column name is in whitelist before using in SQL
                    if col_name not in allowed_columns:
                        print(f"Security: Skipping unauthorized column {col_name}")
                        continue
                    print(f"Migrating database: Adding {col_name} column")
                    alter_table = db.prepare(f'ALTER TABLE prs ADD COLUMN {col_name} {col_type}')
                    await alter_table.run()
        except Exception as migration_error:
            # Column may already exist or migration failed - log but continue
            print(f"Note: Migration check: {str(migration_error)}")
        
        # Create indexes (idempotent with IF NOT EXISTS)
        index1 = db.prepare('CREATE INDEX IF NOT EXISTS idx_repo ON prs(repo_owner, repo_name)')
        await index1.run()
        
        index2 = db.prepare('CREATE INDEX IF NOT EXISTS idx_pr_number ON prs(pr_number)')
        await index2.run()
        
    except Exception as e:
        # Log the error but don't crash - schema may already exist
        print(f"Note: Schema initialization check: {str(e)}")
        # Schema likely already exists, which is fine

async def fetch_with_headers(url, headers=None, token=None):
    """Helper to fetch with proper header handling using pyodide.ffi.to_js"""
    if not headers:
        headers = {}
        
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'PR-Tracker/1.0'        
    if token:
        headers['Authorization'] = f'Bearer {token}'

    options = to_js({
        "method": "GET",
        "headers": headers
    }, dict_converter=Object.fromEntries)
    return await fetch(url, options)

async def fetch_pr_data(owner, repo, pr_number, token=None):
    """Fetch PR data from GitHub API with parallel requests for optimal performance"""
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
        
    try:
        # Fetch PR details first (needed for head SHA)
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_response = await fetch_with_headers(pr_url, headers, token)
        
        if pr_response.status != 200:
            return None
            
        pr_data = (await pr_response.json()).to_py()

        # Prepare URLs for parallel fetching
        files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        reviews_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        checks_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{pr_data['head']['sha']}/check-runs"
        
        # Fetch files, reviews, and checks in parallel using asyncio.gather
        # This reduces total fetch time from sequential sum to max single request time
        files_data = []
        reviews_data = []
        checks_data = {}
        
        try:
            results = await asyncio.gather(
                fetch_with_headers(files_url, headers, token),
                fetch_with_headers(reviews_url, headers, token),
                fetch_with_headers(checks_url, headers, token),
                return_exceptions=True
            )
            
            # Process files result
            if not isinstance(results[0], Exception) and results[0].status == 200:
                files_data = (await results[0].json()).to_py()
            
            # Process reviews result
            if not isinstance(results[1], Exception) and results[1].status == 200:
                reviews_data = (await results[1].json()).to_py()
            
            # Process checks result
            if not isinstance(results[2], Exception) and results[2].status == 200:
                checks_data = (await results[2].json()).to_py()
        except: pass
        
        # Process check runs
        checks_passed = 0
        checks_failed = 0
        checks_skipped = 0
        
        if 'check_runs' in checks_data:
            for check in checks_data['check_runs']:
                if check['conclusion'] == 'success':
                    checks_passed += 1
                elif check['conclusion'] in ['failure', 'timed_out', 'cancelled']:
                    checks_failed += 1
                elif check['conclusion'] in ['skipped', 'neutral']:
                    checks_skipped += 1
        
        # Determine review status - sort by submitted_at to get latest reviews
        review_status = 'pending'
        if reviews_data:
            # Sort reviews by submitted_at to get chronological order
            sorted_reviews = sorted(reviews_data, key=lambda x: x.get('submitted_at', ''))
            latest_reviews = {}
            for review in sorted_reviews:
                user = review['user']['login']
                latest_reviews[user] = review['state']

            # Determine overall status: changes_requested takes precedence over approved
            if 'CHANGES_REQUESTED' in latest_reviews.values():
                review_status = 'changes_requested'
            elif 'APPROVED' in latest_reviews.values():
                review_status = 'approved'
        
        return {
            'title': pr_data.get('title', ''),
            'state': pr_data.get('state', ''),
            'is_merged': 1 if pr_data.get('merged', False) else 0,
            'mergeable_state': pr_data.get('mergeable_state', ''),
            'files_changed': len(files_data), 
            'author_login': pr_data['user']['login'],
            'author_avatar': pr_data['user']['avatar_url'],
            'checks_passed': checks_passed,
            'checks_failed': checks_failed,
            'checks_skipped': checks_skipped,
            'review_status': review_status,
            'last_updated_at': pr_data.get('updated_at', '')
        }
    except Exception as e:
        # Return more informative error for debugging
        error_msg = f"Error fetching PR data: {str(e)}"
        # In Cloudflare Workers, console.error is preferred
        raise Exception(error_msg)

async def fetch_paginated_data(url, headers):
    """
    Fetch all pages of data from a GitHub API endpoint following Link headers
    
    Args:
        url: Initial URL to fetch
        headers: Headers object to use for requests
    
    Returns:
        List of all items across all pages
    """
    all_data = []
    current_url = url
    fetch_options = to_js({'headers': headers}, dict_converter=Object.fromEntries)
    
    while current_url:
        response = await fetch(current_url, fetch_options)
        
        if not response.ok:
            status = getattr(response, 'status', 'unknown')
            status_text = getattr(response, 'statusText', '')
            raise Exception(
                f"GitHub API error: status={status} {status_text} url={current_url}"
            )
        
        page_data = (await response.json()).to_py()
        all_data.extend(page_data)
        
        # Check for Link header to get next page
        link_header = response.headers.get('link')
        current_url = None
        
        if link_header:
            # Parse Link header: <url>; rel="next", <url>; rel="last"
            links = link_header.split(',')
            for link in links:
                if 'rel="next"' in link:
                    # Extract URL from <url>
                    url_match = link.split(';')[0].strip()
                    if url_match.startswith('<') and url_match.endswith('>'):
                        current_url = url_match[1:-1]
                    break
    
    return all_data

async def fetch_pr_timeline_data(owner, repo, pr_number, github_token=None):
    """
    Fetch all timeline data for a PR: commits, reviews, review comments, issue comments
    
    Uses in-memory caching (30 min TTL) to avoid redundant API calls across endpoints.
    
    Returns dict with raw data from GitHub API:
    {
        'commits': [...],
        'reviews': [...],
        'review_comments': [...],
        'issue_comments': [...]
    }
    """
    # Check cache first
    cached_data = get_timeline_cache(owner, repo, pr_number)
    if cached_data:
        return cached_data
    
    base_url = 'https://api.github.com'
    
    # Prepare headers
    headers_dict = {
        'User-Agent': 'PR-Tracker/1.0',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    if github_token:
        headers_dict['Authorization'] = f'Bearer {github_token}'
    
    headers = Headers.new(to_js(headers_dict, dict_converter=Object.fromEntries))
    
    try:
        # Fetch all timeline data in parallel (with pagination)
        commits_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/commits?per_page=100'
        reviews_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews?per_page=100'
        review_comments_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments?per_page=100'
        issue_comments_url = f'{base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments?per_page=100'
        
        # Make truly parallel requests using asyncio.gather
        commits_data, reviews_data, review_comments_data, issue_comments_data = await asyncio.gather(
            fetch_paginated_data(commits_url, headers),
            fetch_paginated_data(reviews_url, headers),
            fetch_paginated_data(review_comments_url, headers),
            fetch_paginated_data(issue_comments_url, headers)
        )
        
        timeline_data = {
            'commits': commits_data,
            'reviews': reviews_data,
            'review_comments': review_comments_data,
            'issue_comments': issue_comments_data
        }
        
        # Cache the result for future requests
        set_timeline_cache(owner, repo, pr_number, timeline_data)
        
        return timeline_data
    except Exception as e:
        raise Exception(f"Error fetching timeline data: {str(e)}")

def parse_github_timestamp(timestamp_str):
    """Parse GitHub ISO 8601 timestamp to datetime object"""
    try:
        # GitHub timestamps are in format: 2024-01-15T10:30:45Z
        return datetime.strptime(timestamp_str.replace('Z', '+00:00'), '%Y-%m-%dT%H:%M:%S%z')
    except Exception as exc:
        # Raise error instead of silently using current time to avoid incorrect event ordering
        raise ValueError(f"Invalid GitHub timestamp: {timestamp_str!r}") from exc

def build_pr_timeline(timeline_data):
    """
    Build unified chronological timeline from PR events
    
    Args:
        timeline_data: Dict with commits, reviews, review_comments, issue_comments
    
    Returns:
        List of event dicts sorted by timestamp:
        {
            'type': 'commit' | 'review' | 'review_comment' | 'issue_comment',
            'timestamp': datetime object,
            'author': str,
            'data': dict with event-specific data
        }
    """
    events = []
    
    # Process commits
    for commit in timeline_data.get('commits', []):
        try:
            commit_data = commit.get('commit', {})
            author_data = commit_data.get('author', {})
            
            events.append({
                'type': 'commit',
                'timestamp': parse_github_timestamp(author_data.get('date', '')),
                'author': commit.get('author', {}).get('login', author_data.get('name', 'Unknown')),
                'data': {
                    'sha': commit.get('sha', '')[:7],
                    'message': commit_data.get('message', '').split('\n')[0]  # First line only
                }
            })
        except Exception:
            continue  # Skip malformed commits
    
    # Process reviews
    for review in timeline_data.get('reviews', []):
        try:
            # Skip pending reviews
            if review.get('state') == 'PENDING':
                continue
            
            events.append({
                'type': 'review',
                'timestamp': parse_github_timestamp(review.get('submitted_at', '')),
                'author': review.get('user', {}).get('login', 'Unknown'),
                'data': {
                    'state': review.get('state', ''),  # APPROVED, CHANGES_REQUESTED, COMMENTED
                    'body': review.get('body', '')
                }
            })
        except Exception:
            continue
    
    # Process review comments (inline code comments)
    for comment in timeline_data.get('review_comments', []):
        try:
            events.append({
                'type': 'review_comment',
                'timestamp': parse_github_timestamp(comment.get('created_at', '')),
                'author': comment.get('user', {}).get('login', 'Unknown'),
                'data': {
                    'body': comment.get('body', ''),
                    'path': comment.get('path', ''),
                    'in_reply_to': comment.get('in_reply_to_id')
                }
            })
        except Exception:
            continue
    
    # Process issue comments (general PR comments)
    for comment in timeline_data.get('issue_comments', []):
        try:
            events.append({
                'type': 'issue_comment',
                'timestamp': parse_github_timestamp(comment.get('created_at', '')),
                'author': comment.get('user', {}).get('login', 'Unknown'),
                'data': {
                    'body': comment.get('body', '')
                }
            })
        except Exception:
            continue
    
    # Sort all events by timestamp
    events.sort(key=lambda x: x['timestamp'])
    
    return events

def analyze_review_progress(timeline, pr_author):
    """
    Analyze review feedback loops and author responsiveness
    
    Args:
        timeline: List of timeline events from build_pr_timeline()
        pr_author: GitHub login of PR author
    
    Returns:
        Dict with:
        {
            'feedback_loops': List of feedback/response pairs,
            'total_feedback_count': int,
            'responded_count': int,
            'response_rate': float (0-1),
            'awaiting_author': bool,
            'awaiting_reviewer': bool,
            'stale_feedback': List of unaddressed feedback,
            'latest_review_state': str or None,
            'last_reviewer_action': datetime or None,
            'last_author_action': datetime or None
        }
    """
    feedback_loops = []
    latest_review_state = None
    last_reviewer_action = None
    last_author_action = None
    
    # Iterate through timeline to detect feedback patterns
    for event in timeline:
        author = event['author']
        timestamp = event['timestamp']
        event_type = event['type']
        
        # Track reviewer actions (reviews and comments from non-authors)
        if event_type in ['review', 'review_comment'] and author != pr_author:
            last_reviewer_action = timestamp
            
            # Update latest review state
            if event_type == 'review':
                latest_review_state = event['data'].get('state', '')
            
            # Create feedback loop entry
            feedback_loops.append({
                'reviewer': author,
                'feedback_time': timestamp,
                'feedback_type': event_type,
                'author_responded': False,
                'response_time': None,
                'response_type': None,
                'response_delay_hours': None
            })
        
        # Track author actions (commits and comments from author)
        elif author == pr_author and event_type in ['commit', 'issue_comment', 'review_comment']:
            last_author_action = timestamp
            
            # Check if this responds to pending feedback
            # Match to the most recent unresponded feedback
            for loop in reversed(feedback_loops):
                if not loop['author_responded'] and loop['feedback_time'] < timestamp:
                    loop['author_responded'] = True
                    loop['response_time'] = timestamp
                    loop['response_type'] = event_type
                    
                    # Calculate delay in hours
                    delay = (timestamp - loop['feedback_time']).total_seconds() / 3600
                    loop['response_delay_hours'] = round(delay, 1)
                    break
    
    # Calculate response metrics
    total_feedback = len(feedback_loops)
    responded_count = sum(1 for loop in feedback_loops if loop['author_responded'])
    response_rate = responded_count / total_feedback if total_feedback > 0 else 1.0
    
    # Determine current state
    awaiting_author = (
        latest_review_state == 'CHANGES_REQUESTED' or
        (last_reviewer_action and 
         (not last_author_action or last_reviewer_action > last_author_action))
    )
    
    awaiting_reviewer = (
        not awaiting_author and
        last_author_action and
        (not last_reviewer_action or last_author_action > last_reviewer_action)
    )
    
    # Find stale feedback (older than 3 days without response)
    now = datetime.now(timezone.utc)
    stale_threshold_hours = 72  # 3 days
    
    stale_feedback = []
    for loop in feedback_loops:
        if not loop['author_responded']:
            hours_old = (now - loop['feedback_time']).total_seconds() / 3600
            if hours_old > stale_threshold_hours:
                stale_feedback.append({
                    'reviewer': loop['reviewer'],
                    'feedback_type': loop['feedback_type'],
                    'days_old': round(hours_old / 24, 1)
                })
    
    return {
        'feedback_loops': feedback_loops,
        'total_feedback_count': total_feedback,
        'responded_count': responded_count,
        'response_rate': response_rate,
        'awaiting_author': awaiting_author,
        'awaiting_reviewer': awaiting_reviewer,
        'stale_feedback': stale_feedback,
        'latest_review_state': latest_review_state,
        'last_reviewer_action': last_reviewer_action.isoformat() if last_reviewer_action else None,
        'last_author_action': last_author_action.isoformat() if last_author_action else None
    }

def classify_review_health(review_data):
    """
    Classify review health and assign score (0-100)
    
    Args:
        review_data: Output from analyze_review_progress()
    
    Returns:
        Tuple of (classification: str, score: int)
        
        Classifications:
        - APPROVED: 90-100 - Reviews approved
        - ACTIVE: 70-85 - Good progress, responsive
        - AWAITING_REVIEWER: 60-80 - Waiting on reviewers
        - AWAITING_AUTHOR: 35-55 - Needs author response
        - STALLED: 10-30 - No activity or unaddressed feedback
        - NO_ACTIVITY: 50 - No reviews or feedback yet
    """
    response_rate = review_data['response_rate']
    stale_count = len(review_data['stale_feedback'])
    awaiting_author = review_data['awaiting_author']
    awaiting_reviewer = review_data['awaiting_reviewer']
    latest_state = review_data['latest_review_state']
    total_feedback = review_data['total_feedback_count']
    
    # No feedback yet
    if total_feedback == 0:
        return ('NO_ACTIVITY', 50)
    
    # Approved state
    if latest_state == 'APPROVED':
        return ('APPROVED', 95)
    
    # Stalled (has stale feedback)
    if stale_count > 0:
        # More stale feedback = lower score
        score = max(10, 50 - (stale_count * 15))
        return ('STALLED', score)
    
    # Awaiting author with poor response rate
    if awaiting_author and response_rate < 0.5:
        return ('AWAITING_AUTHOR', 35)
    
    # Awaiting author with good response rate
    if awaiting_author:
        return ('AWAITING_AUTHOR', 55)
    
    # Awaiting reviewer
    if awaiting_reviewer:
        # Higher score if author has been responsive
        score = 70 + int(response_rate * 10)
        return ('AWAITING_REVIEWER', min(score, 80))
    
    # Active (good back and forth)
    if response_rate > 0.7:
        return ('ACTIVE', 85)
    
    # Default active state
    return ('ACTIVE', 70)

def calculate_ci_confidence(checks_passed, checks_failed, checks_skipped):
    """
    Calculate CI confidence score from check results
    
    Args:
        checks_passed: Number of passing checks
        checks_failed: Number of failing checks
        checks_skipped: Number of skipped checks
    
    Returns:
        int: Confidence score 0-100
    """
    total_checks = checks_passed + checks_failed + checks_skipped
    
    # No checks = neutral score
    if total_checks == 0:
        return 50
    
    # All failed = 0
    if checks_passed == 0 and checks_failed > 0:
        return 0
    
    # All passed = 100
    if checks_failed == 0 and checks_passed > 0:
        return 100
    
    # Calculate based on pass rate, penalize failures more than skipped
    pass_rate = checks_passed / total_checks
    fail_rate = checks_failed / total_checks
    skip_rate = checks_skipped / total_checks
    
    # Weighted score: passes add, failures subtract (reduced for flaky test tolerance), skips slightly reduce
    score = (pass_rate * 100) - (fail_rate * 50) - (skip_rate * 20)
    
    return max(0, min(100, int(score)))

def calculate_pr_readiness(pr_data, review_classification, review_score):
    """
    Calculate overall PR readiness combining CI and review health
    
    Args:
        pr_data: Dict with PR info including CI checks
        review_classification: str from classify_review_health
        review_score: int from classify_review_health
    
    Returns:
        Dict with:
        {
            'overall_score': int 0-100,
            'ci_score': int 0-100,
            'review_score': int 0-100,
            'classification': str,
            'merge_ready': bool,
            'blockers': List[str],
            'warnings': List[str],
            'recommendations': List[str]
        }
    """
    # Calculate CI score
    ci_score = calculate_ci_confidence(
        pr_data.get('checks_passed', 0),
        pr_data.get('checks_failed', 0),
        pr_data.get('checks_skipped', 0)
    )
    
    # Weighted combination: 45% CI, 55% Review (reduced CI weight due to flaky tests)
    overall_score = int((ci_score * 0.45) + (review_score * 0.55))
    
    # Identify blockers, warnings, recommendations
    blockers = []
    warnings = []
    recommendations = []
    
    # CI blockers (with tolerance for 1-2 flaky test failures)
    checks_failed = pr_data.get('checks_failed', 0)
    checks_skipped = pr_data.get('checks_skipped', 0)
    
    if checks_failed > 2:
        blockers.append(f"{checks_failed} CI check(s) failing")
        recommendations.append("Fix failing CI checks before merging")
    elif checks_failed > 0:
        warnings.append(f"{checks_failed} CI check(s) failing (possibly flaky tests)")
        recommendations.append("Verify if failures are from known flaky tests (Selenium, Docker)")
    
    if checks_skipped > 0:
        warnings.append(f"{checks_skipped} CI check(s) skipped")
    
    # Review blockers
    if review_classification == 'AWAITING_AUTHOR':
        blockers.append("Awaiting author response to feedback")
        recommendations.append("Address reviewer comments and push updates")
    
    if review_classification == 'STALLED':
        blockers.append("PR has stale unaddressed feedback")
        recommendations.append("Review and respond to old comments")
    
    if review_classification == 'NO_ACTIVITY':
        warnings.append("No review activity yet")
        recommendations.append("Request reviews from maintainers")
    
    if review_classification == 'AWAITING_REVIEWER':
        warnings.append("Awaiting reviewer approval")
        recommendations.append("Ping reviewers or request re-review")
    
    # PR state warnings
    if pr_data.get('state') == 'closed':
        blockers.append("PR is closed")
    
    if pr_data.get('is_merged') == 1:
        blockers.append("PR is already merged")
    
    mergeable_state = pr_data.get('mergeable_state', '')
    if mergeable_state == 'dirty':
        blockers.append("PR has merge conflicts")
        recommendations.append("Resolve merge conflicts with base branch")
    elif mergeable_state == 'blocked':
        warnings.append("PR is blocked by required status checks or reviews")
    
    # File change warnings
    files_changed = pr_data.get('files_changed', 0)
    if files_changed > 30:
        warnings.append(f"Large PR ({files_changed} files changed)")
        recommendations.append("Consider splitting into smaller PRs for easier review")
    
    # Determine if merge ready
    merge_ready = (
        overall_score >= 70 and
        len(blockers) == 0 and
        review_classification in ['APPROVED', 'AWAITING_REVIEWER', 'ACTIVE']
    )
    
    # Overall classification
    if merge_ready:
        classification = 'READY_TO_MERGE'
    elif overall_score >= 60:
        classification = 'NEARLY_READY'
    elif overall_score >= 40:
        classification = 'NEEDS_WORK'
    else:
        classification = 'NOT_READY'
    
    return {
        'overall_score': overall_score,
        'ci_score': ci_score,
        'review_score': review_score,
        'classification': classification,
        'merge_ready': merge_ready,
        'blockers': blockers,
        'warnings': warnings,
        'recommendations': recommendations
    }

async def upsert_pr(db, pr_url, owner, repo, pr_number, pr_data):
    """Helper to insert or update PR in database (Deduplicates logic)"""
    current_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    stmt = db.prepare('''
        INSERT INTO prs (pr_url, repo_owner, repo_name, pr_number, title, state, 
                       is_merged, mergeable_state, files_changed, author_login, 
                       author_avatar, checks_passed, checks_failed, checks_skipped, 
                       review_status, last_updated_at, last_refreshed_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(pr_url) DO UPDATE SET
            title = excluded.title,
            state = excluded.state,
            is_merged = excluded.is_merged,
            mergeable_state = excluded.mergeable_state,
            files_changed = excluded.files_changed,
            checks_passed = excluded.checks_passed,
            checks_failed = excluded.checks_failed,
            checks_skipped = excluded.checks_skipped,
            review_status = excluded.review_status,
            last_updated_at = excluded.last_updated_at,
            last_refreshed_at = excluded.last_refreshed_at,
            updated_at = excluded.updated_at
    ''').bind(
        pr_url, owner, repo, pr_number,
        pr_data['title'], 
        pr_data['state'],
        pr_data['is_merged'],
        pr_data['mergeable_state'], 
        pr_data['files_changed'],
        pr_data['author_login'], 
        pr_data['author_avatar'],
        pr_data['checks_passed'], 
        pr_data['checks_failed'],
        pr_data['checks_skipped'], 
        pr_data['review_status'],
        pr_data['last_updated_at'], current_timestamp, current_timestamp
    )
    await stmt.run()

async def handle_add_pr(request, env):
    """
    Handle adding a new PR or importing all PRs from a repo.
    
    Security Hardening (Issue #45):
    - Malformed JSON error handling
    - Type validation for pr_url parameter
    - Proper error handling for parse_pr_url ValueError
    """
    try:
        # Handle malformed JSON gracefully
        try:
            data = (await request.json()).to_py()
        except Exception:
            return Response.new(
                json.dumps({'error': 'Malformed JSON payload'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        pr_url = data.get('pr_url')
        add_all = data.get('add_all', False)
        # Capture token from header
        user_token = request.headers.get('x-github-token')
        
        # Type validation for pr_url
        if not pr_url or not isinstance(pr_url, str):
            return Response.new(
                json.dumps({'error': 'A valid GitHub PR URL is required'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        db = get_db(env)
        
        if add_all:
            # Add all prs (in bulk)
            parsed = parse_repo_url(pr_url)
            if not parsed:
                return Response.new(json.dumps({'error': 'Invalid GitHub Repository URL'}), 
                                  {'status': 400, 'headers': {'Content-Type': 'application/json'}})
            
            owner, repo = parsed['owner'], parsed['repo']
            
            # Prepare headers for paginated fetching
            headers_dict = {
                'User-Agent': 'PR-Tracker/1.0',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            if user_token:
                headers_dict['Authorization'] = f'Bearer {user_token}'
            
            headers = Headers.new(to_js(headers_dict, dict_converter=Object.fromEntries))
            
            # Fetch all open PRs for the repo using pagination (supports unlimited PRs)
            list_url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=100"
            
            try:
                prs_list = await fetch_paginated_data(list_url, headers)
            except Exception as e:
                error_msg = str(e)
                if 'status=403' in error_msg:
                    return Response.new(json.dumps({'error': 'Rate Limit Exceeded'}), 
                                      {'status': 403, 'headers': {'Content-Type': 'application/json'}})
                return Response.new(json.dumps({'error': f'Failed to fetch repo PRs: {error_msg}'}), 
                                  {'status': 400, 'headers': {'Content-Type': 'application/json'}})
            added_count = 0
            ts = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            for item in prs_list:
                pr_data = {
                    'title': item.get('title', ''), 
                    'state': 'open', 
                    'is_merged': 0,
                    'mergeable_state': 'unknown', 
                    'files_changed': 0,
                    'author_login': item['user']['login'], 
                    'author_avatar': item['user']['avatar_url'],
                    'checks_passed': 0, 
                    'checks_failed': 0, 
                    'checks_skipped': 0,
                    'review_status': 'pending', 
                    'last_updated_at': item.get('updated_at', ts)
                }
                
                await upsert_pr(db, item['html_url'], owner, repo, item['number'], pr_data)
                added_count += 1
            
            return Response.new(json.dumps({'success': True, 'message': f'Successfully imported {added_count} PRs'}), 
                              {'headers': {'Content-Type': 'application/json'}})

        else:
            # Add single pr
            # Catch ValueError from parse_pr_url
            try:
                parsed = parse_pr_url(pr_url)
            except ValueError as e:
                return Response.new(
                    json.dumps({'error': str(e)}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )
            
            # Fetch PR data 
            pr_data = await fetch_pr_data(parsed['owner'], parsed['repo'], parsed['pr_number'], user_token)
            
            if not pr_data:
                # If null returned
                return Response.new(json.dumps({'error': 'Failed to fetch PR data (Rate Limit or Not Found)'}), 
                                  {'status': 403, 'headers': {'Content-Type': 'application/json'}})
            
            if pr_data['is_merged'] or pr_data['state'] == 'closed':
                return Response.new(json.dumps({'error': 'Cannot add merged/closed PRs'}), 
                                  {'status': 400, 'headers': {'Content-Type': 'application/json'}})
            
            await upsert_pr(db, pr_url, parsed['owner'], parsed['repo'], parsed['pr_number'], pr_data)
            
            return Response.new(json.dumps({'success': True, 'data': pr_data}), 
                              {'headers': {'Content-Type': 'application/json'}})

    except Exception as e:
        # Generic error message to prevent information disclosure
        print(f"Internal error in handle_add_pr: {type(e).__name__}: {str(e)}")
        return Response.new(
            json.dumps({'error': 'Internal server error'}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_list_prs(env, repo_filter=None):
    """List all PRs, optionally filtered by repo."""
    try:
        db = get_db(env)
        if repo_filter:
            parts = repo_filter.split('/')
            if len(parts) == 2:
                stmt = db.prepare('''
                    SELECT * FROM prs 
                    WHERE repo_owner = ? AND repo_name = ?
                    AND is_merged = 0 AND state = 'open'
                    ORDER BY last_updated_at DESC
                ''').bind(parts[0], parts[1])
            else:
                stmt = db.prepare('''
                    SELECT * FROM prs 
                    WHERE is_merged = 0 AND state = 'open'
                    ORDER BY last_updated_at DESC
                ''')
        else:
            stmt = db.prepare('''
                SELECT * FROM prs 
                WHERE is_merged = 0 AND state = 'open'
                ORDER BY last_updated_at DESC
            ''')
        
        result = await stmt.all()
        # Convert JS Array to Python list
        prs = result.results.to_py() if hasattr(result, 'results') else []
        
        return Response.new(json.dumps({'prs': prs}), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_list_repos(env):
    """List all unique repos with count of open PRs"""
    try:
        db = get_db(env)
        stmt = db.prepare('''
            SELECT DISTINCT repo_owner, repo_name, 
                   COUNT(*) as pr_count
            FROM prs 
            WHERE is_merged = 0 AND state = 'open'
            GROUP BY repo_owner, repo_name
            ORDER BY repo_owner, repo_name
        ''')
        
        result = await stmt.all()
        # Convert JS Array to Python list
        repos = result.results.to_py() if hasattr(result, 'results') else []
        
        return Response.new(json.dumps({'repos': repos}), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_refresh_pr(request, env):
    """Refresh a specific PR's data"""
    try:
        data = (await request.json()).to_py()
        pr_id = data.get('pr_id')
        user_token = request.headers.get('x-github-token')
        
        if not pr_id:
            return Response.new(json.dumps({'error': 'PR ID is required'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
        # Get PR URL from database
        db = get_db(env)
        stmt = db.prepare('SELECT pr_url, repo_owner, repo_name, pr_number FROM prs WHERE id = ?').bind(pr_id)
        result = await stmt.first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        # Convert JsProxy to Python dict to make it subscriptable
        result = result.to_py()
        
        # Fetch fresh data from GitHub (with Token)
        pr_data = await fetch_pr_data(result['repo_owner'], result['repo_name'], result['pr_number'], user_token)
        if not pr_data:
            return Response.new(json.dumps({'error': 'Failed to fetch PR data from GitHub'}), 
                              {'status': 403, 'headers': {'Content-Type': 'application/json'}})
        
        # Check if PR is now merged or closed - delete it from database
        if pr_data['is_merged'] or pr_data['state'] == 'closed':
            # Invalidate caches since PR state changed
            await invalidate_readiness_cache(env, pr_id)
            invalidate_timeline_cache(result['repo_owner'], result['repo_name'], result['pr_number'])
            
            # Delete the PR from database
            delete_stmt = db.prepare('DELETE FROM prs WHERE id = ?').bind(pr_id)
            await delete_stmt.run()
            
            status_msg = 'merged' if pr_data['is_merged'] else 'closed'
            return Response.new(json.dumps({
                'success': True, 
                'removed': True,
                'message': f'PR has been {status_msg} and removed from tracking'
            }), {'headers': {'Content-Type': 'application/json'}})
        
        await upsert_pr(db, result['pr_url'], result['repo_owner'], result['repo_name'], result['pr_number'], pr_data)
        
        # Invalidate caches after successful refresh
        # This ensures cached results don't become stale after new commits or review activity
        await invalidate_readiness_cache(env, pr_id)
        invalidate_timeline_cache(result['repo_owner'], result['repo_name'], result['pr_number'])
        
        return Response.new(json.dumps({'success': True, 'data': pr_data}), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_rate_limit(env):
    """Fetch GitHub API rate limit status
    
    Args:
        env: Cloudflare Worker environment object containing bindings
        
    Returns:
        Response object with JSON containing:
            - limit: Maximum number of requests per hour
            - remaining: Number of requests remaining
            - reset: Unix timestamp when the limit resets
            - used: Number of requests used
    """
    global _rate_limit_cache
    
    try:
        # Check cache first to avoid excessive API calls
        # Use JavaScript Date API for Cloudflare Workers compatibility
        current_time = Date.now() / 1000  # Convert milliseconds to seconds
        
        if _rate_limit_cache['data'] and (current_time - _rate_limit_cache['timestamp']) < _RATE_LIMIT_CACHE_TTL:
            # Return cached data
            return Response.new(
                json.dumps(_rate_limit_cache['data']), 
                {'headers': {
                    'Content-Type': 'application/json',
                    'Cache-Control': f'public, max-age={_RATE_LIMIT_CACHE_TTL}'
                }}
            )
        
        # Fetch rate limit from GitHub API
        rate_limit_url = "https://api.github.com/rate_limit"
        response = await fetch_with_headers(rate_limit_url)
        
        if response.status != 200:
            return Response.new(json.dumps({'error': f'GitHub API Error: {response.status}'}), 
                              {'status': response.status, 'headers': {'Content-Type': 'application/json'}})
        
        rate_data = (await response.json()).to_py()
        # Extract core rate limit info
        core_limit = rate_data.get('resources', {}).get('core', {})
        
        result = {
            'limit': core_limit.get('limit', 60),
            'remaining': core_limit.get('remaining', 0),
            'reset': core_limit.get('reset', 0),
            'used': core_limit.get('used', 0)
        }
        
        # Update cache
        _rate_limit_cache['data'] = result
        _rate_limit_cache['timestamp'] = current_time
        
        return Response.new(
            json.dumps(result), 
            {'headers': {'Content-Type': 'application/json', 'Cache-Control': f'public, max-age={_RATE_LIMIT_CACHE_TTL}'}}
        )
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_status(env):
    """Check database status"""
    try:
        db = get_db(env)
        # If we got here, database is configured (would have thrown exception otherwise)
        return Response.new(json.dumps({
            'database_configured': True,
            'environment': getattr(env, 'ENVIRONMENT', 'unknown')
        }), {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        # Database not configured
        return Response.new(json.dumps({
            'database_configured': False,
            'error': str(e),
            'environment': getattr(env, 'ENVIRONMENT', 'unknown')
        }), {'headers': {'Content-Type': 'application/json'}})

async def handle_pr_timeline(request, env, path):
    """
    GET /api/prs/{id}/timeline
    Fetch and return the full timeline for a PR
    
    Features:
    - Application-level rate limiting (10 requests/minute per IP)
    """
    try:
        # Extract PR ID from path: /api/prs/123/timeline
        pr_id = path.split('/')[3]  # Split by / and get the ID
        
        # Get client IP for rate limiting
        client_ip = (
            request.headers.get('cf-connecting-ip') or
            (request.headers.get('x-forwarded-for') or '').split(',')[0].strip() or
            request.headers.get('x-real-ip') or
            'unknown'
        )
        
        # Check rate limit
        allowed, retry_after = check_rate_limit(client_ip)
        if not allowed:
            return Response.new(
                json.dumps({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {retry_after} seconds.',
                    'retry_after': retry_after
                }),
                {
                    'status': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Retry-After': str(retry_after),
                        'X-RateLimit-Limit': str(_READINESS_RATE_LIMIT),
                        'X-RateLimit-Window': str(_READINESS_RATE_WINDOW)
                    }
                }
            )
        
        # Get PR details from database
        db = get_db(env)
        result = await db.prepare(
            'SELECT * FROM prs WHERE id = ?'
        ).bind(pr_id).first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        pr = result.to_py()
        
        # Fetch timeline data from GitHub
        timeline_data = await fetch_pr_timeline_data(
            pr['repo_owner'],
            pr['repo_name'],
            pr['pr_number']
        )
        
        # Build unified timeline
        timeline = build_pr_timeline(timeline_data)
        
        # Convert datetime objects to ISO strings for JSON serialization
        timeline_json = []
        for event in timeline:
            event_copy = event.copy()
            event_copy['timestamp'] = event['timestamp'].isoformat()
            timeline_json.append(event_copy)
        
        return Response.new(json.dumps({
            'pr': {
                'id': pr['id'],
                'title': pr['title'],
                'author': pr['author_login'],
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number']
            },
            'timeline': timeline_json,
            'event_count': len(timeline_json)
        }), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_pr_review_analysis(request, env, path):
    """
    GET /api/prs/{id}/review-analysis
    Analyze PR review progress and health
    
    Features:
    - Application-level rate limiting (10 requests/minute per IP)
    """
    try:
        # Extract PR ID from path: /api/prs/123/review-analysis
        pr_id = path.split('/')[3]
        
        # Get client IP for rate limiting
        client_ip = (
            request.headers.get('cf-connecting-ip') or
            (request.headers.get('x-forwarded-for') or '').split(',')[0].strip() or
            request.headers.get('x-real-ip') or
            'unknown'
        )
        
        # Check rate limit
        allowed, retry_after = check_rate_limit(client_ip)
        if not allowed:
            return Response.new(
                json.dumps({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {retry_after} seconds.',
                    'retry_after': retry_after
                }),
                {
                    'status': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Retry-After': str(retry_after),
                        'X-RateLimit-Limit': str(_READINESS_RATE_LIMIT),
                        'X-RateLimit-Window': str(_READINESS_RATE_WINDOW)
                    }
                }
            )
        
        # Get PR details from database
        db = get_db(env)
        result = await db.prepare(
            'SELECT * FROM prs WHERE id = ?'
        ).bind(pr_id).first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        pr = result.to_py()
        
        # Fetch timeline data from GitHub
        timeline_data = await fetch_pr_timeline_data(
            pr['repo_owner'],
            pr['repo_name'],
            pr['pr_number']
        )
        
        # Build unified timeline
        timeline = build_pr_timeline(timeline_data)
        
        # Analyze review progress
        review_data = analyze_review_progress(timeline, pr['author_login'])
        
        # Classify review health
        classification, score = classify_review_health(review_data)
        
        return Response.new(json.dumps({
            'pr': {
                'id': pr['id'],
                'title': pr['title'],
                'author': pr['author_login'],
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number']
            },
            'review_analysis': {
                'classification': classification,
                'score': score,
                'score_display': f"{score}%",
                'total_feedback': review_data['total_feedback_count'],
                'responded_feedback': review_data['responded_count'],
                'response_rate': review_data['response_rate'],
                'response_rate_display': f"{int(review_data['response_rate'] * 100)}%",
                'awaiting_author': review_data['awaiting_author'],
                'awaiting_reviewer': review_data['awaiting_reviewer'],
                'stale_feedback_count': len(review_data['stale_feedback']),
                'stale_feedback': review_data['stale_feedback'],
                'latest_review_state': review_data['latest_review_state'],
                'last_reviewer_action': review_data['last_reviewer_action'],
                'last_author_action': review_data['last_author_action']
            },
            'feedback_loops': review_data['feedback_loops']
        }), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_pr_readiness(request, env, path):
    """
    GET /api/prs/{id}/readiness
    Calculate overall PR readiness combining CI and review health
    
    Features:
    - Application-level rate limiting (10 requests/minute per IP)
    - Response caching (10 minutes TTL)
    - Cache invalidation on PR refresh
    """
    try:
        # Extract PR ID from path: /api/prs/123/readiness
        pr_id = path.split('/')[3]
        
        # Get client IP for rate limiting
        # Try multiple headers to support different proxy configurations
        client_ip = (
            request.headers.get('cf-connecting-ip') or  # Cloudflare
            (request.headers.get('x-forwarded-for') or '').split(',')[0].strip() or
            request.headers.get('x-real-ip') or
            'unknown'
        )
        
        # Check rate limit
        allowed, retry_after = check_rate_limit(client_ip)
        if not allowed:
            return Response.new(
                json.dumps({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {retry_after} seconds.',
                    'retry_after': retry_after
                }),
                {
                    'status': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Retry-After': str(retry_after),
                        'X-RateLimit-Limit': str(_READINESS_RATE_LIMIT),
                        'X-RateLimit-Window': str(_READINESS_RATE_WINDOW)
                    }
                }
            )
        
        # Check cache first
        cached_result = await get_readiness_cache(env, pr_id)
        if cached_result:
            # Return cached response with cache headers
            return Response.new(
                json.dumps(cached_result),
                {
                    'headers': {
                        'Content-Type': 'application/json',
                        'X-Cache': 'HIT',
                        'Cache-Control': f'private, max-age={_READINESS_CACHE_TTL}'
                    }
                }
            )
        
        # Get PR details from database
        db = get_db(env)
        result = await db.prepare(
            'SELECT * FROM prs WHERE id = ?'
        ).bind(pr_id).first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        pr = result.to_py()
        
        # Fetch timeline data from GitHub
        timeline_data = await fetch_pr_timeline_data(
            pr['repo_owner'],
            pr['repo_name'],
            pr['pr_number']
        )
        
        # Build unified timeline
        timeline = build_pr_timeline(timeline_data)
        
        # Analyze review progress
        review_data = analyze_review_progress(timeline, pr['author_login'])
        
        # Classify review health
        review_classification, review_score = classify_review_health(review_data)
        
        # Calculate combined readiness
        readiness = calculate_pr_readiness(pr, review_classification, review_score)
        
        # Build response data with percentage formatting
        response_data = {
            'pr': {
                'id': pr['id'],
                'title': pr['title'],
                'author': pr['author_login'],
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number'],
                'state': pr['state'],
                'is_merged': pr['is_merged'] == 1,
                'mergeable_state': pr['mergeable_state'],
                'files_changed': pr['files_changed']
            },
            'readiness': {
                **readiness,
                'overall_score_display': f"{readiness['overall_score']}%",
                'ci_score_display': f"{readiness['ci_score']}%",
                'review_score_display': f"{readiness.get('review_score', review_score)}%"
            },
            'review_health': {
                'classification': review_classification,
                'score': review_score,
                'score_display': f"{review_score}%",
                'total_feedback': review_data['total_feedback_count'],
                'responded_feedback': review_data['responded_count'],
                'response_rate': review_data['response_rate'],
                'response_rate_display': f"{int(review_data['response_rate'] * 100)}%",
                'stale_feedback_count': len(review_data['stale_feedback'])
            },
            'ci_checks': {
                'passed': pr['checks_passed'],
                'failed': pr['checks_failed'],
                'skipped': pr['checks_skipped']
            }
        }
        
        # Cache the result
        await set_readiness_cache(env, pr_id, response_data)
        
        return Response.new(
            json.dumps(response_data),
            {
                'headers': {
                    'Content-Type': 'application/json',
                    'X-Cache': 'MISS',
                    'Cache-Control': f'private, max-age={_READINESS_CACHE_TTL}'
                }
            }
        )
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname
    
    # Strip /leaf prefix
    if path == '/leaf': 
        path = '/'
    elif path.startswith('/leaf/'): 
        path = path[5:]  # Remove '/leaf' (5 characters)
    
    # CORS headers
    # NOTE: '*' allows all origins for public access. In production, consider
    # restricting to specific domains by setting this to your domain(s).
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, x-github-token',
    }
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})
    
    # Serve HTML for root path 
    if path == '/' or path == '/index.html':
        # Use env.ASSETS to serve static files if available
        if hasattr(env, 'ASSETS'): 
            return await env.ASSETS.fetch(request)
        # Fallback: return simple message
        return Response.new('Please configure assets in wrangler.toml', 
                          {'status': 200, 'headers': {**cors_headers, 'Content-Type': 'text/html'}})
    
    # Initialize database schema on first API request (idempotent, safe to call multiple times)
    if path.startswith('/api/'): await init_database_schema(env)
    
    # API endpoints
    response = None
    
    if path == '/api/prs':
        if request.method == 'GET':
            response = await handle_list_prs(env, url.searchParams.get('repo'))
        elif request.method == 'POST':
            response = await handle_add_pr(request, env)
    elif path == '/api/repos' and request.method == 'GET':
        response = await handle_list_repos(env)
    elif path == '/api/refresh' and request.method == 'POST':
        response = await handle_refresh_pr(request, env)
    elif path == '/api/rate-limit' and request.method == 'GET':
        response = await handle_rate_limit(env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    elif path == '/api/status' and request.method == 'GET':
        response = await handle_status(env)
    # Timeline endpoint - GET /api/prs/{id}/timeline
    elif path.startswith('/api/prs/') and path.endswith('/timeline') and request.method == 'GET':
        response = await handle_pr_timeline(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    # Review analysis endpoint - GET /api/prs/{id}/review-analysis
    elif path.startswith('/api/prs/') and path.endswith('/review-analysis') and request.method == 'GET':
        response = await handle_pr_review_analysis(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    # PR readiness endpoint - GET /api/prs/{id}/readiness
    elif path.startswith('/api/prs/') and path.endswith('/readiness') and request.method == 'GET':
        response = await handle_pr_readiness(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    # If no API route matched, try static assets or return 404
    if response is None:
        if hasattr(env, 'ASSETS'): return await env.ASSETS.fetch(request)
        return Response.new('Not Found', {'status': 404, 'headers': cors_headers})
    
    # Apply CORS to API responses
    for key, value in cors_headers.items():
        if response: response.headers.set(key, value)
    return response
