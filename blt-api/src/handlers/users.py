"""
Users handler for the BLT API.
"""

import hashlib
import re
import secrets
import time
from typing import Any, Dict
from utils import error_response, parse_pagination_params, convert_d1_results, parse_json_body, check_required_fields
from libs.db import get_db_safe
from libs.constant import __HASHING_ITERATIONS
from workers import Response
from models import User, Bug, Domain, UserFollow
import logging

_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]{3,30}$')
_EMAIL_PATTERN = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
_USER_CREATE_RATE_LIMIT: Dict[str, list] = {}
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 5


def _get_header(request: Any, name: str) -> str:
    """Safely read a request header in Workers and tests."""
    headers = getattr(request, "headers", None)
    if headers and hasattr(headers, "get"):
        value = headers.get(name)
        return str(value) if value is not None else ""
    return ""


def _get_client_identifier(request: Any) -> str:
    """Build a stable client identifier for rate limiting."""
    ip = _get_header(request, "CF-Connecting-IP") or _get_header(request, "X-Forwarded-For")
    ua = _get_header(request, "User-Agent")
    return f"{ip}|{ua}".strip("|") or "unknown-client"


def _is_rate_limited(client_key: str) -> bool:
    """Basic in-memory rate limiter for user creation."""
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS

    attempts = _USER_CREATE_RATE_LIMIT.get(client_key, [])
    attempts = [ts for ts in attempts if ts >= window_start]

    if len(attempts) >= _RATE_LIMIT_MAX_REQUESTS:
        _USER_CREATE_RATE_LIMIT[client_key] = attempts
        return True

    attempts.append(now)
    _USER_CREATE_RATE_LIMIT[client_key] = attempts
    return False


def _is_strong_password(password: str) -> bool:
    """Enforce strong password requirements."""
    if len(password) < 12 or len(password) > 128:
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[^A-Za-z0-9]', password):
        return False
    return True


async def create_user(db: Any, request: Any, logger: Any) -> Any:
    """Create a new user with layered input and abuse protections."""
    if _is_rate_limited(_get_client_identifier(request)):
        return error_response("Too many requests. Please try again later.", status=429)

    content_type = _get_header(request, "Content-Type").lower()
    if "application/json" not in content_type:
        return error_response("Content-Type must be application/json", status=415)

    content_length_header = _get_header(request, "Content-Length")
    if content_length_header and content_length_header.isdigit() and int(content_length_header) > 10_000:
        return error_response("Request body too large", status=413)

    body = await parse_json_body(request)
    if not body:
        return error_response("Invalid JSON body", status=400)

    required_fields = ["username", "email", "password"]
    valid, missing_field = await check_required_fields(body, required_fields)
    if not valid:
        return error_response(f"Missing required field: {missing_field}", status=400)

    username = str(body.get("username", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    description = str(body.get("description", "")).strip()

    if not _USERNAME_PATTERN.fullmatch(username):
        return error_response(
            "Username must be 3-30 chars and contain only letters, numbers, underscore, dot, or hyphen",
            status=400,
        )

    if not _EMAIL_PATTERN.fullmatch(email) or len(email) > 254:
        return error_response("Invalid email format", status=400)

    if not _is_strong_password(password):
        return error_response(
            "Password must be 12-128 chars and include upper, lower, number, and symbol",
            status=400,
        )

    if len(description) > 500:
        return error_response("Description must be 500 characters or less", status=400)

    # Prevent account enumeration and duplicate account creation.
    existing_user = await User.objects(db).filter(username=username).first()
    if not existing_user:
        existing_user = await User.objects(db).filter(email=email).first()
    if existing_user:
        return error_response("Username or email already exists", status=409)

    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        __HASHING_ITERATIONS,
    )
    hashed_password = f"{salt}${password_hash.hex()}"

    user_data = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "is_active": False,
    }
    if description:
        user_data["description"] = description

    created_user = await User.create(db, **user_data)
    user_id = created_user.get("id") if created_user else None
    if user_id is None:
        logger.error("User creation returned no ID")
        return error_response("Failed to create user", status=500)

    return Response.json(
        {
            "success": True,
            "message": "User created. Please verify email to activate account.",
            "data": {
                "id": user_id,
                "username": username,
                "is_active": False,
            },
        },
        status=201,
    )

