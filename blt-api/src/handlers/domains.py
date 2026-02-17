"""
Domains handler for the BLT API.
"""

from typing import Any, Dict, List
from utils import json_response, error_response, paginated_response, parse_pagination_params
from libs.db import get_db_safe
from utils import convert_d1_results

async def handle_domains(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle domain-related requests.
    
    Endpoints:
        GET /domains - List domains with pagination
        GET /domains/{id} - Get a specific domain
        GET /domains/{id}/tags - Get tags for a domain
    """
    try:
        db = await get_db_safe(env)  # Ensure database is available and initialized
    except Exception as e:
        return error_response(str(e), status=503)
    
    # Get specific domain
    if "id" in path_params:
        domain_id = path_params["id"]
        
        # Validate ID is numeric
        if not domain_id.isdigit():
            return error_response("Invalid domain ID", status=400)
        
        # Check if requesting tags for domain: /domains/{id}/tags
        if path.endswith("/tags"):
            try:
                page, per_page = parse_pagination_params(query_params)
                
                result = await db.prepare('''
                    SELECT t.id, t.name, t.created
                    FROM tags t
                    INNER JOIN domain_tags dt ON t.id = dt.tag_id
                    WHERE dt.domain_id = ?
                    ORDER BY t.name
                    LIMIT ? OFFSET ?
                ''').bind(int(domain_id), per_page, (page - 1) * per_page).all()
                
                # Convert D1 proxy results to Python list
                data = convert_d1_results(result.results if hasattr(result, 'results') else [])
                
                return json_response({
                    "success": True,
                    "domain_id": int(domain_id),
                    "data": data,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "count": len(data)
                    }
                })
            except Exception as e:
                return error_response(f"Failed to fetch domain tags: {str(e)}", status=500)
        
        # Get domain details: /domains/{id}
        try:
            result = await db.prepare(
                'SELECT * FROM domains WHERE id = ?'
            ).bind(int(domain_id)).first()
            
            # D1 .first() returns None or a row dict/proxy
            if not result:
                return error_response("Domain not found", status=404)
            
            # Convert JsProxy to Python dict
            if hasattr(result, 'to_py'):
                domain = result.to_py()
            elif isinstance(result, dict):
                domain = result
            else:
                # Try to convert object attributes to dict
                domain = {}
                for key in dir(result):
                    if not key.startswith('_'):
                        try:
                            domain[key] = getattr(result, key)
                        except:
                            pass
            
            return json_response({
                "success": True,
                "data": domain
            })
        except Exception as e:
            return error_response(f"Failed to fetch domain: {str(e)}", status=500)
    
    # List domains with pagination: /domains
    try:
        page, per_page = parse_pagination_params(query_params)
        
        # Get total count
        count_result = await db.prepare(
            'SELECT COUNT(*) as total FROM domains'
        ).first()
        
        # Handle JsProxy object for count
        if count_result:
            if hasattr(count_result, 'to_py'):
                count_dict = count_result.to_py()
                total = count_dict.get('total', 0)
            elif hasattr(count_result, 'total'):
                total = count_result.total
            elif isinstance(count_result, dict):
                total = count_result.get('total', 0)
            else:
                total = 0
        else:
            total = 0
        
        # Get paginated results
        result = await db.prepare('''
            SELECT *
            FROM domains
            ORDER BY created DESC
            LIMIT ? OFFSET ?
        ''').bind(per_page, (page - 1) * per_page).all()
        
        # Convert D1 proxy results to Python list
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
    except Exception as e:
        return error_response(f"Failed to fetch domains: {str(e)}", status=500)
