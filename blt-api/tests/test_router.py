"""
Tests for the Router module.
"""

import pytest
from src.router import Route, Router


class TestRoute:
    """Tests for the Route class."""
    
    def test_route_init(self):
        """Test route initialization."""
        def handler():
            pass
        
        route = Route("GET", "/users", handler)
        assert route.method == "GET"
        assert route.pattern == "/users"
        assert route.handler == handler
    
    def test_route_method_uppercase(self):
        """Test that method is converted to uppercase."""
        route = Route("get", "/test", lambda: None)
        assert route.method == "GET"
    
    def test_route_match_simple(self):
        """Test simple route matching."""
        route = Route("GET", "/users", lambda: None)
        
        assert route.match("GET", "/users") == {}
        assert route.match("POST", "/users") is None
        assert route.match("GET", "/other") is None
    
    def test_route_match_with_params(self):
        """Test route matching with path parameters."""
        route = Route("GET", "/users/{id}", lambda: None)
        
        result = route.match("GET", "/users/123")
        assert result is not None
        assert result["id"] == "123"
        
        result = route.match("GET", "/users/abc")
        assert result is not None
        assert result["id"] == "abc"
        
        assert route.match("GET", "/users") is None
        assert route.match("GET", "/users/123/extra") is None
    
    def test_route_match_multiple_params(self):
        """Test route matching with multiple path parameters."""
        route = Route("GET", "/users/{user_id}/posts/{post_id}", lambda: None)
        
        result = route.match("GET", "/users/123/posts/456")
        assert result is not None
        assert result["user_id"] == "123"
        assert result["post_id"] == "456"


class TestRouter:
    """Tests for the Router class."""
    
    def test_router_init(self):
        """Test router initialization."""
        router = Router()
        assert router.routes == []
    
    def test_add_route(self):
        """Test adding routes."""
        router = Router()
        
        def handler():
            pass
        
        router.add_route("GET", "/test", handler)
        assert len(router.routes) == 1
        assert router.routes[0].method == "GET"
        assert router.routes[0].pattern == "/test"
    
    def test_parse_url_simple(self):
        """Test URL parsing."""
        router = Router()
        
        assert router._parse_url("/users") == "/users"
        assert router._parse_url("/users/") == "/users"
        assert router._parse_url("/") == "/"
    
    def test_parse_url_with_query(self):
        """Test URL parsing with query string."""
        router = Router()
        
        assert router._parse_url("/users?page=1") == "/users"
        assert router._parse_url("/users?page=1&limit=10") == "/users"
    
    def test_parse_url_full_url(self):
        """Test URL parsing with full URL."""
        router = Router()
        
        result = router._parse_url("https://example.com/users")
        assert result == "/users"
        
        result = router._parse_url("https://example.com/users?page=1")
        assert result == "/users"
    
    def test_parse_query_params(self):
        """Test query parameter parsing."""
        router = Router()
        
        params = router._parse_query_params("/users?page=1&limit=10")
        assert params == {"page": "1", "limit": "10"}
        
        params = router._parse_query_params("/users")
        assert params == {}


class TestRouterDecorators:
    """Tests for router decorator methods."""
    
    def test_get_decorator(self):
        """Test GET decorator."""
        router = Router()
        
        @router.get("/test")
        def handler():
            pass
        
        assert len(router.routes) == 1
        assert router.routes[0].method == "GET"
    
    def test_post_decorator(self):
        """Test POST decorator."""
        router = Router()
        
        @router.post("/test")
        def handler():
            pass
        
        assert len(router.routes) == 1
        assert router.routes[0].method == "POST"
    
    def test_put_decorator(self):
        """Test PUT decorator."""
        router = Router()
        
        @router.put("/test")
        def handler():
            pass
        
        assert len(router.routes) == 1
        assert router.routes[0].method == "PUT"
    
    def test_delete_decorator(self):
        """Test DELETE decorator."""
        router = Router()
        
        @router.delete("/test")
        def handler():
            pass
        
        assert len(router.routes) == 1
        assert router.routes[0].method == "DELETE"


