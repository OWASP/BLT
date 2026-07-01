"""
Contributors handler for the BLT API.
"""

from typing import Any, Dict
from utils import json_response, error_response, paginated_response, parse_pagination_params, convert_d1_results
from libs.db import get_db_safe
import logging

async def handle_contributors(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle contributor-related requests natively via D1 database.
    
    Endpoints:
        GET /contributors - List contributors with pagination
        GET /contributors/{id} - Get a specific contributor
    """
    logger = logging.getLogger(__name__)
    try: 
        db = await get_db_safe(env)  
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return error_response(f"Database connection error: {str(e)}", status=500)
    
    # Get specific contributor
    if "id" in path_params:
        contributor_id = path_params["id"]
        
        if not contributor_id.isdigit():
            return error_response("Invalid contributor ID", status=400)
            
        result = await db.prepare('''
            SELECT c.id, c.user_id, c.project_id, c.repository_id, c.score, c.created, u.username
            FROM contributors c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
        ''').bind(int(contributor_id)).first()
        
        contributor_data = None
        if result:
            if hasattr(result, 'to_py'):
                contributor_data = result.to_py()
            elif isinstance(result, dict):
                contributor_data = dict(result)
                
        if not contributor_data:
            return error_response("Contributor not found", status=404)
            
        return json_response({
            "success": True,
            "data": contributor_data
        })
    
    # List contributors with pagination
    page, per_page = parse_pagination_params(query_params)
    
    # Count total
    count_query = "SELECT COUNT(*) as total FROM contributors"
    total_result = await db.prepare(count_query).first()
    
    total = 0
    if total_result:
        if hasattr(total_result, 'to_py'):
            total = total_result.to_py().get('total', 0)
        elif isinstance(total_result, dict):
            total = total_result.get('total', 0)
            
    # Get contributors
    list_query = '''
        SELECT c.id, c.user_id, c.project_id, c.repository_id, c.score, c.created, u.username
        FROM contributors c
        LEFT JOIN users u ON c.user_id = u.id
        ORDER BY c.score DESC, c.created DESC
        LIMIT ? OFFSET ?
    '''
    
    result = await db.prepare(list_query).bind(per_page, (page - 1) * per_page).all()
    data = convert_d1_results(result.results if hasattr(result, 'results') else [])
    
    return json_response({
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "count": len(data),
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
        }
    })
