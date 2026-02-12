from js import Response, fetch, Headers, URL, Object, Date
from pyodide.ffi import to_js
import json
import re
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

def parse_pr_url(pr_url):
    """Parse GitHub PR URL to extract owner, repo, and PR number"""
    pattern = r'https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
    match = re.match(pattern, pr_url)
    if match:
        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'pr_number': int(match.group(3))
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
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await create_table.run()
        
        # Migration: Add last_refreshed_at column if it doesn't exist
        # Check if column exists by querying PRAGMA table_info
        try:
            pragma_result = db.prepare('PRAGMA table_info(prs)')
            columns_result = await pragma_result.all()
            columns = columns_result.results.to_py() if hasattr(columns_result, 'results') else []
            
            # Check if last_refreshed_at column exists
            column_names = [col['name'] for col in columns if isinstance(col, dict)]
            if 'last_refreshed_at' not in column_names:
                print("Migrating database: Adding last_refreshed_at column")
                alter_table = db.prepare('ALTER TABLE prs ADD COLUMN last_refreshed_at TEXT')
                await alter_table.run()
        except Exception as migration_error:
            # Column may already exist or migration failed - log but continue
            print(f"Note: Migration check for last_refreshed_at: {str(migration_error)}")
        
        # Create indexes (idempotent with IF NOT EXISTS)
        index1 = db.prepare('CREATE INDEX IF NOT EXISTS idx_repo ON prs(repo_owner, repo_name)')
        await index1.run()
        
        index2 = db.prepare('CREATE INDEX IF NOT EXISTS idx_pr_number ON prs(pr_number)')
        await index2.run()
        
    except Exception as e:
        # Log the error but don't crash - schema may already exist
        print(f"Note: Schema initialization check: {str(e)}")
        # Schema likely already exists, which is fine

async def fetch_with_headers(url, headers=None):
    """Helper to fetch with proper header handling using pyodide.ffi.to_js"""
    if headers:
        # Convert Python dict to JavaScript object using Object.fromEntries for correct mapping
        options = to_js({
            "method": "GET",
            "headers": headers
        }, dict_converter=Object.fromEntries)
        return await fetch(url, options)
    else:
        return await fetch(url)

