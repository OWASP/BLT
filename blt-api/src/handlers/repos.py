"""
Repositories handler for the BLT API.
"""

from typing import Any, Dict
from utils import json_response, error_response, paginated_response, parse_pagination_params, convert_d1_results
from libs.db import get_db_safe
import logging

async def handle_repos(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle repository-related requests natively via D1 database.
    
    Endpoints:
        GET /repos - List repositories with pagination
        GET /repos/{id} - Get a specific repository
    """
    logger = logging.getLogger(__name__)
    try: 
        db = await get_db_safe(env)  
    except Exception:
        logger.exception("Database connection error")
        return error_response("Database connection error", status=500)
    
    # Get specific repository
    if "id" in path_params:
        repo_id = path_params["id"]
        
        if not repo_id.isdigit():
            return error_response("Invalid repository ID", status=400)
            
        result = await db.prepare('''
            SELECT id, organization_id, project_id, name, url, created, modified 
            FROM repositories 
            WHERE id = ?
        ''').bind(int(repo_id)).first()
        
        repo_data = None
        if result:
            if hasattr(result, 'to_py'):
                repo_data = result.to_py()
            elif isinstance(result, dict):
                repo_data = dict(result)
                
        if not repo_data:
            return error_response("Repository not found", status=404)
            
        return json_response({
            "success": True,
            "data": repo_data
        })
    
    # List repositories with pagination
    page, per_page = parse_pagination_params(query_params)
    org_id = query_params.get("organization")
    project_id = query_params.get("project")
    
    where_clauses = []
    bindings = []
    
    if org_id:
        if not org_id.isdigit():
            return error_response("Invalid organization ID", status=400)
        where_clauses.append("organization_id = ?")
        bindings.append(int(org_id))
    
    if project_id:
        if not project_id.isdigit():
            return error_response("Invalid project ID", status=400)
        where_clauses.append("project_id = ?")
        bindings.append(int(project_id))
        
    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)
        
    # Count total
    count_query = f"SELECT COUNT(*) as total FROM repositories{where_sql}"
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
            
    # Get repos
    list_query = f'''
        SELECT id, organization_id, project_id, name, url, created, modified 
        FROM repositories
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

