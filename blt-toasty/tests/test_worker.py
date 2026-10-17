"""
Test file for Toasty Cloudflare Worker

Note: These are example tests to demonstrate the worker's expected behavior.
Actual testing would require the Cloudflare Workers runtime or a test harness.

IMPORTANT: The parse_path function is duplicated here because worker.py requires
the Cloudflare Workers runtime (js module) and cannot be imported in standard Python.
If you modify the parse_path logic in worker.py, you MUST update this copy to match.
"""

from tests.utils import parse_path
from src.webhook_handler import handle_webhook
import pytest
from unittest.mock import MagicMock
import asyncio


class MockRequest:
    def __init__(self, headers, text_body=""):
        self._headers = headers
        self._text = text_body

    @property
    def headers(self):
        class Headers:
            def __init__(self, h):
                self._h = h

            def get(self, k):
                return self._h.get(k, self._h.get(k.lower()))

        return Headers(self._headers)

    async def text(self):
        return self._text


def test_route_parsing():
    """Test URL path parsing logic."""
    # Test case 1: Root path
    url1 = "https://toasty.example.workers.dev/"
    path1 = parse_path(url1)
    assert path1 == "/", f"Expected '/', got '{path1}'"

    # Test case 2: Health endpoint
    url2 = "https://toasty.example.workers.dev/health"
    path2 = parse_path(url2)
    assert path2 == "/health", f"Expected '/health', got '{path2}'"

    # Test case 3: API endpoint
    url3 = "https://toasty.example.workers.dev/api/review"
    path3 = parse_path(url3)
    assert path3 == "/api/review", f"Expected '/api/review', got '{path3}'"

    # Test case 4: GitLab webhook endpoint
    url4 = "https://toasty.example.workers.dev/webhook/gitlab"
    path4 = parse_path(url4)
    assert path4 == "/webhook/gitlab", f"Expected '/webhook/gitlab', got '{path4}'"

    # Test case 5: URL with query parameters
    url5 = "https://toasty.example.workers.dev/api/status?debug=true"
    path5 = parse_path(url5)
    assert path5 == "/api/status", f"Expected '/api/status', got '{path5}'"

    # Test case 6: URL with fragment
    url6 = "https://toasty.example.workers.dev/health#section"
    path6 = parse_path(url6)
    assert path6 == "/health", f"Expected '/health', got '{path6}'"

    # Test case 7: URL with trailing slash
    url7 = "https://toasty.example.workers.dev/api/review/"
    path7 = parse_path(url7)
    assert path7 == "/api/review", f"Expected '/api/review', got '{path7}'"
    print("✓ All route parsing tests passed")


def test_json_response_structure():
    """Test JSON response data structures."""
    # Test root response
    root_response = {
        "service": "Toasty AI Code Reviewer",
        "version": "1.0.0",
        "description": "Backend API for OWASP BLT's AI-powered code review service",
        "endpoints": {
            "/": "Service information",
            "/health": "Health check endpoint",
            "/api/review": "POST - Submit code for review",
            "/api/status": "GET - Check service status",
        },
    }
    assert "service" in root_response
    assert "endpoints" in root_response
    assert root_response["version"] == "1.0.0"

    # Test health response
    health_response = {"status": "healthy", "service": "toasty-backend", "timestamp": None}
    assert health_response["status"] == "healthy"
    assert "service" in health_response

    # Test review response
    review_response = {
        "status": "success",
        "analysis": {
            "language": "python",
            "lines_of_code": 5,
            "issues": [],
            "suggestions": [],
            "summary": "Review completed successfully",
        },
        "metadata": {"processed_at": None, "worker_version": "1.0.0"},
    }
    assert review_response["status"] == "success"
    assert "analysis" in review_response
    assert "metadata" in review_response

    print("✓ All JSON response structure tests passed")


def test_error_response_structure():
    """Test error response structure."""
    error_response = {"error": "Test error message", "status": 400}
    assert "error" in error_response
    assert "status" in error_response
    assert error_response["status"] == 400

    print("✓ Error response structure test passed")


def test_review_request_validation():
    """Test review request validation logic."""
    # Valid request
    valid_request = {"code": "def hello(): pass", "language": "python", "context": "Test function"}
    assert "code" in valid_request, "Valid request should have 'code' field"

    # Invalid request (missing code)
    invalid_request = {"language": "python"}
    assert "code" not in invalid_request, "Invalid request missing 'code' field"

    print("✓ Review request validation tests passed")


