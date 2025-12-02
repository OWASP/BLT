"""
Health check handler.
"""

from typing import Any, Dict
from ..utils import json_response


async def handle_health(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle health check requests.
    
    Returns API status and version information.
    """
    return json_response({
        "status": "healthy",
        "api": "BLT API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "issues": "/issues",
            "users": "/users",
            "domains": "/domains",
            "organizations": "/organizations",
            "projects": "/projects",
            "hunts": "/hunts",
            "stats": "/stats",
            "leaderboard": "/leaderboard",
            "contributors": "/contributors",
            "repos": "/repos"
        },
        "links": {
            "github": "https://github.com/OWASP-BLT/BLT",
            "website": "https://blt.owasp.org",
            "documentation": "https://github.com/OWASP-BLT/BLT-API"
        }
    })
