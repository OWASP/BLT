from js import Response, Headers, URL
import json
import hashlib
from datetime import datetime
from workers import WorkerEntrypoint #Added this new import to use the modern class-based structure for Cloudflare Workers. 

# ===================================
# Configuration
# ===================================
ALLOWED_ORIGINS = [
    'https://next.owaspbt.org',
    'http://localhost:3000',
    'http://localhost:8000',
]

FRONTEND_SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'Strict-Transport-Security': 'max-age=31536000',
    'X-Frame-Options': 'SAMEORIGIN',
    'X-XSS-Protection': '0',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
    'Cross-Origin-Resource-Policy': 'same-site',
    'X-Permitted-Cross-Domain-Policies': 'none',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; connect-src 'self' https:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'",
}

def apply_security_headers(js_headers):
    """Attach the canonical frontend security headers to a Headers object."""
    for key, value in FRONTEND_SECURITY_HEADERS.items():
        js_headers.set(key, value)
    return js_headers

# ===================================
# CORS Helpers
# ===================================
def get_cors_headers(origin):
    """Generate CORS headers for the response"""
    if not origin:
        return {}
        
    if origin in ALLOWED_ORIGINS:
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400',
        }
    return {}

def create_response(data, status=200, origin=None):
    """Create a JSON response with CORS headers"""
    js_headers = Headers.new()
    js_headers.set('Content-Type', 'application/json')
    apply_security_headers(js_headers)
    
    cors = get_cors_headers(origin)
    for k, v in cors.items():
        js_headers.set(k, v)
    
    return Response.new(
        json.dumps(data),
        status=status,
        headers=js_headers
    )

def handle_html_response(html, origin=None):
    """Create an HTML response with CORS headers"""
    js_headers = Headers.new()
    js_headers.set('Content-Type', 'text/html')
    # Allowed origins rather than using a wildcard
    cors = get_cors_headers(origin)
    for k, v in cors.items():
        js_headers.set(k, v)
    apply_security_headers(js_headers)
    
    return Response.new(
        html,
        status=200,
        headers=js_headers
    )

def handle_cors_preflight(origin):
    """Handle CORS preflight requests"""
    return Response.new(
        '',
        status=204,
        headers=Headers.new(get_cors_headers(origin))
    )


def apply_frontend_security_headers(asset_response):
    """Attach security headers to static asset responses served by ASSETS."""
    js_headers = Headers.new(asset_response.headers)
    apply_security_headers(js_headers)

    return Response.new(
        asset_response.body,
        status=asset_response.status,
        headers=js_headers
    )

# ===================================
# API Data
# ===================================

STATS = {
    'bugs_reported': '15,234',
    'active_researchers': '3,421',
    'rewards_distributed': '$248,500',
    'projects_protected': '892',
}

BUGS = [
    {
        'id': 1,
        'title': 'Reflected XSS in search results',
        'description': 'Search query is rendered without escaping in the demo target.',
        'severity': 'high',
        'status': 'open',
        'created_at': '2026-05-01T12:00:00Z',
    },
    {
        'id': 2,
        'title': 'Missing security headers',
        'description': 'Several pages are missing strict transport and frame protection headers.',
        'severity': 'medium',
        'status': 'triaged',
        'created_at': '2026-05-02T12:00:00Z',
    },
]

LEADERBOARD = [
    {'rank': 1, 'username': 'redteam_ria', 'points': 12840, 'bugs': 84, 'rewards': '$1,840'},
    {'rank': 2, 'username': 'payload_paul', 'points': 11720, 'bugs': 73, 'rewards': '$1,610'},
    {'rank': 3, 'username': 'edge_case_emi', 'points': 10950, 'bugs': 68, 'rewards': '$1,470'},
    {'rank': 4, 'username': 'headers_hari', 'points': 9820, 'bugs': 61, 'rewards': '$1,250'},
    {'rank': 5, 'username': 'cipher_sam', 'points': 8750, 'bugs': 55, 'rewards': '$1,090'},
]

