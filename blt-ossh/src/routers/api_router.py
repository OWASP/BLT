"""
API Router
Handles API endpoint routing and request processing
"""

import json
from cloudflare.workers import Response
from typing import Any, Optional
from services.github_service import GitHubService


class APIRouter:
    """Router for API endpoints"""
    
    def __init__(self, env: Optional[Any] = None):
        """
        Initialize API router
        
        Args:
            env: Environment variables from Workers
        """
        self.env = env
        self.github_service = GitHubService(env)
    
    async def handle_github_analysis(self, request: Any) -> Response:
        """
        Handle GitHub profile analysis endpoint
        
        Args:
            request: The incoming request object
            
        Returns:
            Response object with analysis results
        """
        try:
            # Parse request body
            body = await request.json()
            username = body.get('username', '').strip()
            
            # Validate username
            is_valid, error_message = self.github_service.validate_username(username)
            if not is_valid:
                return Response.json(
                    {"error": error_message},
                    status=400
                )
            
            # Analyze profile
            result = await self.github_service.analyze_profile(username)
            
            if result.get('status') == 'error':
                return Response.json(
                    {"error": result.get('error', 'Unknown error occurred')},
                    status=500
                )
            
            return Response.json(result, status=200)
            
        except json.JSONDecodeError:
            return Response.json(
                {"error": "Invalid JSON in request body"},
                status=400
            )
        except Exception as e:
            return Response.json(
                {"error": f"Internal server error: {str(e)}"},
                status=500
            )
    
    async def handle_health_check(self, request: Any) -> Response:
        """
        Handle health check endpoint
        
        Args:
            request: The incoming request object
            
        Returns:
            Response with health status
        """
        return Response.json({
            "status": "healthy",
            "service": "BLT-OSSH",
            "version": "0.1.0"
        }, status=200)
    
    def handle_method_not_allowed(self, allowed_methods: list[str]) -> Response:
        """
        Return a method not allowed response
        
        Args:
            allowed_methods: List of allowed HTTP methods
            
        Returns:
            Response with 405 status
        """
        return Response.json(
            {
                "error": "Method not allowed",
                "allowed_methods": allowed_methods
            },
            status=405,
            headers={"Allow": ", ".join(allowed_methods)}
        )
