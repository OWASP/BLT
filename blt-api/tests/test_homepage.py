"""
Tests for the homepage handler.
"""

import pytest
import sys
import os

# Add src to path for imports to work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from handlers.homepage import handle_homepage


class MockRequest:
    """Mock request object for testing."""
    
    def __init__(self, url="https://blt-api.workers.dev/"):
        self.url = url
        self.method = "GET"


class MockEnv:
    """Mock environment object for testing."""
    pass


class TestHomepageHandler:
    """Tests for the homepage handler."""
    
    @pytest.mark.asyncio
    async def test_homepage_returns_html(self):
        """Test that homepage handler returns HTML content."""
        request = MockRequest()
        env = MockEnv()
        
        response = await handle_homepage(
            request,
            env,
            path_params={},
            query_params={},
            path="/"
        )
        
        # Check that response has HTML content
        assert response is not None
        # In test environment, response.body should contain HTML
        if hasattr(response, 'body'):
            assert "<!DOCTYPE html>" in response.body
            assert "BLT API" in response.body
    
    @pytest.mark.asyncio
    async def test_homepage_contains_api_info(self):
        """Test that homepage contains API endpoint information."""
        request = MockRequest()
        env = MockEnv()
        
        response = await handle_homepage(
            request,
            env,
            path_params={},
            query_params={},
            path="/"
        )
        
        # Check for key API information
        if hasattr(response, 'body'):
            content = response.body
            assert "/bugs" in content
            assert "/users" in content
            assert "/domains" in content
            assert "/organizations" in content
            assert "/projects" in content
            assert "/hunts" in content
            assert "/stats" in content
            assert "/leaderboard" in content
    
    @pytest.mark.asyncio
    async def test_homepage_contains_documentation(self):
        """Test that homepage contains documentation sections."""
        request = MockRequest()
        env = MockEnv()
        
        response = await handle_homepage(
            request,
            env,
            path_params={},
            query_params={},
            path="/"
        )
        
        if hasattr(response, 'body'):
            content = response.body
            # Check for documentation sections
            assert "Response Format" in content or "response format" in content.lower()
            assert "Authentication" in content or "authentication" in content.lower()
    
    @pytest.mark.asyncio
    async def test_homepage_with_custom_url(self):
        """Test homepage with a custom URL."""
        request = MockRequest(url="https://custom-api.example.com/")
        env = MockEnv()
        
        response = await handle_homepage(
            request,
            env,
            path_params={},
            query_params={},
            path="/"
        )
        
        # Should still work with custom URL
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_homepage_contains_try_it_buttons(self):
        """Test that homepage contains interactive Try it buttons."""
        request = MockRequest()
        env = MockEnv()
        
        response = await handle_homepage(
            request,
            env,
            path_params={},
            query_params={},
            path="/"
        )
        
        if hasattr(response, 'body'):
            content = response.body
            # Check for Try it buttons
            assert "Try it" in content
            assert "testEndpoint" in content  # JavaScript function
            assert "apiTestModal" in content  # Modal element
            assert "API Test Console" in content  # Modal title
            
            # Check for security: should use textContent, not innerHTML for responses
            assert "textContent = JSON.stringify" in content