PROJECTS = [
    {
        'name': 'OWASP BLT',
        'type': 'Open Source',
        'icon': 'fa-shield-halved',
        'description': 'Help secure the OWASP BLT platform itself. All severity levels welcome across the web app and API surfaces.',
        'status': 'Active',
        'bugs': 142,
        'reward': '$500',
    },
    {
        'name': 'API Gateway',
        'type': 'Cloud Security',
        'icon': 'fa-cloud',
        'description': 'Focus on authentication, rate limiting, and access control flaws in our public API gateway.',
        'status': 'Active',
        'bugs': 67,
        'reward': '$1,000',
    },
    {
        'name': 'Mobile Portal',
        'type': 'Web App',
        'icon': 'fa-mobile-screen',
        'description': 'Security testing for the mobile-facing portal. XSS, CSRF, and session handling are high priority.',
        'status': 'Active',
        'bugs': 53,
        'reward': '$750',
    },
]

# Avatar background palette, cycled by leaderboard position.
AVATAR_COLORS = [
    'bg-red-600 dark:bg-red-500 text-white',
    'bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-200',
    'bg-orange-400 dark:bg-orange-600 text-white',
    'bg-blue-500 text-white',
    'bg-purple-500 text-white',
]

# Project status badge styles, keyed by status label.
STATUS_BADGES = {
    'Active': 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400',
    'Critical Only': 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-400',
}


def avatar_initials(username):
    """Derive up to two uppercase initials from a username for the avatar bubble."""
    parts = [p for p in username.replace('-', '_').split('_') if p]
    if not parts:
        return username[:2].upper()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()

# ===================================
# Route Handlers
# ===================================

async def handle_stats(request, env=None):
    """Handle /api/stats endpoint"""
    html = f"""
    <div class="stat-card">
        <div class="stat-value">{STATS.get('bugs_reported', 0)}</div>
        <div class="stat-label">Bugs Reported</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{STATS.get('active_researchers', 0)}</div>
        <div class="stat-label">Active Researchers</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{STATS.get('rewards_distributed', '$0')}</div>
        <div class="stat-label">Rewards Distributed</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{STATS.get('projects_protected', 0)}</div>
        <div class="stat-label">Projects Protected</div>
    </div>
    """
    return handle_html_response(html, origin=request.headers.get('Origin'))

async def handle_auth_login(request, env=None):
    """Handle /api/auth/login endpoint"""
    try:
        body = await request.json()
        email = body.get('email')
        password = body.get('password')
        
        # Mock authentication - DO NOT USE IN PRODUCTION
        if email and password:
            user = {
                'id': 1,
                'username': email.split('@')[0],
                'email': email,
            }
            
            token = f"mock_{hashlib.sha256(f'{email}{datetime.now().isoformat()}'.encode()).hexdigest()}"
            
            return create_response({
                'success': True,
                'token': token,
                'user': user,
            }, origin=request.headers.get('Origin'))
        
        return create_response({
            'success': False,
            'error': 'Invalid credentials'
        }, status=401, origin=request.headers.get('Origin'))
        
    except Exception as e:
        return create_response({
            'success': False,
            'error': str(e)
        }, status=400, origin=request.headers.get('Origin'))

async def handle_auth_signup(request, env=None):
    """Handle /api/auth/signup endpoint"""
    try:
        body = await request.json()
        username = body.get('username')
        email = body.get('email')
        password = body.get('password')
        
        # IMPORTANT: This is mock signup for development/demo only
        # TODO: In production, implement proper user registration:
        # 1. Validate input (email format, password strength, username uniqueness)
        # 2. Hash password with bcrypt/argon2 before storing
        # 3. Check for existing user via the account API
        # 4. Create the user via the account API
        # 5. Send verification email
        # 6. Generate secure JWT token
        
        # Mock signup - DO NOT USE IN PRODUCTION
        if username and email and password:
            user = {
                'id': 1,
                'username': username,
                'email': email,
            }
            
            # WARNING: Mock token - NOT SECURE for production
            token = f"mock_{hashlib.sha256(f'{email}{datetime.now().isoformat()}'.encode()).hexdigest()}"
            
            return create_response({
                'success': True,
                'token': token,
                'user': user,
            }, origin=request.headers.get('Origin'))
        
        return create_response({
            'success': False,
            'error': 'Invalid signup data'
        }, status=400, origin=request.headers.get('Origin'))
        
    except Exception as e:
        return create_response({
            'success': False,
            'error': str(e)
        }, status=400, origin=request.headers.get('Origin'))

