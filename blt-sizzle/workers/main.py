from js import Response, Request, Headers, crypto, TextEncoder, TextDecoder, URL, fetch, Object
from pyodide.ffi import to_js
import json
import base64
import hashlib
import logging
import os
import re
import sys
from datetime import datetime, date

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


def redirect(location, status=302):
    """Create a redirect Response with proper Headers object (supports relative URLs)"""
    h = Headers.new()
    h.set("Location", location)
    return Response.new(None, {"status": status, "headers": h})


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

        elif api_path == "/api/orgs" and method == "GET":
            return await handle_get_orgs(request, env)

        elif api_path == "/api/orgs" and method == "POST":
            return await handle_add_org(request, env)

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
            return Response.new(json.dumps({"error": "API route not found"}), 
                              {"status": 404, "headers": {"Content-Type": "application/json"}})
    
    # Static Pages & Assets
    if method == "GET":
        if path == "" or path == "/" or path == "/index.html":
            if hasattr(env, 'ASSETS'):
                return await env.ASSETS.fetch(request)
            return Response.new("Assets not found", {"status": 404})
        
        elif path in ["/app", "/login", "/dashboard", "/profile", "/organizations", "/leaderboard", "/settings", "/check-ins", "/checkins"]:
            if hasattr(env, 'ASSETS'):
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
                url_clone = URL.new(request.url)
                url_clone.pathname = page_assets[path]
                request_clone = Request.new(url_clone, request)
                return await env.ASSETS.fetch(request_clone)
            return Response.new("Assets not found", {"status": 404})
        
        # Fallback for all other static assets (favicon.ico, CSS, JS, images)
        elif hasattr(env, 'ASSETS'):
            return await env.ASSETS.fetch(request)
    
    return Response.new("Not Found", {"status": 404})


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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """).run()
        
        # Create indexes
        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, checkin_date)
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
                encrypted_slack_webhook_url TEXT,
                encrypted_org_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
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
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, org_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (org_id) REFERENCES organizations(id)
            )
        """).run()

        await env.sizzle_db.prepare("""
            CREATE INDEX IF NOT EXISTS idx_user_orgs_user ON user_organizations(user_id)
        """).run()

    except Exception as e:
        logger.error("Database initialization error: %s", e, exc_info=True)