async def fetch_pr_data(owner, repo, pr_number):
    """Fetch PR data from GitHub API"""
    headers = {
        'User-Agent': 'PR-Tracker/1.0',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
        
    try:
        # Fetch PR details
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_response = await fetch_with_headers(pr_url, headers)
        
        if pr_response.status == 403 or pr_response.status == 429:
            rl_limit = pr_response.headers.get('x-ratelimit-limit', 'unknown')
            rl_remaining = pr_response.headers.get('x-ratelimit-remaining', 'unknown')
            error_body = await pr_response.text()
            error_body = await pr_response.text()
            print(f"DEBUG: GitHub API Error. Status: {pr_response.status}. Body: {error_body}")
            print(f"DEBUG: Sent headers due to error: User-Agent={headers.get('User-Agent', 'MISSING')}")
            raise Exception(f"GitHub API Error {pr_response.status}: {error_body} (Limit: {rl_limit}, Remaining: {rl_remaining})")
        elif pr_response.status == 404:
            raise Exception("PR not found or repository is private")
        elif pr_response.status >= 400:
            error_msg = await pr_response.text()
            raise Exception(f"GitHub API Error: {pr_response.status} {error_msg}")
            
        pr_data = (await pr_response.json()).to_py()
        
        # Fetch PR files
        files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files_response = await fetch_with_headers(files_url, headers)
        files_data = (await files_response.json()).to_py() if files_response.status == 200 else []
        
        # Fetch PR reviews
        reviews_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        reviews_response = await fetch_with_headers(reviews_url, headers)
        reviews_data = (await reviews_response.json()).to_py() if reviews_response.status == 200 else []
        
        # Fetch check runs
        checks_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{pr_data['head']['sha']}/check-runs"
        checks_response = await fetch_with_headers(checks_url, headers)
        checks_data = (await checks_response.json()).to_py() if checks_response.status == 200 else {}
        
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
        review_status = 'none'
        if reviews_data:
            # Sort reviews by submitted_at to get chronological order
            sorted_reviews = sorted(reviews_data, key=lambda x: x.get('submitted_at', ''))
            
            # Get latest review per user
            latest_reviews = {}
            for review in sorted_reviews:
                user = review['user']['login']
                latest_reviews[user] = review['state']
            
            # Determine overall status: changes_requested takes precedence over approved
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
        # Return more informative error for debugging
        error_msg = f"Error fetching PR data: {str(e)}"
        # In Cloudflare Workers, console.error is preferred
        raise Exception(error_msg)

async def fetch_pr_timeline_data(owner, repo, pr_number, github_token=None):
    """
    Fetch all timeline data for a PR: commits, reviews, review comments, issue comments
    
    Returns dict with raw data from GitHub API:
    {
        'commits': [...],
        'reviews': [...],
        'review_comments': [...],
        'issue_comments': [...]
    }
    """
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
        # Fetch all timeline data in parallel
        commits_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/commits'
        reviews_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews'
        review_comments_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments'
        issue_comments_url = f'{base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments'
        
        # Make parallel requests
        commits_response = await fetch(commits_url, {'headers': headers})
        reviews_response = await fetch(reviews_url, {'headers': headers})
        review_comments_response = await fetch(review_comments_url, {'headers': headers})
        issue_comments_response = await fetch(issue_comments_url, {'headers': headers})
        
        # Parse responses
        commits_data = (await commits_response.json()).to_py() if commits_response.ok else []
        reviews_data = (await reviews_response.json()).to_py() if reviews_response.ok else []
        review_comments_data = (await review_comments_response.json()).to_py() if review_comments_response.ok else []
        issue_comments_data = (await issue_comments_response.json()).to_py() if issue_comments_response.ok else []
        
        return {
            'commits': commits_data,
            'reviews': reviews_data,
            'review_comments': review_comments_data,
            'issue_comments': issue_comments_data
        }
    except Exception as e:
        raise Exception(f"Error fetching timeline data: {str(e)}")

def parse_github_timestamp(timestamp_str):
    """Parse GitHub ISO 8601 timestamp to datetime object"""
    try:
        # GitHub timestamps are in format: 2024-01-15T10:30:45Z
        return datetime.strptime(timestamp_str.replace('Z', '+00:00'), '%Y-%m-%dT%H:%M:%S%z')
    except Exception:
        # Fallback to current time if parsing fails
        return datetime.now(timezone.utc)

def build_pr_timeline(timeline_data, pr_author):
    """
    Build unified chronological timeline from PR events
    
    Args:
        timeline_data: Dict with commits, reviews, review_comments, issue_comments
        pr_author: GitHub login of PR author
    
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
        'response_rate': round(response_rate, 2),
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
    
    # Weighted score: passes add, failures subtract heavily, skips slightly reduce
    score = (pass_rate * 100) - (fail_rate * 80) - (skip_rate * 20)
    
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
    
    # Weighted combination: 60% CI, 40% Review
    overall_score = int((ci_score * 0.6) + (review_score * 0.4))
    
    # Identify blockers, warnings, recommendations
    blockers = []
    warnings = []
    recommendations = []
    
    # CI blockers
    checks_failed = pr_data.get('checks_failed', 0)
    checks_skipped = pr_data.get('checks_skipped', 0)
    checks_passed = pr_data.get('checks_passed', 0)
    
    if checks_failed > 0:
        blockers.append(f"{checks_failed} CI check(s) failing")
        recommendations.append("Fix failing CI checks before merging")
    
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

async def handle_add_pr(request, env):
    """Handle adding a new PR"""
    try:
        data = (await request.json()).to_py()
        pr_url = data.get('pr_url')
        
        if not pr_url:
            return Response.new(json.dumps({'error': 'PR URL is required'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
        # Parse PR URL
        parsed = parse_pr_url(pr_url)
        if not parsed:
            return Response.new(json.dumps({'error': 'Invalid GitHub PR URL'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
        # Fetch PR data from GitHub
        pr_data = await fetch_pr_data(parsed['owner'], parsed['repo'], parsed['pr_number'])
        if not pr_data:
            return Response.new(json.dumps({'error': 'Failed to fetch PR data from GitHub'}), 
                              {'status': 500, 'headers': {'Content-Type': 'application/json'}})
        
        # Check if PR is merged or closed - reject if so
        if pr_data['is_merged']:
            return Response.new(json.dumps({'error': 'Cannot add merged PRs'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
        if pr_data['state'] == 'closed':
            return Response.new(json.dumps({'error': 'Cannot add closed PRs'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
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
        
        return Response.new(json.dumps({'success': True, 'data': pr_data}), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

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
        # Convert JS Array to Python list
        prs = result.results.to_py() if hasattr(result, 'results') else []
        
        return Response.new(json.dumps({'prs': prs}), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

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
        
        # Fetch fresh data from GitHub
        pr_data = await fetch_pr_data(result['repo_owner'], result['repo_name'], result['pr_number'])
        if not pr_data:
            return Response.new(json.dumps({'error': 'Failed to fetch PR data from GitHub'}), 
                              {'status': 500, 'headers': {'Content-Type': 'application/json'}})
        
        # Check if PR is now merged or closed - delete it from database
        if pr_data['is_merged'] or pr_data['state'] == 'closed':
            # Delete the PR from database
            delete_stmt = db.prepare('DELETE FROM prs WHERE id = ?').bind(pr_id)
            await delete_stmt.run()
            
            status_msg = 'merged' if pr_data['is_merged'] else 'closed'
            return Response.new(json.dumps({
                'success': True, 
                'removed': True,
                'message': f'PR has been {status_msg} and removed from tracking'
            }), 
                              {'headers': {'Content-Type': 'application/json'}})
        
        # Generate timestamps in Python for consistency and testability
        # Using ISO-8601 format with 'Z' suffix for cross-browser compatibility
        current_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Update database
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
        
        headers = {
            'User-Agent': 'PR-Tracker/1.0',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        # Fetch rate limit from GitHub API
        rate_limit_url = "https://api.github.com/rate_limit"
        response = await fetch_with_headers(rate_limit_url, headers)
        
        if response.status != 200:
            error_msg = await response.text()
            return Response.new(
                json.dumps({
                    'error': f'GitHub API Error: {response.status}',
                    'details': error_msg
                }), 
                {'status': response.status, 'headers': {'Content-Type': 'application/json'}}
            )
        
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
            {'headers': {
                'Content-Type': 'application/json',
                'Cache-Control': f'public, max-age={_RATE_LIMIT_CACHE_TTL}'
            }}
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
        }), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        # Database not configured
        return Response.new(json.dumps({
            'database_configured': False,
            'error': str(e),
            'environment': getattr(env, 'ENVIRONMENT', 'unknown')
        }), 
                          {'headers': {'Content-Type': 'application/json'}})

async def handle_pr_timeline(request, env, path):
    """
    GET /api/prs/{id}/timeline
    Fetch and return the full timeline for a PR
    """
    try:
        # Extract PR ID from path: /api/prs/123/timeline
        pr_id = path.split('/')[3]  # Split by / and get the ID
        
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
        timeline = build_pr_timeline(timeline_data, pr['author_login'])
        
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
    """
    try:
        # Extract PR ID from path: /api/prs/123/review-analysis
        pr_id = path.split('/')[3]
        
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
        timeline = build_pr_timeline(timeline_data, pr['author_login'])
        
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
                'total_feedback': review_data['total_feedback_count'],
                'responded_feedback': review_data['responded_count'],
                'response_rate': review_data['response_rate'],
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
    """
    try:
        # Extract PR ID from path: /api/prs/123/readiness
        pr_id = path.split('/')[3]
        
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
        timeline = build_pr_timeline(timeline_data, pr['author_login'])
        
        # Analyze review progress
        review_data = analyze_review_progress(timeline, pr['author_login'])
        
        # Classify review health
        review_classification, review_score = classify_review_health(review_data)
        
        # Calculate combined readiness
        readiness = calculate_pr_readiness(pr, review_classification, review_score)
        
        return Response.new(json.dumps({
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
            'readiness': readiness,
            'review_health': {
                'classification': review_classification,
                'score': review_score,
                'total_feedback': review_data['total_feedback_count'],
                'responded_feedback': review_data['responded_count'],
                'response_rate': review_data['response_rate'],
                'stale_feedback_count': len(review_data['stale_feedback'])
            },
            'ci_checks': {
                'passed': pr['checks_passed'],
                'failed': pr['checks_failed'],
                'skipped': pr['checks_skipped']
            }
        }), 
                          {'headers': {'Content-Type': 'application/json'}})
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
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})
    
    # Serve HTML for root path  
    if path == '/' or path == '/index.html':
        # Use env.ASSETS to serve static files if available
        if hasattr(env, 'ASSETS'):
            return await env.ASSETS.fetch(request)
        else:
            # Fallback: return simple message
            return Response.new('Please configure assets in wrangler.toml', 
                              {'status': 200, 'headers': {**cors_headers, 'Content-Type': 'text/html'}})
    
    # Initialize database schema on first API request (idempotent, safe to call multiple times)
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
    
    # Timeline endpoint - GET /api/prs/{id}/timeline
    if path.startswith('/api/prs/') and path.endswith('/timeline') and request.method == 'GET':
        response = await handle_pr_timeline(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    # Review analysis endpoint - GET /api/prs/{id}/review-analysis
    if path.startswith('/api/prs/') and path.endswith('/review-analysis') and request.method == 'GET':
        response = await handle_pr_review_analysis(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    # PR readiness endpoint - GET /api/prs/{id}/readiness
    if path.startswith('/api/prs/') and path.endswith('/readiness') and request.method == 'GET':
        response = await handle_pr_readiness(request, env, path)
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
