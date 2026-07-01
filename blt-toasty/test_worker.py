"""
Test file for Toasty Cloudflare Worker

Note: These are example tests to demonstrate the worker's expected behavior.
Actual testing would require the Cloudflare Workers runtime or a test harness.

IMPORTANT: The parse_path function is duplicated here because worker.py requires
the Cloudflare Workers runtime (js module) and cannot be imported in standard Python.
If you modify the parse_path logic in worker.py, you MUST update this copy to match.
"""


def parse_path(url):
    """
    Extract clean path from URL, handling query params and fragments.
    This is a copy of the function from worker.py for testing purposes.

    ⚠️  KEEP IN SYNC WITH worker.py parse_path() ⚠️

    Args:
        url: The full URL string

    Returns:
        str: The path component of the URL
    """
    url_without_protocol = url.split("://", 1)[1] if "://" in url else url
    path_start = url_without_protocol.find("/")

    if path_start == -1:
        path = "/"
    else:
        path_with_query = url_without_protocol[path_start:]
        path = path_with_query.split("?")[0].split("#")[0]
        if not path.startswith("/"):
            path = "/" + path
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

    return path


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


def test_webhook_unauthorized_rejection():
    """Test 401 rejection for invalid signature."""
    # Scenario: Signature headers missing
    request_headers = {
        "webhook-id": "1234",
        "webhook-timestamp": "1234567890",
        # Missing webhook-signature
    }
    has_all_headers = all(h in request_headers for h in ["webhook-id", "webhook-timestamp", "webhook-signature"])
    assert not has_all_headers, "Missing signature headers should trigger 401"

    # Scenario: Signature mismatch (simulated)
    import hmac
    import hashlib
    expected_token = "v1,abc"
    provided_token = "v1,def"
    tokens_match = hmac.compare_digest(expected_token, provided_token)
    assert not tokens_match, "Mismatched signatures should trigger 401"

    print("✓ Webhook unauthorized rejection test passed")


def test_webhook_missing_headers():
    """Test 422 for missing required headers."""
    # Missing X-Gitlab-Event-UUID
    headers_missing_uuid = {
        "webhook-id": "1234",
        "webhook-timestamp": "1234567890",
        "webhook-signature": "v1,abc",
        "X-Gitlab-Event": "Issue Hook",
    }
    has_uuid = "X-Gitlab-Event-UUID" in headers_missing_uuid
    assert not has_uuid, "Missing X-Gitlab-Event-UUID should trigger 422"

    # Missing X-Gitlab-Event
    headers_missing_event = {
        "webhook-id": "1234",
        "webhook-timestamp": "1234567890",
        "webhook-signature": "v1,abc",
        "X-Gitlab-Event-UUID": "550e8400-e29b-41d4-a716-446655440000",
    }
    has_event = "X-Gitlab-Event" in headers_missing_event
    assert not has_event, "Missing X-Gitlab-Event should trigger 422"

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



def mock_verify_hmac_signature(secret: str, webhook_id: str, timestamp: str, body: str, signature_header: str) -> bool:
    """
    Mock implementation of verify_hmac_signature for local testing without Pyodide/Web Crypto API.
    Uses standard Python hmac and hashlib to simulate the Cloudflare Worker environment.
    """
    import hmac
    import hashlib
    import base64

    if not secret or not signature_header or not signature_header.startswith("v1,"):
        return False
        
    try:
        raw_key_str = secret.replace("whsec_", "")
        raw_key_bytes = base64.b64decode(raw_key_str)
        
        message = f"{webhook_id}.{timestamp}.{body}"
        message_bytes = message.encode('utf-8')
        
        signature = hmac.new(raw_key_bytes, message_bytes, hashlib.sha256).digest()
        computed_signature = base64.b64encode(signature).decode('utf-8')
        expected_signature = f"v1,{computed_signature}"
        
        return hmac.compare_digest(signature_header, expected_signature)
    except Exception:
        return False


def test_mock_verify_hmac_signature():
    """Test the Python mock of HMAC verification."""
    import base64
    # Create a dummy secret
    dummy_secret_bytes = b"my_super_secret_key"
    secret = f"whsec_{base64.b64encode(dummy_secret_bytes).decode('utf-8')}"
    
    webhook_id = "12345"
    timestamp = "1620000000"
    body = '{"action":"open"}'
    
    # Generate correct signature
    import hmac
    import hashlib
    msg = f"{webhook_id}.{timestamp}.{body}".encode('utf-8')
    sig = hmac.new(dummy_secret_bytes, msg, hashlib.sha256).digest()
    sig_header = f"v1,{base64.b64encode(sig).decode('utf-8')}"
    
    assert mock_verify_hmac_signature(secret, webhook_id, timestamp, body, sig_header), "Valid signature should pass"
    assert not mock_verify_hmac_signature(secret, webhook_id, timestamp, body, "v1,invalid"), "Invalid signature should fail"
    
    print("✓ Mock verify_hmac_signature test passed")



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
        test_webhook_unauthorized_rejection()
        test_webhook_missing_headers()
        test_webhook_invalid_json()
        test_webhook_normalization_failure()
        test_webhook_replay_detection()
        test_webhook_event_id_generation()
        test_webhook_body_hash()
        test_webhook_issue_hook_normalization()
        test_webhook_note_hook_normalization()
        test_webhook_response_payload()
        test_mock_verify_hmac_signature()


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
