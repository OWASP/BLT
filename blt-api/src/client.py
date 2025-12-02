"""
HTTP Client for making requests to the BLT backend.

This module provides an async HTTP client that interfaces with
the main OWASP BLT API backend.
"""

from typing import Any, Dict, List, Optional
import json

# Try to import Cloudflare Workers JS bindings
try:
    from js import fetch, Headers, Object
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    # Mock fetch for testing outside Workers runtime
    async def fetch(url, **kwargs):
        raise NotImplementedError("fetch is only available in Workers runtime")


class BLTClient:
    """
    HTTP Client for the BLT Backend API.
    
    This client handles all communication with the main OWASP BLT
    Django backend API.
    """
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        """
        Initialize the BLT client.
        
        Args:
            base_url: Base URL of the BLT API
            auth_token: Optional authentication token
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
    
    def _get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get default headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BLT-API-Worker/1.0"
        }
        
        if self.auth_token:
            headers["Authorization"] = f"Token {self.auth_token}"
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the BLT backend.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Request body data
            headers: Extra headers
        
        Returns:
            Dict containing response data or error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add query parameters
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query_string:
                url = f"{url}?{query_string}"
        
        request_headers = self._get_headers(headers)
        
        try:
            # Build fetch options
            options = {
                "method": method,
                "headers": request_headers
            }
            
            if data and method in ["POST", "PUT", "PATCH"]:
                options["body"] = json.dumps(data)
            
            # Make the request using JavaScript fetch
            response = await fetch(url, **options)
            
            # Parse response
            status = response.status
            
            try:
                response_text = await response.text()
                if response_text:
                    response_data = json.loads(response_text)
                else:
                    response_data = {}
            except json.JSONDecodeError:
                response_data = {"raw_response": response_text}
            
            if status >= 400:
                return {
                    "error": True,
                    "status": status,
                    "message": response_data.get("detail", response_data.get("error", "Request failed")),
                    "data": response_data
                }
            
            return {
                "success": True,
                "status": status,
                "data": response_data
            }
            
        except Exception as e:
            return {
                "error": True,
                "status": 500,
                "message": f"Request failed: {str(e)}"
            }
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params, headers=headers)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make a POST request."""
        return await self._request("POST", endpoint, params=params, data=data, headers=headers)
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, params=params, data=data, headers=headers)
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint, params=params, headers=headers)
    
    # ==================== Issues API ====================
    
    async def get_issues(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a list of issues.
        
        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status (open, closed)
            domain: Filter by domain URL
            search: Search query
        
        Returns:
            Dict containing issues data
        """
        params = {
            "page": str(page),
            "per_page": str(per_page)
        }
        if status:
            params["status"] = status
        if domain:
            params["domain"] = domain
        if search:
            params["search"] = search
        
        return await self.get("issues/", params=params)
    
    async def get_issue(self, issue_id: int) -> Dict[str, Any]:
        """Get a specific issue by ID."""
        return await self.get(f"issues/{issue_id}/")
    
    async def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue."""
        return await self.post("issues/", data=issue_data)
    
    async def search_issues(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for issues."""
        return await self.get("search/", params={"q": query, "limit": str(limit)})
    
    # ==================== Users API ====================
    
    async def get_users(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get a list of users."""
        return await self.get("profile/", params={"page": str(page), "per_page": str(per_page)})
    
    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get a specific user profile."""
        return await self.get(f"profile/{user_id}/")
    
    # ==================== Domains API ====================
    
    async def get_domains(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get a list of domains."""
        return await self.get("domain/", params={"page": str(page), "per_page": str(per_page)})
    
    async def get_domain(self, domain_id: int) -> Dict[str, Any]:
        """Get a specific domain."""
        return await self.get(f"domain/{domain_id}/")
    
    # ==================== Organizations API ====================
    
    async def get_organizations(self, page: int = 1, per_page: int = 20, search: Optional[str] = None) -> Dict[str, Any]:
        """Get a list of organizations."""
        params = {"page": str(page), "per_page": str(per_page)}
        if search:
            params["search"] = search
        return await self.get("organizations/", params=params)
    
    async def get_organization(self, org_id: int) -> Dict[str, Any]:
        """Get a specific organization."""
        return await self.get(f"organizations/{org_id}/")
    
    async def get_organization_repos(self, org_id: int) -> Dict[str, Any]:
        """Get repositories for an organization."""
        return await self.get(f"organizations/{org_id}/repositories/")
    
    # ==================== Projects API ====================
    
    async def get_projects(self, page: int = 1, per_page: int = 20, search: Optional[str] = None) -> Dict[str, Any]:
        """Get a list of projects."""
        params = {"page": str(page), "per_page": str(per_page)}
        if search:
            params["q"] = search
        return await self.get("projects/", params=params)
    
    async def get_project(self, project_id: int) -> Dict[str, Any]:
        """Get a specific project."""
        return await self.get(f"projects/{project_id}/")
    
    # ==================== Bug Hunts API ====================
    
    async def get_hunts(
        self,
        page: int = 1,
        per_page: int = 20,
        active: bool = False,
        previous: bool = False,
        upcoming: bool = False
    ) -> Dict[str, Any]:
        """Get a list of bug hunts."""
        params = {"page": str(page), "per_page": str(per_page)}
        if active:
            params["activeHunt"] = "true"
        elif previous:
            params["previousHunt"] = "true"
        elif upcoming:
            params["upcomingHunt"] = "true"
        return await self.get("hunt/", params=params)
    
    async def get_hunt(self, hunt_id: int) -> Dict[str, Any]:
        """Get a specific bug hunt."""
        return await self.get(f"hunt/{hunt_id}/")
    
    # ==================== Stats API ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get overall platform statistics."""
        return await self.get("stats/")
    
    # ==================== Leaderboard API ====================
    
    async def get_leaderboard(
        self,
        page: int = 1,
        per_page: int = 20,
        month: Optional[int] = None,
        year: Optional[int] = None,
        leaderboard_type: str = "global"
    ) -> Dict[str, Any]:
        """Get the leaderboard."""
        params = {"page": str(page), "per_page": str(per_page)}
        if month:
            params["filter"] = "true"
            params["month"] = str(month)
        if year:
            params["filter"] = "true"
            params["year"] = str(year)
        if leaderboard_type == "organizations":
            params["leaderboard_type"] = "organizations"
        return await self.get("leaderboard/", params=params)
    
    # ==================== Contributors API ====================
    
    async def get_contributors(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get a list of contributors."""
        return await self.get("contributors/", params={"page": str(page), "per_page": str(per_page)})


def create_client(env: Any, auth_token: Optional[str] = None) -> BLTClient:
    """
    Create a BLT client from environment settings.
    
    Args:
        env: Environment bindings
        auth_token: Optional authentication token
    
    Returns:
        Configured BLTClient instance
    """
    try:
        base_url = str(env.BLT_API_BASE_URL)
    except AttributeError:
        base_url = "https://blt.owasp.org/api/v1"
    
    return BLTClient(base_url, auth_token)