async def handle_users(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle user-related requests.
    
    Endpoints:
        GET /users - List users with pagination
        POST /users - Create a user account with validation and abuse protection
        GET /users/{id} - Get a specific user
        GET /users/{id}/profile - Get user profile with stats
        GET /users/{id}/bugs - Get bugs reported by user
        GET /users/{id}/domains - Get domains submitted by user
        GET /users/{id}/followers - Get user's followers
        GET /users/{id}/following - Get users this user follows
    """
    method = str(request.method).upper()
    logger = logging.getLogger(__name__)

    if method not in {"GET", "POST"}:
        return error_response("Method Not Allowed", status=405, headers={"Allow": "GET, POST"})
    
    try: 
        db = await get_db_safe(env)  
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return error_response(f"Database connection error: {str(e)}", status=500)
    
    try: 
        if method == "POST" and "id" in path_params:
            return error_response("Method Not Allowed", status=405, headers={"Allow": "GET"})

        if method == "POST":
            return await create_user(db, request, logger)

        # Get specific user
        if "id" in path_params:
            user_id = path_params["id"]
            
            # Validate ID is numeric
            if not user_id.isdigit():
                return error_response("Invalid user ID", status=400)
            
            # Handle different sub-endpoints
            if path.endswith("/profile"):
                return await get_user_profile(db, user_id)
            elif path.endswith("/bugs"):
                return await get_user_bugs(db, user_id, query_params)
            elif path.endswith("/domains"):
                return await get_user_domains(db, user_id, query_params)
            elif path.endswith("/followers"):
                return await get_user_followers(db, user_id, query_params)
            elif path.endswith("/following"):
                return await get_user_following(db, user_id, query_params)
            else:
                # Get basic user info
                return await get_user(db, user_id)
        
        # List users with pagination
        page, per_page = parse_pagination_params(query_params)

        total_count = await User.objects(db).filter(is_active=1).count()
        users = (
            await User.objects(db)
            .filter(is_active=1)
            .values(
                "id", "username", "user_avatar", "total_score",
                "winnings", "description", "date_joined", "is_active"
            )
            .order_by("-total_score")
            .paginate(page, per_page)
            .all()
        )

        return Response.json({
            "success": True,
            "data": users,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(users),
                "total": total_count
            }
        })
    except Exception as e:
        logger.error(f"Error handling user request: {str(e)}")
        return error_response(f"Error handling user request: {str(e)}", status=500)


async def get_user(db: Any, user_id: str) -> Any:
    """
    Fetch basic user information by user ID.
    
    Args:
        db: D1 database connection
        user_id: User ID as string (will be converted to int)
    
    Returns:
        JSON response with user data (excluding sensitive fields like password and email)
        or error response if user not found
    """
    logger = logging.getLogger(__name__)
    try:
        user = await User.objects(db).get(id=int(user_id))

        if not user:
            return error_response("User not found", status=404)

        # Remove sensitive fields
        user.pop('password', None)
        user.pop('email', None)

        return Response.json({"success": True, "data": user})
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        return error_response(f"Error fetching user: {str(e)}", status=500)


async def get_user_profile(db: Any, user_id: str) -> Any:
    """
    Fetch detailed user profile with comprehensive statistics.
    
    Retrieves user information along with aggregated stats including:
    - Bug counts (total, verified, closed)
    - Domain submissions count
    - Social metrics (followers, following)
    
    Args:
        db: D1 database connection
        user_id: User ID as string (will be converted to int)
    
    Returns:
        JSON response with user data and nested 'stats' object containing metrics,
        or error response if user not found
    """
    logger = logging.getLogger(__name__)
    try:
        user = await User.objects(db).get(id=int(user_id))

        if not user:
            return error_response("User not found", status=404)

        user.pop('password', None)
        user.pop('email', None)

        # Aggregated statistics still use raw SQL (aggregate functions /
        # CASE expressions are outside the ORM's current scope).
        bug_stats_row = await db.prepare('''
            SELECT 
                COUNT(*) as total_bugs,
                SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) as verified_bugs,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_bugs
            FROM bugs
            WHERE user = ?
        ''').bind(int(user_id)).first()
        bug_stats = bug_stats_row.to_py() if hasattr(bug_stats_row, 'to_py') else dict(bug_stats_row)

        domains_count = await Domain.objects(db).filter(user=int(user_id)).count()
        followers_count = await UserFollow.objects(db).filter(following_id=int(user_id)).count()
        following_count = await UserFollow.objects(db).filter(follower_id=int(user_id)).count()

        user['stats'] = {
            'total_bugs': bug_stats['total_bugs'] if bug_stats else 0,
            'verified_bugs': bug_stats['verified_bugs'] if bug_stats else 0,
            'closed_bugs': bug_stats['closed_bugs'] if bug_stats else 0,
            'domains': domains_count,
            'followers': followers_count,
            'following': following_count,
        }

        return Response.json({"success": True, "data": user})
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        return error_response(f"Error fetching user profile: {str(e)}", status=500)


async def get_user_bugs(db: Any, user_id: str, query_params: Dict[str, str]) -> Any:
    """
    Retrieve paginated list of bugs reported by a specific user.
    
    Args:
        db: D1 database connection
        user_id: User ID as string (will be converted to int)
        query_params: Query parameters dict containing 'page' and 'per_page' for pagination
    
    Returns:
        Paginated JSON response with bugs data including metadata:
        bug id, url, description, status, verified flag, score, created date, and domain
    """
    logger = logging.getLogger(__name__)
    try:
        page, per_page = parse_pagination_params(query_params)

        total_count = await Bug.objects(db).filter(user=int(user_id)).count()
        bugs = (
            await Bug.objects(db)
            .filter(user=int(user_id))
            .values("id", "url", "description", "status", "verified", "score", "created", "domain")
            .order_by("-created")
            .paginate(page, per_page)
            .all()
        )

        return Response.json({
            "success": True,
            "data": bugs,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(bugs),
                "total": total_count
            }
        })
    except Exception as e:
        logger.error(f"Error fetching user bugs: {str(e)}")
        return error_response(f"Error fetching user bugs: {str(e)}", status=500)


async def get_user_domains(db: Any, user_id: str, query_params: Dict[str, str]) -> Any:
    """
    Retrieve paginated list of domains submitted by a specific user.
    
    Args:
        db: D1 database connection
        user_id: User ID as string (will be converted to int)
        query_params: Query parameters dict containing 'page' and 'per_page' for pagination
    
    Returns:
        Paginated JSON response with domain data including:
        id, name, url, logo, clicks, created timestamp, and active status
    """
    logger = logging.getLogger(__name__)
    try:
        page, per_page = parse_pagination_params(query_params)

        total_count = await Domain.objects(db).filter(user=int(user_id)).count()
        domains = (
            await Domain.objects(db)
            .filter(user=int(user_id))
            .values("id", "name", "url", "logo", "clicks", "created", "is_active")
            .order_by("-created")
            .paginate(page, per_page)
            .all()
        )

        return Response.json({
            "success": True,
            "data": domains,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(domains),
                "total": total_count
            }
        })
    except Exception as e:
        logger.error(f"Error fetching user domains: {str(e)}")
        return error_response(f"Error fetching user domains: {str(e)}", status=500)


async def get_user_followers(db: Any, user_id: str, query_params: Dict[str, str]) -> Any:
    """
    Retrieve paginated list of users who follow the specified user.
    
    Queries the user_follows table to find all follower relationships where
    this user is being followed.
    
    Args:
        db: D1 database connection
        user_id: Target user ID as string (will be converted to int)
        query_params: Query parameters dict containing 'page' and 'per_page' for pagination
    
    Returns:
        Paginated JSON response with follower user data including:
        id, username, avatar, and total_score, ordered by follow date (newest first)
    """
    logger = logging.getLogger(__name__)
    try:
        page, per_page = parse_pagination_params(query_params)

        total_count = await UserFollow.objects(db).filter(following_id=int(user_id)).count()

        # JOIN query – kept as raw parameterized SQL (ORM does not support JOINs).
        result = await db.prepare('''
            SELECT u.id, u.username, u.user_avatar, u.total_score
            FROM users u
            INNER JOIN user_follows uf ON u.id = uf.follower_id
            WHERE uf.following_id = ?
            ORDER BY uf.created DESC
            LIMIT ? OFFSET ?
        ''').bind(int(user_id), per_page, (page - 1) * per_page).all()

        followers = convert_d1_results(result.results if hasattr(result, 'results') else [])

        return Response.json({
            "success": True,
            "data": followers,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(followers),
                "total": total_count
            }
        })
    except Exception as e:
        logger.error(f"Error fetching user followers: {str(e)}")
        return error_response(f"Error fetching user followers: {str(e)}", status=500)

async def get_user_following(db: Any, user_id: str, query_params: Dict[str, str]) -> Any:
    """
    Retrieve paginated list of users that the specified user is following.
    
    Queries the user_follows table to find all users this user has chosen to follow.
    
    Args:
        db: D1 database connection
        user_id: The user ID as string (will be converted to int) whose following list to fetch
        query_params: Query parameters dict containing 'page' and 'per_page' for pagination
    
    Returns:
        Paginated JSON response with followed users data including:
        id, username, avatar, and total_score, ordered by follow date (newest first)
    """
    logger = logging.getLogger(__name__)
    try:
        page, per_page = parse_pagination_params(query_params)

        total_count = await UserFollow.objects(db).filter(follower_id=int(user_id)).count()

        # JOIN query – kept as raw parameterized SQL (ORM does not support JOINs).
        result = await db.prepare('''
            SELECT u.id, u.username, u.user_avatar, u.total_score
            FROM users u
            INNER JOIN user_follows uf ON u.id = uf.following_id
            WHERE uf.follower_id = ?
            ORDER BY uf.created DESC
            LIMIT ? OFFSET ?
        ''').bind(int(user_id), per_page, (page - 1) * per_page).all()

        following = convert_d1_results(result.results if hasattr(result, 'results') else [])

        return Response.json({
            "success": True,
            "data": following,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(following),
                "total": total_count
            }
        })
    except Exception as e:
        logger.error(f"Error fetching user following: {str(e)}")
        return error_response(f"Error fetching user following: {str(e)}", status=500)
