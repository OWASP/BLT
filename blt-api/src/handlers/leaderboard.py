"""
Leaderboard handler for the BLT API.
"""

from typing import Any, Dict
from utils import json_response, error_response, paginated_response, parse_pagination_params, convert_d1_results
from libs.db import get_db_safe
import logging

async def handle_leaderboard(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle leaderboard-related requests natively via D1 database.
    
    Endpoints:
        GET /leaderboard - Get global leaderboard
        GET /leaderboard/monthly - Get monthly leaderboard
        GET /leaderboard/organizations - Get organization leaderboard
    """
    logger = logging.getLogger(__name__)
    try: 
        db = await get_db_safe(env)  
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return error_response(f"Database connection error: {str(e)}", status=500)
        
    page, per_page = parse_pagination_params(query_params)
    
    # Monthly leaderboard
    if path.endswith("/monthly"):
        month = query_params.get("month")
        year = query_params.get("year")
        
        # We need bugs submitted in that month, grouped by user
        # For simplicity, if not provided, just return global
        
        list_query = '''
            SELECT u.id, u.username, u.title, SUM(b.score) as total_score
            FROM users u
            JOIN bugs b ON u.id = b.user
            WHERE b.created >= datetime(?, 'start of month')
              AND b.created < datetime(?, 'start of month', '+1 month')
            GROUP BY u.id, u.username, u.title
            ORDER BY total_score DESC
            LIMIT ? OFFSET ?
        '''
        # This is a simplified version; in a real app you'd parse month/year exactly
        # But wait, without valid month/year, we can't easily query this.
        # So let's fall back to a standard user score query if no dates.
        if month and year:
            date_str = f"{year}-{month.zfill(2)}-01"
            result = await db.prepare(list_query).bind(date_str, date_str, per_page, (page - 1) * per_page).all()
        else:
            result = await db.prepare('''
                SELECT id, username, title, total_score
                FROM users
                ORDER BY total_score DESC
                LIMIT ? OFFSET ?
            ''').bind(per_page, (page - 1) * per_page).all()
            
        data = convert_d1_results(result.results if hasattr(result, 'results') else [])
        
        return json_response({
            "success": True,
            "type": "monthly",
            "month": month,
            "year": year,
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(data)
            }
        })
    
    # Organization leaderboard
    if path.endswith("/organizations"):
        # Organizations ranked by sum of bug scores associated with their domains
        list_query = '''
            SELECT o.id, o.name, SUM(b.score) as total_score
            FROM organization o
            JOIN domains d ON o.id = d.organization
            JOIN bugs b ON d.id = b.domain
            GROUP BY o.id, o.name
            ORDER BY total_score DESC
            LIMIT ? OFFSET ?
        '''
        
        result = await db.prepare(list_query).bind(per_page, (page - 1) * per_page).all()
        data = convert_d1_results(result.results if hasattr(result, 'results') else [])
        
        return json_response({
            "success": True,
            "type": "organizations",
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(data)
            }
        })
    
    # Global leaderboard
    list_query = '''
        SELECT id, username, title, total_score
        FROM users
        ORDER BY total_score DESC
        LIMIT ? OFFSET ?
    '''
    
    result = await db.prepare(list_query).bind(per_page, (page - 1) * per_page).all()
    data = convert_d1_results(result.results if hasattr(result, 'results') else [])
    
    # Count total
    count_query = "SELECT COUNT(*) as total FROM users WHERE total_score > 0"
    total_result = await db.prepare(count_query).first()
    
    total = 0
    if total_result:
        if hasattr(total_result, 'to_py'):
            total = total_result.to_py().get('total', 0)
        elif isinstance(total_result, dict):
            total = total_result.get('total', 0)
            
    return json_response({
        "success": True,
        "type": "global",
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "count": len(data),
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
        }
    })