async def handle_checkin(request, env):
    """Handle check-in submission"""
    try:
        raw_json = await request.json()
        data = raw_json.to_py()
        
        user_id = data.get('userId')
        previous_work = data.get('previousWork', '')
        today_plan = data.get('todayPlan', '')
        blockers = data.get('blockers', '')
        mood = data.get('mood', '😊')
        goal_accomplished = 1 if data.get('goalAccomplished') else 0
        
        if not user_id:
            return Response.new(json.dumps({"error": "User ID required"}), 
                              {"status": 400, "headers": {"Content-Type": "application/json"}})
        
        # Ensure user exists (test/pre-upsert)
        await env.sizzle_db.prepare("INSERT OR IGNORE INTO users (user_id) VALUES (?)").bind(user_id).run()

        # Get encryption key from environment with fallback
        encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')

        # Encrypt sensitive data
        encrypted_previous = await encrypt_data(previous_work, encryption_key)
        encrypted_today = await encrypt_data(today_plan, encryption_key)
        encrypted_blockers = await encrypt_data(blockers, encryption_key)

        # Get current date
        today_obj = date.today()
        today = today_obj.isoformat()

        # Resolve optional org_id: validate user is an APPROVED member of the requested org
        org_id = None
        org_name_req = data.get('orgName', '')
        if org_name_req:
            org_proxy = await env.sizzle_db.prepare("""
                SELECT o.id, o.encrypted_org_key FROM organizations o
                JOIN user_organizations uo ON o.id = uo.org_id
                WHERE o.github_org_name = ? AND uo.user_id = ? AND uo.status = 'approved'
            """).bind(org_name_req, user_id).first()
            if org_proxy:
                org_row = org_proxy.to_py()
                org_id = org_row['id']
                # If the org has its own encryption key, apply a second encryption layer
                if org_row.get('encrypted_org_key'):
                    org_key = await decrypt_data(org_row['encrypted_org_key'], encryption_key)
                    if org_key:
                        encrypted_previous = await encrypt_data(
                            await decrypt_data(encrypted_previous, encryption_key), org_key)
                        encrypted_previous = await encrypt_data(encrypted_previous, encryption_key)
                        encrypted_today = await encrypt_data(
                            await decrypt_data(encrypted_today, encryption_key), org_key)
                        encrypted_today = await encrypt_data(encrypted_today, encryption_key)
                        encrypted_blockers = await encrypt_data(
                            await decrypt_data(encrypted_blockers, encryption_key), org_key)
                        encrypted_blockers = await encrypt_data(encrypted_blockers, encryption_key)

        # 1. Insert check-in
        checkin_op = await env.sizzle_db.prepare("""
            INSERT INTO checkins (user_id, encrypted_previous_work, encrypted_today_plan,
                                encrypted_blockers, mood, goal_accomplished, checkin_date, org_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """).bind(user_id, encrypted_previous, encrypted_today, encrypted_blockers, mood, goal_accomplished, today, org_id).run()
        
        # 2. Update streak and user profile
        user_proxy = await env.sizzle_db.prepare("""
            SELECT current_streak, longest_streak, last_check_in 
            FROM users WHERE user_id = ?
        """).bind(user_id).first()
        
        user = user_proxy.to_py() if user_proxy else None
        
        current_streak = 0
        longest_streak = 0
        last_check_in = None
        
        if user:
            current_streak = user['current_streak'] or 0
            longest_streak = user['longest_streak'] or 0
            last_check_in = user['last_check_in']
        
        # Streak logic
        from datetime import timedelta
        new_streak = 1
        if last_check_in:
            last_date = date.fromisoformat(last_check_in)
            if last_date == today_obj - timedelta(days=1):
                new_streak = current_streak + 1
            elif last_date == today_obj:
                new_streak = current_streak  # Already checked in today
            else:
                new_streak = 1
        
        new_longest = max(new_streak, longest_streak)
        
        display_name = data.get('userName', '')
        
        # Upsert user with new streak
        user_op = await env.sizzle_db.prepare("""
            INSERT INTO users (user_id, current_streak, longest_streak, last_check_in, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                current_streak = excluded.current_streak,
                longest_streak = excluded.longest_streak,
                last_check_in = excluded.last_check_in,
                updated_at = CURRENT_TIMESTAMP
        """).bind(user_id, new_streak, new_longest, today).run()
        
        return Response.new(json.dumps({
            "success": True, 
            "message": "Check-in saved",
            "streak": new_streak
        }), {"headers": {"Content-Type": "application/json"}})
        
    except Exception as e:
        logger.error("Error handling check-in: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}), 
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


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
    """Get all check-ins for a user"""
    try:
        url = URL.new(request.url)
        user_id = url.searchParams.get('userId')
        
        if not user_id:
            return Response.new(json.dumps({"error": "User ID required"}), 
                              {"status": 400, "headers": {"Content-Type": "application/json"}})
        
        # Get encryption key with fallback
        encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')
        
        # Get all check-ins
        result_proxy = await env.sizzle_db.prepare("""
            SELECT id, encrypted_previous_work, encrypted_today_plan, 
                   encrypted_blockers, mood, goal_accomplished, checkin_date
            FROM checkins 
            WHERE user_id = ? 
            ORDER BY id DESC
        """).bind(user_id).all()
        
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        
        rows = []
        if isinstance(result, dict):
            rows = result.get('results', [])
        elif isinstance(result, list):
            rows = result
        
        checkins = []
        for row in rows:
            previous = await decrypt_data(row['encrypted_previous_work'] if row['encrypted_previous_work'] else '', encryption_key)
            today_plan = await decrypt_data(row['encrypted_today_plan'] if row['encrypted_today_plan'] else '', encryption_key)
            blockers = await decrypt_data(row['encrypted_blockers'] if row['encrypted_blockers'] else '', encryption_key)
            
            checkins.append({
                "id": row['id'],
                "previousWork": previous,
                "todayPlan": today_plan,
                "blockers": blockers,
                "mood": row['mood'],
                "goalAccomplished": row['goal_accomplished'] == 1,
                "date": row['checkin_date']
            })
            
        return Response.new(json.dumps({"checkins": checkins}), 
                          {"headers": {"Content-Type": "application/json"}})
        
    except Exception as e:
        logger.error("Error getting check-ins: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}), 
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_get_latest_checkin(request, env):
    """Get the latest check-in for pre-filling"""
    try:
        url = URL.new(request.url)
        user_id = url.searchParams.get('userId')
        
        if not user_id:
            return Response.new(json.dumps({"error": "User ID required"}), 
                              {"status": 400, "headers": {"Content-Type": "application/json"}})
        
        # Get latest check-in and user streak
        result_proxy = await env.sizzle_db.prepare("""
            SELECT c.encrypted_today_plan, c.mood, c.goal_accomplished, c.checkin_date, u.current_streak
            FROM checkins c
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE c.user_id = ? 
            ORDER BY c.id DESC 
            LIMIT 1
        """).bind(user_id).first()
        
        if not result_proxy:
            return Response.new(json.dumps({}), 
                              {"headers": {"Content-Type": "application/json"}})
        
        result = result_proxy.to_py()
        
        # Decrypt data
        if not hasattr(env, 'ENCRYPTION_KEY') or not env.ENCRYPTION_KEY:
            return Response.new(json.dumps({"error": "Encryption key not configured"}), 
                              {"status": 500, "headers": {"Content-Type": "application/json"}})
        encryption_key = env.ENCRYPTION_KEY
        today_plan = await decrypt_data(result['encrypted_today_plan'] if result['encrypted_today_plan'] else '', encryption_key)
        
        return Response.new(json.dumps({
            "todayPlan": today_plan,
            "mood": result['mood'],
            "goalAccomplished": result['goal_accomplished'] == 1,
            "date": result['checkin_date'],
            "streak": result['current_streak'] or 0
        }), {"headers": {"Content-Type": "application/json"}})
        
    except Exception as e:
        logger.error("Error getting latest check-in: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}), 
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


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
    return Response.new(json.dumps(data), {"status": status, "headers": headers})


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
            return Response.new(
                json.dumps({"authenticated": False}),
                {"status": 401, "headers": {"Content-Type": "application/json"}}
            )

        user_proxy = await env.sizzle_db.prepare("""
            SELECT user_id, email, email_verified, encrypted_display_name, github_id
            FROM users WHERE user_id = ?
        """).bind(user_id).first()

        if not user_proxy:
            return Response.new(
                json.dumps({"authenticated": False}),
                {"status": 401, "headers": {"Content-Type": "application/json"}}
            )

        user = user_proxy.to_py()
        encryption_key = get_auth_secret(env, "ENCRYPTION_KEY")
        display_name = await decrypt_data(user.get('encrypted_display_name') or '', encryption_key)
        email = user.get('email') or ''
        fallback_display = email.split('@')[0] if email else user_id
        email_verified = bool(int(user.get('email_verified') or 0))

        return Response.new(json.dumps({
            "authenticated": True,
            "userId": user_id,
            "email": email,
            "displayName": display_name or fallback_display,
            "emailVerified": email_verified,
            "needsEmailVerification": bool(email and not email_verified),
            "authProvider": "email" if email else "github",
            "githubLogin": user_id if user.get('github_id') else ""
        }), {"headers": {"Content-Type": "application/json"}})

    except Exception as e:
        logger.error("Error in auth/me: %s", e, exc_info=True)
        return Response.new(
            json.dumps({"authenticated": False}),
            {"status": 500, "headers": {"Content-Type": "application/json"}}
        )


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


async def handle_get_orgs(request, env):
    """List organizations the authenticated user belongs to (approved + pending)"""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        result_proxy = await env.sizzle_db.prepare("""
            SELECT o.id, o.github_org_name, o.encrypted_slack_webhook_url,
                   o.encrypted_org_key, uo.status
            FROM organizations o
            JOIN user_organizations uo ON o.id = uo.org_id
            WHERE uo.user_id = ?
            ORDER BY o.github_org_name
        """).bind(user_id).all()

        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        rows = result.get('results', []) if isinstance(result, dict) else []

        encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')
        orgs = []
        for row in rows:
            slack_url = await decrypt_data(row['encrypted_slack_webhook_url'] or '', encryption_key)
            orgs.append({
                "id": row['id'],
                "name": row['github_org_name'],
                "slackWebhookUrl": slack_url,
                "hasOrgKey": bool(row.get('encrypted_org_key')),
                "status": row.get('status', 'approved'),
            })

        return Response.new(json.dumps({"orgs": orgs}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error getting orgs: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_add_org(request, env):
    """Add the authenticated user to an organization (verifies GitHub membership)"""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        data = (await request.json()).to_py()
        org_name = data.get('orgName', '').strip().lower()

        if not org_name:
            return Response.new(json.dumps({"error": "orgName is required"}),
                              {"status": 400, "headers": {"Content-Type": "application/json"}})

        # GitHub org names: alphanumeric + hyphens, 1-39 chars
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,37}$', org_name):
            return Response.new(json.dumps({"error": "Invalid organization name"}),
                              {"status": 400, "headers": {"Content-Type": "application/json"}})

        # Verify the user is actually a member of this org via GitHub API
        access_token = await get_access_token_for_request(request, env)
        if access_token:
            try:
                membership_res = await fetch(
                    f"https://api.github.com/orgs/{org_name}/members/{user_id}",
                    {
                        "headers": {
                            "Authorization": f"token {access_token}",
                            "Accept": "application/json",
                            "User-Agent": "BLT-Sizzle"
                        }
                    }
                )
                if membership_res.status == 404:
                    return Response.new(
                        json.dumps({"error": "You are not a member of this organization, or it does not exist"}),
                        {"status": 403, "headers": {"Content-Type": "application/json"}}
                    )
            except Exception as e:
                logger.error("GitHub membership check failed: %s", e)
                # Continue: best-effort verification; org/user data is still isolated

        # Upsert org record
        await env.sizzle_db.prepare("""
            INSERT OR IGNORE INTO organizations (github_org_name) VALUES (?)
        """).bind(org_name).run()

        org_proxy = await env.sizzle_db.prepare(
            "SELECT id FROM organizations WHERE github_org_name = ?"
        ).bind(org_name).first()

        if not org_proxy:
            return Response.new(json.dumps({"error": "Failed to create organization record"}),
                              {"status": 500, "headers": {"Content-Type": "application/json"}})

        org_id = org_proxy.to_py()['id']

        # First member becomes auto-approved; subsequent members need approval
        existing_proxy = await env.sizzle_db.prepare("""
            SELECT COUNT(*) AS cnt FROM user_organizations
            WHERE org_id = ? AND status = 'approved'
        """).bind(org_id).first()
        existing = existing_proxy.to_py() if existing_proxy else {'cnt': 0}
        is_first_member = existing.get('cnt', 0) == 0
        new_status = 'approved' if is_first_member else 'pending'

        # Check if already a member (any status)
        already_proxy = await env.sizzle_db.prepare("""
            SELECT status FROM user_organizations WHERE user_id = ? AND org_id = ?
        """).bind(user_id, org_id).first()

        if already_proxy:
            current_status = already_proxy.to_py().get('status', 'pending')
            if current_status == 'approved':
                return Response.new(json.dumps({"success": True, "org": {"id": org_id, "name": org_name, "status": "approved"}}),
                                  {"headers": {"Content-Type": "application/json"}})
            # Re-request if previously pending/denied
            return Response.new(json.dumps({"success": False, "error": "Your request to join is pending approval by an existing member"}),
                              {"status": 202, "headers": {"Content-Type": "application/json"}})

        await env.sizzle_db.prepare("""
            INSERT INTO user_organizations (user_id, org_id, status, joined_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """).bind(user_id, org_id, new_status).run()

        if new_status == 'pending':
            return Response.new(json.dumps({"success": True, "pending": True,
                "message": "Join request sent — an existing member must approve you",
                "org": {"id": org_id, "name": org_name, "status": "pending"}}),
                {"headers": {"Content-Type": "application/json"}})

        return Response.new(json.dumps({"success": True, "org": {"id": org_id, "name": org_name, "status": "approved"}}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error adding org: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_remove_org(request, env, org_name):
    """Remove the authenticated user from an organization (any status)"""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        org_proxy = await env.sizzle_db.prepare(
            "SELECT id FROM organizations WHERE github_org_name = ?"
        ).bind(org_name).first()

        if not org_proxy:
            return Response.new(json.dumps({"error": "Organization not found"}),
                              {"status": 404, "headers": {"Content-Type": "application/json"}})

        org_id = org_proxy.to_py()['id']
        await env.sizzle_db.prepare("""
            DELETE FROM user_organizations WHERE user_id = ? AND org_id = ?
        """).bind(user_id, org_id).run()

        return Response.new(json.dumps({"success": True}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error removing org: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_update_org_settings(request, env, org_name):
    """Update org Slack webhook URL and/or org encryption key. Caller must be approved."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        data = (await request.json()).to_py()
        slack_webhook_url = data.get('slackWebhookUrl', '')
        org_key = data.get('orgKey', '')  # user-supplied org-level encryption passphrase

        # Caller must be an APPROVED member
        membership_proxy = await env.sizzle_db.prepare("""
            SELECT o.id FROM organizations o
            JOIN user_organizations uo ON o.id = uo.org_id
            WHERE o.github_org_name = ? AND uo.user_id = ? AND uo.status = 'approved'
        """).bind(org_name, user_id).first()

        if not membership_proxy:
            return Response.new(
                json.dumps({"error": "Organization not found or you are not an approved member"}),
                {"status": 403, "headers": {"Content-Type": "application/json"}}
            )

        org_id = membership_proxy.to_py()['id']
        encryption_key = getattr(env, 'ENCRYPTION_KEY', 'sizzle-dev-key-12345')

        updates = ["updated_at = CURRENT_TIMESTAMP"]
        binds = []

        if 'slackWebhookUrl' in data:
            encrypted_slack = await encrypt_data(slack_webhook_url, encryption_key)
            updates.append("encrypted_slack_webhook_url = ?")
            binds.append(encrypted_slack)

        if 'orgKey' in data:
            if org_key:
                encrypted_org_key = await encrypt_data(org_key, encryption_key)
            else:
                encrypted_org_key = ''  # clearing the key
            updates.append("encrypted_org_key = ?")
            binds.append(encrypted_org_key)

        binds.append(org_id)
        await env.sizzle_db.prepare(
            f"UPDATE organizations SET {', '.join(updates)} WHERE id = ?"
        ).bind(*binds).run()

        return Response.new(json.dumps({"success": True}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error updating org settings: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_get_org_members(request, env, org_name):
    """List approved + pending members for an org. Caller must be approved."""
    try:
        user_id = await get_session_user(request, env)
        if not user_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        # Caller must be approved
        org_proxy = await env.sizzle_db.prepare("""
            SELECT o.id FROM organizations o
            JOIN user_organizations uo ON o.id = uo.org_id
            WHERE o.github_org_name = ? AND uo.user_id = ? AND uo.status = 'approved'
        """).bind(org_name, user_id).first()

        if not org_proxy:
            return Response.new(json.dumps({"error": "Not found or not an approved member"}),
                              {"status": 403, "headers": {"Content-Type": "application/json"}})

        org_id = org_proxy.to_py()['id']

        result_proxy = await env.sizzle_db.prepare("""
            SELECT uo.user_id, uo.status, uo.joined_at
            FROM user_organizations uo
            WHERE uo.org_id = ?
            ORDER BY uo.status DESC, uo.joined_at ASC
        """).bind(org_id).all()

        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        rows = result.get('results', []) if isinstance(result, dict) else []

        return Response.new(json.dumps({"members": rows}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error getting org members: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


async def handle_approve_org_member(request, env, org_name, target_user_id):
    """Approve a pending member. Caller must be an approved member."""
    try:
        approver_id = await get_session_user(request, env)
        if not approver_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        # Approver must be approved
        org_proxy = await env.sizzle_db.prepare("""
            SELECT o.id FROM organizations o
            JOIN user_organizations uo ON o.id = uo.org_id
            WHERE o.github_org_name = ? AND uo.user_id = ? AND uo.status = 'approved'
        """).bind(org_name, approver_id).first()

        if not org_proxy:
            return Response.new(json.dumps({"error": "Not found or not an approved member"}),
                              {"status": 403, "headers": {"Content-Type": "application/json"}})

        org_id = org_proxy.to_py()['id']

        result = await env.sizzle_db.prepare("""
            UPDATE user_organizations
            SET status = 'approved'
            WHERE user_id = ? AND org_id = ? AND status = 'pending'
        """).bind(target_user_id, org_id).run()

        result_py = result.to_py() if hasattr(result, 'to_py') else {}
        if result_py.get('changes', 1) == 0:
            return Response.new(json.dumps({"error": "No pending request found for that user"}),
                              {"status": 404, "headers": {"Content-Type": "application/json"}})

        return Response.new(json.dumps({"success": True}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error approving org member: %s", e, exc_info=True)
        return Response.new(json.dumps({"error": str(e)}),
                          {"status": 500, "headers": {"Content-Type": "application/json"}})


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


async def handle_deny_org_member(request, env, org_name, target_user_id):
    """Deny/remove a pending member. Caller must be an approved member."""
    try:
        approver_id = await get_session_user(request, env)
        if not approver_id:
            return Response.new(json.dumps({"error": "Unauthorized"}),
                              {"status": 401, "headers": {"Content-Type": "application/json"}})

        org_proxy = await env.sizzle_db.prepare("""
            SELECT o.id FROM organizations o
            JOIN user_organizations uo ON o.id = uo.org_id
            WHERE o.github_org_name = ? AND uo.user_id = ? AND uo.status = 'approved'
        """).bind(org_name, approver_id).first()

        if not org_proxy:
            return Response.new(json.dumps({"error": "Not found or not an approved member"}),
                              {"status": 403, "headers": {"Content-Type": "application/json"}})

        org_id = org_proxy.to_py()['id']
        await env.sizzle_db.prepare("""
            DELETE FROM user_organizations
            WHERE user_id = ? AND org_id = ? AND status = 'pending'
        """).bind(target_user_id, org_id).run()

        return Response.new(json.dumps({"success": True}),
                          {"headers": {"Content-Type": "application/json"}})
    except Exception as e:
        logger.error("Error denying org member: %s", e, exc_info=True)
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