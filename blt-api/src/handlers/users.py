"""
Users handler for the BLT API.
"""

from typing import Any, Dict
from utils import error_response, parse_pagination_params, convert_d1_results
from libs.db import get_db_safe
from workers import Response
from models import User, Bug, Domain, UserFollow
import logging

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
        GET /users/{id} - Get a specific user
        GET /users/{id}/profile - Get user profile with stats
        GET /users/{id}/bugs - Get bugs reported by user
        GET /users/{id}/domains - Get domains submitted by user
        GET /users/{id}/followers - Get user's followers
        GET /users/{id}/following - Get users this user follows
    """
    method = str(request.method).upper()
    logger = logging.getLogger(__name__)
    
    try: 
        db = await get_db_safe(env)  
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return error_response(f"Database connection error: {str(e)}", status=500)
    
    try: 
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