async def handle_auth_me(request, env=None):
    """Handle /api/auth/me endpoint"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return create_response({
            'error': 'Unauthorized'
        }, status=401, origin=request.headers.get('Origin'))
    
    token = auth_header.replace('Bearer ', '')
    
    # IMPORTANT: This is mock token validation for development/demo only
    # TODO: In production, implement proper JWT validation:
    # 1. Verify JWT signature with secret key
    # 2. Check token expiration
    # 3. Validate token claims
    # 4. Fetch current user data from the account API
    # Example: decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    
    # Mock token validation - DO NOT USE IN PRODUCTION
    if token.startswith('mock_'):
        # Extract email from mock token (this is insecure)
        # In production, decode JWT properly
        try:
            # For demo purposes, return a mock user
            user = {
                'id': 1,
                'username': 'demo_user',
                'email': 'demo@example.com',
            }
            return create_response({
                'user': user
            }, origin=request.headers.get('Origin'))
        except Exception:
            pass
    
    return create_response({
        'error': 'Invalid token'
    }, status=401, origin=request.headers.get('Origin'))

async def handle_auth_logout(request, env=None):
    """Handle /api/auth/logout endpoint"""
    # In production, invalidate the token through the auth API
    return create_response({
        'success': True
    }, origin=request.headers.get('Origin'))

async def handle_bugs_list(request, env=None):
    """Handle /api/bugs endpoint (GET and POST)"""
    if request.method == 'POST':
        try:
            body = await request.json()
            title = body.get('title')
            description = body.get('description')
            severity = body.get('severity')

            if not title or not description or not severity:
                return create_response({'error': 'Missing required bug report fields'}, status=400, origin=request.headers.get('Origin'))

            # Mock success response in HTML for HTMX
            html = """
                <div style="background: #ecfdf5; color: #065f46; padding: 2rem; border-radius: 0.5rem; text-align: center; border: 1px solid #10b981;">
                    <h2 style="margin-bottom: 1rem;">✅ Report Submitted!</h2>
                    <p>Thank you for contributing to OWASP BLT. Our team will review your report shortly.</p>
                    <a href="/" class="btn btn-primary" style="margin-top: 1.5rem; display: inline-block;">Back to Home</a>
                </div>
            """
            return handle_html_response(html, origin=request.headers.get('Origin'))
        except Exception as e:
            return create_response({'error': str(e)}, status=500, origin=request.headers.get('Origin'))

    # GET case (list bugs)
    return create_response({'bugs': BUGS}, origin=request.headers.get('Origin'))

async def handle_leaderboard(request, env=None):
    """Handle /api/leaderboard endpoint.

    Returns only the data rows. The page (leaderboard.html) already renders the
    column header and table shell, and swaps this markup into #leaderboard-body
    via HTMX, so the rows must match its Tailwind grid layout
    (columns: rank / researcher / bugs / points / rewards).
    """
    rows = ""
    for idx, item in enumerate(LEADERBOARD):
        color = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
        if item['rank'] == 1:
            rank_cell = '<div class="text-center"><i class="fa-solid fa-crown text-yellow-400 text-sm" aria-hidden="true"></i></div>'
        else:
            rank_cell = f'<div class="text-center text-sm font-bold text-gray-400 dark:text-gray-500">{item["rank"]}</div>'

        rows += f"""
        <div class="leaderboard-row grid grid-cols-[44px_1fr_80px_80px_80px] items-center px-4 py-3.5 border-b border-[#E5E5E5] dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
            {rank_cell}
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full {color} text-xs font-bold flex items-center justify-center shrink-0">{avatar_initials(item['username'])}</div>
                <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{item['username']}</span>
            </div>
            <div class="text-center text-sm font-semibold text-red-600 dark:text-red-400">{item['bugs']}</div>
            <div class="text-center text-sm font-semibold text-red-600 dark:text-red-400">{item['points']:,}</div>
            <div class="text-center text-sm text-gray-500 dark:text-gray-400">{item.get('rewards', 'N/A')}</div>
        </div>
        """
    return handle_html_response(rows, origin=request.headers.get('Origin'))

async def handle_projects(request, env=None):
    """Handle /api/projects endpoint.

    Returns project cards that match the Tailwind card layout in projects.html.
    HTMX swaps this markup into the grid container (hx-swap="innerHTML"), so the
    cards must use the same utility classes as the page's placeholder cards.
    """
    cards = ""
    for p in PROJECTS:
        status = p.get('status', 'Active')
        badge = STATUS_BADGES.get(status, STATUS_BADGES['Active'])
        cards += f"""
        <div class="bg-white dark:bg-gray-800 border border-[#E5E5E5] dark:border-gray-700 rounded-lg p-5 hover:border-red-200 dark:hover:border-red-800 hover:shadow-sm transition-all cursor-pointer group">
            <div class="flex items-start justify-between mb-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-red-50 dark:bg-red-950 flex items-center justify-center">
                        <i class="fa-solid {p.get('icon', 'fa-building')} text-red-600 dark:text-red-400 text-sm" aria-hidden="true"></i>
                    </div>
                    <div>
                        <h3 class="font-semibold text-gray-900 dark:text-gray-100 text-sm group-hover:text-red-600 dark:group-hover:text-red-400 transition-colors">{p['name']}</h3>
                        <p class="text-xs text-gray-400 dark:text-gray-500">{p['type']}</p>
                    </div>
                </div>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium {badge}">{status}</span>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-4">{p.get('description', '')}</p>
            <div class="flex items-center justify-between pt-4 border-t border-[#E5E5E5] dark:border-gray-700">
                <div class="flex items-center gap-4">
                    <div class="text-center"><div class="text-sm font-bold text-red-600 dark:text-red-400">{p.get('bugs', 0)}</div><div class="text-[10px] text-gray-400 dark:text-gray-500">Bugs Found</div></div>
                    <div class="text-center"><div class="text-sm font-bold text-red-600 dark:text-red-400">{p.get('reward', 'N/A')}</div><div class="text-[10px] text-gray-400 dark:text-gray-500">Max Reward</div></div>
                </div>
                <a href="#" class="text-xs font-medium text-red-600 dark:text-red-400 hover:underline">View <i class="fa-solid fa-arrow-right text-[10px]" aria-hidden="true"></i></a>
            </div>
        </div>
        """
    return handle_html_response(cards, origin=request.headers.get('Origin'))

# ===================================
# Router
# ===================================

ROUTES = {
    'GET': {
        '/api/stats': handle_stats,
        '/api/auth/me': handle_auth_me,
        '/api/bugs': handle_bugs_list,
        '/api/leaderboard': handle_leaderboard,
        '/api/projects': handle_projects,
    },
    'POST': {
        '/api/auth/login': handle_auth_login,
        '/api/auth/signup': handle_auth_signup,
        '/api/auth/logout': handle_auth_logout,
        '/api/bugs': handle_bugs_list,
    },
}

# ===================================
# Old-site links ("this page has moved") and 404
# ===================================

# blt.owasp.org now redirects to owaspblt.org with its path and query, so the old Django
# app's deep links (/issue/1/, /profile/<u>/, /api/v1/...) arrive at this Worker. That app
# (blt-legacy, formerly blt-core) is offline while its data is migrated, so its page links
# go to /moved, which says where that part of BLT lives now, and its API paths get a JSON
# answer saying the same.
MOVED_PATH = '/moved'
REPORT_PAGE = '/pages/report-bug'
API_HOME = 'https://api.owaspblt.org'

# First path segments of the legacy app's routes (blt-legacy/blt/urls.py). An allowlist,
# so blt-next's own routes and pages are never caught. Left out on purpose: '' (the home
# page), favicon.ico, robots.txt, .well-known, and debug-only routes (__debug__, 500,
# test-sentry). 'api' is not listed as a whole: see LEGACY_API_SEGMENTS.
LEGACY_SEGMENTS = frozenset({
    'Submitpr', 'about', 'accounts', 'activity', 'add-sizzle-checkin', 'add_domain_to_organization',
    'add_repo', 'adventures', 'all_activity', 'apps', 'assign-badge', 'auth', 'authenticate', 'bacon',
    'bacon-requests', 'badges', 'batch-send-bacon-tokens', 'bidding', 'blt-tomato', 'bounties',
    'bounty_payout', 'captcha', 'change_bid_status', 'check-in', 'check_domain_security_txt',
    'check_owasp_compliance', 'comment', 'content', 'contribute', 'contributor-stats', 'contributors',
    'create', 'create_github_issue', 'dashboard', 'delete_issue', 'delete_time_entry', 'deletions',
    'discussion-rooms', 'dislike_issue', 'distribute_bacon', 'domain', 'domains', 'donate',
    'duplicate-check-example', 'education', 'extension', 'features', 'feed', 'fetch-current-bid',
    'flag_issue', 'follow', 'generate_bid_image', 'get-github-data', 'get-recommended-articles',
    'get-recommended-communities', 'get-recommended-discussion-channels', 'get-recommended-repos',
    'get_unique_issues', 'github-issues', 'github-webhook', 'googleplayapp', 'gsoc', 'hackathons', 'hunt',
    'i18n', 'initiate-transaction', 'invite', 'invite-friend', 'issue', 'issues', 'jobs', 'join',
    'label_activity', 'leaderboard', 'like_issue', 'map', 'messaging', 'notifications', 'oauth',
    'open-source-sorting-hat', 'organization', 'organizations', 'owasp', 'page-vote',
    'pending-transactions', 'privacypolicy', 'profile', 'project', 'projects', 'queue', 'ratings',
    'redoc', 'referral', 'reminder-settings', 'remove_user_from_issue', 'repo_list', 'report',
    'report-ip', 'reported-ips', 'repos', 'repository', 'resolve', 'rest-auth', 'review', 'roadmap',
    'save_issue', 'scoreboard', 'search', 'security', 'select_bid', 'select_contribution',
    'send-test-reminder', 'sendgrid_webhook', 'set-theme', 'similarity_scan', 'simulation', 'sitemap',
    'sizzle', 'sizzle-daily-log', 'sizzle-docs', 'slack', 'social', 'socialaccounts', 'sponsor',
    'staking', 'start', 'stats', 'stats-dashboard', 'status', 'status_page', 'style-guide',
    'submit-roadmap-pr', 'swagger', 'swagger.json', 'swagger.yaml', 'teams', 'template_list', 'terms',
    'time-logs', 'trademarks', 'tz_detect', 'update-submission-status', 'update_bch_address', 'upload',
    'user-sizzle-report', 'user_challenges', 'users', 'video_call', 'view-pr-analysis', 'vote_count',
    'website_stats', 'weekly-report',
})

# blt-next serves /api/stats, /api/bugs, /api/auth/... itself. Only the legacy app's own
# /api/<segment>/ families are caught (not the debug-only /api/debug/).
LEGACY_API_SEGMENTS = frozenset({
    'v1', 'v2', 'bacon', 'get-wallet-balance', 'load-more-issues', 'messaging', 'organization', 'ossh',
    'room-messages', 'send-message', 'timelogsreport', 'trademarks',
})


# Where each part of the old site lives now: (first path segment(s), what it was, new URL).
# From the blt-core parity audit; only homes that really serve that feature are listed.
NEW_HOMES = [
    (('report',), 'Bug reporting', REPORT_PAGE),
    (('leaderboard', 'scoreboard', 'contributors', 'contributor-stats'),
     'The contributor leaderboard', 'https://pool.owaspblt.org/leaderboard'),
    (('hackathons',), 'Hackathons', 'https://hackathons.owaspblt.org/'),
    (('gsoc',), 'Google Summer of Code', 'https://gsoc.owaspblt.org/'),
    (('jobs',), 'Jobs', 'https://jobs.owaspblt.org/'),
    (('education', 'simulation'), 'Courses and security labs', 'https://university.owaspblt.org/'),
    (('sizzle', 'check-in', 'add-sizzle-checkin', 'sizzle-daily-log', 'sizzle-docs', 'user-sizzle-report',
      'reminder-settings', 'send-test-reminder'), 'Daily check-ins and reminders', 'https://sizzle.owaspblt.org/'),
    (('time-logs',), 'Time logs', 'https://timer.owaspblt.org/'),
    (('open-source-sorting-hat', 'get-recommended-articles', 'get-recommended-communities',
      'get-recommended-discussion-channels', 'get-recommended-repos'),
     'The Open Source Sorting Hat', 'https://ossh.owaspblt.org/'),
    (('projects', 'project'), 'OWASP projects', 'https://projects.owaspblt.org/'),
    (('repository', 'repo_list'), 'BLT repositories and their activity', 'https://waypoint.owaspblt.org/'),
    (('blt-tomato',), 'OWASP project funding', 'https://tomato.owaspblt.org/'),
    (('trademarks', 'similarity_scan'), 'Trademark and similarity checks', 'https://enforcement.owaspblt.org/'),
    (('check_owasp_compliance',), 'The OWASP compliance checker', 'https://wich.owaspblt.org/'),
    (('view-pr-analysis',), 'Pull request analysis', 'https://leaf.owaspblt.org/'),
    (('slack',), 'The BLT Slack apps', 'https://sammich.owaspblt.org/'),
    (('video_call',), 'Video calls', 'https://safecloak.owaspblt.org/'),
    (('bacon',), 'BACON rewards', 'https://rewards.owaspblt.org/'),
    (('swagger', 'swagger.json', 'swagger.yaml', 'redoc'), 'The BLT API and its docs', API_HOME + '/'),
    (('style-guide', 'template_list'), 'The BLT design system', 'https://design.owaspblt.org/'),
    (('extension',), 'The BLT browser extension', 'https://extension.owaspblt.org/'),
    (('about',), 'About BLT', '/pages/about'),
]


def _first_segments(path):
    parts = path.split('/')
    return (parts[1] if len(parts) > 1 else ''), (parts[2] if len(parts) > 2 else '')


def is_legacy_path(path):
    """True for paths that belonged to the old Django site (an allowlist of its routes)."""
    if not path.startswith('/') or path.startswith('//'):
        return False
    first, second = _first_segments(path)
    if first == 'api':
        return second in LEGACY_API_SEGMENTS
    return first in LEGACY_SEGMENTS


def new_home_for(path):
    """(what it was, new URL) for an old-site path, or None when nothing replaces it yet."""
    first, _ = _first_segments(path)
    for segments, label, url in NEW_HOMES:
        if first in segments:
            return label, url
    return None


def moved_location(path, search=''):
    """/moved?from=<old path and query>. Always a path on this site, never another host."""
    from urllib.parse import quote
    return MOVED_PATH + '?from=' + quote(path + (search or ''), safe='/')


def _redirect(location):
    js_headers = Headers.new()
    js_headers.set('Location', location)
    # Temporary: once the old data is migrated these links may point somewhere better.
    js_headers.set('Cache-Control', 'public, max-age=3600')
    apply_security_headers(js_headers)
    return Response.new('', status=302, headers=js_headers)


def legacy_api_response(path, request):
    """Old /api/v1/... calls get JSON (they come from scripts and apps, not browsers)."""
    return create_response({
        'error': 'This endpoint belonged to the old BLT API, which is offline while its data is migrated.',
        'path': path,
        'api': API_HOME,
        'report_bug': REPORT_PAGE,
    }, status=404, origin=request.headers.get('Origin'))


PAGE_STYLE = """
    body { margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
           font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #f9fafb; color: #111827; }
    main { max-width: 36rem; padding: 2rem 1rem; }
    h1 { font-size: 1.75rem; margin: 0 0 1rem; color: #dc2626; }
    p, li { line-height: 1.6; color: #4b5563; }
    code { background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 0.25rem; word-break: break-all; }
    a { color: #dc2626; font-weight: 600; }
    .box { border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 0.75rem 1rem; background: #fff; }
    @media (prefers-color-scheme: dark) {
      body { background: #111827; color: #f9fafb; } p, li { color: #d1d5db; } a, h1 { color: #f87171; }
      code { background: #1f2937; } .box { background: #1f2937; border-color: #374151; }
    }
"""


def _page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>{title} | OWASP BLT</title>
  <link rel="icon" href="/favicon.ico">
  <style>{PAGE_STYLE}</style>
</head>
<body>
  <main>
{body}
  </main>
</body>
</html>
"""


def _html_response(html_text, status):
    js_headers = Headers.new()
    js_headers.set('Content-Type', 'text/html; charset=utf-8')
    apply_security_headers(js_headers)
    return Response.new(html_text, status=status, headers=js_headers)


def moved_page_response(url):
    """The page old-site links land on. ?from= is shown escaped and only used for lookup."""
    from html import escape
    from urllib.parse import parse_qs
    old = (parse_qs((url.search or '').lstrip('?')).get('from') or [''])[0][:500]
    old_path = old.split('?', 1)[0]
    if old and is_legacy_path(old_path):
        intro = (f'<p>The page you opened, <code>{escape(old)}</code>, belonged to the old BLT site, '
                 'which is being migrated to the new BLT platform.</p>')
        home = new_home_for(old_path)
    else:
        intro = '<p>This page belonged to the old BLT site, which is being migrated to the new BLT platform.</p>'
        home = None
    if home:
        label, target = home
        where = f'<p class="box">{escape(label)} now lives at <a href="{escape(target)}">{escape(target)}</a>.</p>'
    else:
        where = '<p class="box">This part of BLT doesn\'t have a new home yet.</p>'
    body = f"""    <h1>This page has moved</h1>
    {intro}
    {where}
    <p>Found a bug? <a href="{REPORT_PAGE}">Report it here</a>.</p>
    <p>Bug reports, profiles, organizations and points from the old site will be back after the migration.</p>
    <p><a href="/">Go to the home page</a></p>"""
    return _html_response(_page('This page has moved', body), 200)


def not_found_response(path, request):
    """A clean 404: an HTML page for browsers, JSON for /api/ paths."""
    origin = request.headers.get('Origin')
    if path.startswith('/api/'):
        return create_response({'error': 'Not found', 'path': path}, status=404, origin=origin)
    body = f"""    <h1>404: page not found</h1>
    <p>This page doesn't exist on OWASP BLT.</p>
    <p>Found a bug? <a href="{REPORT_PAGE}">Report it here</a>.</p>
    <p><a href="/">Go to the home page</a></p>"""
    return _html_response(_page('Page not found', body), 404)


def handle_old_site(request, url):
    """Answer /moved and old-site links; None for everything else."""
    path = url.pathname
    if path in (MOVED_PATH, MOVED_PATH + '/') and request.method in ('GET', 'HEAD'):
        return moved_page_response(url)
    if not is_legacy_path(path):
        return None
    if path.startswith('/api/'):
        return legacy_api_response(path, request)
    return _redirect(moved_location(path, url.search))


async def route_request(request, env):
    """Route the request to the appropriate handler"""
    url = URL.new(request.url)
    path = url.pathname

    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return handle_cors_preflight(request.headers.get('Origin'))

    # Find and execute handler
    handler = ROUTES.get(request.method, {}).get(path)

    if handler:
        try:
            return await handler(request, env)
        except Exception as e:
            print(f"Handler Error: {e}")
            raise e

    # Old blt.owasp.org links and the /moved page.
    old_site = handle_old_site(request, url)
    if old_site:
        return old_site

    # Static assets. Cloudflare serves files that exist before the Worker runs, so this
    # is mostly a fallback (e.g. a request that skipped asset routing).
    # Pass the original Request through: building one from a Python dict
    # (Request.new(url, {...})) crashes Pyodide with an uncatchable fatal error, which is
    # what made every unknown path answer with Cloudflare error 1101.
    if request.method in ('GET', 'HEAD') and hasattr(env, 'ASSETS'):
        try:
            asset_response = await env.ASSETS.fetch(request)
            if asset_response.status != 404:
                return apply_frontend_security_headers(asset_response)
        except Exception as e:
            print(f"Assets Error: {e}")

    return not_found_response(path, request)

# ===================================
# Main Entry Point
# ===================================

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        """Main entry point for Cloudflare Worker"""
        try:
            return await route_request(request, self.env)
        except Exception as e:
            return create_response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=500, origin=request.headers.get('Origin'))