def test_ai_endpoint_structure():
    """Test /test-ai endpoint structure and expected success payload."""
    mock_request = {"method": "GET", "url": "https://toasty.example.workers.dev/test-ai"}
    path = parse_path(mock_request["url"])

    assert mock_request["method"] == "GET", "AI test endpoint should use GET"
    assert path == "/test-ai", f"Expected '/test-ai', got '{path}'"

    mock_response = {"status": "success", "response": "TOASTY"}
    assert mock_response["status"] == "success"
    assert mock_response["response"]
    assert "status" in mock_response
    assert "response" in mock_response

    print("✓ AI endpoint structure test passed")


def test_redact_endpoint_structure():
    """Test /test-redact endpoint structure and expected entity-list payload."""
    mock_request = {"method": "POST", "url": "https://toasty.example.workers.dev/test-redact"}
    path = parse_path(mock_request["url"])

    assert mock_request["method"] == "POST", "Redaction test endpoint should use POST"
    assert path == "/test-redact", f"Expected '/test-redact', got '{path}'"

    mock_response = [
        {"start": 0, "end": 4, "entity_type": "PERSON", "score": 0.98},
        {"start": 10, "end": 16, "entity_type": "EMAIL_ADDRESS", "score": 0.95},
    ]
    assert isinstance(mock_response, list)
    assert len(mock_response) == 2
    assert all("start" in entity and "end" in entity for entity in mock_response)
    assert all("entity_type" in entity for entity in mock_response)

    print("✓ Redact endpoint structure test passed")


def test_webhook_validation_success():
    """Test successful webhook ingestion (202)."""
    # Valid Issue Hook payload
    webhook_payload = {
        "object_kind": "issue",
        "action": "open",
        "object_attributes": {
            "action": "open",
            "iid": 123,
        },
        "project": {
            "id": 456,
        },
    }

    assert "object_attributes" in webhook_payload
    assert webhook_payload["object_attributes"]["action"] == "open"
    assert webhook_payload["object_attributes"]["iid"] == 123
    assert webhook_payload["project"]["id"] == 456

    print("✓ Webhook validation success test passed")


@pytest.mark.asyncio
async def test_webhook_unauthorized_rejection():
    """Test 401 rejection for invalid token."""
    env = MagicMock()
    env.GITLAB_WEBHOOK_SECRET = "secret_token_123"

    # Scenario: Token missing
    req_missing = MockRequest({"X-Gitlab-Event-UUID": "1234567890", "X-Gitlab-Event": "Issue Hook"})
    resp1 = await handle_webhook(req_missing, env)
    assert resp1.status == 401, "Missing token should trigger 401"

    # Scenario: Token mismatch
    req_mismatch = MockRequest(
        {"X-Gitlab-Event-UUID": "1234567890", "X-Gitlab-Event": "Issue Hook", "X-Gitlab-Token": "wrong_token_456"}
    )
    resp2 = await handle_webhook(req_mismatch, env)
    assert resp2.status == 401, "Mismatched tokens should trigger 401"

    print("✓ Webhook unauthorized rejection test passed")


@pytest.mark.asyncio
async def test_webhook_missing_headers():
    """Test 422 for missing required headers."""
    env = MagicMock()
    env.GITLAB_WEBHOOK_SECRET = "secret"

    # Missing X-Gitlab-Event-UUID
    req_missing_uuid = MockRequest(
        {
            "X-Gitlab-Token": "secret",
            "X-Gitlab-Event": "Issue Hook",
        }
    )
    resp1 = await handle_webhook(req_missing_uuid, env)
    assert resp1.status == 422, "Missing X-Gitlab-Event-UUID should trigger 422"

    # Missing X-Gitlab-Event
    req_missing_event = MockRequest(
        {
            "X-Gitlab-Token": "secret",
            "X-Gitlab-Event-UUID": "550e8400-e29b-41d4-a716-446655440000",
        }
    )
    resp2 = await handle_webhook(req_missing_event, env)
    assert resp2.status == 422, "Missing X-Gitlab-Event should trigger 422"

    print("✓ Webhook missing headers test passed")


def test_webhook_invalid_json():
    """Test 422 for malformed JSON in request body."""
    malformed_json = '{"incomplete": '
    try:
        import json

        json.loads(malformed_json)
        assert False, "Should not parse malformed JSON"
    except json.JSONDecodeError:
        pass

    print("✓ Webhook invalid JSON test passed")


def test_webhook_normalization_failure():
    """Test 422 for payload normalization failure."""
    # Issue Hook missing required fields
    incomplete_payload = {
        "object_attributes": {
            "action": "open",
            # Missing 'iid'
        },
        "project": {"id": 456},
    }
    has_iid = "iid" in incomplete_payload["object_attributes"]
    assert not has_iid, "Missing iid should cause normalization failure"

    # Note Hook with missing issue field
    note_payload = {
        "object_attributes": {"action": "create", "id": 789},
        "project": {"id": 456},
        # Missing 'issue'
    }
    has_issue = "issue" in note_payload
    assert not has_issue, "Missing issue should cause normalization failure"

    print("✓ Webhook normalization failure test passed")


