from js import Response, Headers, URL, Request
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
    {'rank': 1, 'username': 'redteam_ria', 'points': 12840, 'bugs': 84},
    {'rank': 2, 'username': 'payload_paul', 'points': 11720, 'bugs': 73},
    {'rank': 3, 'username': 'edge_case_emi', 'points': 10950, 'bugs': 68},
    {'rank': 4, 'username': 'headers_hari', 'points': 9820, 'bugs': 61},
    {'rank': 5, 'username': 'cipher_sam', 'points': 8750, 'bugs': 55},
]

PROJECTS = [
    {'name': 'OWASP BLT', 'type': 'Open Source', 'reward': '$500+', 'bugs': 142},
    {'name': 'API Gateway', 'type': 'Cloud Security', 'reward': '$1,000+', 'bugs': 67},
    {'name': 'Mobile Portal', 'type': 'Web App', 'reward': '$750+', 'bugs': 53},
]

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
    """Handle /api/leaderboard endpoint"""
    rows = "".join([
        f"""
        <div class="leaderboard-row">
            <div class="rank">{item['rank']}</div>
            <div class="username">{item['username']}</div>
            <div class="stat">{item['points']} pts</div>
            <div class="stat">{item['bugs']} bugs</div>
        </div>
        """ for item in LEADERBOARD
    ])

    html = f"""
    <div class="leaderboard-table">
        <div class="leaderboard-row leaderboard-header">
            <div>Rank</div>
            <div>Researcher</div>
            <div style="text-align: right;">Points</div>
            <div style="text-align: right;">Bugs</div>
        </div>
        {rows}
    </div>
    """
    return handle_html_response(html, origin=request.headers.get('Origin'))

async def handle_projects(request, env=None):
    """Handle /api/projects endpoint"""
    cards = "".join([
        f"""
        <div class="project-card">
            <div class="project-header">
                <div class="project-logo">BT</div>
                <div class="project-info">
                    <div class="project-name">{p['name']}</div>
                    <div class="project-type">{p['type']}</div>
                </div>
            </div>
            <div class="project-reward">{p.get('reward', 'N/A')}</div>
            <div class="project-stats">
                <div class="stat">
                    <div class="stat-value">{p.get('bugs', 0)}</div>
                    <div class="stat-label">Bugs</div>
                </div>
                <div class="stat">
                    <div class="stat-value">Active</div>
                    <div class="stat-label">Status</div>
                </div>
            </div>
        </div>
        """ for p in PROJECTS
    ])
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
    
    # Handle root and static assets
    if hasattr(env, 'ASSETS'):
        try:
            fetch_url = request.url
            if path == '/':
                fetch_url = str(url).replace(path, '/index.html')

            # Use a Request object to preserve original method and headers
            asset_request = Request.new(fetch_url, { 'method': request.method, 'headers': request.headers })
            asset_response = await env.ASSETS.fetch(asset_request)
            return apply_frontend_security_headers(asset_response)
        except Exception as e:
            print(f"Assets Error: {e}")
    
    return create_response({'error': 'Not found', 'path': path}, status=404, origin=request.headers.get('Origin'))

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
