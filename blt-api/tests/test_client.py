"""
Tests for the BLT Client.
"""

import pytest
from src.client import BLTClient


class TestBLTClient:
    """Tests for the BLTClient class."""
    
    def test_client_init(self):
        """Test client initialization."""
        client = BLTClient("https://api.example.com")
        assert client.base_url == "https://api.example.com"
        assert client.auth_token is None
    
    def test_client_init_with_token(self):
        """Test client initialization with auth token."""
        client = BLTClient("https://api.example.com", auth_token="test-token")
        assert client.auth_token == "test-token"
    
    def test_client_base_url_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        client = BLTClient("https://api.example.com/")
        assert client.base_url == "https://api.example.com"
    
    def test_get_headers_default(self):
        """Test default headers."""
        client = BLTClient("https://api.example.com")
        headers = client._get_headers()
        
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Accept" in headers
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers
    
    def test_get_headers_with_token(self):
        """Test headers with authentication token."""
        client = BLTClient("https://api.example.com", auth_token="test-token")
        headers = client._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Token test-token"
    
    def test_get_headers_extra(self):
        """Test headers with extra headers."""
        client = BLTClient("https://api.example.com")
        headers = client._get_headers({"X-Custom-Header": "custom-value"})
        
        assert "X-Custom-Header" in headers
        assert headers["X-Custom-Header"] == "custom-value"


class TestBLTClientMethods:
    """Tests for BLTClient HTTP method helpers."""
    
    def test_client_has_get_method(self):
        """Test that client has get method."""
        client = BLTClient("https://api.example.com")
        assert hasattr(client, "get")
        assert callable(client.get)
    
    def test_client_has_post_method(self):
        """Test that client has post method."""
        client = BLTClient("https://api.example.com")
        assert hasattr(client, "post")
        assert callable(client.post)
    
    def test_client_has_put_method(self):
        """Test that client has put method."""
        client = BLTClient("https://api.example.com")
        assert hasattr(client, "put")
        assert callable(client.put)
    
    def test_client_has_delete_method(self):
        """Test that client has delete method."""
        client = BLTClient("https://api.example.com")
        assert hasattr(client, "delete")
        assert callable(client.delete)


class TestBLTClientAPIEndpoints:
    """Tests for BLTClient API endpoint methods."""
    
    def test_client_has_issues_methods(self):
        """Test that client has issues-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_issues")
        assert hasattr(client, "get_issue")
        assert hasattr(client, "create_issue")
        assert hasattr(client, "search_issues")
    
    def test_client_has_users_methods(self):
        """Test that client has users-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_users")
        assert hasattr(client, "get_user")
    
    def test_client_has_domains_methods(self):
        """Test that client has domains-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_domains")
        assert hasattr(client, "get_domain")
    
    def test_client_has_organizations_methods(self):
        """Test that client has organizations-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_organizations")
        assert hasattr(client, "get_organization")
        assert hasattr(client, "get_organization_repos")
    
    def test_client_has_projects_methods(self):
        """Test that client has projects-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_projects")
        assert hasattr(client, "get_project")
    
    def test_client_has_hunts_methods(self):
        """Test that client has hunts-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_hunts")
        assert hasattr(client, "get_hunt")
    
    def test_client_has_stats_methods(self):
        """Test that client has stats-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_stats")
    
    def test_client_has_leaderboard_methods(self):
        """Test that client has leaderboard-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_leaderboard")
    
    def test_client_has_contributors_methods(self):
        """Test that client has contributors-related methods."""
        client = BLTClient("https://api.example.com")
        
        assert hasattr(client, "get_contributors")