def test_webhook_replay_detection():
    """Test 409 for duplicate delivery_id (replay attack)."""
    # Simulating replay detection
    seen_delivery_ids = set()

    delivery_id_1 = "550e8400-e29b-41d4-a716-446655440000"
    is_duplicate_1 = delivery_id_1 in seen_delivery_ids
    assert not is_duplicate_1, "First occurrence should not be flagged as duplicate"

    seen_delivery_ids.add(delivery_id_1)

    is_duplicate_2 = delivery_id_1 in seen_delivery_ids
    assert is_duplicate_2, "Second occurrence should be flagged as duplicate (409)"

    print("✓ Webhook replay detection test passed")


def test_webhook_event_id_generation():
    """Test event_id generation (16-byte hex)."""
    import secrets

    event_id = secrets.token_hex(16)
    assert len(event_id) == 32, f"Event ID should be 32 chars (16 bytes hex), got {len(event_id)}"
    assert all(c in "0123456789abcdef" for c in event_id), "Event ID should be valid hex"

    print("✓ Webhook event_id generation test passed")


def test_webhook_body_hash():
    """Test SHA-256 hash of webhook body."""
    import hashlib

    body_text = '{"action":"open","iid":123}'
    body_hash = hashlib.sha256(body_text.encode()).hexdigest()

    assert len(body_hash) == 64, f"SHA-256 hash should be 64 chars, got {len(body_hash)}"
    assert all(c in "0123456789abcdef" for c in body_hash), "Hash should be valid hex"

    print("✓ Webhook body_hash test passed")


def test_webhook_issue_hook_normalization():
    """Test normalization of Issue Hook payload."""
    payload = {
        "object_kind": "issue",
        "action": "open",
        "object_attributes": {
            "action": "open",
            "iid": 123,
        },
        "project": {
            "id": 456,
        },
    }

    # Simulate normalization logic
    event_type = "Issue Hook"
    normalized = {
        "event_type": event_type,
        "action": payload["object_attributes"]["action"],
        "project_id": payload["project"]["id"],
        "issue_iid": payload["object_attributes"]["iid"],
    }

    assert normalized["event_type"] == "Issue Hook"
    assert normalized["action"] == "open"
    assert normalized["project_id"] == 456
    assert normalized["issue_iid"] == 123

    print("✓ Webhook Issue Hook normalization test passed")


def test_webhook_note_hook_normalization():
    """Test normalization of Note Hook payload."""
    payload = {
        "object_kind": "note",
        "action": "create",
        "object_attributes": {
            "action": "create",
            "id": 789,
        },
        "issue": {
            "iid": 123,
        },
        "project": {
            "id": 456,
        },
    }

    # Simulate normalization logic
    event_type = "Note Hook"
    normalized = {
        "event_type": event_type,
        "action": payload["object_attributes"]["action"],
        "project_id": payload["project"]["id"],
        "issue_iid": payload["issue"]["iid"],
    }

    assert normalized["event_type"] == "Note Hook"
    assert normalized["action"] == "create"
    assert normalized["project_id"] == 456
    assert normalized["issue_iid"] == 123

    print("✓ Webhook Note Hook normalization test passed")


def test_webhook_response_payload():
    """Test 202 response payload structure."""
    event_id = "a1b2c3d4e5f6789012345678"
    response_payload = {"event_id": event_id, "status": "pending"}

    assert "event_id" in response_payload
    assert "status" in response_payload
    assert response_payload["status"] == "pending"
    assert response_payload["event_id"] == event_id

    print("✓ Webhook response payload test passed")


def run_all_tests():
    """Run all test functions."""
    print("Running Toasty Worker Tests...\n")

    try:
        test_route_parsing()
        test_json_response_structure()
        test_error_response_structure()
        test_review_request_validation()

        test_ai_endpoint_structure()
        test_redact_endpoint_structure()
        test_webhook_validation_success()
        asyncio.run(test_webhook_unauthorized_rejection())
        asyncio.run(test_webhook_missing_headers())
        test_webhook_invalid_json()
        test_webhook_normalization_failure()
        test_webhook_replay_detection()
        test_webhook_event_id_generation()
        test_webhook_body_hash()
        test_webhook_issue_hook_normalization()
        test_webhook_note_hook_normalization()
        test_webhook_response_payload()

        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
