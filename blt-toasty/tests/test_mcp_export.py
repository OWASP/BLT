import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

import sys

js_mock = MagicMock()
Date = MagicMock()
Date.now.return_value = 1700000000000  # ms for JS Date
Date.new = MagicMock()
Date.new.return_value.toISOString.return_value = "2023-11-14T22:13:20.000Z"


class MockResponse:
    def __init__(self, body, status, headers=None):
        self._body = body
        self.status = status
        self.headers = headers

    async def text(self):
        return self._body

    @classmethod
    def new(cls, body, status=200, headers=None):
        return cls(body, status, headers)


js_mock.Response = MockResponse
js_mock.Date = Date

# For mcp_export.py WebCrypto mocks
crypto_mock = MagicMock()
crypto_mock.subtle = AsyncMock()
crypto_mock.subtle.importKey.return_value = "mock_key"
crypto_mock.subtle.verify.return_value = True
js_mock.crypto = crypto_mock
sys.modules["js"] = js_mock

from src.mcp_export import handle_mcp_export


def create_mock_jwt(payload_dict):
    header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(b"mock_signature").decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


class TestMCPExport:
    @pytest.fixture
    def mock_env(self):
        env = MagicMock()
        b64_key = base64.b64encode(b"fake_spki_key_material_for_testing").decode()
        env.MCP_PUBLIC_KEY = f"-----BEGIN PUBLIC KEY-----\n{b64_key}\n-----END PUBLIC KEY-----"

        # Mock RateLimiterDO
        rl_stub = AsyncMock()
        rl_stub.fetch.return_value = MockResponse('{"allowed": true}', 200)
        env.RATE_LIMITER_DO = MagicMock()
        env.RATE_LIMITER_DO.get.return_value = rl_stub

        return env

    @pytest.fixture
    def mock_db(self):

        def prepare_side_effect(sql):
            stmt = MagicMock()
            stmt.bind = MagicMock(return_value=stmt)

            if "FROM triage_events" in sql:
                stmt.first = AsyncMock(
                    return_value={"status": "complete", "project_id": 1, "issue_iid": 123, "created_at": "2023-01-01"}
                )
            elif "FROM triage_summaries" in sql:
                stmt.first = AsyncMock(return_value={"executive_summary": "Test Summary", "model_used": "test-model"})
            elif "FROM triage_rationale" in sql:
                stmt.first = AsyncMock(
                    return_value={"cwe_rationale": '[{"cwe_id": "CWE-79"}]', "confidence_trace": '{"overall": 0.9}'}
                )
            elif "FROM duplicate_candidates" in sql:
                stmt.all = AsyncMock(
                    return_value=MagicMock(
                        results=[{"candidate_event_id": "evt-001", "similarity_score": 0.95, "llm_rationale": "sim"}]
                    )
                )
            elif "FROM redaction_audit" in sql:
                stmt.first = AsyncMock(return_value={"cnt": 5})

            return stmt

        db = MagicMock()
        db.prepare = MagicMock(side_effect=prepare_side_effect)
        return db

    @pytest.mark.asyncio
    async def test_successful_export(self, mock_env, mock_db):
        mock_env.DB = mock_db

        req = MagicMock()
        valid_jwt = create_mock_jwt(
            {"iss": "owasp-blt-service", "aud": "toasty-mcp", "sub": "agent-1", "exp": 2000000000}  # Future
        )
        req.headers = {"Authorization": f"Bearer {valid_jwt}"}

        from unittest.mock import patch

        with patch("src.mcp_export.audit_completeness_check", new_callable=AsyncMock) as mock_audit:
            mock_audit.return_value = (True, [])

            resp = await handle_mcp_export(req, mock_env, "evt-123")

            assert resp.status == 200
            body = json.loads(await resp.text())
            assert body["schema_version"] == "1.0"
            assert body["triage_id"] == "evt-123"
            assert body["cwe_hints"] == [{"cwe_id": "CWE-79"}]
            assert body["audit"]["redaction_entity_count"] == 5

    @pytest.mark.asyncio
    async def test_unauthorized_missing_header(self, mock_env):
        req = MagicMock()
        req.headers = {}

        resp = await handle_mcp_export(req, mock_env, "evt-123")
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_unauthorized_expired_token(self, mock_env):
        req = MagicMock()
        expired_jwt = create_mock_jwt(
            {"iss": "owasp-blt-service", "aud": "toasty-mcp", "sub": "agent-1", "exp": 1000000000}  # Past
        )
        req.headers = {"Authorization": f"Bearer {expired_jwt}"}

        resp = await handle_mcp_export(req, mock_env, "evt-123")
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_rate_limited(self, mock_env, mock_db):
        mock_env.DB = mock_db

        # Override DO stub to return 429
        rl_stub = AsyncMock()
        rl_stub.fetch.return_value = MockResponse('{"error": "rate_limit_exceeded", "retry_after": 60}', 429)
        mock_env.RATE_LIMITER_DO.get.return_value = rl_stub

        req = MagicMock()
        valid_jwt = create_mock_jwt(
            {"iss": "owasp-blt-service", "aud": "toasty-mcp", "sub": "agent-1", "exp": 2000000000}
        )
        req.headers = {"Authorization": f"Bearer {valid_jwt}"}

        resp = await handle_mcp_export(req, mock_env, "evt-123")
        assert resp.status == 429

        body = json.loads(await resp.text())
        assert body["error"] == "rate_limit_exceeded"
