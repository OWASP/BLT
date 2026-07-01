"""
Bug Hunts handler for the BLT API.
"""

from typing import Any, Dict
from utils import json_response, error_response, paginated_response, parse_pagination_params, convert_d1_results
from libs.db import get_db_safe
from models import Hunt
import logging

async def handle_hunts(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle bug hunt-related requests natively via D1 database.
    
    Endpoints:
        GET /hunts - List all bug hunts
        GET /hunts/{id} - Get a specific bug hunt
        GET /hunts/active - Get currently active hunts
        GET /hunts/previous - Get past hunts
        GET /hunts/upcoming - Get upcoming hunts
    """
    logger = logging.getLogger(__name__)
    try: 
        db = await get_db_safe(env)  
    except Exception:
        logger.exception("Database connection error")
        return error_response("Database connection error", status=500)
    
    # Get specific hunt
    if "id" in path_params:
        hunt_id = path_params["id"]
        
        if not hunt_id.isdigit():
            return error_response("Invalid hunt ID", status=400)
        
        result = await db.prepare('''
            SELECT id, title, description, starts_at, ends_at, is_active, created, modified 
            FROM hunts 
            WHERE id = ?
        ''').bind(int(hunt_id)).first()
        
        if result and hasattr(result, 'to_py'):
            hunt_data = result.to_py()
        elif result and isinstance(result, dict):
            hunt_data = dict(result)
        else:
            hunt_data = None
            
        if not hunt_data:
            return error_response("Hunt not found", status=404)
        
        return json_response({
            "success": True,
            "data": hunt_data
        })
    
    # Determine filters
    is_active_filter = path.endswith("/active") or query_params.get("active") == "true"
    is_previous_filter = path.endswith("/previous") or query_params.get("previous") == "true"
    is_upcoming_filter = path.endswith("/upcoming") or query_params.get("upcoming") == "true"
    
    where_clauses = []
    if is_active_filter:
        where_clauses.append("is_active = 1 AND starts_at <= CURRENT_TIMESTAMP AND ends_at >= CURRENT_TIMESTAMP")
    elif is_previous_filter:
        where_clauses.append("ends_at < CURRENT_TIMESTAMP")
    elif is_upcoming_filter:
        where_clauses.append("starts_at > CURRENT_TIMESTAMP")
        
    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)
        
    # Pagination
    page, per_page = parse_pagination_params(query_params)
    
    # Count total
    count_query = f"SELECT COUNT(*) as total FROM hunts{where_sql}"
    total_result = await db.prepare(count_query).first()
    
    if total_result and hasattr(total_result, 'to_py'):
        total = total_result.to_py().get('total', 0)
    elif total_result and isinstance(total_result, dict):
        total = total_result.get('total', 0)
    elif total_result and hasattr(total_result, 'total'):
        total = getattr(total_result, 'total')
    else:
        total = 0
        
    # List queries
    list_query = f'''
        SELECT id, title, description, starts_at, ends_at, is_active, created, modified 
        FROM hunts
        {where_sql}
        ORDER BY created DESC
        LIMIT ? OFFSET ?
    '''
    
    result = await db.prepare(list_query).bind(per_page, (page - 1) * per_page).all()
    data = convert_d1_results(result.results if hasattr(result, 'results') else [])
    
    filter_name = None
    if is_active_filter:
        filter_name = "active"
    elif is_previous_filter:
        filter_name = "previous"
    elif is_upcoming_filter:
        filter_name = "upcoming"
        
    response = {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "count": len(data),
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
        }
    }
    
    if filter_name:
        response["filter"] = filter_name
        
    return json_response(response)
