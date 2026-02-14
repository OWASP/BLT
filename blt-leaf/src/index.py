from js import Response, fetch, Headers, URL, Object, Date
from pyodide.ffi import to_js
import json
import re
from datetime import datetime, timezone

# Track if schema initialization has been attempted in this worker instance
_schema_init_attempted = False

# In-memory cache for rate limit data (per worker isolate)
_rate_limit_cache = {
    'data': None,
    'timestamp': 0
}
# Cache TTL in seconds (5 minutes)
_RATE_LIMIT_CACHE_TTL = 300

def parse_pr_url(pr_url):
    """
    Parse and validate GitHub PR URL with strict anchoring.
    Accepts PRs from any GitHub organization.
    
    Args:
        pr_url: GitHub PR URL string
        
    Returns:
        dict with owner, repo, pr_number
        
    Raises:
        ValueError: If URL is invalid or not properly formatted
    """
    # Type validation
    if not isinstance(pr_url, str):
        raise ValueError("PR URL must be a string")
    
    # Strict anchored pattern - must match EXACTLY, no trailing junk
    # Format: https://github.com/OWNER/REPO/pull/NUMBER
    pattern = r'^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$'
    match = re.match(pattern, pr_url.strip(), re.IGNORECASE)
    
    if not match:
        raise ValueError("Invalid GitHub PR URL. Format: https://github.com/OWNER/REPO/pull/NUMBER")
    
    return {
        'owner': match.group(1),
        'repo': match.group(2),
        'pr_number': int(match.group(3))
    }

def get_db(env):
    """Helper to get DB binding from env, handling different env types."""
    for name in ['pr_tracker', 'DB']:
        if hasattr(env, name):
            return getattr(env, name)
        if hasattr(env, '__getitem__'):
            try:
                return env[name]
            except (KeyError, TypeError):
                pass
    
    print(f"DEBUG: env attributes: {dir(env)}")
    raise Exception("Database binding 'pr_tracker' or 'DB' not found in env. Please configure a D1 database.")

async def init_database_schema(env):
    """Initialize database schema if it doesn't exist."""
    global _schema_init_attempted
    
    if _schema_init_attempted:
        return
    
    _schema_init_attempted = True
    
    try:
        db = get_db(env)
        
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
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await create_table.run()
        
        # Migration: Add last_refreshed_at column if it doesn't exist
        try:
            pragma_result = db.prepare('PRAGMA table_info(prs)')
            columns_result = await pragma_result.all()
            columns = columns_result.results.to_py() if hasattr(columns_result, 'results') else []
            
            column_names = [col['name'] for col in columns if isinstance(col, dict)]
            if 'last_refreshed_at' not in column_names:
                print("Migrating database: Adding last_refreshed_at column")
                alter_table = db.prepare('ALTER TABLE prs ADD COLUMN last_refreshed_at TEXT')
                await alter_table.run()
        except Exception as migration_error:
            print(f"Note: Migration check for last_refreshed_at: {str(migration_error)}")
        
        # Create indexes
        index1 = db.prepare('CREATE INDEX IF NOT EXISTS idx_repo ON prs(repo_owner, repo_name)')
        await index1.run()
        
        index2 = db.prepare('CREATE INDEX IF NOT EXISTS idx_pr_number ON prs(pr_number)')
        await index2.run()
        
    except Exception as e:
        print(f"Note: Schema initialization check: {str(e)}")

async def fetch_with_headers(url, headers=None):
    """Helper to fetch with proper header handling using pyodide.ffi.to_js"""
    if headers:
        options = to_js({
            "method": "GET",
            "headers": headers
        }, dict_converter=Object.fromEntries)
        return await fetch(url, options)
    else:
        return await fetch(url)

