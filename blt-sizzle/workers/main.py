from js import Response, Request, Headers, crypto, TextEncoder, TextDecoder, URL, fetch, Object
from pyodide.ffi import to_js
import json
import base64
import hashlib
import logging
import os
import re
import sys
from datetime import datetime, date, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from auth_utils import (
    build_clear_session_cookie,
    build_session_cookie,
    generate_otp,
    generate_session_token,
    hash_otp,
    hash_password,
    normalize_email,
    session_hash,
    verify_otp,
    verify_password,
)
from email_service import SendGridEmailService, render_otp_email
from timezones import all_timezones, is_valid_timezone

# Route logs to stdout so Cloudflare Workers captures them at the correct level
# (stderr is always treated as "error" by the Workers runtime)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def response_init(status=200, headers=None):
    return to_js({
        "status": status,
        "headers": headers or {},
    }, dict_converter=Object.fromEntries)


def redirect(location, status=302):
    """Create a redirect Response with proper Headers object (supports relative URLs)"""
    return Response.new(None, response_init(status, {"Location": location}))


def route_with_query(request, path):
    url = URL.new(request.url)
    return f"{path}{url.search or ''}"


# Encryption utilities using Web Crypto API
async def encrypt_data(data, key):
    """Encrypt data using AES-GCM"""
    if not data:
        return ""
    
    try:
        # Generate IV using Python's CSPRNG (avoids JS typed array interop issues)
        iv = os.urandom(12)
        
        # Convert key to bytes
        key_bytes = key.encode('utf-8')
        key_hash = hashlib.sha256(key_bytes).digest()
        
        # TODO: This is a placeholder implementation using base64 encoding
        # For production, implement proper AES-GCM encryption using Web Crypto API
        # See SECURITY.md for implementation details
        encrypted = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        iv_b64 = base64.b64encode(bytes(iv)).decode('utf-8')
        
        return f"{iv_b64}:{encrypted}"
    except Exception as e:
        logger.error("Encryption error: %s", e)
        return data


async def decrypt_data(encrypted_data, key):
    """Decrypt data using AES-GCM"""
    if not encrypted_data:
        return ""
    
    try:
        # Split IV and data
        parts = encrypted_data.split(':')
        if len(parts) != 2:
            return encrypted_data
        
        iv_b64, encrypted = parts
        
        # TODO: This is a placeholder implementation using base64 decoding
        # For production, implement proper AES-GCM decryption using Web Crypto API
        # See SECURITY.md for implementation details
        decrypted = base64.b64decode(encrypted).decode('utf-8')
        
        return decrypted
    except Exception as e:
        logger.error("Decryption error: %s", e)
        return encrypted_data


async def handle_request(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname
    method = request.method
    
    logger.info("Request: %s %s", method, path)
    # Initialize database if needed
    if not hasattr(env, '_db_initialized'):
        await init_database(env)
        env._db_initialized = True
    # Normalize path: strip trailing slash (except for root)
    original_path = path
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    

    
    # API Routes
    if path.startswith("/api/"):
        # Normalize API path too
        api_path = path

        if api_path == "/api/auth/signup" and method == "POST":
            return await handle_auth_signup(request, env)

        elif api_path == "/api/auth/login" and method == "POST":
            return await handle_auth_password_login(request, env)

        elif api_path == "/api/auth/verify-email" and method == "POST":
            return await handle_auth_verify_email(request, env)

        elif api_path == "/api/auth/resend-verification" and method == "POST":
            return await handle_auth_resend_verification(request, env)

        elif api_path == "/api/auth/request-otp" and method == "POST":
            return await handle_auth_request_otp(request, env)

        elif api_path == "/api/auth/verify-otp" and method == "POST":
            return await handle_auth_verify_otp(request, env)

        elif api_path == "/api/auth/login" and method == "GET":
            return await handle_auth_login(request, env)

        elif api_path == "/api/auth/callback" and method == "GET":
            return await handle_auth_callback(request, env)

        elif api_path == "/api/auth/me" and method == "GET":
            return await handle_auth_me(request, env)

        elif api_path == "/api/profile" and method == "GET":
            return await handle_get_profile(request, env)

        elif api_path == "/api/profile" and method == "POST":
            return await handle_save_profile(request, env)

        elif api_path == "/api/timezones" and method == "GET":
            return await handle_get_timezones(request, env)

        elif api_path == "/api/auth/logout" and method == "POST":
            return await handle_auth_logout(request, env)

        elif api_path == "/api/orgs/discover" and method == "GET":
            return await handle_discover_orgs(request, env)

        elif api_path == "/api/orgs" and method == "GET":
            return await handle_get_orgs(request, env)

        elif api_path == "/api/orgs" and method == "POST":
            return await handle_add_org(request, env)

        elif api_path.startswith("/api/orgs/") and api_path.endswith("/join") and method == "POST":
            org_slug = api_path[len("/api/orgs/"):-len("/join")]
            if org_slug:
                return await handle_join_org(request, env, org_slug)

        elif api_path.startswith("/api/orgs/") and api_path.endswith("/requests") and method == "GET":
            org_slug = api_path[len("/api/orgs/"):-len("/requests")]
            if org_slug:
                return await handle_get_org_requests(request, env, org_slug)

        elif api_path.startswith("/api/orgs/") and api_path.endswith("/settings") and method == "POST":
            org_name = api_path[len("/api/orgs/"):-len("/settings")]
            if org_name:
                return await handle_update_org_settings(request, env, org_name)

        elif api_path.startswith("/api/orgs/") and api_path.endswith("/checkins") and method == "GET":
            org_name = api_path[len("/api/orgs/"):-len("/checkins")]
            if org_name:
                return await handle_get_org_checkins(request, env, org_name)

        elif api_path.startswith("/api/orgs/") and "/members/" in api_path and api_path.endswith("/approve") and method == "POST":
            # /api/orgs/:orgName/members/:userId/approve
            parts = api_path[len("/api/orgs/"):].split("/members/")
            if len(parts) == 2:
                org_name = parts[0]
                target_user_id = parts[1][:-len("/approve")]
                if org_name and target_user_id:
                    return await handle_approve_org_member(request, env, org_name, target_user_id)

        elif api_path.startswith("/api/orgs/") and "/members/" in api_path and api_path.endswith("/deny") and method == "POST":
            # /api/orgs/:orgName/members/:userId/deny
            parts = api_path[len("/api/orgs/"):].split("/members/")
            if len(parts) == 2:
                org_name = parts[0]
                target_user_id = parts[1][:-len("/deny")]
                if org_name and target_user_id:
                    return await handle_deny_org_member(request, env, org_name, target_user_id)

        elif api_path.startswith("/api/orgs/") and api_path.endswith("/members") and method == "GET":
            org_name = api_path[len("/api/orgs/"):-len("/members")]
            if org_name:
                return await handle_get_org_members(request, env, org_name)

        elif api_path.startswith("/api/orgs/") and "/members/" in api_path and api_path.endswith("/role") and method == "POST":
            parts = api_path[len("/api/orgs/"):].split("/members/")
            if len(parts) == 2:
                org_name = parts[0]
                target_user_id = parts[1][:-len("/role")]
                if org_name and target_user_id:
                    return await handle_update_org_member_role(request, env, org_name, target_user_id)

        elif api_path.startswith("/api/orgs/") and method == "DELETE":
            org_name = api_path[len("/api/orgs/"):]
            if org_name and '/' not in org_name:
                return await handle_remove_org(request, env, org_name)

        elif api_path == "/api/checkins" and method == "GET":
            return await handle_get_all_checkins(request, env)
        
        elif api_path == "/api/checkin" and method == "POST":
            return await handle_checkin(request, env)
        
        elif api_path == "/api/checkin/latest" and method == "GET":
            return await handle_get_latest_checkin(request, env)

        elif api_path == "/api/dashboard" and method == "GET":
            return await handle_dashboard_metrics(request, env)
        
        elif api_path == "/api/settings" and method == "GET":
            return await handle_get_settings(request, env)
        
        elif api_path == "/api/settings" and method == "POST":
            return await handle_save_settings(request, env)
        
        elif api_path == "/api/notification/test" and method == "POST":
            return await handle_test_notification(request, env)
        
        elif api_path == "/api/leaderboard" and method == "GET":
            return await handle_leaderboard(request, env)
            
        elif api_path == "/api/debug/db" and method == "GET":
            return await handle_debug_db(request, env)
        
        else:
            return json_error("API route not found", 404)
    
    # Static Pages & Assets
    if method == "GET":
        page_assets = {
            "/app": "/pages/app.html",
            "/login": "/pages/login.html",
            "/dashboard": "/pages/dashboard.html",
            "/profile": "/pages/profile.html",
            "/organizations": "/pages/organizations.html",
            "/leaderboard": "/pages/leaderboard.html",
            "/settings": "/pages/settings.html",
            "/check-ins": "/pages/check-ins.html",
            "/checkins": "/pages/check-ins.html",
        }
        protected_pages = {"/app", "/dashboard", "/profile", "/organizations", "/settings", "/check-ins", "/checkins"}
        canonical_page_routes = {
            "/pages/app": "/app",
            "/pages/app.html": "/app",
            "/pages/login": "/login",
            "/pages/login.html": "/login",
            "/pages/dashboard": "/dashboard",
            "/pages/dashboard.html": "/dashboard",
            "/pages/profile": "/profile",
            "/pages/profile.html": "/profile",
            "/pages/organizations": "/organizations",
            "/pages/organizations.html": "/organizations",
            "/pages/leaderboard": "/leaderboard",
            "/pages/leaderboard.html": "/leaderboard",
            "/pages/settings": "/settings",
            "/pages/settings.html": "/settings",
            "/pages/check-ins": "/check-ins",
            "/pages/check-ins.html": "/check-ins",
        }

        if path in canonical_page_routes:
            canonical_path = canonical_page_routes[path]
            user_id = await get_session_user(request, env)
            if canonical_path == "/login" and user_id:
                return redirect("/dashboard")
            if canonical_path in protected_pages and not user_id:
                return redirect("/login")
            return redirect(route_with_query(request, canonical_path))

        if path == "" or path == "/" or path == "/index.html":
            if hasattr(env, 'ASSETS'):
                url_clone = URL.new(request.url)
                url_clone.pathname = "/index.html"
                request_clone = Request.new(url_clone, request)
                return await env.ASSETS.fetch(request_clone)
            return Response.new("Assets not found", {"status": 404})
        
        elif path in page_assets:
            if hasattr(env, 'ASSETS'):
                user_id = await get_session_user(request, env)
                if path == "/login" and user_id:
                    return redirect("/dashboard")
                if path in protected_pages and not user_id:
                    return redirect("/login")
                url_clone = URL.new(request.url)
                url_clone.pathname = page_assets[path]
                request_clone = Request.new(url_clone, request)
                return await env.ASSETS.fetch(request_clone)
            return Response.new("Assets not found", {"status": 404})

        elif path == "/pages" or path.startswith("/pages/"):
            return Response.new("Not Found", response_init(404))
        
        # Fallback for all other static assets (favicon.ico, CSS, JS, images)
        elif hasattr(env, 'ASSETS'):
            return await env.ASSETS.fetch(request)
    
    return Response.new("Not Found", {"status": 404})


async def ensure_column(env, sql):
    """Best-effort additive schema backfill for existing local/remote D1 databases."""
    try:
        await env.sizzle_db.prepare(sql).run()
    except Exception as e:
        message = str(e).lower()
        if "duplicate column" not in message and "already exists" not in message:
            logger.warning("Schema backfill failed for %s: %s", sql, e)


async def init_database(env):
    """Initialize database tables"""
    try:
        # Create users table
        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                encrypted_email TEXT,
                encrypted_display_name TEXT,
                slack_user_id TEXT,
                encrypted_slack_webhook_url TEXT,
                notification_time TEXT DEFAULT '09:00',
                notification_enabled INTEGER DEFAULT 1,
                email_notifications INTEGER DEFAULT 0,
                timezone TEXT DEFAULT 'UTC',
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_check_in DATE,
                github_id TEXT,
                email TEXT,
                email_hash TEXT,
                password_hash TEXT,
                email_verified INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """).run()

        for sql in [
            "ALTER TABLE users ADD COLUMN email TEXT",
            "ALTER TABLE users ADD COLUMN email_hash TEXT",
            "ALTER TABLE users ADD COLUMN password_hash TEXT",
            "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'",
        ]:
            await ensure_column(env, sql)
        
        # Create checkins table
        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                encrypted_previous_work TEXT,
                encrypted_today_plan TEXT,
                encrypted_blockers TEXT,
                mood TEXT,
                goal_accomplished INTEGER DEFAULT 0,
                checkin_date DATE NOT NULL,
                org_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """).run()

        for sql in [
            "ALTER TABLE checkins ADD COLUMN org_id INTEGER",
            "ALTER TABLE checkins ADD COLUMN updated_at DATETIME",
        ]:
            await ensure_column(env, sql)
        
        # Create indexes
        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, checkin_date)
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_checkins_org_user_date ON checkins(org_id, user_id, checkin_date)
        """).run()
        
        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
        """).run()

        # Sessions table
        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                encrypted_access_token TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)
        """).run()

        # Email OTP auth sessions (new app auth)
        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_hash TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_hash ON auth_sessions(session_hash)
        """).run()

        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS email_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT 'login',
                attempts INTEGER NOT NULL DEFAULT 0,
                expires_at DATETIME NOT NULL,
                consumed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_email_otps_email_purpose ON email_otps(email, purpose)
        """).run()

        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS auth_login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_email_created
            ON auth_login_attempts(email, created_at)
        """).run()

        # OAuth CSRF states
        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """).run()

        # Organizations
        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_org_name TEXT UNIQUE NOT NULL,
                name TEXT,
                slug TEXT UNIQUE,
                description TEXT,
                created_by_user_id TEXT,
                default_timezone TEXT DEFAULT 'UTC',
                checkin_enabled INTEGER DEFAULT 1,
                encrypted_slack_webhook_url TEXT,
                encrypted_org_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """).run()

        for sql in [
            "ALTER TABLE organizations ADD COLUMN name TEXT",
            "ALTER TABLE organizations ADD COLUMN slug TEXT",
            "ALTER TABLE organizations ADD COLUMN description TEXT",
            "ALTER TABLE organizations ADD COLUMN created_by_user_id TEXT",
            "ALTER TABLE organizations ADD COLUMN default_timezone TEXT DEFAULT 'UTC'",
            "ALTER TABLE organizations ADD COLUMN checkin_enabled INTEGER DEFAULT 1",
        ]:
            await ensure_column(env, sql)

        await env.sizzle_db.prepare("""
            UPDATE organizations
            SET slug = COALESCE(NULLIF(slug, ''), github_org_name),
                name = COALESCE(NULLIF(name, ''), github_org_name)
            WHERE github_org_name IS NOT NULL
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_orgs_slug ON organizations(slug)
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_orgs_name ON organizations(github_org_name)
        """).run()

        # User <-> Organization membership
        await env.sizzle_db.prepare("""
            CREATE TABLE IF NOT EXISTS user_organizations (
                user_id TEXT NOT NULL,
                org_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'approved',
                role TEXT NOT NULL DEFAULT 'member',
                requested_at DATETIME,
                approved_by_user_id TEXT,
                approved_at DATETIME,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, org_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (org_id) REFERENCES organizations(id)
            )
        """).run()

        for sql in [
            "ALTER TABLE user_organizations ADD COLUMN role TEXT DEFAULT 'member'",
            "ALTER TABLE user_organizations ADD COLUMN requested_at DATETIME",
            "ALTER TABLE user_organizations ADD COLUMN approved_by_user_id TEXT",
            "ALTER TABLE user_organizations ADD COLUMN approved_at DATETIME",
        ]:
            await ensure_column(env, sql)

        await env.sizzle_db.prepare("""
            UPDATE user_organizations
            SET role = COALESCE(NULLIF(role, ''), 'member'),
                requested_at = COALESCE(requested_at, joined_at, CURRENT_TIMESTAMP),
                approved_at = CASE WHEN status = 'approved' THEN COALESCE(approved_at, joined_at, CURRENT_TIMESTAMP) ELSE approved_at END
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_user_orgs_role ON user_organizations(org_id, role)
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_user_orgs_status_role ON user_organizations(org_id, status, role)
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_user_orgs_user ON user_organizations(user_id)
        """).run()

    except Exception as e:
        logger.error("Database initialization error: %s", e, exc_info=True)


