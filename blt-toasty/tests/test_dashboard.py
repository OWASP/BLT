import pytest
from unittest.mock import MagicMock, AsyncMock
from src.dashboard import aggregate_dashboard


@pytest.fixture
def mock_db():
    db = MagicMock()

    def prepare_side_effect(sql):
        stmt = MagicMock()

        if "FROM triage_events WHERE status = 'exported'" in sql:
            stmt.first = AsyncMock(return_value={"avg_lat": 10.5})
        elif "FROM triage_events WHERE created_at >=" in sql:
            stmt.first = AsyncMock(return_value={"count": 50})
        elif "GROUP BY status" in sql:
            stmt.all = AsyncMock(
                return_value=MagicMock(
                    results=[{"status": "exported", "count": 100}, {"status": "quarantined", "count": 5}]
                )
            )
        elif "FROM triage_events" in sql:
            stmt.first = AsyncMock(return_value={"count": 200})

        elif "GROUP BY entity_type" in sql:
            stmt.all = AsyncMock(return_value=MagicMock(results=[{"entity_type": "EMAIL_ADDRESS", "count": 150}]))
        elif "FROM redaction_audit" in sql:
            stmt.first = AsyncMock(return_value={"count": 300})

        elif "FROM duplicate_candidates dc JOIN triage_events te" in sql:
            stmt.first = AsyncMock(return_value={"count": 20})
        elif "GROUP BY detection_method" in sql:
            stmt.all = AsyncMock(return_value=MagicMock(results=[{"detection_method": "retrieval_only", "count": 40}]))
        elif "FROM duplicate_candidates" in sql:
            stmt.first = AsyncMock(return_value={"count": 50})

        elif "GROUP BY model_used" in sql:
            stmt.all = AsyncMock(return_value=MagicMock(results=[{"model_used": "gpt-4o-mini", "count": 100}]))
        elif "FROM triage_summaries" in sql:
            stmt.first = AsyncMock(return_value={"p_tok": 10000, "c_tok": 2000})

        elif "FROM shadow_predictions" in sql:
            stmt.first = AsyncMock(return_value={"total": 10, "matched": 8})

        return stmt

    db.prepare = MagicMock(side_effect=prepare_side_effect)
    return db


@pytest.mark.asyncio
async def test_aggregate_dashboard(mock_db):
    result = await aggregate_dashboard(mock_db)

    assert "generated_at" in result

    # Pipeline
    assert result["pipeline"]["total_events"] == 200
    assert result["pipeline"]["events_this_month"] == 50
    assert result["pipeline"]["events_by_status"]["exported"] == 100
    assert result["pipeline"]["quarantine_rate_pct"] == 2.5
    assert result["pipeline"]["avg_latency_seconds"] == 10.5

    # Redaction
    assert result["redaction"]["total_pii_entities"] == 300
    assert result["redaction"]["avg_pii_per_event"] == 1.5
    assert result["redaction"]["entities_by_type"]["EMAIL_ADDRESS"] == 150

    # Duplicates
    assert result["duplicates"]["total_candidates"] == 50
    assert result["duplicates"]["duplicate_rate_pct"] == 20.0
    assert result["duplicates"]["by_method"]["retrieval_only"] == 40

    # LLM
    assert result["llm"]["total_prompt_tokens"] == 10000
    assert result["llm"]["total_completion_tokens"] == 2000
    assert result["llm"]["model_usage"]["gpt-4o-mini"] == 100

    # Shadow Accuracy
    assert result["shadow_accuracy"]["total"] == 10
    assert result["shadow_accuracy"]["matched"] == 8
    assert result["shadow_accuracy"]["accuracy_pct"] == 80.0


@pytest.mark.asyncio
async def test_aggregate_dashboard_empty_db(mock_db):
    # Override mock to return empty/null values for a fresh DB
    def empty_prepare_side_effect(sql):
        stmt = MagicMock()
        stmt.first = AsyncMock(return_value=None)
        stmt.all = AsyncMock(return_value=MagicMock(results=[]))
        return stmt

    mock_db.prepare.side_effect = empty_prepare_side_effect

    result = await aggregate_dashboard(mock_db)

    assert result["pipeline"]["total_events"] == 0
    assert result["pipeline"]["quarantine_rate_pct"] == 0.0
    assert result["pipeline"]["avg_latency_seconds"] == 0.0
    assert result["redaction"]["avg_pii_per_event"] == 0.0
    assert result["duplicates"]["duplicate_rate_pct"] == 0.0
    assert result["shadow_accuracy"]["accuracy_pct"] == 0.0


@pytest.mark.asyncio
async def test_aggregate_dashboard_no_shadow_table(mock_db):
    # Override only shadow_predictions to throw exception (simulating missing table)
    original_prepare = mock_db.prepare.side_effect

    def side_effect(sql):
        if "shadow_predictions" in sql:
            stmt = MagicMock()
            stmt.first = AsyncMock(side_effect=Exception("no such table"))
            return stmt
        return original_prepare(sql)

    mock_db.prepare.side_effect = side_effect

    result = await aggregate_dashboard(mock_db)

    assert result["shadow_accuracy"]["total"] == 0
    assert result["shadow_accuracy"]["matched"] == 0
    assert result["shadow_accuracy"]["accuracy_pct"] == 0.0
    # Other metrics should still be intact
    assert result["pipeline"]["total_events"] == 200


@pytest.mark.asyncio
async def test_aggregate_dashboard_database_failure(mock_db):
    # Simulate a generic D1 failure on a normal query
    def side_effect(sql):
        stmt = MagicMock()
        stmt.first = AsyncMock(side_effect=Exception("D1 Error: Internal Server Error"))
        return stmt

    mock_db.prepare.side_effect = side_effect

    with pytest.raises(Exception, match="D1 Error: Internal Server Error"):
        await aggregate_dashboard(mock_db)
