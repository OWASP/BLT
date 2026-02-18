"""
Bugs handler for the BLT API.
"""

from typing import Any, Dict
from utils import json_response, error_response, paginated_response, parse_pagination_params, parse_json_body
from libs.db import get_db_safe
from utils import convert_d1_results

async def handle_bugs(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle bugs-related requests.
    
    Endpoints:
        GET /bugs - List bugs with pagination and filters
        GET /bugs/{id} - Get a specific bug
        POST /bugs - Create a new bug
        GET /bugs/search - Search bugs
    """
    method = str(request.method).upper()
    try: 
        db = await get_db_safe(env)  
    except Exception as e:
        return error_response(f"Database connection error: {str(e)}", status=500)
    
    if path.endswith("/search"):
        query = query_params.get("q", "")
        if not query:
            return error_response("Search query 'q' is required", status=400)
        
        limit = query_params.get("limit", "10")
        try:
            limit_int = min(max(int(limit), 1), 100)
        except ValueError:
            limit_int = 10
        
        search_result = await db.prepare('''
            SELECT 
                b.id,
                b.url,
                b.description,
                b.status,   
                b.verified,
                b.score,
                b.views,    
                b.created,
                b.modified,
                b.is_hidden,
                b.rewarded, 
                b.cve_id,
                b.cve_score,    
                b.domain,
                d.name as domain_name,
                d.url as domain_url 
            FROM bugs b   
            LEFT JOIN domains d ON b.domain = d.id
            WHERE b.url LIKE ? OR b.description LIKE ?
            ORDER BY b.created DESC
            LIMIT ? OFFSET 0
        ''').bind(f"%{query}%", f"%{query}%", limit_int).all()
        
        response_data = convert_d1_results(search_result.results if hasattr(search_result, 'results') else [])
        return json_response({
            "success": True,
            "query": query,
            "data": response_data
        })
    
    # Get specific bug
    if "id" in path_params:
        try:
            bug_id = int(path_params["id"])
        except ValueError:
            return error_response("Invalid bug id format", status=400)

        result = await db.prepare('''
            SELECT 
                b.id,
                b.url,
                b.description,
                b.markdown_description,
                b.label,
                b.views,
                b.verified,
                b.score,
                b.status,
                b.user_agent,
                b.ocr,
                b.screenshot,
                b.closed_date,
                b.github_url,
                b.created,
                b.modified,
                b.is_hidden,
                b.rewarded,
                b.reporter_ip_address,
                b.cve_id,
                b.cve_score,
                b.hunt,
                b.domain,
                b.user,
                b.closed_by,
                d.id as domain_id,
                d.name as domain_name,
                d.url as domain_url,
                d.logo as domain_logo
            FROM bugs b
            LEFT JOIN domains d ON b.domain = d.id
            WHERE b.id = ?
        ''').bind(bug_id).first()
        
        # Convert JsProxy result directly to Python dict
        if result and hasattr(result, 'to_py'):
            bug_data = result.to_py()
        elif result and isinstance(result, dict):
            bug_data = dict(result)
        else:
            bug_data = None
        
        if not bug_data:
            return error_response("Bug not found", status=404)
        
        # Get screenshots for this bug
        screenshots_result = await db.prepare('''
            SELECT id, image, created
            FROM bug_screenshots
            WHERE bug = ?
            ORDER BY created DESC
        ''').bind(bug_id).all()
        
        # Get tags for this bug
        tags_result = await db.prepare('''
            SELECT t.id, t.name
            FROM bug_tags bt
            JOIN tags t ON bt.tag_id = t.id
            WHERE bt.bug_id = ?
            ORDER BY t.name
        ''').bind(bug_id).all()
        
        # Convert results
        screenshots_data = convert_d1_results(screenshots_result.results if hasattr(screenshots_result, 'results') else [])
        tags_data = convert_d1_results(tags_result.results if hasattr(tags_result, 'results') else [])
        
        # Add screenshots and tags to bug data
        bug_data['screenshots'] = screenshots_data
        bug_data['tags'] = tags_data
        
        return json_response({
            "success": True,
            "data": bug_data
        })
    
    # Create bug
    if method == "POST":
        body = await parse_json_body(request)
        
        if not body:
            return error_response("Request body is required", status=400)
        
        # Validate required fields
        required_fields = ["url", "description"]
        missing_fields = [f for f in required_fields if f not in body]
        
        if missing_fields:
            return error_response(
                f"Missing required fields: {', '.join(missing_fields)}",
                status=400
            )
        
        # Validate URL length
        if len(body["url"]) > 200:
            return error_response("URL must be 200 characters or less", status=400)
        
        try:
            # Insert the new bug - use None for NULL values
            result = await db.prepare('''
                INSERT INTO bugs (
                    url, description, markdown_description, label, views, verified,
                    score, status, user_agent, ocr, screenshot, github_url,
                    is_hidden, rewarded, reporter_ip_address, cve_id, cve_score,
                    hunt, domain, user, closed_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''').bind(
                body.get("url"),
                body.get("description"),
                body.get("markdown_description") or None,
                body.get("label") or None,
                body.get("views") or None,
                1 if body.get("verified") else 0,
                body.get("score") or None,
                body.get("status") or "open",
                body.get("user_agent") or None,
                body.get("ocr") or None,
                body.get("screenshot") or None,
                body.get("github_url") or None,
                1 if body.get("is_hidden") else 0,
                body.get("rewarded") or 0,
                body.get("reporter_ip_address") or None,
                body.get("cve_id") or None,
                body.get("cve_score") or None,
                body.get("hunt") or None,
                body.get("domain") or None,
                body.get("user") or None,
                body.get("closed_by") or None
            ).run()
            
            # Get the last inserted row ID
            last_id_result = await db.prepare(
                'SELECT last_insert_rowid() as id'
            ).first()
            
            if last_id_result:
                if hasattr(last_id_result, 'to_py'):
                    last_id = last_id_result.to_py().get('id')
                elif hasattr(last_id_result, 'id'):
                    last_id = last_id_result.id
                elif isinstance(last_id_result, dict):
                    last_id = last_id_result.get('id')
                else:
                    last_id = None
            else:
                last_id = None
            
            # Fetch the created bug
            if last_id:
                created_bug = await db.prepare(
                    'SELECT * FROM bugs WHERE id = ?'
                ).bind(last_id).first()
                
                # Convert JsProxy result directly to Python dict
                if created_bug and hasattr(created_bug, 'to_py'):
                    bug_data = created_bug.to_py()
                elif created_bug and isinstance(created_bug, dict):
                    bug_data = dict(created_bug)
                else:
                    bug_data = {"id": last_id}
                
                return json_response({
                    "success": True,
                    "message": "Bug created successfully",
                    "data": bug_data
                }, status=201)
            else:
                return json_response({
                    "success": True,
                    "message": "Bug created successfully"
                }, status=201)
                
        except Exception as e:
            return error_response(f"Failed to create bug: {str(e)}", status=500)
    
    # List bugs with pagination
    page, per_page = parse_pagination_params(query_params)
    
    # Build WHERE conditions based on filters
    where_conditions = []
    params = []
    
    # Filter by status
    status = query_params.get("status")
    if status:
        where_conditions.append("b.status = ?")
        params.append(status)
    
    # Filter by domain
    domain = query_params.get("domain")
    if domain and domain.isdigit():
        where_conditions.append("b.domain = ?")
        params.append(int(domain))
    
    # Filter by verified
    verified = query_params.get("verified")
    if verified:
        where_conditions.append("b.verified = ?")
        params.append(1 if verified.lower() == "true" else 0)
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    try:
        # Get total count
        count_query = f'SELECT COUNT(*) as total FROM bugs b{where_clause}'
        count_result = await db.prepare(count_query).bind(*params).first()
        
        # Handle count result
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
        
        # Get paginated results with domain info
        list_query = f'''
            SELECT 
                b.id,
                b.url,
                b.description,
                b.status,
                b.verified,
                b.score,
                b.views,
                b.created,
                b.modified,
                b.is_hidden,
                b.rewarded,
                b.cve_id,
                b.cve_score,
                b.domain,
                d.name as domain_name,
                d.url as domain_url
            FROM bugs b
            LEFT JOIN domains d ON b.domain = d.id
            {where_clause}
            ORDER BY b.created DESC
            LIMIT ? OFFSET ?
        '''
        
        result = await db.prepare(list_query).bind(
            *params, per_page, (page - 1) * per_page
        ).all()
        
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
        return error_response(f"Failed to fetch bugs: {str(e)}", status=500)