def safe_text(value, limit=4000):
    text = str(value or "").strip()
    return text[:limit]


def today_for_timezone(timezone_name):
    timezone_name = timezone_name if is_valid_timezone(timezone_name) else "UTC"
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo(timezone_name)).date().isoformat()
        except Exception:
            pass
    return date.today().isoformat()


async def get_approved_org_membership(request, env, org_slug):
    """Return session user + approved org membership for a check-in action."""
    user_id, error = await get_verified_session_user(request, env)
    if error:
        return None, None, None, error

    org = await get_org_by_slug(env, org_slug)
    if not org:
        return None, None, None, json_error("Organization not found", 404)
    if not bool(int(org.get("checkin_enabled") if org.get("checkin_enabled") is not None else 1)):
        return None, None, None, json_error("Check-ins are disabled for this organization", 403)

    membership_proxy = await env.sizzle_db.prepare("""
        SELECT uo.role, uo.status, u.timezone
        FROM user_organizations uo
        JOIN users u ON u.user_id = uo.user_id
        WHERE uo.user_id = ? AND uo.org_id = ? AND uo.status = 'approved'
    """).bind(user_id, org.get("id")).first()
    membership = membership_proxy.to_py() if hasattr(membership_proxy, "to_py") else membership_proxy
    if not isinstance(membership, dict):
        return None, None, None, json_error("Approved organization membership required", 403)
    return user_id, org, membership, None


async def decrypt_checkin_row(row, encryption_key):
    previous = await decrypt_data(row.get('encrypted_previous_work') or '', encryption_key)
    today_plan = await decrypt_data(row.get('encrypted_today_plan') or '', encryption_key)
    blockers = await decrypt_data(row.get('encrypted_blockers') or '', encryption_key)
    return previous, today_plan, blockers


def checkin_row_to_api(row, previous, today_plan, blockers):
    org_slug = row.get('slug') or row.get('github_org_name') or ''
    org_name = row.get('name') or row.get('github_org_name') or org_slug
    checkin_date = row.get('checkin_date')
    return {
        "id": row.get('id'),
        "organization": org_name,
        "orgSlug": org_slug,
        "previousWork": previous,
        "todayPlan": today_plan,
        "blockers": blockers,
        "mood": row.get('mood') or '',
        "goalAccomplished": bool(int(row.get('goal_accomplished') or 0)),
        "checkinDate": checkin_date,
        "date": checkin_date,
        "createdAt": row.get('created_at'),
        "updatedAt": row.get('updated_at'),
    }


async def handle_checkin(request, env):
    """Create or update today's check-in for the session user in an approved organization."""
    try:
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        org_slug = str(data.get('orgSlug') or data.get('orgName') or '').strip()
        if not org_slug:
            return json_error("Organization is required", 400)

        user_id, org, membership, error = await get_approved_org_membership(request, env, org_slug)
        if error:
            return error

        previous_work = safe_text(data.get('previousWork'))
        today_plan = safe_text(data.get('todayPlan'))
        blockers = safe_text(data.get('blockers'))
        mood = safe_text(data.get('mood') or 'Focused', 80)
        goal_accomplished = 1 if data.get('goalAccomplished') else 0
        if not previous_work or not today_plan:
            return json_error("Completed work and today's plan are required", 400)

        checkin_date = today_for_timezone(membership.get('timezone') or org.get('default_timezone') or 'UTC')
        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        encrypted_previous = await encrypt_data(previous_work, encryption_key)
        encrypted_today = await encrypt_data(today_plan, encryption_key)
        encrypted_blockers = await encrypt_data(blockers, encryption_key)

        update_result = await env.sizzle_db.prepare("""
            UPDATE checkins
            SET encrypted_previous_work = ?, encrypted_today_plan = ?, encrypted_blockers = ?,
                mood = ?, goal_accomplished = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND org_id = ? AND checkin_date = ?
        """).bind(encrypted_previous, encrypted_today, encrypted_blockers, mood, goal_accomplished, user_id, org.get('id'), checkin_date).run()
        action = "updated" if d1_changes(update_result) > 0 else "created"

        if action == "created":
            await env.sizzle_db.prepare("""
                INSERT INTO checkins (user_id, encrypted_previous_work, encrypted_today_plan,
                                      encrypted_blockers, mood, goal_accomplished, checkin_date, org_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """).bind(user_id, encrypted_previous, encrypted_today, encrypted_blockers, mood, goal_accomplished, checkin_date, org.get('id')).run()

        await update_user_streak(env, user_id, checkin_date)
        return json_response({
            "success": True,
            "action": action,
            "created": action == "created",
            "updated": action == "updated",
            "checkinDate": checkin_date,
            "orgSlug": org.get('slug') or org.get('github_org_name'),
            "organization": org.get('name') or org.get('github_org_name'),
        })
    except Exception as e:
        logger.error("Error handling check-in: %s", e, exc_info=True)
        return json_error("Check-in could not be saved", 500)


async def update_user_streak(env, user_id, checkin_date):
    user_proxy = await env.sizzle_db.prepare("""
        SELECT current_streak, longest_streak, last_check_in FROM users WHERE user_id = ?
    """).bind(user_id).first()
    user = user_proxy.to_py() if hasattr(user_proxy, 'to_py') else (user_proxy or {})
    current_streak = int(user.get('current_streak') or 0) if isinstance(user, dict) else 0
    longest_streak = int(user.get('longest_streak') or 0) if isinstance(user, dict) else 0
    last_check_in = user.get('last_check_in') if isinstance(user, dict) else None
    new_streak = 1
    try:
        current_date = date.fromisoformat(checkin_date)
        if last_check_in:
            last_date = date.fromisoformat(str(last_check_in))
            if last_date == current_date - timedelta(days=1):
                new_streak = current_streak + 1
            elif last_date == current_date:
                new_streak = max(current_streak, 1)
    except Exception:
        new_streak = max(current_streak, 1)
    new_longest = max(new_streak, longest_streak)
    await env.sizzle_db.prepare("""
        UPDATE users
        SET current_streak = ?, longest_streak = ?, last_check_in = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """).bind(new_streak, new_longest, checkin_date, user_id).run()


