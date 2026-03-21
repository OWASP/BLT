"""
Organizations handler for the BLT API.
"""

from typing import Any, Dict, List
from utils import convert_d1_results, error_response, paginated_response, parse_pagination_params, success_response
from workers import Response
from libs.db import get_db_safe
from libs.data_protection import decrypt_sensitive

async def handle_organizations(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle organization-related requests.
    
    Endpoints:
        GET /organizations - List organizations with pagination and search
        GET /organizations/{id} - Get a specific organization with details
        GET /organizations/{id}/domains - Get organization domains
        GET /organizations/{id}/bugs - Get bugs from organization domains
        GET /organizations/{id}/managers - Get organization managers
        GET /organizations/{id}/tags - Get organization tags
        GET /organizations/{id}/integrations - Get organization integrations
        GET /organizations/{id}/stats - Get organization statistics
    """
    try:
        db = await get_db_safe(env)
    except Exception as e:
        return error_response(str(e), status=503)
    
    # Get specific organization
    if "id" in path_params:
        org_id = path_params["id"]
        
        # Validate ID is numeric
        if not org_id.isdigit():
            return error_response("Invalid organization ID", status=400)
        
        org_id_int = int(org_id)
        
        # Get organization domains
        if path.endswith("/domains"):
            page, per_page = parse_pagination_params(query_params)
            
            # Get domains for this organization
            result = await db.prepare('''
                SELECT d.id, d.name, d.url, d.logo, d.clicks, d.email, 
                       d.twitter, d.facebook, d.github, d.created, d.is_active
                FROM domains d
                WHERE d.organization = ?
                ORDER BY d.created DESC
                LIMIT ? OFFSET ?
            ''').bind(org_id_int, per_page, (page - 1) * per_page).all()
            
            domains = convert_d1_results(result.results if hasattr(result, 'results') else [])
            
            # Get total count
            count_result = await db.prepare('''
                SELECT COUNT(*) as total FROM domains WHERE organization = ?
            ''').bind(org_id_int).first()
            
            count_data = count_result.to_py() if hasattr(count_result, 'to_py') else dict(count_result) if count_result else {}
            total = count_data.get("total", 0)
            
            return paginated_response(domains, page=page, per_page=per_page, total=total)
        
        # Get bugs from organization's domains
        if path.endswith("/bugs"):
            page, per_page = parse_pagination_params(query_params)
            
            result = await db.prepare('''
                SELECT b.id, b.url, b.description, b.verified, b.score, 
                       b.status, b.created, b.domain, d.name as domain_name
                FROM bugs b
                JOIN domains d ON b.domain = d.id
                WHERE d.organization = ?
                ORDER BY b.created DESC
                LIMIT ? OFFSET ?
            ''').bind(org_id_int, per_page, (page - 1) * per_page).all()
            
            bugs = convert_d1_results(result.results if hasattr(result, 'results') else [])
            
            # Get total count
            count_result = await db.prepare('''
                SELECT COUNT(*) as total 
                FROM bugs b
                JOIN domains d ON b.domain = d.id
                WHERE d.organization = ?
            ''').bind(org_id_int).first()
            
            count_data = count_result.to_py() if hasattr(count_result, 'to_py') else dict(count_result) if count_result else {}
            total = count_data.get("total", 0)
            
            return paginated_response(bugs, page=page, per_page=per_page, total=total)
        
        # Get organization managers
        if path.endswith("/managers"):
            result = await db.prepare('''
                SELECT u.id, u.username_encrypted, u.total_score,
                       u.email_encrypted, u.user_avatar_encrypted,
                       om.created as joined_as_manager
                FROM organization_managers om
                JOIN users u ON om.user_id = u.id
                WHERE om.organization_id = ?
                ORDER BY om.created DESC
            ''').bind(org_id_int).all()
            
            managers = convert_d1_results(result.results if hasattr(result, 'results') else [])

            for manager in managers:
                if manager.get("username_encrypted"):
                    manager["username"] = decrypt_sensitive(manager.pop("username_encrypted"), env)
                else:
                    manager.pop("username_encrypted", None)
                if manager.get("email_encrypted"):
                    manager["email"] = decrypt_sensitive(manager.get("email_encrypted"), env)
                if manager.get("user_avatar_encrypted"):
                    manager["user_avatar"] = decrypt_sensitive(manager.get("user_avatar_encrypted"), env)
                manager.pop("email_encrypted", None)
                manager.pop("user_avatar_encrypted", None)
            
            return Response.json({
                "success": True,
                "data": managers,
                "count": len(managers)
            })
        
        # Get organization tags
        if path.endswith("/tags"):
            result = await db.prepare('''
                SELECT t.id, t.name, ot.created
                FROM organization_tags ot
                JOIN tags t ON ot.tag_id = t.id
                WHERE ot.organization_id = ?
                ORDER BY t.name ASC
            ''').bind(org_id_int).all()
            
            tags = convert_d1_results(result.results if hasattr(result, 'results') else [])
            
            return Response.json({
                "success": True,
                "data": tags,
                "count": len(tags)
            })
        
        # Get organization integrations
        if path.endswith("/integrations"):
            result = await db.prepare('''
                SELECT id, integration_type, integration_name, 
                       webhook_url, is_active, created, modified
                FROM organization_integrations
                WHERE organization_id = ?
                ORDER BY integration_type ASC
            ''').bind(org_id_int).all()
            
            integrations = convert_d1_results(result.results if hasattr(result, 'results') else [])
            
            return Response.json({
                "success": True,
                "data": integrations,
                "count": len(integrations)
            })
        
        # Get organization statistics
        if path.endswith("/stats"):
            # Get domain count
            domain_count_result = await db.prepare('''
                SELECT COUNT(*) as count FROM domains WHERE organization = ?
            ''').bind(org_id_int).first()
            domain_count_data = domain_count_result.to_py() if hasattr(domain_count_result, 'to_py') else dict(domain_count_result) if domain_count_result else {}
            
            # Get bug count
            bug_count_result = await db.prepare('''
                SELECT COUNT(*) as count 
                FROM bugs b
                JOIN domains d ON b.domain = d.id
                WHERE d.organization = ?
            ''').bind(org_id_int).first()
            bug_count_data = bug_count_result.to_py() if hasattr(bug_count_result, 'to_py') else dict(bug_count_result) if bug_count_result else {}
            
            # Get verified bug count
            verified_bug_result = await db.prepare('''
                SELECT COUNT(*) as count 
                FROM bugs b
                JOIN domains d ON b.domain = d.id
                WHERE d.organization = ? AND b.verified = 1
            ''').bind(org_id_int).first()
            verified_bug_data = verified_bug_result.to_py() if hasattr(verified_bug_result, 'to_py') else dict(verified_bug_result) if verified_bug_result else {}
            
            # Get manager count
            manager_count_result = await db.prepare('''
                SELECT COUNT(*) as count FROM organization_managers WHERE organization_id = ?
            ''').bind(org_id_int).first()
            manager_count_data = manager_count_result.to_py() if hasattr(manager_count_result, 'to_py') else dict(manager_count_result) if manager_count_result else {}
            
            stats = {
                "domain_count": domain_count_data.get("count", 0),
                "bug_count": bug_count_data.get("count", 0),
                "verified_bug_count": verified_bug_data.get("count", 0),
                "manager_count": manager_count_data.get("count", 0)
            }
            
            return Response.json({
                "success": True,
                "data": stats
            })
        
        # Get organization details with related data
        org_result = await db.prepare('''
            SELECT o.*, u.username_encrypted as admin_username_encrypted, u.email_encrypted as admin_email_encrypted
            FROM organization o
            LEFT JOIN users u ON o.admin = u.id
            WHERE o.id = ?
        ''').bind(org_id_int).first()
        
        if not org_result:
            return error_response("Organization not found", status=404)
        
        org = org_result.to_py() if hasattr(org_result, 'to_py') else dict(org_result)
        if org.get("admin_username_encrypted"):
            org["admin_username"] = decrypt_sensitive(org.pop("admin_username_encrypted"), env)
        else:
            org.pop("admin_username_encrypted", None)
        if org.get("admin_email_encrypted"):
            org["admin_email"] = decrypt_sensitive(org.get("admin_email_encrypted"), env)
        org.pop("admin_email_encrypted", None)
        
        # Optionally include related data if requested
        include_related = query_params.get("include", "").split(",")
        
        if "managers" in include_related:
            managers_result = await db.prepare('''
                SELECT u.id, u.username_encrypted, u.user_avatar_encrypted
                FROM organization_managers om
                JOIN users u ON om.user_id = u.id
                WHERE om.organization_id = ?
            ''').bind(org_id_int).all()
            managers = convert_d1_results(managers_result.results if hasattr(managers_result, 'results') else [])
            for manager in managers:
                if manager.get("username_encrypted"):
                    manager["username"] = decrypt_sensitive(manager.pop("username_encrypted"), env)
                else:
                    manager.pop("username_encrypted", None)
                if manager.get("user_avatar_encrypted"):
                    manager["user_avatar"] = decrypt_sensitive(manager.get("user_avatar_encrypted"), env)
                manager.pop("user_avatar_encrypted", None)
            org["managers"] = managers
        
        if "tags" in include_related:
            tags_result = await db.prepare('''
                SELECT t.id, t.name
                FROM organization_tags ot
                JOIN tags t ON ot.tag_id = t.id
                WHERE ot.organization_id = ?
            ''').bind(org_id_int).all()
            org["tags"] = convert_d1_results(tags_result.results if hasattr(tags_result, 'results') else [])
        
        if "stats" in include_related:
            domain_count_result = await db.prepare('''
                SELECT COUNT(*) as count FROM domains WHERE organization = ?
            ''').bind(org_id_int).first()
            domain_count_data = domain_count_result.to_py() if hasattr(domain_count_result, 'to_py') else dict(domain_count_result) if domain_count_result else {}
            org["domain_count"] = domain_count_data.get("count", 0)
        
        return Response.json({
            "success": True,
            "data": org
        })
    
    # List organizations with pagination and search
    page, per_page = parse_pagination_params(query_params)
    search = query_params.get("search", query_params.get("q", "")).strip()
    org_type = query_params.get("type", "").strip()
    is_active = query_params.get("is_active", "").strip()
    
    # Build WHERE clause dynamically
    where_clauses = []
    bind_params = []
    
    if search:
        where_clauses.append("(o.name LIKE ? OR o.slug LIKE ? OR o.description LIKE ?)")
        search_pattern = f"%{search}%"
        bind_params.extend([search_pattern, search_pattern, search_pattern])
    
    if org_type and org_type in ["company", "nonprofit", "education"]:
        where_clauses.append("o.type = ?")
        bind_params.append(org_type)
    
    if is_active:
        where_clauses.append("o.is_active = ?")
        bind_params.append(1 if is_active.lower() in ["true", "1", "yes"] else 0)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Get organizations
    query = f'''
        SELECT o.id, o.name, o.slug, o.description, o.logo, o.url, 
               o.type, o.is_active, o.team_points, o.created, o.tagline,
               u.username_encrypted as admin_username_encrypted
        FROM organization o
        LEFT JOIN users u ON o.admin = u.id
        WHERE {where_sql}
        ORDER BY o.created DESC
        LIMIT ? OFFSET ?
    '''
    
    bind_params.extend([per_page, (page - 1) * per_page])
    
    result = await db.prepare(query).bind(*bind_params).all()
    organizations = convert_d1_results(result.results if hasattr(result, 'results') else [])

    for org in organizations:
        if org.get("admin_username_encrypted"):
            org["admin_username"] = decrypt_sensitive(org.pop("admin_username_encrypted"), env)
        else:
            org.pop("admin_username_encrypted", None)

    # Get total count
    count_query = f'''
        SELECT COUNT(*) as total FROM organization o WHERE {where_sql}
    '''
    count_result = await db.prepare(count_query).bind(*bind_params[:-2]).first()
    count_data = count_result.to_py() if hasattr(count_result, 'to_py') else dict(count_result) if count_result else {}
    total = count_data.get("total", 0)
    
    return paginated_response(organizations, page=page, per_page=per_page, total=total)
