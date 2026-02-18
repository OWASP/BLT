"""
Router module for handling URL routing in the BLT API.

This module provides a simple but powerful routing system that supports
path parameters and different HTTP methods.
"""

import re
from typing import Callable, Dict, List, Optional, Tuple, Any
from utils import error_response, json_response


class Route:
    """Represents a single route with its pattern and handler."""
    
    def __init__(self, method: str, pattern: str, handler: Callable):
        self.method = method.upper()
        self.pattern = pattern
        self.handler = handler
        self.regex, self.param_names = self._compile_pattern(pattern)
        self.specificity = self._calculate_specificity()
    
    def _compile_pattern(self, pattern: str) -> Tuple[re.Pattern, List[str]]:
        """
        Compile the URL pattern into a regex.
        
        Supports path parameters like {id}, {slug}, etc.
        """
        param_names = []
        regex_pattern = pattern
        
        # Find all path parameters like {param_name}
        param_regex = re.compile(r'\{(\w+)\}')
        
        for match in param_regex.finditer(pattern):
            param_name = match.group(1)
            param_names.append(param_name)
            # Replace {param} with a regex group that captures word characters, numbers, and hyphens
            regex_pattern = regex_pattern.replace(
                match.group(0),
                f'(?P<{param_name}>[\\w\\-]+)'
            )
        
        # Anchor the pattern
        regex_pattern = '^' + regex_pattern + '$'
        
        return re.compile(regex_pattern), param_names
    
    def _calculate_specificity(self) -> Tuple[int, int, int]:
        """
        Calculate specificity score for route ordering.
        
        Returns:
            Tuple: (param_count, -literal_count, -segment_count)
            
            Lower tuples sort first. Routes are ordered by:
            - Fewer path parameters (0 params before 1 param)
            - More literal characters in path
            - Fewer path segments
        """
        param_count = self.pattern.count('{')
        segments = self.pattern.split('/')
        segment_count = len(segments)
        literal_count = sum(len(seg) for seg in segments if '{' not in seg)
        
        return (param_count, -literal_count, -segment_count)
    
    def match(self, method: str, path: str) -> Optional[Dict[str, str]]:
        """
        Check if the route matches the given method and path.
        
        Returns:
            Dict of path parameters if matched, None otherwise
        """
        if self.method != method.upper():
            return None
        
        match = self.regex.match(path)
        if match:
            return match.groupdict()
        return None


class Router:
    """
    URL Router for the BLT API.
    
    Manages route registration and request dispatching.
    """
    
    def __init__(self):
        """Initialize the router."""
        self.routes: List[Route] = []
    
    def add_route(self, method: str, pattern: str, handler: Callable) -> None:
        """
        Register a new route.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            pattern: URL pattern (e.g., "/users/{id}")
            handler: Async function to handle the request
        """
        route = Route(method, pattern, handler)
        self.routes.append(route)
        self._sort_routes()
    
    def _sort_routes(self) -> None:
        """
        Sort routes by specificity.
        
        Routes are ordered so more specific patterns are evaluated before
        parameterized patterns. This prevents routes like /bugs/search from
        being shadowed by routes like /bugs/{id}.
        """
        self.routes.sort(key=lambda route: route.specificity)
    
    def get(self, pattern: str) -> Callable:
        """Decorator for registering GET routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route("GET", pattern, handler)
            return handler
        return decorator
    
    def post(self, pattern: str) -> Callable:
        """Decorator for registering POST routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route("POST", pattern, handler)
            return handler
        return decorator
    
    def put(self, pattern: str) -> Callable:
        """Decorator for registering PUT routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route("PUT", pattern, handler)
            return handler
        return decorator
    
    def delete(self, pattern: str) -> Callable:
        """Decorator for registering DELETE routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route("DELETE", pattern, handler)
            return handler
        return decorator
    
    def _parse_url(self, url: str) -> str:
        """Extract the path from a full URL."""
        # Handle full URLs
        if url.startswith("http://") or url.startswith("https://"):
            # Find the path part after the domain
            parts = url.split("/", 3)
            if len(parts) >= 4:
                path = "/" + parts[3].split("?")[0]  # Remove query string
            else:
                path = "/"
        else:
            path = url.split("?")[0]  # Remove query string
        
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        
        # Remove trailing slash except for root
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        
        return path
    
    def _parse_query_params(self, url: str) -> Dict[str, str]:
        """Parse query parameters from URL."""
        params = {}
        if "?" in url:
            query_string = url.split("?", 1)[1]
            for pair in query_string.split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    params[key] = value
        return params
    
    async def handle(self, request: Any, env: Any) -> Any:
        """
        Handle an incoming request by routing it to the appropriate handler.
        
        Args:
            request: The incoming Request object
            env: Environment bindings
        
        Returns:
            Response from the matched handler or 404 error
        """
        url = str(request.url)
        method = str(request.method).upper()
        path = self._parse_url(url)
        query_params = self._parse_query_params(url)
        
        # Try to match against registered routes
        for route in self.routes:
            path_params = route.match(method, path)
            if path_params is not None:
                try:
                    return await route.handler(
                        request=request,
                        env=env,
                        path_params=path_params,
                        query_params=query_params,
                        path=path
                    )
                except Exception as e:
                    return error_response(
                        message=f"Handler error: {str(e)}",
                        status=500
                    )
        
        # No route matched
        return error_response(
            message=f"Not Found: {method} {path}",
            status=404
        )