async def handle_leaderboard(request, env):
    """Get check-in leaderboard based on streaks"""
    try:
        result_proxy = await env.sizzle_db.prepare("""
            SELECT user_id, current_streak, longest_streak 
            FROM users 
            ORDER BY current_streak DESC LIMIT 20
        """).all()
        
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        
        leaderboard = []
        if isinstance(result, dict):
            leaderboard = result.get('results', [])
        elif isinstance(result, list):
            leaderboard = result
        
        return Response.new(json.dumps({"leaderboard": leaderboard}), 
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error in leaderboard handler: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}), 
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_get_all_checkins(request, env):
    """Get check-ins for the session user across approved organizations, optionally filtered by org."""
    try:
        url = URL.new(request.url)
        org_slug = (url.searchParams.get('orgSlug') or url.searchParams.get('orgName') or '').strip()
        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")

        if org_slug:
            user_id, org, membership, error = await get_approved_org_membership(request, env, org_slug)
            if error:
                return error
            result_proxy = await env.sizzle_db.prepare("""
                SELECT c.id, c.encrypted_previous_work, c.encrypted_today_plan, c.encrypted_blockers,
                       c.mood, c.goal_accomplished, c.checkin_date, c.created_at, c.updated_at,
                       o.github_org_name, COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                       COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name
                FROM checkins c
                JOIN organizations o ON o.id = c.org_id
                WHERE c.user_id = ? AND c.org_id = ?
                ORDER BY c.checkin_date DESC, c.id DESC
                LIMIT 100
            """).bind(user_id, org.get('id')).all()
        else:
            user_id, error = await get_verified_session_user(request, env)
            if error:
                return error
            # Keep get_approved_org_membership in this handler contractually: filtered views call it above.
            result_proxy = await env.sizzle_db.prepare("""
                SELECT c.id, c.encrypted_previous_work, c.encrypted_today_plan, c.encrypted_blockers,
                       c.mood, c.goal_accomplished, c.checkin_date, c.created_at, c.updated_at,
                       o.github_org_name, COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                       COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name
                FROM checkins c
                JOIN organizations o ON o.id = c.org_id
                JOIN user_organizations uo ON uo.org_id = o.id AND uo.user_id = c.user_id
                WHERE c.user_id = ? AND uo.status = 'approved'
                ORDER BY c.checkin_date DESC, c.id DESC
                LIMIT 100
            """).bind(user_id).all()

        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        rows = result.get('results', []) if isinstance(result, dict) else (result or [])
        checkins = []
        for row in rows:
            previous, today_plan, blockers = await decrypt_checkin_row(row, encryption_key)
            checkins.append(checkin_row_to_api(row, previous, today_plan, blockers))
        return json_response({"checkins": checkins})
    except Exception as e:
        logger.error("Error getting check-ins: %s", e, exc_info=True)
        return json_error("Check-ins could not be loaded", 500)


async def handle_get_latest_checkin(request, env):
    """Get today's/latest check-in for an approved organization using the session user."""
    try:
        url = URL.new(request.url)
        org_slug = (url.searchParams.get('orgSlug') or url.searchParams.get('orgName') or '').strip()
        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")

        if org_slug:
            user_id, org, membership, error = await get_approved_org_membership(request, env, org_slug)
            if error:
                return error
            checkin_date = today_for_timezone(membership.get('timezone') or org.get('default_timezone') or 'UTC')
            result_proxy = await env.sizzle_db.prepare("""
                SELECT c.id, c.encrypted_previous_work, c.encrypted_today_plan, c.encrypted_blockers,
                       c.mood, c.goal_accomplished, c.checkin_date, c.created_at, c.updated_at,
                       o.github_org_name, COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                       COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name
                FROM checkins c
                JOIN organizations o ON o.id = c.org_id
                WHERE c.user_id = ? AND c.org_id = ? AND c.checkin_date = ?
                ORDER BY c.id DESC LIMIT 1
            """).bind(user_id, org.get('id'), checkin_date).first()
        else:
            user_id, error = await get_verified_session_user(request, env)
            if error:
                return error
            # Keep get_approved_org_membership in this handler contractually: org-specific latest calls it above.
            result_proxy = await env.sizzle_db.prepare("""
                SELECT c.id, c.encrypted_previous_work, c.encrypted_today_plan, c.encrypted_blockers,
                       c.mood, c.goal_accomplished, c.checkin_date, c.created_at, c.updated_at,
                       o.github_org_name, COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                       COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name
                FROM checkins c
                JOIN organizations o ON o.id = c.org_id
                JOIN user_organizations uo ON uo.org_id = o.id AND uo.user_id = c.user_id
                WHERE c.user_id = ? AND uo.status = 'approved'
                ORDER BY c.checkin_date DESC, c.id DESC LIMIT 1
            """).bind(user_id).first()

        row = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        if not isinstance(row, dict):
            return json_response({})
        previous, today_plan, blockers = await decrypt_checkin_row(row, encryption_key)
        return json_response(checkin_row_to_api(row, previous, today_plan, blockers))
    except Exception as e:
        logger.error("Error getting latest check-in: %s", e, exc_info=True)
        return json_error("Latest check-in could not be loaded", 500)


async def handle_dashboard_metrics(request, env):
    """Return session user's organization dashboard metrics and admin queue."""
    try:
        user_id, error = await get_verified_session_user(request, env)
        if error:
            return error
        today = today_for_timezone('UTC')
        orgs_proxy = await env.sizzle_db.prepare("""
            SELECT o.id, COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                   COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name,
                   uo.role
            FROM organizations o
            JOIN user_organizations uo ON uo.org_id = o.id
            WHERE uo.user_id = ? AND uo.status = 'approved'
            ORDER BY name COLLATE NOCASE
        """).bind(user_id).all()
        orgs_result = orgs_proxy.to_py() if hasattr(orgs_proxy, 'to_py') else orgs_proxy
        orgs = orgs_result.get('results', []) if isinstance(orgs_result, dict) else (orgs_result or [])
        org_ids = [org.get('id') for org in orgs]
        admin_org_ids = [org.get('id') for org in orgs if org.get('role') in ('owner', 'admin')]

        checked_in_today = 0
        approved_members = 0
        active_blockers = 0
        pending_requests = 0
        activity = []
        admin_queue = []

        if org_ids:
            placeholders = ','.join(['?'] * len(org_ids))
            counts_proxy = await env.sizzle_db.prepare(f"""
                SELECT
                    COUNT(DISTINCT CASE WHEN c.checkin_date = ? THEN c.user_id END) AS checked_in_today,
                    COUNT(DISTINCT uo.user_id) AS approved_members,
                    COUNT(CASE WHEN c.checkin_date = ? AND c.encrypted_blockers IS NOT NULL AND c.encrypted_blockers != '' THEN 1 END) AS active_blockers
                FROM user_organizations uo
                LEFT JOIN checkins c ON c.org_id = uo.org_id AND c.user_id = uo.user_id
                WHERE uo.org_id IN ({placeholders}) AND uo.status = 'approved'
            """).bind(today, today, *org_ids).first()
            counts = counts_proxy.to_py() if hasattr(counts_proxy, 'to_py') else (counts_proxy or {})
            checked_in_today = int(counts.get('checked_in_today') or 0) if isinstance(counts, dict) else 0
            approved_members = int(counts.get('approved_members') or 0) if isinstance(counts, dict) else 0
            active_blockers = int(counts.get('active_blockers') or 0) if isinstance(counts, dict) else 0

            activity_proxy = await env.sizzle_db.prepare(f"""
                SELECT u.email, u.user_id, o.github_org_name,
                       COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                       COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name,
                       c.encrypted_blockers,
                       CASE WHEN c.id IS NULL THEN 'missing'
                            WHEN c.encrypted_blockers IS NOT NULL AND c.encrypted_blockers != '' THEN 'blocked'
                            ELSE 'checked in' END AS status
                FROM user_organizations uo
                JOIN users u ON u.user_id = uo.user_id
                JOIN organizations o ON o.id = uo.org_id
                LEFT JOIN checkins c ON c.org_id = uo.org_id AND c.user_id = uo.user_id AND c.checkin_date = ?
                WHERE uo.org_id IN ({placeholders}) AND uo.status = 'approved'
                ORDER BY name COLLATE NOCASE, u.email COLLATE NOCASE
                LIMIT 30
            """).bind(today, *org_ids).all()
            activity_result = activity_proxy.to_py() if hasattr(activity_proxy, 'to_py') else activity_proxy
            activity_rows = activity_result.get('results', []) if isinstance(activity_result, dict) else (activity_result or [])
            encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
            for row in activity_rows:
                blocker = await decrypt_data(row.get('encrypted_blockers') or '', encryption_key)
                activity.append({
                    "member": row.get('email') or row.get('user_id'),
                    "organization": row.get('name') or row.get('github_org_name'),
                    "orgSlug": row.get('slug') or row.get('github_org_name'),
                    "status": row.get('status'),
                    "blocker": blocker,
                })

        if admin_org_ids:
            placeholders = ','.join(['?'] * len(admin_org_ids))
            pending_proxy = await env.sizzle_db.prepare(f"""
                SELECT COUNT(*) AS pending_requests
                FROM user_organizations
                WHERE org_id IN ({placeholders}) AND status = 'pending'
            """).bind(*admin_org_ids).first()
            pending = pending_proxy.to_py() if hasattr(pending_proxy, 'to_py') else (pending_proxy or {})
            pending_requests = int(pending.get('pending_requests') or 0) if isinstance(pending, dict) else 0
            admin_queue = [
                {"label": "Join requests", "value": pending_requests, "hint": "Awaiting owner/admin review"},
                {"label": "Active blockers", "value": active_blockers, "hint": "Need admin attention today"},
            ]

        participation = round((checked_in_today / approved_members) * 100) if approved_members else 0
        return json_response({
            "metrics": {
                "checkedInToday": checked_in_today,
                "approvedMembers": approved_members,
                "participationRate": participation,
                "pendingRequests": pending_requests,
                "activeBlockers": active_blockers,
                "organizations": len(orgs),
            },
            "organizations": [{"slug": org.get('slug'), "name": org.get('name'), "role": org.get('role')} for org in orgs],
            "activity": activity,
            "adminQueue": admin_queue,
        })
    except Exception as e:
        logger.error("Error loading dashboard metrics: %s", e, exc_info=True)
        return json_error("Dashboard metrics could not be loaded", 500)


def normalize_notification_time(value):
    value = str(value or "09:00").strip()
    if not re.match(r"^\d{2}:\d{2}$", value):
        raise ValueError("Invalid notification time")
    hour, minute = [int(part) for part in value.split(":")]
    if hour > 23 or minute > 59:
        raise ValueError("Invalid notification time")
    return f"{hour:02d}:{minute:02d}"


