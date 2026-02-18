"""
Tests for the Issues handler module.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, Mock
from src.handlers.issues import handle_issues


class MockRequest:
    """Mock request object for testing."""
    
    def __init__(self, method="GET", body=None):
        self.method = method
        self._body = body
    
    async def text(self):
        """Return request body as text."""
        if self._body:
            return json.dumps(self._body)
        return ""


class MockDBResult:
    """Mock D1 database result."""
    
    def __init__(self, data):
        self._data = data
        self.results = data if isinstance(data, list) else [data] if data else []
    
    def to_py(self):
        """Convert to Python dict."""
        return self._data


class MockDBStatement:
    """Mock D1 database prepared statement."""
    
    def __init__(self, result_data):
        self._result_data = result_data
        self._bound_params = []
    
    def bind(self, *args):
        """Mock bind parameters."""
        self._bound_params = args
        return self
    
    async def first(self):
        """Mock first() - returns single row or None."""
        if self._result_data is None:
            return None
        return MockDBResult(self._result_data)
    
    async def all(self):
        """Mock all() - returns result with .results property."""
        result = MockDBResult(self._result_data)
        return result
    
    async def run(self):
        """Mock run() for INSERT/UPDATE/DELETE."""
        return MockDBResult({})


class MockDB:
    """Mock D1 database connection."""
    
    def __init__(self, mock_data=None):
        self.mock_data = mock_data or {}
        self._last_query = None
    
    def prepare(self, query):
        """Mock prepare statement."""
        self._last_query = query
        
        # Handle table existence check from get_db_safe
        if "sqlite_master" in query and "type='table'" in query:
            # Return all required tables to pass initialization check
            return MockDBStatement([
                {"name": "domains"},
                {"name": "tags"},
                {"name": "domain_tags"},
                {"name": "issues"},
                {"name": "issue_screenshots"},
                {"name": "issue_tags"}
            ])
        
        # Determine what data to return based on query
        if "SELECT" in query and "WHERE i.id = ?" in query:
            # Single issue query
            return MockDBStatement(self.mock_data.get("issue"))
        elif "SELECT" in query and "issue_screenshots" in query:
            # Screenshots query
            return MockDBStatement(self.mock_data.get("screenshots", []))
        elif "SELECT" in query and "issue_tags" in query:
            # Tags query
            return MockDBStatement(self.mock_data.get("tags", []))
        elif "SELECT COUNT(*)" in query:
            # Count query
            return MockDBStatement({"total": self.mock_data.get("count", 0)})
        elif "SELECT" in query and "LIMIT" in query:
            # List query
            return MockDBStatement(self.mock_data.get("issues", []))
        elif "INSERT INTO issues" in query:
            # Insert query
            return MockDBStatement({})
        elif "SELECT last_insert_rowid()" in query:
            # Last insert ID
            return MockDBStatement({"id": self.mock_data.get("last_id", 1)})
        elif "SELECT * FROM issues WHERE id = ?" in query:
            # Fetch created issue
            return MockDBStatement(self.mock_data.get("created_issue"))
        elif "LIKE" in query:
            # Search query
            return MockDBStatement(self.mock_data.get("search_results", []))
        
        return MockDBStatement(None)


class MockEnv:
    """Mock environment object."""
    
    def __init__(self, db=None):
        self.blt_api = db if db else MockDB()


@pytest.mark.asyncio
class TestIssuesHandler:
    """Tests for the issues handler."""
    
    async def test_get_issue_by_id(self):
        """Test getting a single issue by ID."""
        mock_issue = {
            "id": 1,
            "url": "https://example.com/test",
            "description": "Test issue",
            "status": "open",
            "verified": 1,
            "score": 75,
            "domain_name": "Example",
            "domain_url": "https://example.com"
        }
        
        mock_db = MockDB({
            "issue": mock_issue,
            "screenshots": [],
            "tags": []
        })
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env, 
            path_params={"id": "1"},
            query_params={},
            path="/issues/1"
        )
        
        assert response.status == 200
        body = json.loads(response.body)
        assert body["success"] is True
        assert body["data"]["id"] == 1
        assert body["data"]["url"] == "https://example.com/test"
        assert "screenshots" in body["data"]
        assert "tags" in body["data"]
    
    async def test_get_issue_not_found(self):
        """Test getting a non-existent issue."""
        mock_db = MockDB({"issue": None})
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={"id": "999"},
            query_params={},
            path="/issues/999"
        )
        
        assert response.status == 404
        body = json.loads(response.body)
        assert body["error"] is True
        assert "not found" in body["message"].lower()
    
    async def test_get_issue_with_screenshots_and_tags(self):
        """Test getting issue with screenshots and tags."""
        mock_issue = {
            "id": 1,
            "url": "https://example.com/test",
            "description": "Test issue"
        }
        
        mock_screenshots = [
            {"id": 1, "image": "https://cdn.example.com/img1.png", "created": "2026-02-17"},
            {"id": 2, "image": "https://cdn.example.com/img2.png", "created": "2026-02-17"}
        ]
        
        mock_tags = [
            {"id": 1, "name": "security"},
            {"id": 2, "name": "critical"}
        ]
        
        mock_db = MockDB({
            "issue": mock_issue,
            "screenshots": mock_screenshots,
            "tags": mock_tags
        })
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={"id": "1"},
            query_params={},
            path="/issues/1"
        )
        
        assert response.status == 200
        body = json.loads(response.body)
        assert len(body["data"]["screenshots"]) == 2
        assert len(body["data"]["tags"]) == 2
        assert body["data"]["tags"][0]["name"] == "security"
    
    async def test_list_issues(self):
        """Test listing issues with pagination."""
        mock_issues = [
            {"id": 1, "url": "https://example.com/1", "description": "Issue 1"},
            {"id": 2, "url": "https://example.com/2", "description": "Issue 2"}
        ]
        
        mock_db = MockDB({
            "count": 10,
            "issues": mock_issues
        })
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={"page": "1", "per_page": "2"},
            path="/issues"
        )
        
        assert response.status == 200
        body = json.loads(response.body)
        assert body["success"] is True
        assert len(body["data"]) == 2
        assert "pagination" in body
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["per_page"] == 2
        assert body["pagination"]["total"] == 10
    
    async def test_list_issues_with_filters(self):
        """Test listing issues with status filter."""
        mock_issues = [
            {"id": 1, "url": "https://example.com/1", "status": "open"}
        ]
        
        mock_db = MockDB({
            "count": 1,
            "issues": mock_issues
        })
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={"status": "open", "verified": "true"},
            path="/issues"
        )
        
        assert response.status == 200
        body = json.loads(response.body)
        assert body["success"] is True
    
    async def test_search_issues(self):
        """Test searching issues."""
        mock_results = [
            {"id": 1, "url": "https://example.com/sql", "description": "SQL injection"},
            {"id": 2, "url": "https://example.com/xss", "description": "XSS vulnerability"}
        ]
        
        mock_db = MockDB({"search_results": mock_results})
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={"q": "sql"},
            path="/issues/search"
        )
        
        assert response.status == 200
        body = json.loads(response.body)
        assert body["success"] is True
        assert body["query"] == "sql"
        assert len(body["data"]) == 2
    
    async def test_search_issues_missing_query(self):
        """Test search without query parameter."""
        mock_db = MockDB({})
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={},
            path="/issues/search"
        )
        
        assert response.status == 400
        body = json.loads(response.body)
        assert body["error"] is True
        assert "required" in body["message"].lower()
    
    async def test_create_issue(self):
        """Test creating a new issue."""
        issue_data = {
            "url": "https://example.com/vuln",
            "description": "Test vulnerability",
            "status": "open",
            "verified": True,
            "score": 80
        }
        
        created_issue = {
            "id": 1,
            "url": "https://example.com/vuln",
            "description": "Test vulnerability",
            "status": "open"
        }
        
        mock_db = MockDB({
            "last_id": 1,
            "created_issue": created_issue
        })
        env = MockEnv(mock_db)
        request = MockRequest("POST", body=issue_data)
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={},
            path="/issues"
        )
        
        assert response.status == 201
        body = json.loads(response.body)
        assert body["success"] is True
        assert "created successfully" in body["message"]
        assert body["data"]["id"] == 1
    
    async def test_create_issue_missing_required_fields(self):
        """Test creating issue without required fields."""
        issue_data = {
            "url": "https://example.com/vuln"
            # Missing description
        }
        
        mock_db = MockDB({})
        env = MockEnv(mock_db)
        request = MockRequest("POST", body=issue_data)
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={},
            path="/issues"
        )
        
        assert response.status == 400
        body = json.loads(response.body)
        assert body["error"] is True
        assert "missing required fields" in body["message"].lower()
    
    async def test_create_issue_url_too_long(self):
        """Test creating issue with URL that's too long."""
        issue_data = {
            "url": "https://example.com/" + "a" * 200,  # Over 200 chars
            "description": "Test issue"
        }
        
        mock_db = MockDB({})
        env = MockEnv(mock_db)
        request = MockRequest("POST", body=issue_data)
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={},
            path="/issues"
        )
        
        assert response.status == 400
        body = json.loads(response.body)
        assert body["error"] is True
        assert "200 characters" in body["message"]


class TestIssuesEdgeCases:
    """Tests for edge cases in issues handler."""
    
    @pytest.mark.asyncio
    async def test_pagination_defaults(self):
        """Test that pagination uses correct defaults."""
        mock_db = MockDB({"count": 50, "issues": []})
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={},
            path="/issues"
        )
        
        body = json.loads(response.body)
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["per_page"] == 20
    
    @pytest.mark.asyncio
    async def test_pagination_max_per_page(self):
        """Test that per_page is capped at 100."""
        mock_db = MockDB({"count": 200, "issues": []})
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={"per_page": "500"},  # Try to request 500
            path="/issues"
        )
        
        body = json.loads(response.body)
        assert body["pagination"]["per_page"] == 100  # Should be capped at 100
    
    @pytest.mark.asyncio
    async def test_search_with_limit(self):
        """Test search with custom limit."""
        mock_db = MockDB({"search_results": []})
        env = MockEnv(mock_db)
        request = MockRequest("GET")
        
        response = await handle_issues(
            request, env,
            path_params={},
            query_params={"q": "test", "limit": "50"},
            path="/issues/search"
        )
        
        assert response.status == 200
        body = json.loads(response.body)
        assert body["success"] is True
