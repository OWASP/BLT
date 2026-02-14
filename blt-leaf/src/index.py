from js import Response, fetch, Headers, URL, Object, Date
from pyodide.ffi import to_js
import json
import re
from datetime import datetime, timezone

# Track if schema initialization has been attempted
_schema_init_attempted = False

# In-memory cache for rate limit data
_rate_limit_cache = {
    'data': None,
    'timestamp': 0
}
_RATE_LIMIT_CACHE_TTL = 300


# CENTRALIZED RESPONSE HELPERS


def json_response(data, status=200):
    """Return a successful JSON response with CORS headers"""
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    return Response.new(
        json.dumps(data),
        {'status': status, 'headers': cors_headers}
    )

def json_error(message, status=400):
    """Return an error JSON response with CORS headers"""
    return json_response({
        'success': False,
        'error': message,
        'status': status
    }, status=status)

# UTILITIES

def parse_pr_url(url):
    """
    Parse and validate GitHub PR URL with strict anchoring.
    Accepts PRs from ANY GitHub organization.
    
    Args:
        url: GitHub PR URL string
        
    Returns:
        dict with owner, repo, pr_number
        
    Raises:
        ValueError: If URL is invalid or not properly formatted
    """
    # Type validation (Issue #45 - Strict Input Validation)
    if not isinstance(url, str):
        raise ValueError("PR URL must be a string")
    
    # Strict anchored pattern (Issue #45 - Anchored URL Validation)
    # Format: https://github.com/OWNER/REPO/pull/NUMBER
    # Must match EXACTLY, no trailing junk allowed
    pattern = r'^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$'
    match = re.match(pattern, url.strip(), re.IGNORECASE)
    
    if not match:
        raise ValueError("Invalid GitHub PR URL. Format: https://github.com/OWNER/REPO/pull/NUMBER")
    
    return {
        'owner': match.group(1),
        'repo': match.group(2),
        'pr_number': int(match.group(3))
    }

def get_db(env):
    """Get database binding from environment"""
    for name in ['DB', 'pr_tracker']:
        if hasattr(env, name):
            return getattr(env, name)
    raise Exception("Database binding 'DB' not found. Check wrangler.toml")
    
# DATABASE INITIALIZATION

async def init_database_schema(env):
    """Initialize database schema if not already done"""
    global _schema_init_attempted
    if _schema_init_attempted:
        return
    _schema_init_attempted = True
    
    try:
        db = get_db(env)
        await db.prepare('''
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
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''').run()
    except Exception as e:
        print(f"Schema Init Note: {str(e)}")
        
# GITHUB API HELPERS#

async def fetch_with_headers(url, headers=None):
    """Fetch URL with optional headers"""
    if headers:
        options = to_js({
            "method": "GET",
            "headers": headers
        }, dict_converter=Object.fromEntries)
        return await fetch(url, options)
    return await fetch(url)