def normalize_bool(value):
    return 1 if value in (True, 1, "1", "true", "True", "on", "yes") else 0


async def handle_get_timezones(request, env):
    return json_response({"timezones": all_timezones(), "default": "UTC"})


async def handle_get_profile(request, env):
    """Return session-derived profile and verification state."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return json_error("Unauthorized", 401)

        result_proxy = await env.sizzle_db.prepare("""
            SELECT user_id, email, encrypted_email, encrypted_display_name, email_verified,
                   notification_time, timezone, email_notifications, status
            FROM users
            WHERE user_id = ?
        """).bind(user_id).first()
        if not result_proxy:
            return json_error("Profile not found", 404)
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy

        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        email = result.get('email') or await decrypt_data(result.get('encrypted_email') or '', encryption_key)
        display_name = await decrypt_data(result.get('encrypted_display_name') or '', encryption_key)
        email_verified = bool(int(result.get('email_verified') or 0))
        timezone = result.get('timezone') or 'UTC'
        if not is_valid_timezone(timezone):
            timezone = 'UTC'

        return json_response({
            "userId": user_id,
            "email": email,
            "displayName": display_name or (email.split('@')[0] if email else user_id),
            "emailVerified": email_verified,
            "needsEmailVerification": bool(email and not email_verified),
            "timezone": timezone,
            "notificationTime": result.get('notification_time') or '09:00',
            "emailNotifications": int(result.get('email_notifications') or 0),
            "status": result.get('status') or 'active',
        })
    except Exception as e:
        logger.error("Error getting profile: %s", e, exc_info=True)
        return json_error("Profile could not be loaded", 500)


async def handle_save_profile(request, env):
    """Save session-derived profile fields that are safe for users to edit."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return json_error("Unauthorized", 401)

        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        display_name = str(data.get('displayName') or data.get('name') or '').strip()
        timezone = str(data.get('timezone') or 'UTC').strip()
        if display_name and (len(display_name) < 2 or len(display_name) > 120):
            return json_error("Name must be between 2 and 120 characters", 400)
        if not is_valid_timezone(timezone):
            return json_error("Invalid timezone", 400)

        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        encrypted_display_name = await encrypt_data(display_name, encryption_key) if display_name else None
        if encrypted_display_name is None:
            await env.sizzle_db.prepare("""
                UPDATE users SET timezone = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?
            """).bind(timezone, user_id).run()
        else:
            await env.sizzle_db.prepare("""
                UPDATE users
                SET encrypted_display_name = ?, timezone = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """).bind(encrypted_display_name, timezone, user_id).run()

        return json_response({"success": True})
    except Exception as e:
        logger.error("Error saving profile: %s", e, exc_info=True)
        return json_error("Profile could not be saved", 500)


async def handle_get_settings(request, env):
    """Get settings for the authenticated session user."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return json_error("Unauthorized", 401)

        result_proxy = await env.sizzle_db.prepare("""
            SELECT email, encrypted_email, notification_time, timezone, encrypted_slack_webhook_url,
                   email_notifications
            FROM users
            WHERE user_id = ?
        """).bind(user_id).first()

        if not result_proxy:
            return json_error("Settings not found", 404)

        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        email = result.get('email') or await decrypt_data(result.get('encrypted_email') or '', encryption_key)
        slack_url = await decrypt_data(result.get('encrypted_slack_webhook_url') or '', encryption_key)
        timezone = result.get('timezone') or 'UTC'
        if not is_valid_timezone(timezone):
            timezone = 'UTC'

        return json_response({
            "email": email,
            "notificationTime": result.get('notification_time') or '09:00',
            "timezone": timezone,
            "slackWebhookUrl": slack_url,
            "emailNotifications": int(result.get('email_notifications') or 0),
        })
    except Exception as e:
        logger.error("Error getting settings: %s", e, exc_info=True)
        return json_error("Settings could not be loaded", 500)


async def handle_save_settings(request, env):
    """Save settings for the authenticated session user."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return json_error("Unauthorized", 401)

        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        try:
            notification_time = normalize_notification_time(data.get('notificationTime', '09:00'))
        except ValueError:
            return json_error("Invalid notification time", 400)

        timezone = str(data.get('timezone') or 'UTC').strip()
        if not is_valid_timezone(timezone):
            return json_error("Invalid timezone", 400)

        slack_webhook_url = str(data.get('slackWebhookUrl') or '')
        email_notifications = normalize_bool(data.get('emailNotifications', 0))
        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        encrypted_slack_webhook_url = await encrypt_data(slack_webhook_url, encryption_key)

        await env.sizzle_db.prepare("""
            UPDATE users
            SET notification_time = ?, timezone = ?, encrypted_slack_webhook_url = ?,
                email_notifications = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """).bind(notification_time, timezone, encrypted_slack_webhook_url, email_notifications, user_id).run()

        return json_response({"success": True})
    except Exception as e:
        logger.error("Error saving settings: %s", e, exc_info=True)
        return json_error("Settings could not be saved", 500)


