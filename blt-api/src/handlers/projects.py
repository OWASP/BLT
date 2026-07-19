"""
Projects handler for the BLT API.
"""

from typing import Any, Dict
from utils import json_response, error_response, paginated_response, parse_pagination_params, convert_d1_results
from libs.db import get_db_safe
import logging

async def handle_projects(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle project-related requests natively via D1 database.
    
    Endpoints:
        GET /projects - List projects with pagination
        GET /projects/{id} - Get a specific project
        GET /projects/{id}/contributors - Get contributors for a project
    """
    logger = logging.getLogger(__name__)
    try: 
        db = await get_db_safe(env)  
    except Exception:
        logger.exception("Database connection error")
        return error_response("Database connection error", status=500)
    
    # Check if this is a request for project contributors
    if path.endswith("/contributors") and "id" in path_params:
        project_id = path_params["id"]
        if not project_id.isdigit():
            return error_response("Invalid project ID", status=400)
            
        page, per_page = parse_pagination_params(query_params)
        
        # Count total contributors
        count_result = await db.prepare("SELECT COUNT(*) as total FROM contributors WHERE project_id = ?").bind(int(project_id)).first()
        total = count_result.get('total', 0) if count_result and isinstance(count_result, dict) else (count_result.to_py().get('total', 0) if count_result and hasattr(count_result, 'to_py') else 0)
        
        # Get contributors
        query = '''
            SELECT c.id, c.user_id, c.score, c.created, u.username
            FROM contributors c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.project_id = ?
            ORDER BY c.score DESC
            LIMIT ? OFFSET ?
        '''
        result = await db.prepare(query).bind(int(project_id), per_page, (page - 1) * per_page).all()
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
        
    # Get specific project
    if "id" in path_params:
        project_id = path_params["id"]
        
        if not project_id.isdigit():
            return error_response("Invalid project ID", status=400)
        
        result = await db.prepare('''
            SELECT id, organization_id, name, description, status, created, modified 
            FROM projects 
            WHERE id = ?
        ''').bind(int(project_id)).first()
        
        project_data = None
        if result:
            if hasattr(result, 'to_py'):
                project_data = result.to_py()
            elif isinstance(result, dict):
                project_data = dict(result)
                
        if not project_data:
            return error_response("Project not found", status=404)
            
        return json_response({
            "success": True,
            "data": project_data
        })
    
    # List projects with pagination
    page, per_page = parse_pagination_params(query_params)
    organization_id = query_params.get("organization")
    
    where_sql = ""
    bindings = []
    if organization_id:
        if not organization_id.isdigit():
            return error_response("Invalid organization ID", status=400)
        where_sql = " WHERE organization_id = ?"
        bindings.append(int(organization_id))
    
    # Count total
    count_query = f"SELECT COUNT(*) as total FROM projects{where_sql}"
    stmt = db.prepare(count_query)
    if bindings:
        stmt = stmt.bind(*bindings)
    total_result = await stmt.first()
    
    total = 0
    if total_result:
        if hasattr(total_result, 'to_py'):
            total = total_result.to_py().get('total', 0)
        elif isinstance(total_result, dict):
            total = total_result.get('total', 0)
            
    # Get projects
    list_query = f'''
        SELECT id, organization_id, name, description, status, created, modified 
        FROM projects
        {where_sql}
        ORDER BY created DESC
        LIMIT ? OFFSET ?
    '''
    
    bindings.extend([per_page, (page - 1) * per_page])
    stmt = db.prepare(list_query)
    stmt = stmt.bind(*bindings)
    result = await stmt.all()
    
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
