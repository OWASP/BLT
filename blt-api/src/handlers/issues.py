"""
Issues handler for the BLT API.
"""

from typing import Any, Dict
from utils import json_response, error_response, paginated_response, parse_pagination_params, parse_json_body
from client import create_client
from libs.db import get_db_safe
from utils import convert_d1_results

async def handle_issues(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle issues-related requests.
    
    Endpoints:
        GET /issues - List issues with pagination and filters
        GET /issues/{id} - Get a specific issue
        POST /issues - Create a new issue
        GET /issues/search - Search issues
    """
    client = create_client(env)
    method = str(request.method).upper()
    db = await get_db_safe(env)  
    
    # Get specific issue
    if "id" in path_params:
        issue_id = path_params["id"]
        
        # Validate ID is numeric
        if not issue_id.isdigit():
            return error_response("Invalid issue ID", status=400)
        
        result = await db.prepare('''
            SELECT 
                i.id,
                i.url,
                i.description,
                i.markdown_description,
                i.label,
                i.views,
                i.verified,
                i.score,
                i.status,
                i.user_agent,
                i.ocr,
                i.screenshot,
                i.closed_date,
                i.github_url,
                i.created,
                i.modified,
                i.is_hidden,
                i.rewarded,
                i.reporter_ip_address,
                i.cve_id,
                i.cve_score,
                i.hunt,
                i.domain,
                i.user,
                i.closed_by,
                d.id as domain_id,
                d.name as domain_name,
                d.url as domain_url,
                d.logo as domain_logo
            FROM issues i
            LEFT JOIN domains d ON i.domain = d.id
            WHERE i.id = ?
        ''').bind(issue_id).first()
        
        if not result:
            return error_response("Issue not found", status=404)
        
        # Get screenshots for this issue
        screenshots_result = await db.prepare('''
            SELECT id, image, created
            FROM issue_screenshots
            WHERE issue = ?
            ORDER BY created DESC
        ''').bind(issue_id).all()
        
        # Get tags for this issue
        tags_result = await db.prepare('''
            SELECT t.id, t.name
            FROM issue_tags it
            JOIN tags t ON it.tag_id = t.id
            WHERE it.issue_id = ?
            ORDER BY t.name
        ''').bind(issue_id).all()
        
        # Convert results
        issue_data = convert_d1_results([result] if result else [])
        screenshots_data = convert_d1_results(screenshots_result.results if hasattr(screenshots_result, 'results') else [])
        tags_data = convert_d1_results(tags_result.results if hasattr(tags_result, 'results') else [])
        
        # Add screenshots and tags to issue data
        if issue_data:
            issue_data[0]['screenshots'] = screenshots_data
            issue_data[0]['tags'] = tags_data
    
        return json_response({
            "success": True,
            "data": issue_data[0] if issue_data else None
        })
    
    # Search issues
    if path.endswith("/search"):
        query = query_params.get("q", "")
        if not query:
            return error_response("Search query 'q' is required", status=400)
        
        limit = query_params.get("limit", "10")
        try:
            limit_int = min(max(int(limit), 1), 100)
        except ValueError:
            limit_int = 10
        
        result = await client.search_issues(query, limit=limit_int)
        
        if result.get("error"):
            return error_response(
                result.get("message", "Search failed"),
                status=result.get("status", 500)
            )
        
        return json_response({
            "success": True,
            "query": query,
            "data": result.get("data")
        })
    
    # Create issue
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
        
        result = await client.create_issue(body)
        
        if result.get("error"):
            return error_response(
                result.get("message", "Failed to create issue"),
                status=result.get("status", 400)
            )
        
        return json_response({
            "success": True,
            "message": "Issue created successfully",
            "data": result.get("data")
        }, status=201)
    
    # List issues with pagination
    page, per_page = parse_pagination_params(query_params)
    
    # Build WHERE conditions based on filters
    where_conditions = []
    params = []
    
    # Filter by status
    status = query_params.get("status")
    if status:
        where_conditions.append("i.status = ?")
        params.append(status)
    
    # Filter by domain
    domain = query_params.get("domain")
    if domain and domain.isdigit():
        where_conditions.append("i.domain = ?")
        params.append(int(domain))
    
    # Filter by verified
    verified = query_params.get("verified")
    if verified:
        where_conditions.append("i.verified = ?")
        params.append(1 if verified.lower() == "true" else 0)
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    try:
        # Get total count
        count_query = f'SELECT COUNT(*) as total FROM issues i{where_clause}'
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
                i.id,
                i.url,
                i.description,
                i.status,
                i.verified,
                i.score,
                i.views,
                i.created,
                i.modified,
                i.is_hidden,
                i.rewarded,
                i.cve_id,
                i.cve_score,
                i.domain,
                d.name as domain_name,
                d.url as domain_url
            FROM issues i
            LEFT JOIN domains d ON i.domain = d.id
            {where_clause}
            ORDER BY i.created DESC
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
        return error_response(f"Failed to fetch issues: {str(e)}", status=500)