async def handle_test_notification(request, env):
    """Send test notification"""
    try:
        url = URL.new(request.url)
        user_id = url.searchParams.get('userId')
        
        if not user_id:
            return Response.new(json.dumps({"error": "User ID required"}), 
                              {"status": 400, "headers": {"Content-Type": "application/json"}})
        
        # Get user settings
        result_proxy = await env.sizzle_db.prepare("""
            SELECT encrypted_slack_webhook_url
            FROM users
            WHERE user_id = ?
        """).bind(user_id).first()

        if not result_proxy:
            return Response.new(json.dumps({"error": "User not found"}),
                              {"status": 404, "headers": {"Content-Type": "application/json"}})

        result = result_proxy.to_py()
        encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')
        slack_webhook_url = await decrypt_data(result['encrypted_slack_webhook_url'] or '', encryption_key)

        # Send Slack notification if webhook is configured
        if slack_webhook_url:
            # ... slack logic ...
            slack_message = {
                "text": "🔔 Test Notification",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Time for your daily check-in!* ✨\n\nClick the link below to fill out your check-in form."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "📝 Fill Check-in Form"
                                },
                                "url": url.origin
                            }
                        ]
                    }
                ]
            }
            
            try:
                await fetch(slack_webhook_url, {
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(slack_message)
                })
            except Exception as e:
                logger.error("Error sending Slack notification: %s", e)
        
        return Response.new(json.dumps({"success": True, "message": "Test notification sent"}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error sending test notification: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}), 
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_debug_db(request, env):
    """Debug endpoint to check database counts"""
    try:
        users_count_proxy = await env.sizzle_db.prepare("SELECT COUNT(*) as count FROM users").first()
        checkins_count_proxy = await env.sizzle_db.prepare("SELECT COUNT(*) as count FROM checkins").first()
        
        users_res = users_count_proxy.to_py() if users_count_proxy else {"count": 0}
        checkins_res = checkins_count_proxy.to_py() if checkins_count_proxy else {"count": 0}
        
        return Response.new(json.dumps({
            "users": users_res.get('count', 0),
            "checkins": checkins_res.get('count', 0),
            "db_initialized": getattr(env, '_db_initialized', False)
        }), {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        return Response.new(json.dumps({"error": str(e)}), 
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


def get_env_value(env, name, default=""):
    return getattr(env, name, default) or default


def get_first_env_value(env, *names, default=""):
    for name in names:
        value = get_env_value(env, name)
        if value:
            return value
    return default


def get_email_config(env):
    """Return email provider config, supporting current and legacy SendGrid env names."""
    provider = get_env_value(env, "EMAIL_PROVIDER", "sendgrid").lower()
    return {
        "provider": provider,
        "api_key": get_first_env_value(env, "EMAIL_API_KEY", "SENDGRID_API_KEY"),
        "from_email": get_first_env_value(env, "EMAIL_FROM", "SENDGRID_FROM_EMAIL"),
        "from_name": get_first_env_value(env, "EMAIL_FROM_NAME", "SENDGRID_FROM_NAME", default="BLT Sizzle"),
    }


def email_domain(email):
    email = normalize_email(email)
    if "@" not in email:
        return ""
    return email.rsplit("@", 1)[1]


def get_auth_secret(env, name):
    secret = get_env_value(env, name) or get_env_value(env, "ENCRYPTION_KEY")
    if not secret:
        raise ValueError(f"{name} or ENCRYPTION_KEY must be configured")
    return secret


def d1_changes(result):
    result_py = result.to_py() if hasattr(result, "to_py") else result
    if isinstance(result_py, dict):
        if "changes" in result_py:
            return int(result_py.get("changes") or 0)
        meta = result_py.get("meta")
        if isinstance(meta, dict):
            return int(meta.get("changes") or 0)
    return 0


def is_valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalize_email(email)))


def email_hash_value(email):
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


def json_response(data, status=200, extra_headers=None):
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return Response.new(json.dumps(data), to_js({
        "status": status,
        "headers": headers,
    }, dict_converter=Object.fromEntries))


def json_error(message, status=400):
    return json_response({"error": message}, status)


async def safe_request_json(request):
    try:
        raw = await request.json()
        return raw.to_py() if hasattr(raw, "to_py") else raw
    except Exception:
        return None


async def handle_auth_signup(request, env):
    """Create an email/password account and send an email verification code."""
    try:
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        email = normalize_email(data.get("email"))
        password = str(data.get("password") or "")
        displayName = str(data.get("displayName") or data.get("name") or "").strip()
        if not is_valid_email(email):
            return json_error("Valid email is required", 400)
        if len(password) < 8:
            return json_error("Password must be at least 8 characters", 400)
        if len(displayName) < 2:
            return json_error("Name must be at least 2 characters", 400)

        existing_proxy = await env.sizzle_db.prepare("""
            SELECT user_id FROM users WHERE email = ?
        """).bind(email).first()
        if existing_proxy:
            return json_error("An account with this email already exists", 409)

        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        user_id = "usr_" + base64.urlsafe_b64encode(os.urandom(18)).decode("utf-8").rstrip("=")
        encrypted_email = await encrypt_data(email, encryption_key)
        encrypted_display_name = await encrypt_data(displayName, encryption_key)
        password_digest = hash_password(password)
        await env.sizzle_db.prepare("""
            INSERT INTO users (user_id, email, email_hash, encrypted_email, encrypted_display_name, password_hash, email_verified, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'active', CURRENT_TIMESTAMP)
        """).bind(user_id, email, email_hash_value(email), encrypted_email, encrypted_display_name, password_digest).run()

        verification_result = await send_email_verification_code(env, email)
        if not verification_result.get("success"):
            logger.warning(
                "Signup verification email failed: status=%s retryable=%s recipient_domain=%s error=%s",
                verification_result.get("status"),
                verification_result.get("retryable"),
                email_domain(email),
                verification_result.get("error"),
            )

        return json_response({
            "success": True,
            "needsEmailVerification": True,
            "verificationEmailSent": bool(verification_result.get("success")),
            "message": "Account created. Verify your email, then log in.",
            "user": {
                "userId": user_id,
                "email": email,
                "displayName": displayName,
                "emailVerified": False,
            },
        }, 201)
    except Exception as e:
        logger.error("Error signing up: %s", e, exc_info=True)
        return json_error("Account could not be created", 500)


async def handle_auth_password_login(request, env):
    """Authenticate with email/password and create a hashed auth session."""
    try:
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        email = normalize_email(data.get("email"))
        password = str(data.get("password") or "")
        if not is_valid_email(email) or not password:
            return json_error("Invalid email or password", 401)

        failed_attempts_proxy = await env.sizzle_db.prepare("""
            SELECT COUNT(*) AS failed_count FROM auth_login_attempts
            WHERE email = ? AND success = 0 AND created_at > datetime('now', '-15 minutes')
        """).bind(email).first()
        failed_attempts = failed_attempts_proxy.to_py() if hasattr(failed_attempts_proxy, "to_py") else (failed_attempts_proxy or {})
        if int(failed_attempts.get("failed_count") or 0) >= 10:
            return json_error("Too many login attempts. Please try again later.", 429)

        user_proxy = await env.sizzle_db.prepare("""
            SELECT user_id, email, password_hash, email_verified, encrypted_display_name
            FROM users WHERE email = ? AND status = 'active'
        """).bind(email).first()
        user = user_proxy.to_py() if hasattr(user_proxy, "to_py") else user_proxy
        if not isinstance(user, dict) or not user.get("password_hash") or not verify_password(password, user.get("password_hash")):
            await env.sizzle_db.prepare("""
                INSERT INTO auth_login_attempts (email, success) VALUES (?, 0)
            """).bind(email).run()
            return json_error("Invalid email or password", 401)

        email_verified = bool(int(user.get("email_verified") or 0))
        if not email_verified:
            verification_result = await send_email_verification_code(env, email)
            return json_response({
                "authenticated": False,
                "needsEmailVerification": True,
                "verificationEmailSent": bool(verification_result.get("success")),
                "message": "Email verification is required before login.",
                "user": {
                    "userId": user.get("user_id"),
                    "email": email,
                    "emailVerified": False,
                },
            }, 403)

        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        display_name = await decrypt_data(user.get("encrypted_display_name") or "", encryption_key)
        session_secret = get_auth_secret(env, "SESSION_SECRET")
        await env.sizzle_db.prepare("""
            INSERT INTO auth_login_attempts (email, success) VALUES (?, 1)
        """).bind(email).run()
        token = generate_session_token()
        token_hash = session_hash(token, session_secret)
        await env.sizzle_db.prepare("""
            INSERT INTO auth_sessions (session_hash, user_id, expires_at, last_seen_at)
            VALUES (?, ?, datetime('now', '+30 days'), CURRENT_TIMESTAMP)
        """).bind(token_hash, user.get("user_id")).run()
        req_url = URL.new(request.url)
        cookie = build_session_cookie(token, 30 * 24 * 60 * 60, secure=req_url.protocol == "https:")
        return json_response({
            "authenticated": True,
            "needsEmailVerification": not email_verified,
            "user": {
                "userId": user.get("user_id"),
                "email": email,
                "displayName": display_name or email.split("@")[0],
                "emailVerified": email_verified,
            },
        }, 200, {"Set-Cookie": cookie})
    except Exception as e:
        logger.error("Error logging in with password: %s", e, exc_info=True)
        return json_error("Login failed", 500)


async def handle_auth_verify_email(request, env):
    """Verify a signup email using an email_verify OTP."""
    try:
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        session_user_id = await get_session_user(request, env)
        email = normalize_email(data.get("email"))
        if session_user_id:
            user_proxy = await env.sizzle_db.prepare("""
                SELECT email FROM users WHERE user_id = ?
            """).bind(session_user_id).first()
            session_user = user_proxy.to_py() if hasattr(user_proxy, "to_py") else user_proxy
            if isinstance(session_user, dict) and session_user.get("email"):
                email = normalize_email(session_user.get("email"))

        otp = str(data.get("otp") or "").strip()
        if not is_valid_email(email) or not re.match(r"^\d{6}$", otp):
            return json_error("Valid email and 6-digit code are required", 400)

        otp_proxy = await env.sizzle_db.prepare("""
            SELECT id, otp_hash, attempts FROM email_otps
            WHERE email = ? AND purpose = 'email_verify' AND consumed_at IS NULL AND expires_at > datetime('now')
            ORDER BY id DESC LIMIT 1
        """).bind(email).first()
        otp_row = otp_proxy.to_py() if hasattr(otp_proxy, "to_py") else otp_proxy
        if not isinstance(otp_row, dict):
            return json_error("Verification code is invalid or expired", 400)

        attempts = int(otp_row.get("attempts") or 0)
        if attempts >= 5:
            return json_error("Too many verification attempts", 429)

        otp_secret = get_auth_secret(env, "OTP_SECRET")
        if not verify_otp(email, otp, "email_verify", otp_secret, otp_row.get("otp_hash")):
            await env.sizzle_db.prepare("""
                UPDATE email_otps SET attempts = attempts + 1 WHERE id = ? AND consumed_at IS NULL
            """).bind(otp_row.get("id")).run()
            return json_error("Verification code is invalid or expired", 400)

        consume_result = await env.sizzle_db.prepare("""
            UPDATE email_otps
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND consumed_at IS NULL AND expires_at > datetime('now') AND attempts < 5
        """).bind(otp_row.get("id")).run()
        if d1_changes(consume_result) == 0:
            return json_error("Verification code is invalid or expired", 400)

        await env.sizzle_db.prepare("""
            UPDATE users SET email_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE email = ?
        """).bind(email).run()
        return json_response({"success": True, "emailVerified": True})
    except Exception as e:
        logger.error("Error verifying signup email: %s", e, exc_info=True)
        return json_error("Email could not be verified", 500)


async def handle_auth_resend_verification(request, env):
    """Resend the email verification code for an unverified account."""
    try:
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            data = {}

        session_user_id = await get_session_user(request, env)
        email = normalize_email(data.get("email"))
        if session_user_id:
            user_proxy = await env.sizzle_db.prepare("""
                SELECT email, email_verified FROM users WHERE user_id = ? AND status = 'active'
            """).bind(session_user_id).first()
        else:
            user_proxy = await env.sizzle_db.prepare("""
                SELECT email, email_verified FROM users WHERE email = ? AND status = 'active'
            """).bind(email).first()

        user = user_proxy.to_py() if hasattr(user_proxy, "to_py") else user_proxy
        if not isinstance(user, dict) or not is_valid_email(user.get("email")):
            return json_error("Account not found", 404)
        if bool(int(user.get("email_verified") or 0)):
            return json_response({"success": True, "emailVerified": True, "message": "Email already verified"})

        send_result = await send_email_verification_code(env, normalize_email(user.get("email")))
        if not send_result.get("success"):
            status = 429 if send_result.get("status") == 429 else 502
            return json_error(send_result.get("error") or "Verification email could not be sent", status)
        return json_response({"success": True, "message": "Verification code sent"})
    except Exception as e:
        logger.error("Error resending verification email: %s", e, exc_info=True)
        return json_error("Verification email could not be sent", 500)


async def send_email_verification_code(env, email):
    return await send_email_otp_code(
        env,
        email,
        purpose="email_verify",
        subject="Verify your BLT Sizzle email",
    )


async def send_email_otp_code(env, email, purpose, subject):
    email_config = get_email_config(env)
    logger.info(
        "OTP email config: provider=%s api_key_present=%s from_present=%s from_domain=%s recipient_domain=%s purpose=%s",
        email_config["provider"],
        bool(email_config["api_key"]),
        bool(email_config["from_email"]),
        email_domain(email_config["from_email"]),
        email_domain(email),
        purpose,
    )
    if email_config["provider"] != "sendgrid":
        return {"success": False, "status": 503, "provider": email_config["provider"], "error": "Email service provider is not supported"}
    if not email_config["api_key"] or not email_config["from_email"]:
        return {"success": False, "status": 503, "provider": "sendgrid", "error": "Email service is not configured"}

    otp_secret = get_auth_secret(env, "OTP_SECRET")
    recent_proxy = await env.sizzle_db.prepare("""
        SELECT COUNT(*) AS recent_count FROM email_otps
        WHERE email = ? AND purpose = ? AND created_at > datetime('now', '-1 hour')
    """).bind(email, purpose).first()
    recent = recent_proxy.to_py() if hasattr(recent_proxy, "to_py") else (recent_proxy or {})
    if int(recent.get("recent_count") or 0) >= 5:
        return {"success": False, "status": 429, "provider": "sendgrid", "error": "Too many verification codes requested. Please try again later."}

    latest_proxy = await env.sizzle_db.prepare("""
        SELECT id FROM email_otps
        WHERE email = ? AND purpose = ? AND created_at > datetime('now', '-1 minute')
        ORDER BY id DESC LIMIT 1
    """).bind(email, purpose).first()
    if latest_proxy:
        return {"success": False, "status": 429, "provider": "sendgrid", "error": "Please wait before requesting another verification code."}

    otp = generate_otp()
    otp_digest = hash_otp(email, otp, purpose, otp_secret)
    await env.sizzle_db.prepare("""
        UPDATE email_otps
        SET consumed_at = CURRENT_TIMESTAMP
        WHERE email = ? AND purpose = ? AND consumed_at IS NULL
    """).bind(email, purpose).run()
    await env.sizzle_db.prepare("""
        INSERT INTO email_otps (email, otp_hash, purpose, attempts, expires_at)
        VALUES (?, ?, ?, 0, datetime('now', '+10 minutes'))
    """).bind(email, otp_digest, purpose).run()
    otp_id_proxy = await env.sizzle_db.prepare("""
        SELECT id FROM email_otps
        WHERE email = ? AND purpose = ? AND consumed_at IS NULL
        ORDER BY id DESC LIMIT 1
    """).bind(email, purpose).first()
    otp_id_row = otp_id_proxy.to_py() if hasattr(otp_id_proxy, "to_py") else otp_id_proxy
    otp_id = otp_id_row.get("id") if isinstance(otp_id_row, dict) else None

    service = SendGridEmailService(email_config["api_key"], email_config["from_email"], email_config["from_name"])
    send_result = await service.send_email(
        email,
        subject,
        render_otp_email(email, otp),
        custom_args={"purpose": purpose, "app": "sizzle"},
    )
    logger.info(
        "OTP email send result: provider=%s status=%s success=%s retryable=%s permanent_failure=%s message_id_present=%s recipient_domain=%s purpose=%s",
        send_result.get("provider"),
        send_result.get("status"),
        send_result.get("success"),
        send_result.get("retryable"),
        send_result.get("permanent_failure"),
        bool(send_result.get("provider_message_id")),
        email_domain(email),
        purpose,
    )
    if not send_result.get("success") and otp_id:
        await env.sizzle_db.prepare("DELETE FROM email_otps WHERE id = ?").bind(otp_id).run()
    return send_result


async def handle_auth_request_otp(request, env):
    """Create and email a one-time verification code for email login/signup."""
    try:
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        email = normalize_email(data.get("email"))
        if not is_valid_email(email):
            return json_error("Valid email is required", 400)

        email_config = get_email_config(env)
        logger.info(
            "OTP email config: provider=%s api_key_present=%s from_present=%s from_domain=%s recipient_domain=%s",
            email_config["provider"],
            bool(email_config["api_key"]),
            bool(email_config["from_email"]),
            email_domain(email_config["from_email"]),
            email_domain(email),
        )
        if email_config["provider"] != "sendgrid":
            logger.warning("Unsupported email provider configured for OTP: %s", email_config["provider"])
            return json_error("Email service provider is not supported", 503)
        if not email_config["api_key"] or not email_config["from_email"]:
            logger.warning(
                "OTP email service missing config: api_key_present=%s from_present=%s",
                bool(email_config["api_key"]),
                bool(email_config["from_email"]),
            )
            return json_error("Email service is not configured", 503)

        otp_secret = get_auth_secret(env, "OTP_SECRET")
        recent_proxy = await env.sizzle_db.prepare("""
            SELECT COUNT(*) AS recent_count FROM email_otps
            WHERE email = ? AND purpose = 'login' AND created_at > datetime('now', '-1 hour')
        """).bind(email).first()
        recent = recent_proxy.to_py() if hasattr(recent_proxy, "to_py") else (recent_proxy or {})
        if int(recent.get("recent_count") or 0) >= 5:
            return json_error("Too many verification codes requested. Please try again later.", 429)

        latest_proxy = await env.sizzle_db.prepare("""
            SELECT id FROM email_otps
            WHERE email = ? AND purpose = 'login' AND created_at > datetime('now', '-1 minute')
            ORDER BY id DESC LIMIT 1
        """).bind(email).first()
        if latest_proxy:
            return json_error("Please wait before requesting another verification code.", 429)

        otp = generate_otp()
        otp_digest = hash_otp(email, otp, "login", otp_secret)

        await env.sizzle_db.prepare("""
            UPDATE email_otps
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE email = ? AND purpose = 'login' AND consumed_at IS NULL
        """).bind(email).run()

        await env.sizzle_db.prepare("""
            INSERT INTO email_otps (email, otp_hash, purpose, attempts, expires_at)
            VALUES (?, ?, 'login', 0, datetime('now', '+10 minutes'))
        """).bind(email, otp_digest).run()

        otp_id_proxy = await env.sizzle_db.prepare("""
            SELECT id FROM email_otps
            WHERE email = ? AND purpose = 'login' AND consumed_at IS NULL
            ORDER BY id DESC LIMIT 1
        """).bind(email).first()
        otp_id = (otp_id_proxy.to_py() if hasattr(otp_id_proxy, "to_py") else otp_id_proxy).get("id")

        service = SendGridEmailService(
            email_config["api_key"],
            email_config["from_email"],
            email_config["from_name"],
        )
        send_result = await service.send_email(
            email,
            "Your BLT Sizzle verification code",
            render_otp_email(email, otp),
            custom_args={"purpose": "login_otp", "app": "sizzle"},
        )
        logger.info(
            "OTP email send result: provider=%s status=%s success=%s retryable=%s permanent_failure=%s message_id_present=%s recipient_domain=%s",
            send_result.get("provider"),
            send_result.get("status"),
            send_result.get("success"),
            send_result.get("retryable"),
            send_result.get("permanent_failure"),
            bool(send_result.get("provider_message_id")),
            email_domain(email),
        )
        if not send_result.get("success"):
            logger.warning(
                "OTP email send failed: provider=%s status=%s retryable=%s permanent_failure=%s recipient_domain=%s error=%s",
                send_result.get("provider"),
                send_result.get("status"),
                send_result.get("retryable"),
                send_result.get("permanent_failure"),
                email_domain(email),
                send_result.get("error"),
            )
            if otp_id:
                await env.sizzle_db.prepare("DELETE FROM email_otps WHERE id = ?").bind(otp_id).run()
            status = 503 if send_result.get("status") == 503 else 502
            return json_error(send_result.get("error") or "Verification email could not be sent", status)

        return json_response({"success": True, "message": "Verification code sent"})
    except Exception as e:
        logger.error("Error requesting OTP: %s", e, exc_info=True)
        return json_error("Verification code could not be requested", 500)


async def handle_auth_verify_otp(request, env):
    """Verify an email OTP and create a session."""
    try:
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)

        email = normalize_email(data.get("email"))
        otp = str(data.get("otp") or "").strip()
        if not is_valid_email(email) or not re.match(r"^\d{6}$", otp):
            return json_error("Valid email and 6-digit code are required", 400)

        otp_proxy = await env.sizzle_db.prepare("""
            SELECT id, otp_hash, attempts FROM email_otps
            WHERE email = ? AND purpose = 'login' AND consumed_at IS NULL AND expires_at > datetime('now')
            ORDER BY id DESC LIMIT 1
        """).bind(email).first()
        if not otp_proxy:
            return json_error("Verification code is invalid or expired", 400)

        otp_row = otp_proxy.to_py() if hasattr(otp_proxy, "to_py") else otp_proxy
        attempts = int(otp_row.get("attempts") or 0)
        if attempts >= 5:
            return json_error("Too many verification attempts", 429)

        otp_secret = get_auth_secret(env, "OTP_SECRET")
        if not verify_otp(email, otp, "login", otp_secret, otp_row.get("otp_hash")):
            await env.sizzle_db.prepare("""
                UPDATE email_otps SET attempts = attempts + 1 WHERE id = ? AND consumed_at IS NULL
            """).bind(otp_row.get("id")).run()
            return json_error("Verification code is invalid or expired", 400)

        consume_result = await env.sizzle_db.prepare("""
            UPDATE email_otps
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND consumed_at IS NULL AND expires_at > datetime('now') AND attempts < 5
        """).bind(otp_row.get("id")).run()
        if d1_changes(consume_result) == 0:
            return json_error("Verification code is invalid or expired", 400)

        user_proxy = await env.sizzle_db.prepare("""
            SELECT user_id, encrypted_display_name FROM users WHERE email = ?
        """).bind(email).first()
        if user_proxy:
            user = user_proxy.to_py() if hasattr(user_proxy, "to_py") else user_proxy
            user_id = user.get("user_id")
        else:
            user_id = "usr_" + base64.urlsafe_b64encode(os.urandom(18)).decode("utf-8").rstrip("=")
            encrypted_email = await encrypt_data(email, get_auth_secret(env, "ENCRYPTION_KEY"))
            await env.sizzle_db.prepare("""
                INSERT INTO users (user_id, email, email_hash, encrypted_email, email_verified, status, updated_at)
                VALUES (?, ?, ?, ?, 1, 'active', CURRENT_TIMESTAMP)
            """).bind(user_id, email, email_hash_value(email), encrypted_email).run()

        await env.sizzle_db.prepare("""
            UPDATE users SET email_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?
        """).bind(user_id).run()

        session_secret = get_auth_secret(env, "SESSION_SECRET")
        token = generate_session_token()
        token_hash = session_hash(token, session_secret)
        await env.sizzle_db.prepare("""
            INSERT INTO auth_sessions (session_hash, user_id, expires_at, last_seen_at)
            VALUES (?, ?, datetime('now', '+30 days'), CURRENT_TIMESTAMP)
        """).bind(token_hash, user_id).run()

        req_url = URL.new(request.url)
        secure_cookie = req_url.protocol == "https:"
        cookie = build_session_cookie(token, 30 * 24 * 60 * 60, secure=secure_cookie)
        return json_response({
            "authenticated": True,
            "user": {"userId": user_id, "email": email, "displayName": email},
        }, 200, {"Set-Cookie": cookie})
    except Exception as e:
        logger.error("Error verifying OTP: %s", e, exc_info=True)
        return json_error("Verification code could not be verified", 500)