def get_github_headers(env):
    """Get GitHub API headers with optional authentication"""
    github_token = getattr(env, "GITHUB_TOKEN", None)
    headers = {
        'User-Agent': 'PR-Tracker/1.0',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    if github_token:
        headers['Authorization'] = f'Bearer {github_token}'
    return headers

async def fetch_pr_data(owner, repo, pr_number, env):
    """
    Fetch PR data from GitHub API with authentication.
    
    FIX Issue #43: Reads response body only ONCE to prevent "Body already used" error
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        env: Worker environment
        
    Returns:
        dict: PR data
        
    Raises:
        Exception: If GitHub API returns error
    """
    headers = get_github_headers(env)
    
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    pr_response = await fetch_with_headers(pr_url, headers)
    
    # FIX Issue #43: Read response body ONCE and store it
    pr_body = await pr_response.text()
    
    if pr_response.status >= 400:
        raise Exception(f"GitHub API Error {pr_response.status}: {pr_body}")

    # Parse the stored body instead of calling .json() again
    pr_data = json.loads(pr_body)
    
    # Fetch check runs
    checks_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{pr_data['head']['sha']}/check-runs"
    checks_res = await fetch_with_headers(checks_url, headers)
    
    # FIX Issue #43: Read checks response body once
    checks_body = await checks_res.text()
    checks_data = json.loads(checks_body) if checks_res.status == 200 else {}

    # Calculate check statistics
    passed = sum(1 for c in checks_data.get('check_runs', []) if c['conclusion'] == 'success')
    failed = sum(1 for c in checks_data.get('check_runs', []) if c['conclusion'] in ['failure', 'timed_out'])

    return {
        'title': pr_data.get('title', ''),
        'state': pr_data.get('state', ''),
        'is_merged': 1 if pr_data.get('merged', False) else 0,
        'mergeable_state': pr_data.get('mergeable_state', ''),
        'files_changed': pr_data.get('changed_files', 0),
        'author_login': pr_data['user']['login'],
        'author_avatar': pr_data['user']['avatar_url'],
        'checks_passed': passed,
        'checks_failed': failed,
        'checks_skipped': 0,
        'review_status': 'pending',
        'last_updated_at': pr_data.get('updated_at', '')
    }

# API HANDLERS #

async def handle_rate_limit(env):
    """
    Get GitHub API rate limit information.
    
    Returns authenticated rate limit if GITHUB_TOKEN is set,
    otherwise returns unauthenticated rate limit.
    
    Returns:
        Response with {limit, remaining, reset, reset_time}
    """
    try:
        headers = get_github_headers(env)
        
        res = await fetch_with_headers("https://api.github.com/rate_limit", headers)
        
        # FIX Issue #43: Read response body once
        res_body = await res.text()
        
        if res.status >= 400:
            return json_error(f"GitHub API Error: {res_body}", status=res.status)
        
        data = json.loads(res_body)
        core = data.get('resources', {}).get('core', {})
        
        # Format response with additional info
        response_data = {
            'limit': core.get('limit', 0),
            'remaining': core.get('remaining', 0),
            'reset': core.get('reset', 0),
            'reset_time': datetime.fromtimestamp(core.get('reset', 0), tz=timezone.utc).isoformat() if core.get('reset') else None,
            'authenticated': bool(getattr(env, "GITHUB_TOKEN", None))
        }
        
        return json_response(response_data)
        
    except Exception as e:
        return json_error(f"Failed to fetch rate limit: {str(e)}", status=500)

async def handle_add_pr(request, env):
    """
    Add a new PR to track.
    
    FIX Issue #43: Single request body read
    FIX Issue #45: Strict input validation and error handling
    """
    try:
        # FIX Issue #43 & #45: Read request body ONCE with error handling
        try:
            data = (await request.json()).to_py()
        except Exception:
            return json_error("Malformed JSON payload", status=400)
        
        pr_url = data.get('pr_url', '')
        
        # FIX Issue #45: Strict type validation
        if not pr_url or not isinstance(pr_url, str):
            return json_error("A valid GitHub PR URL is required", status=400)
        
        # Parse and validate PR URL (will raise ValueError if invalid)
        # FIX Issue #45: Uses anchored regex pattern in parse_pr_url
        try:
            parsed = parse_pr_url(pr_url)
        except ValueError as e:
            return json_error(str(e), status=400)
        
        # Fetch PR data from GitHub
        pr_data = await fetch_pr_data(
            parsed['owner'], 
            parsed['repo'], 
            parsed['pr_number'], 
            env
        )
        
        # Save to database
        db = get_db(env)
        await db.prepare('''
            INSERT INTO prs (
                pr_url, repo_owner, repo_name, pr_number, 
                title, state, is_merged, mergeable_state,
                files_changed, author_login, author_avatar,
                checks_passed, checks_failed, checks_skipped,
                review_status, last_updated_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(pr_url) DO UPDATE SET 
                title=excluded.title,
                state=excluded.state,
                is_merged=excluded.is_merged,
                mergeable_state=excluded.mergeable_state,
                files_changed=excluded.files_changed,
                checks_passed=excluded.checks_passed,
                checks_failed=excluded.checks_failed,
                review_status=excluded.review_status,
                last_updated_at=excluded.last_updated_at,
                updated_at=CURRENT_TIMESTAMP
        ''').bind(
            pr_url,
            parsed['owner'],
            parsed['repo'],
            parsed['pr_number'],
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
            pr_data['last_updated_at']
        ).run()
        
        return json_response({
            'success': True,
            'data': pr_data
        })
        
    except Exception as e:
        # FIX Issue #45: Generic error message to client, detailed log server-side
        print(f"Internal error in handle_add_pr: {type(e).__name__}: {str(e)}")
        return json_error("Internal server error", status=500)

async def handle_list_prs(env):
    """Get all tracked PRs"""
    try:
        db = get_db(env)
        # Show PRs from ALL orgs, not just OWASP-BLT
        result = await db.prepare('SELECT * FROM prs ORDER BY updated_at DESC').all()
        
        return json_response({
            'success': True,
            'prs': result.results.to_py()
        })
        
    except Exception as e:
        return json_error(f"Failed to list PRs: {str(e)}", status=500)

# MAIN ENTRY POINT
async def on_fetch(request, env):
    url = URL.new(request.url)
    # Use rstrip('/') so that /api/prs/ and /api/prs both work
    path = url.pathname.rstrip('/')
    
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})

    try:
        if path == '/api/rate-limit':
            return await handle_rate_limit(env)
            
        elif path == '/api/prs':
            if request.method == 'POST':
                return await handle_add_pr(request, env)
            elif request.method == 'GET':
                return await handle_list_prs(env)

        # Final Fallback
        return Response.new('Endpoint Not Found', {'status': 404})
        
    except Exception as e:
        # Generic error handling
        print(f"Unhandled error: {type(e).__name__}: {str(e)}")
        return json_error("Internal server error", status=500)
