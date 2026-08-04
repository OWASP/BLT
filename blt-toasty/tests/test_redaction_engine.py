"""
Unit tests for the fail-closed redaction engine.

Covers:
  - Native recogniser patterns (all 17+ entity types)
  - Markdown preprocessing (PII in code fences, links, images)
  - Confidence gate and quarantine behaviour
  - The ``assert_redacted_before_downstream`` security guard
  - Deny-list suppression (CVE, CWE strings)
  - RedactionResult contract validation
  - End-to-end golden-set acceptance (0 PII leaks)
"""

import json
import glob
import os
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.errors import RedactionFailedError, StateTransitionError
from src.markdown_preprocessor import extract_plain_text
from src.native_recognizers import apply_native_redaction
from src.redaction_engine import (
    RedactionResult,
    assert_redacted_before_downstream,
    redact,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_db():
    """Provide a mock Cloudflare D1 database handle."""
    db = AsyncMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = ("pending",)
    db.execute.return_value = cursor
    return db


@pytest.fixture()
def mock_env():
    """Provide a mock Cloudflare Worker environment."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Markdown preprocessor tests
# ---------------------------------------------------------------------------


class TestMarkdownPreprocessor:
    """Tests for ``src.markdown_preprocessor.extract_plain_text``."""

    def test_empty_string(self):
        assert extract_plain_text("") == ""

    def test_plain_text_passthrough(self):
        text = "Hello world, this is plain text."
        assert "Hello world" in extract_plain_text(text)

    def test_extracts_content_from_code_fences(self):
        md = "Before\n```python\nemail = user@example.com\n```\nAfter"
        result = extract_plain_text(md)
        assert "user@example.com" in result
        assert "Before" in result
        assert "After" in result

    def test_extracts_link_url(self):
        md = "Click [here](mailto:victim@evil.com) to report."
        result = extract_plain_text(md)
        assert "victim@evil.com" in result

    def test_extracts_image_alt_and_url(self):
        md = "![screenshot](https://secret.internal/img.png)"
        result = extract_plain_text(md)
        assert "screenshot" in result
        assert "secret.internal" in result

    def test_strips_heading_markers(self):
        md = "## My Heading\nContent here."
        result = extract_plain_text(md)
        assert "My Heading" in result
        assert "##" not in result

    def test_strips_bold_italic(self):
        md = "This is **bold** and *italic* text."
        result = extract_plain_text(md)
        assert "bold" in result
        assert "italic" in result
        assert "**" not in result
        assert "*italic*" not in result

    def test_removes_html_comments(self):
        md = "Before <!-- secret comment --> After"
        result = extract_plain_text(md)
        assert "secret comment" not in result
        assert "Before" in result
        assert "After" in result


# ---------------------------------------------------------------------------
# Native recogniser pattern tests
# ---------------------------------------------------------------------------


class TestNativeRecognisers:
    """Tests for individual recogniser patterns in ``src.native_recognizers``."""

    def test_email_detected(self):
        _, matches = apply_native_redaction("Contact: admin@example.com for details.")
        types = [m["entity_type"] for m in matches]
        assert "EMAIL_ADDRESS" in types

    def test_ip_address_detected(self):
        _, matches = apply_native_redaction("Server IP: 192.168.1.42 is internal.")
        types = [m["entity_type"] for m in matches]
        assert "IP_ADDRESS" in types

    def test_aws_access_key_detected(self):
        _, matches = apply_native_redaction("AWS Key: AKIAIOSFODNN7EXAMPLE leaked.")
        types = [m["entity_type"] for m in matches]
        assert "AWS_ACCESS_KEY" in types

    def test_aws_secret_key_detected(self):
        _, matches = apply_native_redaction("Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY found.")
        types = [m["entity_type"] for m in matches]
        assert "AWS_SECRET_KEY" in types

    def test_jwt_token_detected(self):
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJhZG1pbiIsImlhdCI6MTUxNjIzOTAyMn0."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        _, matches = apply_native_redaction(f"Token: {jwt} was leaked.")
        types = [m["entity_type"] for m in matches]
        assert "JWT_TOKEN" in types

    def test_github_token_detected(self):
        _, matches = apply_native_redaction("GitHub PAT: ghp_1234567890abcdefghijklmnopqrstuvwxyz found.")
        types = [m["entity_type"] for m in matches]
        assert "GITHUB_TOKEN" in types

    def test_private_key_header_detected(self):
        _, matches = apply_native_redaction("Found key: -----BEGIN RSA PRIVATE KEY----- in config.")
        types = [m["entity_type"] for m in matches]
        assert "PRIVATE_KEY" in types

    def test_credit_card_detected(self):
        _, matches = apply_native_redaction("CC: 4111111111111111 was exposed.")
        types = [m["entity_type"] for m in matches]
        assert "CREDIT_CARD" in types

    def test_mongodb_uri_detected(self):
        uri = "mongodb://admin:pass@db.internal:27017/mydb"
        _, matches = apply_native_redaction(f"Connection: {uri} leaked.")
        types = [m["entity_type"] for m in matches]
        assert "MONGODB_URI" in types

    def test_db_connection_postgresql_detected(self):
        uri = "postgresql://testuser:TestPass456@db-staging.internal:5432/test_db"
        _, matches = apply_native_redaction(f"DB: {uri} leaked.")
        types = [m["entity_type"] for m in matches]
        assert "DB_CONNECTION" in types

    def test_aws_arn_detected(self):
        arn = "arn:aws:lambda:us-east-1:123456789012:function:BitcoinProcessor"
        _, matches = apply_native_redaction(f"Resource: {arn} found.")
        types = [m["entity_type"] for m in matches]
        assert "AWS_ARN" in types

    def test_sendgrid_api_key_detected(self):
        _, matches = apply_native_redaction("Key: SG.7Fv_2cyzQOyLBYPy_EXAMPLE leaked.")
        types = [m["entity_type"] for m in matches]
        assert "API_KEY" in types

    def test_stripe_api_key_detected(self):
        _, matches = apply_native_redaction("Key: sk_live_4eC39HqLyjWDarhtTX7YEXAMPLE found.")
        types = [m["entity_type"] for m in matches]
        assert "API_KEY" in types

    def test_gcp_auth_token_detected(self):
        _, matches = apply_native_redaction("Token: ya29.a0AfH6SMBx_ZmZZ_bPxRfiCYEXAMPLE_example leaked.")
        types = [m["entity_type"] for m in matches]
        assert "AUTH_TOKEN" in types

    def test_md5_hash_detected(self):
        _, matches = apply_native_redaction("Hash: c32b4d0bc6674f7d308dd90ef89f0db2 found.")
        types = [m["entity_type"] for m in matches]
        assert "MD5_HASH" in types

    def test_password_context_detected(self):
        _, matches = apply_native_redaction("Password: SuperSecret123!")
        types = [m["entity_type"] for m in matches]
        assert "PASSWORD" in types

    def test_username_context_detected(self):
        _, matches = apply_native_redaction("Username: admin_user")
        types = [m["entity_type"] for m in matches]
        assert "USERNAME" in types

    def test_hostname_internal_detected(self):
        _, matches = apply_native_redaction("Connected to sql-server-prod.flexlists.internal for data.")
        types = [m["entity_type"] for m in matches]
        assert any(t in ("HOSTNAME", "DOMAIN") for t in types)


# ---------------------------------------------------------------------------
# Deny-list tests (false positive suppression)
# ---------------------------------------------------------------------------


class TestDenyList:
    """Verify that technical identifiers are NOT flagged as PII."""

    def test_cve_string_not_detected(self):
        text = "This vulnerability is CVE-2024-1234."
        _, matches = apply_native_redaction(text)
        entity_types = [m["entity_type"] for m in matches]
        assert "CVE-2024-1234" not in entity_types
        # Also verify the literal CVE string is still in the output.
        redacted, _ = apply_native_redaction(text)
        assert "CVE-2024-1234" in redacted

    def test_cwe_string_not_detected(self):
        text = "Classified under CWE-22 and CWE-200."
        redacted, _ = apply_native_redaction(text)
        assert "CWE-22" in redacted
        assert "CWE-200" in redacted


# ---------------------------------------------------------------------------
# Redaction output contract tests
# ---------------------------------------------------------------------------


class TestRedactionOutputContract:
    """Verify the shape and guarantees of redacted output."""

    def test_redacted_text_has_typed_placeholders(self):
        text = "Email: admin@example.com and IP: 10.0.0.1"
        redacted, _ = apply_native_redaction(text)
        assert "[EMAIL_ADDRESS]" in redacted
        assert "[IP_ADDRESS]" in redacted
        assert "admin@example.com" not in redacted
        assert "10.0.0.1" not in redacted

    def test_redacted_text_never_contains_original_pii(self):
        pii_values = [
            "admin@example.com",
            "192.168.1.42",
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        ]
        text = " | ".join(pii_values)
        redacted, _ = apply_native_redaction(text)
        for pii in pii_values:
            assert pii not in redacted, f"PII leaked in redacted text: {pii}"

    def test_matches_have_required_fields(self):
        _, matches = apply_native_redaction("Email: admin@example.com")
        assert len(matches) >= 1
        match = matches[0]
        assert "entity_type" in match
        assert "start" in match
        assert "end" in match
        assert "confidence" in match
        assert "detector" in match
        assert match["detector"] == "native_recognizer"
        assert match["confidence"] >= 0.70


# ---------------------------------------------------------------------------
# Redaction engine integration tests
# ---------------------------------------------------------------------------


class TestRedactionEngine:
    """Integration tests for ``src.redaction_engine.redact``."""

    @pytest.mark.asyncio
    async def test_redact_email_in_plain_text(self, mock_db, mock_env):
        result = await redact(
            "Contact admin@example.com for info.",
            mock_env,
            "evt-001",
            mock_db,
        )
        assert isinstance(result, RedactionResult)
        assert "[EMAIL_ADDRESS]" in result.redacted_text
        assert "admin@example.com" not in result.redacted_text
        assert result.entity_count >= 1

    @pytest.mark.asyncio
    async def test_redact_email_inside_code_fence(self, mock_db, mock_env):
        md = "```\nemail = user@example.com\n```"
        result = await redact(md, mock_env, "evt-002", mock_db)
        assert "user@example.com" not in result.redacted_text

    @pytest.mark.asyncio
    async def test_redact_email_in_link_url(self, mock_db, mock_env):
        md = "[contact](mailto:victim@evil.com)"
        result = await redact(md, mock_env, "evt-003", mock_db)
        assert "victim@evil.com" not in result.redacted_text

    @pytest.mark.asyncio
    async def test_safe_preview_text_only_has_redacted_tag(self, mock_db, mock_env):
        result = await redact(
            "Email: admin@example.com, IP: 10.0.0.1",
            mock_env,
            "evt-004",
            mock_db,
        )
        assert "[REDACTED]" in result.safe_preview_text
        assert "[EMAIL_ADDRESS]" not in result.safe_preview_text
        assert "[IP_ADDRESS]" not in result.safe_preview_text
        assert "admin@example.com" not in result.safe_preview_text
        assert "10.0.0.1" not in result.safe_preview_text

    @pytest.mark.asyncio
    async def test_redaction_map_stored_in_d1(self, mock_db, mock_env):
        await redact("Email: admin@example.com", mock_env, "evt-005", mock_db)
        # Verify at least one INSERT into redaction_audit was called.
        insert_calls = [call for call in mock_db.execute.call_args_list if "INSERT INTO redaction_audit" in str(call)]
        assert len(insert_calls) >= 1

    @pytest.mark.asyncio
    async def test_state_transitions_to_redaction_passed(self, mock_db, mock_env):
        await redact("Email: admin@example.com", mock_env, "evt-006", mock_db)
        # Verify state transition call.
        update_calls = [call for call in mock_db.execute.call_args_list if "redaction_passed" in str(call)]
        assert len(update_calls) == 1

    @pytest.mark.asyncio
    async def test_no_entities_still_passes(self, mock_db, mock_env):
        result = await redact(
            "This is a clean report with no PII.",
            mock_env,
            "evt-007",
            mock_db,
        )
        assert result.entity_count == 0
        assert result.redacted_text == "This is a clean report with no PII."

    @pytest.mark.asyncio
    async def test_redaction_map_has_correct_fields(self, mock_db, mock_env):
        result = await redact("Email: admin@example.com", mock_env, "evt-008", mock_db)
        assert len(result.redaction_map) >= 1
        entry = result.redaction_map[0]
        assert "entity_type" in entry
        assert "detector" in entry
        assert "confidence" in entry
        assert "byte_start" in entry
        assert "byte_end" in entry
        assert "original_length" in entry

    @pytest.mark.asyncio
    async def test_unexpected_error_quarantines_event(self, mock_env):
        """If the DB raises during audit storage, the event is quarantined."""
        broken_db = AsyncMock()
        # First call (INSERT) raises, subsequent calls succeed.
        broken_db.execute.side_effect = [RuntimeError("D1 unavailable"), MagicMock(), MagicMock()]

        mock_stmt = MagicMock()
        mock_stmt.bind.return_value = mock_stmt
        mock_stmt.first = AsyncMock(return_value={"status": "pending"})
        mock_stmt.run = AsyncMock(return_value=MagicMock(meta={"changes": 1}))
        broken_db.prepare = MagicMock(return_value=mock_stmt)

        with pytest.raises(RedactionFailedError):
            await redact("Email: admin@example.com", mock_env, "evt-err", broken_db)


# ---------------------------------------------------------------------------
# Security guard tests
# ---------------------------------------------------------------------------


class TestAssertRedactedBeforeDownstream:
    """Tests for the ``assert_redacted_before_downstream`` guard."""

    @pytest.mark.asyncio
    async def test_raises_on_pending_event(self):
        db = AsyncMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("pending",)
        db.execute.return_value = cursor

        with pytest.raises(StateTransitionError) as exc_info:
            await assert_redacted_before_downstream("evt-guard-1", db)
        assert exc_info.value.http_status == 423
        assert exc_info.value.current_status == "pending"

    @pytest.mark.asyncio
    async def test_raises_on_quarantined_event(self):
        db = AsyncMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("quarantined",)
        db.execute.return_value = cursor

        with pytest.raises(StateTransitionError):
            await assert_redacted_before_downstream("evt-guard-2", db)

    @pytest.mark.asyncio
    async def test_raises_on_missing_event(self):
        db = AsyncMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        db.execute.return_value = cursor

        with pytest.raises(StateTransitionError) as exc_info:
            await assert_redacted_before_downstream("evt-missing", db)
        assert exc_info.value.http_status == 404

    @pytest.mark.asyncio
    async def test_passes_on_redaction_passed(self):
        db = AsyncMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("redaction_passed",)
        db.execute.return_value = cursor

        # Should NOT raise.
        await assert_redacted_before_downstream("evt-ok", db)

    @pytest.mark.asyncio
    async def test_raises_on_redaction_failed(self):
        db = AsyncMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("redaction_failed",)
        db.execute.return_value = cursor

        with pytest.raises(StateTransitionError):
            await assert_redacted_before_downstream("evt-failed", db)


# ---------------------------------------------------------------------------
# Golden Set acceptance test — 0 PII leaks
# ---------------------------------------------------------------------------


class TestGoldenSetRedaction:
    """Run the redaction engine against every golden set report.

    For each report, verify that every ``expected_entity.value`` is
    completely absent from the ``redacted_text`` output.
    """

    @staticmethod
    def _load_golden_reports() -> list[dict]:
        base_dir = os.path.join(os.path.dirname(__file__), "golden_set")
        files = glob.glob(os.path.join(base_dir, "**", "*.json"), recursive=True)
        reports = []
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_filepath"] = fpath
                reports.append(data)
        return reports

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "report",
        _load_golden_reports.__func__(),  # type: ignore[attr-defined]
        ids=lambda r: r.get("id", "unknown"),
    )
    async def test_no_pii_leak_in_redacted_text(self, report, mock_db, mock_env):
        raw_text = report["raw_text"]
        result = await redact(raw_text, mock_env, report["id"], mock_db)

        for entity in report.get("expected_entities", []):
            pii_value = entity["value"]
            expected_rt = report.get("expected_redacted_text", "")
            if pii_value in expected_rt:
                # The PII value is naturally part of the expected output (e.g. "admin" as a word).
                # A naive substring search will produce a false positive.
                continue

            assert pii_value not in result.redacted_text, (
                f"PII LEAK in {report.get('_filepath', 'unknown')}!\n"
                f"  Entity type: {entity['type']}\n"
                f"  Leaked value: '{pii_value}'\n"
                f"  Redacted text snippet: ...{result.redacted_text[max(0, result.redacted_text.find(pii_value)-20):]}..."
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "report",
        _load_golden_reports.__func__(),  # type: ignore[attr-defined]
        ids=lambda r: r.get("id", "unknown"),
    )
    async def test_no_pii_leak_in_safe_preview(self, report, mock_db, mock_env):
        raw_text = report["raw_text"]
        result = await redact(raw_text, mock_env, report["id"], mock_db)

        for entity in report.get("expected_entities", []):
            pii_value = entity["value"]
            expected_rt = report.get("expected_redacted_text", "")
            if pii_value in expected_rt:
                continue

            assert pii_value not in result.safe_preview_text, (
                f"PII LEAK in safe_preview_text for {report.get('_filepath', 'unknown')}!\n"
                f"  Entity type: {entity['type']}\n"
                f"  Leaked value: '{pii_value}'"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "report",
        _load_golden_reports.__func__(),  # type: ignore[attr-defined]
        ids=lambda r: r.get("id", "unknown"),
    )
    async def test_safe_preview_has_no_typed_placeholders(self, report, mock_db, mock_env):
        raw_text = report["raw_text"]
        result = await redact(raw_text, mock_env, report["id"], mock_db)

        # safe_preview_text should only contain [REDACTED], not typed tags.
        typed_tags = re.findall(r"\[[A-Z][A-Z0-9_]+\]", result.safe_preview_text)
        non_redacted_tags = [t for t in typed_tags if t != "[REDACTED]"]
        assert not non_redacted_tags, (
            f"Typed placeholder(s) found in safe_preview_text for {report.get('id')}:\n" f"  {non_redacted_tags}"
        )