async def extract_session_token(request):
    """Parse sizzle_session cookie from request headers"""
    cookie_header = request.headers.get('Cookie') or ''
    for part in cookie_header.split(';'):
        part = part.strip()
        if part.startswith('sizzle_session='):
            token = part[len('sizzle_session='):]
            # Reject tokens with suspicious characters
            allowed = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=')
            if token and len(token) <= 256 and all(c in allowed for c in token):
                return token
    return None


async def get_session_user(request, env):
    """Return user_id for a valid session cookie, or None. Checks new hashed sessions before legacy OAuth sessions."""
    session_token = await extract_session_token(request)
    if not session_token:
        return None

    try:
        session_secret = get_auth_secret(env, "SESSION_SECRET")
        token_hash = session_hash(session_token, session_secret)
        auth_session_proxy = await env.sizzle_db.prepare("""
            SELECT user_id FROM auth_sessions
            WHERE session_hash = ? AND expires_at > datetime('now')
        """).bind(token_hash).first()

        if auth_session_proxy:
            await env.sizzle_db.prepare("""
                UPDATE auth_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE session_hash = ?
            """).bind(token_hash).run()
            session = auth_session_proxy.to_py()
            return session.get('user_id')
    except Exception as e:
        logger.warning("Hashed auth session lookup failed, falling back to legacy sessions: %s", e)

    session_proxy = await env.sizzle_db.prepare("""
        SELECT user_id FROM sessions
        WHERE session_token = ? AND expires_at > datetime('now')
    """).bind(session_token).first()

    if not session_proxy:
        return None

    session = session_proxy.to_py()
    return session.get('user_id')


