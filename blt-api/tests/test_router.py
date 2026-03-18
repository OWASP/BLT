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

    def test_parse_query_params_url_encoded(self):
        """Test that query parameters are URL-decoded."""
        router = Router()

        # Plus-encoded spaces
        params = router._parse_query_params("/bugs/search?q=sql+injection")
        assert params == {"q": "sql injection"}

        # Percent-encoded characters
        params = router._parse_query_params("/bugs/search?q=hello%20world&domain=example%2Ecom")
        assert params == {"q": "hello world", "domain": "example.com"}

        # Mixed encoding
        params = router._parse_query_params("/bugs/search?status=open&q=cross-site+scripting%20%28XSS%29")
        assert params == {"status": "open", "q": "cross-site scripting (XSS)"}

        # Blank values are preserved
        params = router._parse_query_params("/bugs?status=&page=1")
        assert params == {"status": "", "page": "1"}

        # Duplicate keys: first value wins (v[0] from parse_qs list)
        params = router._parse_query_params("/bugs?tag=xss&tag=sqli")
        assert params == {"tag": "xss"}


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


class TestRouteRegistrationOrder:
    """Tests for route registration order matching."""
    
    def test_routes_kept_in_registration_order(self):
        """Test that routes are kept in the order they are registered, not sorted."""
        router = Router()
        
        handlers = []
        for i in range(3):
            handlers.append(lambda i=i: None)
        
        # Add routes in this specific order
        router.add_route("GET", "/bugs/{id}", handlers[0])
        router.add_route("GET", "/bugs/search", handlers[1])
        router.add_route("GET", "/bugs", handlers[2])
        
        # Verify routes are kept in registration order (NO sorting)
        assert router.routes[0].pattern == "/bugs/{id}"
        assert router.routes[1].pattern == "/bugs/search"
        assert router.routes[2].pattern == "/bugs"
    
    def test_route_matching_respects_registration_order(self):
        """Test that routes are matched in registration order."""
        router = Router()
        
        # Add specific route first, then generic
        router.add_route("GET", "/bugs/search", lambda: "specific")
        router.add_route("GET", "/bugs/{id}", lambda: "generic")
        
        # When /bugs/search is requested, it should match the specific route first
        path = "/bugs/search"
        method = "GET"
        
        matched_pattern = None
        for route in router.routes:
            result = route.match(method, path)
            if result is not None:
                matched_pattern = route.pattern
                break
        
        # Should match the specific route because it was registered first
        assert matched_pattern is not None
        assert matched_pattern == "/bugs/search"
    
    def test_route_shadowing_with_wrong_order(self):
        """Test that routes CAN be shadowed if registered in wrong order."""
        router = Router()
        
        # Add generic route FIRST (wrong order)
        router.add_route("GET", "/bugs/{id}", lambda: "generic")
        # Then add specific route
        router.add_route("GET", "/bugs/search", lambda: "specific")
        
        # When /bugs/search is requested, it WILL match the generic route first
        # because that's how registration-order matching works
        path = "/bugs/search"
        method = "GET"
        
        matched_route = None
        for route in router.routes:
            result = route.match(method, path)
            if result is not None:
                matched_route = route
                break
        
        # The generic route matches first (shadowing the specific route)
        assert matched_route is not None
        assert matched_route.pattern == "/bugs/{id}"
        assert matched_route.match(method, path) == {"id": "search"}
    
    def test_correct_route_ordering_prevents_shadowing(self):
        """Test that correct registration order prevents shadowing."""
        router = Router()
        
        # Add specific route FIRST (correct order) 
        router.add_route("GET", "/bugs/search", lambda: "specific")
        # Then add generic route
        router.add_route("GET", "/bugs/{id}", lambda: "generic")
        
        path = "/bugs/search"
        method = "GET"
        
        matched_route = None
        for route in router.routes:
            result = route.match(method, path)
            if result is not None:
                matched_route = route
                break
        
        # The specific route matches first (correct behavior)
        assert matched_route is not None
        assert matched_route.pattern == "/bugs/search"
        assert matched_route.match(method, path) == {}


class TestRouterGetRouteList:
    """Tests for Router.get_route_list() method."""
    
    def test_get_route_list_empty(self):
        """Test get_route_list returns empty list for router with no routes."""
        router = Router()
        assert router.get_route_list() == []
    
    def test_get_route_list_single_route(self):
        """Test get_route_list with a single registered route."""
        router = Router()
        router.add_route("GET", "/users", lambda: None)
        
        result = router.get_route_list()
        assert len(result) == 1
        assert result[0] == {"method": "GET", "path": "/users"}
    
    def test_get_route_list_multiple_routes(self):
        """Test get_route_list with multiple routes."""
        router = Router()
        router.add_route("GET", "/users", lambda: None)
        router.add_route("POST", "/bugs", lambda: None)
        router.add_route("GET", "/domains/{id}", lambda: None)
        
        result = router.get_route_list()
        assert len(result) == 3
        assert result == [
            {"method": "GET", "path": "/users"},
            {"method": "POST", "path": "/bugs"},
            {"method": "GET", "path": "/domains/{id}"},
        ]
    
    def test_get_route_list_no_handler_exposed(self):
        """Test that handler names are not included in route list."""
        router = Router()
        
        def my_handler():
            pass
        
        router.add_route("GET", "/test", my_handler)
        
        result = router.get_route_list()
        assert len(result) == 1
        assert "handler" not in result[0]
        assert result[0].keys() == {"method", "path"}
    
    def test_get_route_list_preserves_method_case(self):
        """Test that HTTP methods are stored in uppercase."""
        router = Router()
        router.add_route("get", "/test", lambda: None)
        router.add_route("post", "/test", lambda: None)
        
        result = router.get_route_list()
        assert result[0]["method"] == "GET"
        assert result[1]["method"] == "POST"
    
    def test_get_route_list_includes_path_params(self):
        """Test that path parameters are preserved in route list."""
        router = Router()
        router.add_route("GET", "/users/{id}/posts/{post_id}", lambda: None)
        
        result = router.get_route_list()
        assert result[0]["path"] == "/users/{id}/posts/{post_id}"