class TestRouteSpecificity:
    """Tests for route specificity and sorting."""
    
    def test_route_specificity_calculation(self):
        """Test that route specificity is calculated correctly."""
        # Route with 0 parameters is more specific
        route1 = Route("GET", "/bugs/search", lambda: None)
        # Route with 1 parameter is less specific
        route2 = Route("GET", "/bugs/{id}", lambda: None)
        
        # route1 should be more specific (smaller tuple)
        assert route1.specificity[0] == 0  # 0 params
        assert route2.specificity[0] == 1  # 1 param
        assert route1.specificity < route2.specificity
    
    def test_routes_sorted_by_specificity(self):
        """Test that routes are sorted by specificity when added."""
        router = Router()
        
        handlers = []
        for i in range(3):
            handlers.append(lambda i=i: None)
        
        # Add routes in wrong order: generic before specific
        router.add_route("GET", "/bugs/{id}", handlers[0])
        router.add_route("GET", "/bugs/search", handlers[1])
        router.add_route("GET", "/bugs", handlers[2])
        
        # Verify the key constraint: parameterized route comes after all literals
        idx_literal_search = None
        idx_literal_bugs = None
        idx_param_id = None
        
        for i, route in enumerate(router.routes):
            if route.pattern == "/bugs/search":
                idx_literal_search = i
            elif route.pattern == "/bugs":
                idx_literal_bugs = i
            elif route.pattern == "/bugs/{id}":
                idx_param_id = i
        
        # The key fix: parameterized route must come AFTER all literal routes
        assert idx_param_id > idx_literal_search, "/bugs/{id} must come after /bugs/search"
        assert idx_param_id > idx_literal_bugs, "/bugs/{id} must come after /bugs"

    
    def test_route_shadowing_fixed(self):
        """Test that specific routes are no longer shadowed by generic routes."""
        from src.router import Route
        
        # Create routes in problematic order
        route_generic = Route("GET", "/bugs/{id}", lambda: "generic")
        route_specific = Route("GET", "/bugs/search", lambda: "specific")
        
        routes = [route_generic, route_specific]
        # Sort by specificity
        routes.sort(key=lambda r: r.specificity)
        
        # After sorting, specific route should come first
        assert routes[0].pattern == "/bugs/search"
        assert routes[1].pattern == "/bugs/{id}"
        
        # Now the specific route will be matched first
        path = "/bugs/search"
        for route in routes:
            result = route.match("GET", path)
            if result is not None:
                matched_pattern = route.pattern
                break
        
        # Should match the specific route, not the generic one
        assert matched_pattern == "/bugs/search"
    
    def test_complex_route_sorting(self):
        """Test sorting with multiple parameters and different path lengths."""
        router = Router()
        
        # Add routes in mixed order
        router.add_route("GET", "/users/{user_id}/posts/{post_id}", lambda: None)
        router.add_route("GET", "/users/{id}", lambda: None)
        router.add_route("GET", "/users/me", lambda: None)
        router.add_route("GET", "/users", lambda: None)
        
        # Find indices
        idx_literal_users = None
        idx_literal_me = None
        idx_param_id = None
        idx_param_posts = None
        
        for i, route in enumerate(router.routes):
            if route.pattern == "/users":
                idx_literal_users = i
            elif route.pattern == "/users/me":
                idx_literal_me = i
            elif route.pattern == "/users/{id}":
                idx_param_id = i
            elif route.pattern == "/users/{user_id}/posts/{post_id}":
                idx_param_posts = i
        
        # Key assertions: all literal routes before parameterized
        assert idx_literal_users < idx_param_id and idx_literal_users < idx_param_posts
        assert idx_literal_me < idx_param_id and idx_literal_me < idx_param_posts
        assert idx_param_id < idx_param_posts