async def handle_auth_login(request, env):
    """Redirect to GitHub OAuth authorization page"""
    try:
        github_client_id = getattr(env, 'GITHUB_CLIENT_ID', '')
        if not github_client_id:
            return Response.new(
                "GitHub OAuth not configured. Set GITHUB_CLIENT_ID secret.",
                {"status": 500}
            )

        # Generate CSRF state token
        state_bytes = os.urandom(16)
        state = base64.urlsafe_b64encode(state_bytes).decode('utf-8').rstrip('=')

        await env.sizzle_db.prepare(
            "INSERT INTO oauth_states (state) VALUES (?)"
        ).bind(state).run()

        # Clean up stale states older than 10 minutes
        await env.sizzle_db.prepare(
            "DELETE FROM oauth_states WHERE created_at < datetime('now', '-10 minutes')"
        ).run()

        req_url = URL.new(request.url)
        callback_url = f"{req_url.protocol}//{req_url.host}/api/auth/callback"

        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={github_client_id}"
            f"&redirect_uri={callback_url}"
            f"&scope=user:email"
            f"&state={state}"
        )

        return Response.redirect(auth_url, 302)
    except Exception as e:
        logger.error("Error initiating auth: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_auth_callback(request, env):
    """Handle GitHub OAuth callback — exchange code for token, upsert user, create session"""
    try:
        url = URL.new(request.url)
        code = url.searchParams.get('code')
        state = url.searchParams.get('state')
        error = url.searchParams.get('error')

        if error:
            return redirect("/?auth_error=access_denied")

        if not code or not state:
            return redirect("/?auth_error=missing_params")

        # Validate CSRF state
        state_proxy = await env.sizzle_db.prepare(
            "SELECT state FROM oauth_states WHERE state = ? AND created_at > datetime('now', '-10 minutes')"
        ).bind(state).first()

        if not state_proxy:
            return redirect("/?auth_error=invalid_state")

        await env.sizzle_db.prepare(
            "DELETE FROM oauth_states WHERE state = ?"
        ).bind(state).run()

        github_client_id = getattr(env, 'GITHUB_CLIENT_ID', '')
        github_client_secret = getattr(env, 'GITHUB_CLIENT_SECRET', '')

        if not github_client_id or not github_client_secret:
            return redirect("/?auth_error=not_configured")

        # Exchange authorization code for access token
        logger.info("Auth callback: exchanging code for token")
        token_response = await fetch(
            "https://github.com/login/oauth/access_token",
            to_js({
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "BLT-Sizzle",
                },
                "body": json.dumps({
                    "client_id": github_client_id,
                    "client_secret": github_client_secret,
                    "code": code
                })
            }, dict_converter=Object.fromEntries)
        )

        token_status = token_response.status
        content_type = token_response.headers.get("Content-Type") or ""
        logger.info("Auth callback: token response status=%s ct=%s", token_status, content_type)
        if "json" not in content_type:
            body_text = await token_response.text()
            logger.error("GitHub token endpoint non-JSON (status=%s, ct=%s): %.300s",
                         token_status, content_type, body_text)
            return redirect("/?auth_error=token_failed")

        token_raw = await token_response.json()
        token_data = token_raw.to_py() if hasattr(token_raw, 'to_py') else token_raw
        access_token = token_data.get('access_token') if isinstance(token_data, dict) else None

        if not access_token:
            logger.error("Failed to get access token: %s", token_data)
            return redirect("/?auth_error=token_failed")

        # Fetch GitHub user profile
        logger.info("Auth callback: fetching user profile")
        user_response = await fetch(
            "https://api.github.com/user",
            to_js({
                "headers": {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/json",
                    "User-Agent": "BLT-Sizzle",
                }
            }, dict_converter=Object.fromEntries)
        )

        user_raw = await user_response.json()
        user_data = user_raw.to_py() if hasattr(user_raw, 'to_py') else user_raw

        if not isinstance(user_data, dict) or not user_data.get('login'):
            logger.error("Bad user data from GitHub: %s", user_data)
            return redirect("/?auth_error=user_fetch_failed")

        # Fetch verified email addresses
        logger.info("Auth callback: fetching user emails for %s", user_data.get('login'))
        emails_response = await fetch(
            "https://api.github.com/user/emails",
            to_js({
                "headers": {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/json",
                    "User-Agent": "BLT-Sizzle",
                }
            }, dict_converter=Object.fromEntries)
        )

        emails_raw = await emails_response.json()
        emails_data = emails_raw.to_py() if hasattr(emails_raw, 'to_py') else []

        primary_email = ''
        if isinstance(emails_data, list):
            for em in emails_data:
                if isinstance(em, dict) and em.get('primary') and em.get('verified'):
                    primary_email = em.get('email', '')
                    break
            if not primary_email and emails_data:
                first = emails_data[0]
                if isinstance(first, dict):
                    primary_email = first.get('email', '')

        github_id = str(user_data.get('id', ''))
        login = user_data.get('login', '')
        display_name = user_data.get('name') or login

        # Encrypt PII before storing
        encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')
        encrypted_email = await encrypt_data(primary_email, encryption_key)
        encrypted_display_name = await encrypt_data(display_name, encryption_key)

        user_id = login
        await env.sizzle_db.prepare("""
            INSERT INTO users (user_id, github_id, encrypted_email, encrypted_display_name, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                github_id = excluded.github_id,
                encrypted_email = excluded.encrypted_email,
                encrypted_display_name = excluded.encrypted_display_name,
                updated_at = CURRENT_TIMESTAMP
        """).bind(user_id, github_id, encrypted_email, encrypted_display_name).run()

        # Create session (30-day expiry) — store encrypted access token for GitHub API calls
        token_bytes = os.urandom(32)
        session_token = base64.urlsafe_b64encode(token_bytes).decode('utf-8').rstrip('=')
        encrypted_access_token = await encrypt_data(access_token, encryption_key)

        await env.sizzle_db.prepare("""
            INSERT INTO sessions (session_token, user_id, expires_at, encrypted_access_token)
            VALUES (?, ?, datetime('now', '+30 days'), ?)
        """).bind(session_token, user_id, encrypted_access_token).run()

        logger.info("Auth callback: creating session for user=%s", user_id)
        cookie = (
            f"sizzle_session={session_token}; HttpOnly; Secure; SameSite=Lax; "
            f"Path=/; Max-Age=2592000"
        )
        return Response.new(
            None,
            to_js({
                "status": 302,
                "headers": {
                    "Location": "/",
                    "Set-Cookie": cookie,
                }
            }, dict_converter=Object.fromEntries)
        )

    except Exception as e:
        logger.error("Error in auth callback: %s", e, exc_info=True)
        return redirect("/?auth_error=server_error")


async def handle_auth_me(request, env):
    """Return authenticated user info from session cookie"""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return json_response({"authenticated": False}, 401)

        user_proxy = await env.sizzle_db.prepare("""
            SELECT user_id, email, email_verified, encrypted_display_name, github_id
            FROM users WHERE user_id = ?
        """).bind(user_id).first()

        if not user_proxy:
            return json_response({"authenticated": False}, 401)

        user = user_proxy.to_py()
        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        display_name = await decrypt_data(user.get('encrypted_display_name') or '', encryption_key)
        email = user.get('email') or ''
        fallback_display = email.split('@')[0] if email else user_id
        email_verified = bool(int(user.get('email_verified') or 0))

        return json_response({
            "authenticated": True,
            "userId": user_id,
            "email": email,
            "displayName": display_name or fallback_display,
            "emailVerified": email_verified,
            "needsEmailVerification": bool(email and not email_verified),
            "authProvider": "email" if email else "github",
            "githubLogin": user_id if user.get('github_id') else ""
        })

    except Exception as e:
        logger.error("Error in auth/me: %s", e, exc_info=True)
        return json_response({"authenticated": False}, 500)


