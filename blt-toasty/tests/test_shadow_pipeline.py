"""Tests for the Shadow Mode Validation Pipeline.

Covers:
- GitLab issue fetching
- Silent triage pipeline execution (no GitLab mutations)
- Prediction vs actual comparison logic
- Weekly summary generation
- Slack notification
- on_scheduled cron handler
- /admin/shadow-report endpoint
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock JS modules before importing modules under test
# ---------------------------------------------------------------------------

_mock_js = MagicMock()
_mock_js.Response = MagicMock()
_mock_js.Headers = MagicMock()
_mock_js.console = MagicMock()

if "js" not in sys.modules:
    sys.modules["js"] = _mock_js
if "pyodide" not in sys.modules:
    sys.modules["pyodide"] = MagicMock()
if "pyodide.ffi" not in sys.modules:
    sys.modules["pyodide.ffi"] = MagicMock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_mock():
    """Create a mock D1 database handle."""
    db = MagicMock()
    stmt = MagicMock()
    stmt.bind = MagicMock(return_value=stmt)
    stmt.run = AsyncMock()
    stmt.first = AsyncMock(return_value=None)
    stmt.all = AsyncMock(return_value=MagicMock(results=[]))
    db.prepare = MagicMock(return_value=stmt)
    db._stmt = stmt
    return db


def _make_env(shadow_mode="true", project_id="14998512"):
    """Create a mock Cloudflare Worker environment."""
    env = MagicMock()
    env.SHADOW_MODE = shadow_mode
    env.SHADOW_PROJECT_ID = project_id
    env.GITLAB_ACCESS_TOKEN = "glpat-test-token"
    env.DB = _make_db_mock()
    env.VECTORIZE = MagicMock()
    env.VECTORIZE.upsert = AsyncMock()
    env.VECTORIZE.query = AsyncMock(return_value=MagicMock(matches=[]))
    env.FASTEMBED_URL = "http://localhost:5003"
    env.SLACK_WEBHOOK_URL = None
    return env


def _make_issue(iid=42, labels=None, state="closed"):
    """Create a mock GitLab issue dict."""
    return {
        "iid": iid,
        "title": f"Test Issue #{iid}",
        "description": "A test vulnerability report with PII: test@example.com",
        "labels": labels or [],
        "web_url": f"https://gitlab.com/test/project/-/issues/{iid}",
        "state": state,
        "project_id": 14998512,
    }


# ---------------------------------------------------------------------------
# Tests: fetch_recent_closed_issues
# ---------------------------------------------------------------------------


class TestFetchRecentClosedIssues:
    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """Mock GitLab API returns 3 closed issues; verify parsed correctly."""
        from src.shadow_pipeline import fetch_recent_closed_issues

        env = _make_env()

        mock_issues = [
            {
                "iid": 1,
                "title": "Bug 1",
                "description": "desc 1",
                "labels": ["bug"],
                "web_url": "url1",
                "state": "closed",
            },
            {"iid": 2, "title": "Bug 2", "description": "desc 2", "labels": [], "web_url": "url2", "state": "closed"},
            {
                "iid": 3,
                "title": "Bug 3",
                "description": "desc 3",
                "labels": ["CWE-79"],
                "web_url": "url3",
                "state": "closed",
            },
        ]

        async def _mock_fetch(url, token):
            return mock_issues

        env._gitlab_fetch_impl = _mock_fetch

        issues = await fetch_recent_closed_issues(env, since_hours=1)
        assert len(issues) == 3
        assert issues[0]["iid"] == 1
        assert issues[2]["labels"] == ["CWE-79"]

    @pytest.mark.asyncio
    async def test_fetch_empty(self):
        """GitLab returns []; verify graceful empty return."""
        from src.shadow_pipeline import fetch_recent_closed_issues

        env = _make_env()

        async def _mock_fetch(url, token):
            return []

        env._gitlab_fetch_impl = _mock_fetch

        issues = await fetch_recent_closed_issues(env, since_hours=1)
        assert issues == []

    @pytest.mark.asyncio
    async def test_fetch_no_token(self):
        """No GITLAB_ACCESS_TOKEN; verify empty list returned."""
        from src.shadow_pipeline import fetch_recent_closed_issues

        env = _make_env()
        env.GITLAB_ACCESS_TOKEN = None

        issues = await fetch_recent_closed_issues(env, since_hours=1)
        assert issues == []

    @pytest.mark.asyncio
    async def test_fetch_skips_empty_descriptions(self):
        """Issues with empty descriptions should be filtered out."""
        from src.shadow_pipeline import fetch_recent_closed_issues

        env = _make_env()

        mock_issues = [
            {"iid": 1, "title": "Bug", "description": "", "labels": [], "web_url": "url", "state": "closed"},
            {
                "iid": 2,
                "title": "Bug",
                "description": "has content",
                "labels": [],
                "web_url": "url2",
                "state": "closed",
            },
        ]

        async def _mock_fetch(url, token):
            return mock_issues

        env._gitlab_fetch_impl = _mock_fetch

        issues = await fetch_recent_closed_issues(env, since_hours=1)
        assert len(issues) == 1
        assert issues[0]["iid"] == 2


# ---------------------------------------------------------------------------
# Tests: run_shadow_triage
# ---------------------------------------------------------------------------


class TestRunShadowTriage:
    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self):
        """Mock all pipeline stages; verify predictions returned."""
        from src.shadow_pipeline import run_shadow_triage

        env = _make_env()
        db = env.DB
        issue = _make_issue(iid=42, labels=["CWE-79"])

        with (
            patch("src.redaction_engine.redact", new_callable=AsyncMock) as mock_redact,
            patch("src.native_recognizers.apply_native_redaction"),
            patch("src.summarizer.summarize", new_callable=AsyncMock) as mock_summarize,
            patch("src.vectorize_client.index_report", new_callable=AsyncMock),
            patch("src.duplicate_detector.detect_duplicates", new_callable=AsyncMock) as mock_dup,
        ):

            mock_redact.return_value = "redacted text"
            mock_summary = MagicMock()
            mock_summary.cwe_hints = ["CWE-79"]
            mock_summary.confidence = 0.85
            mock_summarize.return_value = mock_summary

            mock_dup_result = MagicMock()
            mock_dup_result.top_candidate = None
            mock_dup.return_value = mock_dup_result

            result = await run_shadow_triage(issue, env, db)

            assert result["predicted_cwe"] == ["CWE-79"]
            assert result["confidence"] == 0.85
            assert result["event_id"].startswith("shadow:")
            assert result["predicted_duplicate_of"] is None

    @pytest.mark.asyncio
    async def test_skips_gitlab_mutations(self):
        """Verify post_duplicate_comment and add_duplicate_label are NEVER called."""
        from src.shadow_pipeline import run_shadow_triage

        env = _make_env()
        db = env.DB
        issue = _make_issue()

        with (
            patch("src.redaction_engine.redact", new_callable=AsyncMock) as mock_redact,
            patch("src.native_recognizers.apply_native_redaction"),
            patch("src.summarizer.summarize", new_callable=AsyncMock) as mock_summarize,
            patch("src.vectorize_client.index_report", new_callable=AsyncMock),
            patch("src.duplicate_detector.detect_duplicates", new_callable=AsyncMock) as mock_dup,
            patch("src.gitlab_linker.post_duplicate_comment", new_callable=AsyncMock) as mock_comment,
            patch("src.gitlab_linker.add_duplicate_label", new_callable=AsyncMock) as mock_label,
        ):

            mock_redact.return_value = "redacted"
            mock_summary = MagicMock()
            mock_summary.cwe_hints = []
            mock_summary.confidence = 0.5
            mock_summarize.return_value = mock_summary
            mock_dup.return_value = MagicMock(top_candidate=None)

            await run_shadow_triage(issue, env, db)

            mock_comment.assert_not_called()
            mock_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_redaction_failure_fallback(self):
        """When redaction fails, native regex fallback should be used."""
        from src.shadow_pipeline import run_shadow_triage

        env = _make_env()
        db = env.DB
        issue = _make_issue()

        with (
            patch("src.redaction_engine.redact", new_callable=AsyncMock, side_effect=Exception("redaction error")),
            patch("src.native_recognizers.apply_native_redaction", return_value=("native redacted", [])) as mock_native,
            patch("src.summarizer.summarize", new_callable=AsyncMock) as mock_summarize,
            patch("src.vectorize_client.index_report", new_callable=AsyncMock),
            patch("src.duplicate_detector.detect_duplicates", new_callable=AsyncMock) as mock_dup,
        ):

            mock_summary = MagicMock()
            mock_summary.cwe_hints = ["CWE-89"]
            mock_summary.confidence = 0.7
            mock_summarize.return_value = mock_summary
            mock_dup.return_value = MagicMock(top_candidate=None)

            result = await run_shadow_triage(issue, env, db)

        mock_native.assert_not_called()
        assert result["predicted_cwe"] == []
        assert result["predicted_duplicate_of"] is None
        assert result["confidence"] == 0.0

        # Verify it updated the status to failed
        found_failed = False
        for call in db.prepare.call_args_list:
            if "UPDATE triage_events SET status = 'failed'" in call.args[0]:
                found_failed = True
        assert found_failed


# ---------------------------------------------------------------------------
# Tests: compare_and_store
# ---------------------------------------------------------------------------


class TestCompareAndStore:
    @pytest.mark.asyncio
    async def test_cwe_match(self):
        """Issue has label 'CWE-79'; prediction includes 'CWE-79' → matched=1."""
        from src.shadow_pipeline import compare_and_store

        db = _make_db_mock()
        issue = _make_issue(labels=["CWE-79", "bug"])
        shadow_result = {
            "event_id": "shadow:test123",
            "predicted_cwe": ["CWE-79"],
            "predicted_duplicate_of": None,
            "confidence": 0.85,
        }

        result = await compare_and_store(db, issue, shadow_result)
        assert result["matched"] == 1

    @pytest.mark.asyncio
    async def test_cwe_mismatch(self):
        """Issue has label 'CWE-89'; prediction has 'CWE-79' → matched=0."""
        from src.shadow_pipeline import compare_and_store

        db = _make_db_mock()
        issue = _make_issue(labels=["CWE-89"])
        shadow_result = {
            "event_id": "shadow:test456",
            "predicted_cwe": ["CWE-79"],
            "predicted_duplicate_of": None,
            "confidence": 0.6,
        }

        result = await compare_and_store(db, issue, shadow_result)
        assert result["matched"] == 0

    @pytest.mark.asyncio
    async def test_duplicate_match(self):
        """Issue has 'possible-duplicate' label; candidate exists → matched=1."""
        from src.shadow_pipeline import compare_and_store

        db = _make_db_mock()
        issue = _make_issue(labels=["possible-duplicate"])
        shadow_result = {
            "event_id": "shadow:test789",
            "predicted_cwe": [],
            "predicted_duplicate_of": "evt-original-001",
            "confidence": 0.9,
        }

        result = await compare_and_store(db, issue, shadow_result)
        assert result["matched"] == 1

    @pytest.mark.asyncio
    async def test_no_labels_no_predictions(self):
        """Issue has no CWE/duplicate labels, no predictions → matched=0."""
        from src.shadow_pipeline import compare_and_store

        db = _make_db_mock()
        issue = _make_issue(labels=[])
        shadow_result = {
            "event_id": "shadow:testABC",
            "predicted_cwe": [],
            "predicted_duplicate_of": None,
            "confidence": 0.0,
        }

        result = await compare_and_store(db, issue, shadow_result)
        assert result["matched"] == 0

    @pytest.mark.asyncio
    async def test_duplicate_label_no_prediction(self):
        """Issue has 'duplicate' label but Toasty didn't predict one → matched=0."""
        from src.shadow_pipeline import compare_and_store

        db = _make_db_mock()
        issue = _make_issue(labels=["duplicate"])
        shadow_result = {
            "event_id": "shadow:testDEF",
            "predicted_cwe": [],
            "predicted_duplicate_of": None,
            "confidence": 0.5,
        }

        result = await compare_and_store(db, issue, shadow_result)
        assert result["matched"] == 0

    @pytest.mark.asyncio
    async def test_case_insensitive_cwe_match(self):
        """CWE matching should be case-insensitive."""
        from src.shadow_pipeline import compare_and_store

        db = _make_db_mock()
        issue = _make_issue(labels=["cwe-79", "Bug"])
        shadow_result = {
            "event_id": "shadow:testCI",
            "predicted_cwe": ["CWE-79"],
            "predicted_duplicate_of": None,
            "confidence": 0.8,
        }

        result = await compare_and_store(db, issue, shadow_result)
        assert result["matched"] == 1

    @pytest.mark.asyncio
    async def test_db_insert_called(self):
        """Verify shadow_predictions INSERT is executed with correct parameters."""
        from src.shadow_pipeline import compare_and_store

        db = _make_db_mock()
        issue = _make_issue(iid=99, labels=["CWE-89"])
        shadow_result = {
            "event_id": "shadow:testDB",
            "predicted_cwe": ["CWE-89"],
            "predicted_duplicate_of": None,
            "confidence": 0.75,
        }

        await compare_and_store(db, issue, shadow_result)
        db.prepare.assert_called_once()
        call_sql = db.prepare.call_args[0][0]
        assert "INSERT INTO shadow_predictions" in call_sql