async def fetch_pr_data(owner, repo, pr_number):
    """
    Fetch PR data from GitHub API.
    
    IMPORTANT: Reads response bodies only once to avoid "Body already used" errors.
    """
    headers = {
        'User-Agent': 'PR-Tracker/1.0',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
        
    try:
        # Fetch PR details
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_response = await fetch_with_headers(pr_url, headers)
        
        # Read response body ONCE and store it
        pr_body = await pr_response.text()
        
        # Check for errors
        if pr_response.status == 403 or pr_response.status == 429:
            rl_limit = pr_response.headers.get('x-ratelimit-limit', 'unknown')
            rl_remaining = pr_response.headers.get('x-ratelimit-remaining', 'unknown')
            raise Exception(f"GitHub API rate limit exceeded. Limit: {rl_limit}, Remaining: {rl_remaining}")
        elif pr_response.status == 404:
            raise Exception("PR not found or repository is private")
        elif pr_response.status >= 400:
            raise Exception(f"GitHub API Error {pr_response.status}: {pr_body}")
        
        # Parse the stored body
        pr_data = json.loads(pr_body)
        
        # Fetch PR files
        files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files_response = await fetch_with_headers(files_url, headers)
        files_body = await files_response.text()
        files_data = json.loads(files_body) if files_response.status == 200 else []
        
        # Fetch PR reviews
        reviews_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        reviews_response = await fetch_with_headers(reviews_url, headers)
        reviews_body = await reviews_response.text()
        reviews_data = json.loads(reviews_body) if reviews_response.status == 200 else []
        
        # Fetch check runs
        checks_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{pr_data['head']['sha']}/check-runs"
        checks_response = await fetch_with_headers(checks_url, headers)
        checks_body = await checks_response.text()
        checks_data = json.loads(checks_body) if checks_response.status == 200 else {}
        
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
        
        # Determine review status
        review_status = 'none'
        if reviews_data:
            sorted_reviews = sorted(reviews_data, key=lambda x: x.get('submitted_at', ''))
            
            latest_reviews = {}
            for review in sorted_reviews:
                user = review['user']['login']
                latest_reviews[user] = review['state']
            
            if 'CHANGES_REQUESTED' in latest_reviews.values():
                review_status = 'changes_requested'
            elif 'APPROVED' in latest_reviews.values():
                review_status = 'approved'
            else:
                review_status = 'pending'
        
        return {
            'title': pr_data.get('title', ''),
            'state': pr_data.get('state', ''),
            'is_merged': 1 if pr_data.get('merged', False) else 0,
            'mergeable_state': pr_data.get('mergeable_state', ''),
            'files_changed': len(files_data) if isinstance(files_data, list) else 0,
            'author_login': pr_data['user']['login'],
            'author_avatar': pr_data['user']['avatar_url'],
            'checks_passed': checks_passed,
            'checks_failed': checks_failed,
            'checks_skipped': checks_skipped,
            'review_status': review_status,
            'last_updated_at': pr_data.get('updated_at', '')
        }
    except Exception as e:
        raise Exception(f"Error fetching PR data: {str(e)}")

async def handle_add_pr(request, env):
    """
    Handle adding a new PR with strict input validation.
    
    Security hardening:
    - Single request body read
    - Type validation
    - Anchored URL pattern matching
    - Generic error messages
    """
    try:
        # Read request body ONCE - prevent "Body already used" error
        try:
            request_body = (await request.json()).to_py()
        except Exception:
            return Response.new(
                json.dumps({'error': 'Malformed JSON payload'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        pr_url = request_body.get('pr_url')
        
        # Strict type and existence validation
        if not pr_url or not isinstance(pr_url, str):
            return Response.new(
                json.dumps({'error': 'A valid GitHub PR URL is required'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        # Parse and validate URL (strict anchored pattern)
        try:
            parsed = parse_pr_url(pr_url)
        except ValueError as e:
            return Response.new(
                json.dumps({'error': str(e)}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        # Fetch PR data from GitHub
        pr_data = await fetch_pr_data(parsed['owner'], parsed['repo'], parsed['pr_number'])
        
        if not pr_data:
            return Response.new(
                json.dumps({'error': 'Failed to fetch PR data from GitHub'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )
        
        # Check if PR is merged or closed
        if pr_data['is_merged']:
            return Response.new(
                json.dumps({'error': 'Cannot add merged PRs'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        if pr_data['state'] == 'closed':
            return Response.new(
                json.dumps({'error': 'Cannot add closed PRs'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        # Insert or update in database
        db = get_db(env)
        stmt = db.prepare('''
            INSERT INTO prs (pr_url, repo_owner, repo_name, pr_number, title, state, 
                           is_merged, mergeable_state, files_changed, author_login, 
                           author_avatar, checks_passed, checks_failed, checks_skipped, 
                           review_status, last_updated_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                updated_at = CURRENT_TIMESTAMP
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
        )
        
        await stmt.run()
        
        return Response.new(
            json.dumps({'success': True, 'data': pr_data}),
            {'headers': {'Content-Type': 'application/json'}}
        )
        
    except Exception as e:
        # Log detailed error server-side, return generic error to client
        print(f"Internal error in handle_add_pr: {type(e).__name__}: {str(e)}")
        return Response.new(
            json.dumps({'error': 'Internal server error'}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_list_prs(env, repo_filter=None):
    """List all PRs, optionally filtered by repo. Excludes merged and closed PRs."""
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
        prs = result.results.to_py() if hasattr(result, 'results') else []
        
        return Response.new(
            json.dumps({'prs': prs}),
            {'headers': {'Content-Type': 'application/json'}}
        )
    except Exception as e:
        return Response.new(
            json.dumps({'error': 'Failed to list PRs'}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_list_repos(env):
    """List all unique repos with count of open PRs only"""
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
        repos = result.results.to_py() if hasattr(result, 'results') else []
        
        return Response.new(
            json.dumps({'repos': repos}),
            {'headers': {'Content-Type': 'application/json'}}
        )
    except Exception as e:
        return Response.new(
            json.dumps({'error': 'Failed to list repositories'}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_refresh_pr(request, env):
    """Refresh a specific PR's data"""
    try:
        data = (await request.json()).to_py()
        pr_id = data.get('pr_id')
        
        if not pr_id:
            return Response.new(
                json.dumps({'error': 'PR ID is required'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        db = get_db(env)
        stmt = db.prepare('SELECT pr_url, repo_owner, repo_name, pr_number FROM prs WHERE id = ?').bind(pr_id)
        result = await stmt.first()
        
        if not result:
            return Response.new(
                json.dumps({'error': 'PR not found'}),
                {'status': 404, 'headers': {'Content-Type': 'application/json'}}
            )
        
        result = result.to_py()
        
        pr_data = await fetch_pr_data(result['repo_owner'], result['repo_name'], result['pr_number'])
        
        if not pr_data:
            return Response.new(
                json.dumps({'error': 'Failed to fetch PR data from GitHub'}),
                {'status': 500, 'headers': {'Content-Type': 'application/json'}}
            )
        
        # Check if PR is now merged or closed
        if pr_data['is_merged'] or pr_data['state'] == 'closed':
            delete_stmt = db.prepare('DELETE FROM prs WHERE id = ?').bind(pr_id)
            await delete_stmt.run()
            
            status_msg = 'merged' if pr_data['is_merged'] else 'closed'
            return Response.new(
                json.dumps({
                    'success': True,
                    'removed': True,
                    'message': f'PR has been {status_msg} and removed from tracking'
                }),
                {'headers': {'Content-Type': 'application/json'}}
            )
        
        current_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        stmt = db.prepare('''
            UPDATE prs SET
                title = ?, state = ?, is_merged = ?, mergeable_state = ?,
                files_changed = ?, checks_passed = ?, checks_failed = ?,
                checks_skipped = ?, review_status = ?, last_updated_at = ?,
                last_refreshed_at = ?,
                updated_at = ?
            WHERE id = ?
        ''').bind(
            pr_data['title'],
            pr_data['state'],
            pr_data['is_merged'],
            pr_data['mergeable_state'],
            pr_data['files_changed'],
            pr_data['checks_passed'],
            pr_data['checks_failed'],
            pr_data['checks_skipped'],
            pr_data['review_status'],
            pr_data['last_updated_at'],
            current_timestamp,
            current_timestamp,
            pr_id
        )
        
        await stmt.run()
        
        return Response.new(
            json.dumps({'success': True, 'data': pr_data}),
            {'headers': {'Content-Type': 'application/json'}}
        )
    except Exception as e:
        return Response.new(
            json.dumps({'error': 'Failed to refresh PR'}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_rate_limit(env):
    """Fetch GitHub API rate limit status with caching"""
    global _rate_limit_cache
    
    try:
        current_time = Date.now() / 1000
        
        if _rate_limit_cache['data'] and (current_time - _rate_limit_cache['timestamp']) < _RATE_LIMIT_CACHE_TTL:
            return Response.new(
                json.dumps(_rate_limit_cache['data']),
                {'headers': {
                    'Content-Type': 'application/json',
                    'Cache-Control': f'public, max-age={_RATE_LIMIT_CACHE_TTL}'
                }}
            )
        
        headers = {
            'User-Agent': 'PR-Tracker/1.0',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        rate_limit_url = "https://api.github.com/rate_limit"
        response = await fetch_with_headers(rate_limit_url, headers)
        
        response_body = await response.text()
        
        if response.status != 200:
            return Response.new(
                json.dumps({
                    'error': f'GitHub API Error: {response.status}',
                    'details': response_body
                }),
                {'status': response.status, 'headers': {'Content-Type': 'application/json'}}
            )
        
        rate_data = json.loads(response_body)
        core_limit = rate_data.get('resources', {}).get('core', {})
        
        result = {
            'limit': core_limit.get('limit', 60),
            'remaining': core_limit.get('remaining', 0),
            'reset': core_limit.get('reset', 0),
            'used': core_limit.get('used', 0)
        }
        
        _rate_limit_cache['data'] = result
        _rate_limit_cache['timestamp'] = current_time
        
        return Response.new(
            json.dumps(result),
            {'headers': {
                'Content-Type': 'application/json',
                'Cache-Control': f'public, max-age={_RATE_LIMIT_CACHE_TTL}'
            }}
        )
    except Exception as e:
        return Response.new(
            json.dumps({'error': 'Failed to fetch rate limit'}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_status(env):
    """Check database status"""
    try:
        db = get_db(env)
        return Response.new(
            json.dumps({
                'database_configured': True,
                'environment': getattr(env, 'ENVIRONMENT', 'unknown')
            }),
            {'headers': {'Content-Type': 'application/json'}}
        )
    except Exception as e:
        return Response.new(
            json.dumps({
                'database_configured': False,
                'error': str(e),
                'environment': getattr(env, 'ENVIRONMENT', 'unknown')
            }),
            {'headers': {'Content-Type': 'application/json'}}
        )

async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname
    
    # Strip /leaf prefix
    if path == '/leaf':
        path = '/'
    elif path.startswith('/leaf/'):
        path = path[5:]
    
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})
    
    # Serve HTML for root path
    if path == '/' or path == '/index.html':
        if hasattr(env, 'ASSETS'):
            return await env.ASSETS.fetch(request)
        else:
            return Response.new(
                'Please configure assets in wrangler.toml',
                {'status': 200, 'headers': {**cors_headers, 'Content-Type': 'text/html'}}
            )
    
    # Initialize database schema on first API request
    if path.startswith('/api/'):
        await init_database_schema(env)
    
    # API endpoints
    if path == '/api/prs' and request.method == 'GET':
        repo_filter = url.searchParams.get('repo')
        response = await handle_list_prs(env, repo_filter)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/prs' and request.method == 'POST':
        response = await handle_add_pr(request, env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/repos' and request.method == 'GET':
        response = await handle_list_repos(env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/refresh' and request.method == 'POST':
        response = await handle_refresh_pr(request, env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/rate-limit' and request.method == 'GET':
        response = await handle_rate_limit(env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/status' and request.method == 'GET':
        response = await handle_status(env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    # Try to serve from assets
    if hasattr(env, 'ASSETS'):
        return await env.ASSETS.fetch(request)
    
    # 404
    return Response.new('Not Found', {'status': 404, 'headers': cors_headers})
