"""
Main entry point for the BLT API Cloudflare Worker.

This module provides a full-featured REST API that interfaces with
the OWASP BLT project, running efficiently on Cloudflare Workers.
"""

# Try to import Cloudflare Workers JS bindings
try:
    from js import Response, Headers, JSON
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    from .utils import Response, Headers

from .router import Router
from .handlers import (
    handle_issues,
    handle_users,
    handle_domains,
    handle_organizations,
    handle_projects,
    handle_hunts,
    handle_stats,
    handle_leaderboard,
    handle_contributors,
    handle_repos,
    handle_health,
)
from .utils import json_response, error_response, cors_headers


# Initialize the router
router = Router()

# Register routes

# Health check
router.add_route("GET", "/", handle_health)
router.add_route("GET", "/health", handle_health)

# Issues API
router.add_route("GET", "/issues", handle_issues)
router.add_route("GET", "/issues/{id}", handle_issues)
router.add_route("POST", "/issues", handle_issues)
router.add_route("GET", "/issues/search", handle_issues)

# Users API
router.add_route("GET", "/users", handle_users)
router.add_route("GET", "/users/{id}", handle_users)
router.add_route("GET", "/users/{id}/profile", handle_users)

# Domains API
router.add_route("GET", "/domains", handle_domains)
router.add_route("GET", "/domains/{id}", handle_domains)
router.add_route("GET", "/domains/{id}/issues", handle_domains)

# Organizations API
router.add_route("GET", "/organizations", handle_organizations)
router.add_route("GET", "/organizations/{id}", handle_organizations)
router.add_route("GET", "/organizations/{id}/repos", handle_organizations)
router.add_route("GET", "/organizations/{id}/projects", handle_organizations)

# Projects API
router.add_route("GET", "/projects", handle_projects)
router.add_route("GET", "/projects/{id}", handle_projects)
router.add_route("GET", "/projects/{id}/contributors", handle_projects)

# Bug Hunts API
router.add_route("GET", "/hunts", handle_hunts)
router.add_route("GET", "/hunts/{id}", handle_hunts)
router.add_route("GET", "/hunts/active", handle_hunts)
router.add_route("GET", "/hunts/previous", handle_hunts)
router.add_route("GET", "/hunts/upcoming", handle_hunts)

# Stats API
router.add_route("GET", "/stats", handle_stats)

# Leaderboard API
router.add_route("GET", "/leaderboard", handle_leaderboard)
router.add_route("GET", "/leaderboard/monthly", handle_leaderboard)
router.add_route("GET", "/leaderboard/organizations", handle_leaderboard)

# Contributors API
router.add_route("GET", "/contributors", handle_contributors)
router.add_route("GET", "/contributors/{id}", handle_contributors)

# Repositories API
router.add_route("GET", "/repos", handle_repos)
router.add_route("GET", "/repos/{id}", handle_repos)


async def on_fetch(request, env):
    """
    Main entry point for Cloudflare Workers.
    
    This function handles all incoming HTTP requests and routes them
    to the appropriate handler based on the URL path and method.
    
    Args:
        request: The incoming Request object
        env: Environment bindings (variables, secrets, KV namespaces, etc.)
    
    Returns:
        Response: The HTTP response to return to the client
    """
    try:
        # Handle CORS preflight requests
        if request.method == "OPTIONS":
            return Response.new(
                None,
                status=204,
                headers=Headers.new(cors_headers())
            )
        
        # Get URL and method
        url = request.url
        method = request.method
        
        # Route the request
        response = await router.handle(request, env)
        
        return response
        
    except Exception as e:
        return error_response(
            message=f"Internal Server Error: {str(e)}",
            status=500
        )