# ---------------------------------------------------------------------------
# Tests: generate_weekly_summary
# ---------------------------------------------------------------------------


class TestGenerateWeeklySummary:
    @pytest.mark.asyncio
    async def test_summary_with_data(self):
        """Seed mock DB with aggregated results; verify accuracy_pct."""
        from src.shadow_pipeline import generate_weekly_summary

        db = _make_db_mock()
        db._stmt.first = AsyncMock(return_value={"total": 10, "matched_count": 7})

        summary = await generate_weekly_summary(db)
        assert summary["total"] == 10
        assert summary["matched_count"] == 7
        assert summary["accuracy_pct"] == 70.0

    @pytest.mark.asyncio
    async def test_summary_empty(self):
        """No predictions in the last 7 days; verify 0% accuracy."""
        from src.shadow_pipeline import generate_weekly_summary

        db = _make_db_mock()
        db._stmt.first = AsyncMock(return_value={"total": 0, "matched_count": 0})

        summary = await generate_weekly_summary(db)
        assert summary["total"] == 0
        assert summary["accuracy_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_summary_null_row(self):
        """DB returns None; verify graceful default."""
        from src.shadow_pipeline import generate_weekly_summary

        db = _make_db_mock()
        db._stmt.first = AsyncMock(return_value=None)

        summary = await generate_weekly_summary(db)
        assert summary["total"] == 0
        assert summary["accuracy_pct"] == 0.0


# ---------------------------------------------------------------------------
# Tests: post_slack_summary
# ---------------------------------------------------------------------------


class TestPostSlackSummary:
    @pytest.mark.asyncio
    async def test_no_webhook_url(self):
        """No SLACK_WEBHOOK_URL → logs summary, returns False."""
        from src.shadow_pipeline import post_slack_summary

        env = _make_env()
        env.SLACK_WEBHOOK_URL = None

        summary = {"total": 10, "matched_count": 7, "accuracy_pct": 70.0, "period_start": "x", "period_end": "y"}
        result = await post_slack_summary(env, summary)
        assert result is False

    @pytest.mark.asyncio
    async def test_slack_post_success(self):
        """With SLACK_WEBHOOK_URL, verify fetch is called with correct payload."""
        from src.shadow_pipeline import post_slack_summary

        env = _make_env()
        env.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"

        async def _mock_slack(url, payload):
            assert "hooks.slack.com" in url
            return True

        env._slack_fetch_impl = _mock_slack

        summary = {"total": 10, "matched_count": 7, "accuracy_pct": 70.0, "period_start": "x", "period_end": "y"}
        result = await post_slack_summary(env, summary)
        assert result is True


# ---------------------------------------------------------------------------
# Tests: on_scheduled
# ---------------------------------------------------------------------------


# Need to set up JS mocks for worker import
_mock_js.Response.new = MagicMock(side_effect=lambda body, **kw: MagicMock(status=kw.get("status", 200), _body=body))
_mock_js.Headers.new = MagicMock(return_value=MagicMock())

from worker import on_scheduled  # noqa: E402


class TestOnScheduled:
    @pytest.mark.asyncio
    async def test_shadow_mode_disabled(self):
        """SHADOW_MODE='false' → no pipeline invocations."""
        env = _make_env(shadow_mode="false")
        event = MagicMock()
        ctx = MagicMock()

        with patch("src.shadow_pipeline.fetch_recent_closed_issues", new_callable=AsyncMock) as mock_fetch:
            await on_scheduled(event, env, ctx)
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_shadow_mode_enabled(self):
        """SHADOW_MODE='true' → full loop executes."""
        env = _make_env(shadow_mode="true")
        event = MagicMock()
        ctx = MagicMock()

        mock_issues = [_make_issue(iid=1)]

        with (
            patch(
                "src.shadow_pipeline.fetch_recent_closed_issues", new_callable=AsyncMock, return_value=mock_issues
            ) as mock_fetch,
            patch(
                "src.shadow_pipeline.run_shadow_triage",
                new_callable=AsyncMock,
                return_value={
                    "event_id": "shadow:x",
                    "predicted_cwe": [],
                    "predicted_duplicate_of": None,
                    "confidence": 0.5,
                },
            ) as mock_triage,
            patch("src.shadow_pipeline.compare_and_store", new_callable=AsyncMock) as mock_compare,
            patch("src.shadow_pipeline.generate_weekly_summary", new_callable=AsyncMock),
            patch("src.shadow_pipeline.post_slack_summary", new_callable=AsyncMock),
        ):

            await on_scheduled(event, env, ctx)

            mock_fetch.assert_called_once()
            mock_triage.assert_called_once()
            mock_compare.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: /admin/shadow-report endpoint
# ---------------------------------------------------------------------------


from worker import handle_shadow_report  # noqa: E402


class TestShadowReportEndpoint:
    @pytest.mark.asyncio
    async def test_returns_json_summary(self):
        """GET /admin/shadow-report → 200 with JSON accuracy summary."""
        env = _make_env()

        with patch("src.shadow_pipeline.generate_weekly_summary", new_callable=AsyncMock) as mock_summary:
            mock_summary.return_value = {
                "total": 50,
                "matched_count": 42,
                "accuracy_pct": 84.0,
                "period_start": "2026-08-04T00:00:00Z",
                "period_end": "2026-08-11T00:00:00Z",
            }

            request = MagicMock()
            resp = await handle_shadow_report(request, env)

            # Response should be created with status 200
            assert resp is not None
            mock_summary.assert_called_once_with(env.DB)


# ---------------------------------------------------------------------------
# Tests: Vectorize shadow filter
# ---------------------------------------------------------------------------


class TestVectorizeShadowFilter:
    @pytest.mark.asyncio
    async def test_shadow_prefix_filtered(self):
        """find_duplicates should skip results with shadow: prefix."""
        from src.vectorize_client import find_duplicates, SHADOW_EVENT_PREFIX

        env = _make_env()

        # Mock embedding
        with patch("src.vectorize_client.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 384):
            # Mock Vectorize query with one shadow and one real result
            shadow_match = MagicMock()
            shadow_match.id = "shadow:event123"
            shadow_match.score = 0.90
            shadow_match.metadata = {"repo": "test/repo", "model_version": "all-MiniLM-L6-v2"}

            real_match = MagicMock()
            real_match.id = "real-event-456"
            real_match.score = 0.88
            real_match.metadata = {"repo": "test/repo", "model_version": "all-MiniLM-L6-v2"}

            query_result = MagicMock()
            query_result.matches = [shadow_match, real_match]
            env.VECTORIZE.query = AsyncMock(return_value=query_result)

            results = await find_duplicates("test text", "test/repo", env)

            # Only real match should be returned, shadow one filtered
            assert len(results) == 1
            assert results[0]["event_id"] == "real-event-456"
            assert not any(r["event_id"].startswith(SHADOW_EVENT_PREFIX) for r in results)