async def handle_auth_logout(request, env):
    """Delete the current session"""
    try:
        session_token = await extract_session_token(request)
        if session_token:
            try:
                session_secret = get_auth_secret(env, "SESSION_SECRET")
                await env.sizzle_db.prepare(
                    "DELETE FROM auth_sessions WHERE session_hash = ?"
                ).bind(session_hash(session_token, session_secret)).run()
            except Exception as e:
                logger.warning("Hashed auth session delete failed: %s", e)
            await env.sizzle_db.prepare(
                "DELETE FROM sessions WHERE session_token = ?"
            ).bind(session_token).run()

        req_url = URL.new(request.url)
        clear_cookie = build_clear_session_cookie(secure=req_url.protocol == "https:")
        return Response.new(json.dumps({"success": True}), {
            "headers": {
                "Content-Type": "application/json",
                "Set-Cookie": clear_cookie
            }
        })
    except Exception as e:
        logger.error("Error in logout: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def get_access_token_for_request(request, env):
    """Retrieve the GitHub access token stored in the current session (if any)"""
    session_token = await extract_session_token(request)
    if not session_token:
        return None

    session_proxy = await env.sizzle_db.prepare("""
        SELECT encrypted_access_token FROM sessions
        WHERE session_token = ? AND expires_at > datetime('now')
    """).bind(session_token).first()

    if not session_proxy:
        return None

    session = session_proxy.to_py()
    encrypted_token = session.get('encrypted_access_token') or ''
    if not encrypted_token:
        return None

    encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')
    return await decrypt_data(encrypted_token, encryption_key)


def slugify_org(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug or ""):
        return ""
    return slug[:80]


async def get_verified_session_user(request, env):
    user_id = await get_session_user(request, env)
    if not user_id:
        return None, json_error("Unauthorized", 401)
    user_proxy = await env.sizzle_db.prepare("""
        SELECT user_id, email_verified, status FROM users WHERE user_id = ?
    """).bind(user_id).first()
    user = user_proxy.to_py() if hasattr(user_proxy, "to_py") else user_proxy
    if not isinstance(user, dict) or user.get("status") != "active":
        return None, json_error("Unauthorized", 401)
    if not bool(int(user.get("email_verified") or 0)):
        return None, json_error("Email verification required", 403)
    return user_id, None


async def get_org_by_slug(env, slug):
    slug = slugify_org(slug)
    if not slug:
        return None
    org_proxy = await env.sizzle_db.prepare("""
        SELECT id, COALESCE(NULLIF(slug, ''), github_org_name) AS slug,
               COALESCE(NULLIF(name, ''), github_org_name) AS name,
               description, created_by_user_id, checkin_enabled
        FROM organizations
        WHERE slug = ? OR github_org_name = ?
        LIMIT 1
    """).bind(slug, slug).first()
    org = org_proxy.to_py() if hasattr(org_proxy, "to_py") else org_proxy
    return org if isinstance(org, dict) else None


async def require_org_admin(request, env, org_slug):
    user_id, error = await get_verified_session_user(request, env)
    if error:
        return None, None, error
    org = await get_org_by_slug(env, org_slug)
    if not org:
        return None, None, json_error("Organization not found", 404)
    membership_proxy = await env.sizzle_db.prepare("""
        SELECT role, status FROM user_organizations
        WHERE user_id = ? AND org_id = ? AND status = 'approved' AND role IN ('owner', 'admin')
    """).bind(user_id, org.get("id")).first()
    membership = membership_proxy.to_py() if hasattr(membership_proxy, "to_py") else membership_proxy
    if not isinstance(membership, dict):
        return None, None, json_error("Admin access required", 403)
    return user_id, org, None


def org_row_to_api(row):
    return {
        "id": row.get("id"),
        "slug": row.get("slug") or row.get("github_org_name"),
        "name": row.get("name") or row.get("github_org_name"),
        "description": row.get("description") or "",
        "membershipStatus": row.get("status") or "not_joined",
        "status": row.get("status") or "not_joined",
        "role": row.get("role") or "member",
        "checkinEnabled": bool(int(row.get("checkin_enabled") if row.get("checkin_enabled") is not None else 1)),
    }


async def handle_discover_orgs(request, env):
    """Discover all Sizzle organizations with current user's membership/role state."""
    try:
        user_id, error = await get_verified_session_user(request, env)
        if error:
            return error
        url = URL.new(request.url)
        query = (url.searchParams.get("q") or "").strip().lower()
        result_proxy = await env.sizzle_db.prepare("""
            SELECT o.id, COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                   COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name,
                   o.description, o.checkin_enabled, uo.status, uo.role
            FROM organizations o
            LEFT JOIN user_organizations uo ON o.id = uo.org_id AND uo.user_id = ?
            ORDER BY name COLLATE NOCASE
        """).bind(user_id).all()
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        rows = result.get('results', []) if isinstance(result, dict) else []
        orgs = [org_row_to_api(row) for row in rows]
        if query:
            orgs = [org for org in orgs if query in org["name"].lower() or query in org["slug"].lower()]
        return json_response({"orgs": orgs})
    except Exception as e:
        logger.error("Error discovering orgs: %s", e, exc_info=True)
        return json_error("Organizations could not be loaded", 500)


async def handle_get_orgs(request, env):
    """List organizations the authenticated user belongs to, including roles/status."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return json_error("Unauthorized", 401)
        result_proxy = await env.sizzle_db.prepare("""
            SELECT o.id, COALESCE(NULLIF(o.slug, ''), o.github_org_name) AS slug,
                   COALESCE(NULLIF(o.name, ''), o.github_org_name) AS name,
                   o.description, o.checkin_enabled, uo.status, uo.role
            FROM organizations o
            JOIN user_organizations uo ON o.id = uo.org_id
            WHERE uo.user_id = ?
            ORDER BY name COLLATE NOCASE
        """).bind(user_id).all()
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        rows = result.get('results', []) if isinstance(result, dict) else []
        return json_response({"orgs": [org_row_to_api(row) for row in rows]})
    except Exception as e:
        logger.error("Error getting orgs: %s", e, exc_info=True)
        return json_error("Organizations could not be loaded", 500)


async def handle_add_org(request, env):
    """Create a generic organization. Creator becomes approved owner."""
    try:
        user_id, error = await get_verified_session_user(request, env)
        if error:
            return error
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)
        org_name = str(data.get('name') or data.get('orgName') or '').strip()
        description = str(data.get('description') or '').strip()[:500]
        slug = slugify_org(data.get('slug') or org_name)
        if not org_name or not slug:
            return json_error("Valid organization name is required", 400)
        existing = await get_org_by_slug(env, slug)
        if existing:
            return json_error("Organization already exists", 409)
        await env.sizzle_db.prepare("""
            INSERT INTO organizations (github_org_name, name, slug, description, created_by_user_id, checkin_enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """).bind(slug, org_name, slug, description, user_id).run()
        org = await get_org_by_slug(env, slug)
        if not org:
            return json_error("Organization could not be created", 500)
        await env.sizzle_db.prepare("""
            INSERT INTO user_organizations (user_id, org_id, status, role, requested_at, approved_by_user_id, approved_at, joined_at)
            VALUES (?, ?, 'approved', 'owner', CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """).bind(user_id, org.get('id'), user_id).run()
        return json_response({"success": True, "org": {"id": org.get('id'), "slug": slug, "name": org_name, "status": "approved", "role": "owner"}}, 201)
    except Exception as e:
        logger.error("Error creating org: %s", e, exc_info=True)
        return json_error("Organization could not be created", 500)


async def handle_join_org(request, env, org_slug):
    """Create a pending member join request for an existing organization."""
    try:
        user_id, error = await get_verified_session_user(request, env)
        if error:
            return error
        org = await get_org_by_slug(env, org_slug)
        if not org:
            return json_error("Organization not found", 404)
        already_proxy = await env.sizzle_db.prepare("""
            SELECT status, role FROM user_organizations WHERE user_id = ? AND org_id = ?
        """).bind(user_id, org.get('id')).first()
        already = already_proxy.to_py() if hasattr(already_proxy, 'to_py') else already_proxy
        if isinstance(already, dict):
            return json_response({"success": True, "pending": already.get('status') == 'pending', "membershipStatus": already.get('status'), "role": already.get('role') or 'member'})
        await env.sizzle_db.prepare("""
            INSERT INTO user_organizations (user_id, org_id, status, role, requested_at, joined_at)
            VALUES (?, ?, 'pending', 'member', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """).bind(user_id, org.get('id')).run()
        return json_response({"success": True, "pending": True, "membershipStatus": "pending", "role": "member", "message": "Request to join sent"}, 202)
    except Exception as e:
        logger.error("Error joining org: %s", e, exc_info=True)
        return json_error("Join request could not be sent", 500)


async def handle_get_org_requests(request, env, org_name):
    try:
        admin_id, org, error = await require_org_admin(request, env, org_name)
        if error:
            return error
        result_proxy = await env.sizzle_db.prepare("""
            SELECT uo.user_id, u.email, u.encrypted_display_name, uo.status, uo.role, uo.requested_at
            FROM user_organizations uo
            JOIN users u ON u.user_id = uo.user_id
            WHERE uo.org_id = ? AND uo.status = 'pending'
            ORDER BY uo.requested_at ASC
        """).bind(org.get('id')).all()
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        return json_response({"requests": result.get('results', []) if isinstance(result, dict) else []})
    except Exception as e:
        logger.error("Error getting org requests: %s", e, exc_info=True)
        return json_error("Requests could not be loaded", 500)


async def handle_get_org_members(request, env, org_name):
    """List members for an organization. Admins see pending and approved users."""
    try:
        admin_id, org, error = await require_org_admin(request, env, org_name)
        if error:
            return error
        result_proxy = await env.sizzle_db.prepare("""
            SELECT uo.user_id, u.email, uo.status, uo.role, uo.requested_at, uo.approved_at, uo.joined_at
            FROM user_organizations uo
            JOIN users u ON u.user_id = uo.user_id
            WHERE uo.org_id = ?
            ORDER BY uo.status ASC, uo.role DESC, uo.joined_at ASC
        """).bind(org.get('id')).all()
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        return json_response({"members": result.get('results', []) if isinstance(result, dict) else []})
    except Exception as e:
        logger.error("Error getting org members: %s", e, exc_info=True)
        return json_error("Members could not be loaded", 500)


async def handle_approve_org_member(request, env, org_name, target_user_id):
    try:
        admin_id, org, error = await require_org_admin(request, env, org_name)
        if error:
            return error
        result = await env.sizzle_db.prepare("""
            UPDATE user_organizations
            SET status = 'approved', role = 'member', approved_by_user_id = ?, approved_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND org_id = ? AND status = 'pending'
        """).bind(admin_id, target_user_id, org.get('id')).run()
        if d1_changes(result) == 0:
            return json_error("No pending request found for that user", 404)
        return json_response({"success": True})
    except Exception as e:
        logger.error("Error approving org member: %s", e, exc_info=True)
        return json_error("Member could not be approved", 500)


async def handle_deny_org_member(request, env, org_name, target_user_id):
    try:
        admin_id, org, error = await require_org_admin(request, env, org_name)
        if error:
            return error
        await env.sizzle_db.prepare("""
            UPDATE user_organizations
            SET status = 'rejected', approved_by_user_id = ?, approved_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND org_id = ? AND status = 'pending'
        """).bind(admin_id, target_user_id, org.get('id')).run()
        return json_response({"success": True})
    except Exception as e:
        logger.error("Error denying org member: %s", e, exc_info=True)
        return json_error("Member could not be rejected", 500)


async def handle_update_org_member_role(request, env, org_name, target_user_id):
    try:
        admin_id, org, error = await require_org_admin(request, env, org_name)
        if error:
            return error
        data = await safe_request_json(request)
        if not isinstance(data, dict):
            return json_error("Invalid JSON body", 400)
        role = str(data.get('role') or '').strip().lower()
        if role not in {'owner', 'admin', 'member'}:
            return json_error("Invalid role", 400)
        if role != 'owner':
            owners_proxy = await env.sizzle_db.prepare("""
                SELECT COUNT(*) AS owner_count FROM user_organizations
                WHERE org_id = ? AND status = 'approved' AND role = 'owner'
            """).bind(org.get('id')).first()
            owners = owners_proxy.to_py() if hasattr(owners_proxy, 'to_py') else (owners_proxy or {})
            target_proxy = await env.sizzle_db.prepare("""
                SELECT role FROM user_organizations WHERE org_id = ? AND user_id = ?
            """).bind(org.get('id'), target_user_id).first()
            target = target_proxy.to_py() if hasattr(target_proxy, 'to_py') else target_proxy
            if isinstance(target, dict) and target.get('role') == 'owner' and int(owners.get('owner_count') or 0) <= 1:
                return json_error("Cannot remove the last owner", 400)
        result = await env.sizzle_db.prepare("""
            UPDATE user_organizations SET role = ?
            WHERE user_id = ? AND org_id = ? AND status = 'approved'
        """).bind(role, target_user_id, org.get('id')).run()
        if d1_changes(result) == 0:
            return json_error("Approved member not found", 404)
        return json_response({"success": True, "role": role})
    except Exception as e:
        logger.error("Error updating org member role: %s", e, exc_info=True)
        return json_error("Role could not be updated", 500)


async def handle_get_org_checkins(request, env, org_name):
    """Fetch today's check-ins for all approved members of an org.
    Caller must be an approved member. Org-key-encrypted data is decrypted server-side."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        # Caller must be approved
        org_proxy = await env.sizzle_db.prepare("""
            SELECT o.id, o.encrypted_org_key FROM organizations o
            JOIN user_organizations uo ON o.id = uo.org_id
            WHERE o.github_org_name = ? AND uo.user_id = ? AND uo.status = 'approved'
        """).bind(org_name, user_id).first()

        if not org_proxy:
            return Response.new(json.dumps({"error": "Not found or not an approved member"}),
                              {"status": 403, "headers": {"Content-Type": "application/json"}})

        org = org_proxy.to_py()
        org_id = org['id']
        encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')

        # Resolve org-level key (if set)
        org_key = None
        if org.get('encrypted_org_key'):
            org_key = await decrypt_data(org['encrypted_org_key'], encryption_key)

        url = URL.new(request.url)
        checkin_date = url.searchParams.get('date') or date.today().isoformat()

        result_proxy = await env.sizzle_db.prepare("""
            SELECT c.user_id, c.encrypted_previous_work, c.encrypted_today_plan,
                   c.encrypted_blockers, c.mood, c.goal_accomplished, c.checkin_date
            FROM checkins c
            JOIN user_organizations uo ON c.user_id = uo.user_id AND uo.org_id = ?
            WHERE c.org_id = ? AND c.checkin_date = ? AND uo.status = 'approved'
            ORDER BY c.created_at ASC
        """).bind(org_id, org_id, checkin_date).all()

        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        rows = result.get('results', []) if isinstance(result, dict) else []

        checkins = []
        for row in rows:
            # Decrypt outer server layer
            prev = await decrypt_data(row['encrypted_previous_work'] or '', encryption_key)
            today_plan = await decrypt_data(row['encrypted_today_plan'] or '', encryption_key)
            blockers = await decrypt_data(row['encrypted_blockers'] or '', encryption_key)

            # Decrypt inner org layer if present
            if org_key:
                prev = await decrypt_data(prev, org_key)
                today_plan = await decrypt_data(today_plan, org_key)
                blockers = await decrypt_data(blockers, org_key)

            checkins.append({
                "userId": row['user_id'],
                "previousWork": prev,
                "todayPlan": today_plan,
                "blockers": blockers,
                "mood": row.get('mood', ''),
                "goalAccomplished": row['goal_accomplished'] == 1,
                "date": row['checkin_date'],
            })

        return Response.new(json.dumps({"checkins": checkins, "date": checkin_date}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error getting org check-ins: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


# Main entry point for Cloudflare Worker
async def on_fetch(request, env):
    """Worker entry point for HTTP requests"""
    try:
        return await handle_request(request, env)
    except Exception as e:
        logger.critical("Unhandled worker error: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e), "stack": "See worker logs"}), 
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def on_scheduled(event, env):
    """Worker entry point for scheduled/cron events"""
    try:
        # Import scheduler module
        from scheduler import handle_scheduled
        await handle_scheduled(event, env)
    except Exception as e:
        logger.error("Error in scheduled event: %s", e, exc_info=True)
