"""
Domains handler for the BLT API.
"""

from typing import Any, Dict
from utils import error_response, parse_pagination_params, convert_d1_results
from libs.db import get_db_safe
from workers import Response
from models import Domain


async def handle_domains(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle all domain-related API requests using D1 database.

    This handler manages domain data stored in Cloudflare D1 (SQLite),
    providing listing, detail views, and tag associations.

    Endpoints:
        GET /domains - List all domains with pagination (ordered by creation date)
        GET /domains/{id} - Get detailed information for a specific domain
        GET /domains/{id}/tags - Get all tags associated with a domain (paginated)

    Query parameters for listing:
        - page: Page number for pagination (default: 1)
        - per_page: Items per page (default: 20, max: 100)

    Returns:
        JSON response with domain data and pagination metadata,
        or error response (400 for invalid ID, 404 for not found, 500 for DB errors)
    """
    try:
        db = await get_db_safe(env)
    except Exception as e:
        return error_response(str(e), status=503)

    # Get specific domain
    if "id" in path_params:
        domain_id = path_params["id"]

        # Validate ID is numeric
        if not domain_id.isdigit():
            return error_response("Invalid domain ID", status=400)

        # GET /domains/{id}/tags
        if path.endswith("/tags"):
            try:
                page, per_page = parse_pagination_params(query_params)

                # JOIN query – kept as raw parameterized SQL because the ORM
                # does not yet support cross-table JOINs.
                result = await db.prepare('''
                    SELECT t.id, t.name, t.created
                    FROM tags t
                    INNER JOIN domain_tags dt ON t.id = dt.tag_id
                    WHERE dt.domain_id = ?
                    ORDER BY t.name
                    LIMIT ? OFFSET ?
                ''').bind(int(domain_id), per_page, (page - 1) * per_page).all()

                data = convert_d1_results(
                    result.results if hasattr(result, 'results') else []
                )

                return Response.json({
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
                return error_response(
                    f"Failed to fetch domain tags: {str(e)}", status=500
                )

        # GET /domains/{id}
        try:
            domain = await Domain.objects(db).get(id=int(domain_id))
            if not domain:
                return error_response("Domain not found", status=404)

            return Response.json({"success": True, "data": domain})
        except Exception as e:
            return error_response(f"Failed to fetch domain: {str(e)}", status=500)

    # GET /domains  –  list with pagination
    try:
        page, per_page = parse_pagination_params(query_params)

        total = await Domain.objects(db).count()
        data = (
            await Domain.objects(db)
            .order_by("-created")
            .paginate(page, per_page)
            .all()
        )

        return Response.json({
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
