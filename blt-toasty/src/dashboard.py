from datetime import datetime, timezone
from typing import Any


def _get(row, key, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    if hasattr(row, key):
        val = getattr(row, key)
        return val if val is not None else default
    if hasattr(row, "__getitem__"):
        try:
            val = row[key]
            return val if val is not None else default
        except Exception:
            pass  # nosec B110
    return default


async def aggregate_dashboard(db: Any) -> dict:
    """
    Generate the insights dashboard aggregating data from D1 tables.

    Args:
        db: The D1 database binding.

    Returns:
        dict: The dashboard summary data.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Pipeline Metrics (triage_events)
    # Total events
    total_events_res = await db.prepare(
        "SELECT COUNT(*) as count FROM triage_events WHERE id NOT LIKE 'shadow:%'"
    ).first()
    total_events = _get(total_events_res, "count", 0)

    # Events this month
    month_res = await db.prepare(
        "SELECT COUNT(*) as count FROM triage_events WHERE created_at >= date('now', 'start of month') AND id NOT LIKE 'shadow:%'"
    ).first()
    events_this_month = _get(month_res, "count", 0)

    # Status distribution
    status_res = await db.prepare(
        "SELECT status, COUNT(*) as count FROM triage_events WHERE id NOT LIKE 'shadow:%' GROUP BY status"
    ).all()
    events_by_status = {}
    if status_res and hasattr(status_res, "results"):
        for row in status_res.results:
            events_by_status[_get(row, "status")] = _get(row, "count", 0)

    quarantined = events_by_status.get("quarantined", 0)
    quarantine_rate_pct = round((quarantined / total_events * 100) if total_events > 0 else 0.0, 2)

    # Average latency (seconds) for exported events
    latency_res = await db.prepare(
        "SELECT AVG((julianday(updated_at) - julianday(created_at)) * 86400) as avg_lat "
        "FROM triage_events WHERE status = 'exported' AND id NOT LIKE 'shadow:%'"
    ).first()
    avg_latency_seconds = round(_get(latency_res, "avg_lat", 0.0), 2)

    # 2. Redaction Metrics (redaction_audit)
    pii_total_res = await db.prepare(
        "SELECT COUNT(*) as count FROM redaction_audit WHERE triage_event_id NOT LIKE 'shadow:%'"
    ).first()
    total_pii_entities = _get(pii_total_res, "count", 0)

    avg_pii_per_event = round((total_pii_entities / total_events) if total_events > 0 else 0.0, 2)

    pii_type_res = await db.prepare(
        "SELECT entity_type, COUNT(*) as count FROM redaction_audit WHERE triage_event_id NOT LIKE 'shadow:%' GROUP BY entity_type"
    ).all()
    entities_by_type = {}
    if pii_type_res and hasattr(pii_type_res, "results"):
        for row in pii_type_res.results:
            entities_by_type[_get(row, "entity_type")] = _get(row, "count", 0)

    # 3. Duplicate Candidates (duplicate_candidates)
    dup_total_res = await db.prepare(
        "SELECT COUNT(*) as count FROM duplicate_candidates WHERE triage_event_id NOT LIKE 'shadow:%'"
    ).first()
    total_candidates = _get(dup_total_res, "count", 0)

    # Duplicate rate (% of exported events that had at least one candidate)
    exported_count = events_by_status.get("exported", 0)
    dup_events_res = await db.prepare(
        "SELECT COUNT(DISTINCT triage_event_id) as count FROM duplicate_candidates dc "
        "JOIN triage_events te ON dc.triage_event_id = te.id "
        "WHERE te.status = 'exported' AND te.id NOT LIKE 'shadow:%'"
    ).first()
    dup_events_count = _get(dup_events_res, "count", 0)
    duplicate_rate_pct = round((dup_events_count / exported_count * 100) if exported_count > 0 else 0.0, 2)

    dup_method_res = await db.prepare(
        "SELECT detection_method, COUNT(*) as count FROM duplicate_candidates WHERE triage_event_id NOT LIKE 'shadow:%' GROUP BY detection_method"
    ).all()
    by_method = {}
    if dup_method_res and hasattr(dup_method_res, "results"):
        for row in dup_method_res.results:
            by_method[_get(row, "detection_method")] = _get(row, "count", 0)

    # 4. LLM / Summarizer Metrics (triage_summaries)
    llm_tokens_res = await db.prepare(
        "SELECT SUM(prompt_tokens) as p_tok, SUM(completion_tokens) as c_tok FROM triage_summaries WHERE triage_event_id NOT LIKE 'shadow:%'"
    ).first()
    total_prompt_tokens = _get(llm_tokens_res, "p_tok", 0)
    total_completion_tokens = _get(llm_tokens_res, "c_tok", 0)

    model_usage_res = await db.prepare(
        "SELECT model_used, COUNT(*) as count FROM triage_summaries WHERE triage_event_id NOT LIKE 'shadow:%' GROUP BY model_used"
    ).all()
    model_usage = {}
    if model_usage_res and hasattr(model_usage_res, "results"):
        for row in model_usage_res.results:
            model_usage[_get(row, "model_used")] = _get(row, "count", 0)

    # 5. Shadow Validation Pipeline Accuracy (shadow_predictions)
    shadow_accuracy = {"total": 0, "matched": 0, "accuracy_pct": 0.0}
    try:
        shadow_res = await db.prepare(
            "SELECT COUNT(*) as total, SUM(CASE WHEN matched = 1 THEN 1 ELSE 0 END) as matched "
            "FROM shadow_predictions WHERE matched IS NOT NULL"
        ).first()
        if shadow_res:
            s_total = _get(shadow_res, "total", 0)
            s_matched = _get(shadow_res, "matched", 0)
            shadow_accuracy["total"] = s_total
            shadow_accuracy["matched"] = s_matched
            shadow_accuracy["accuracy_pct"] = round((s_matched / s_total * 100) if s_total > 0 else 0.0, 2)
    except Exception as e:
        # Table might not exist yet if shadow mode isn't fully merged/deployed in upstream/main
        if "no such table" in str(e):
            pass  # nosec B110
        else:
            raise

    return {
        "generated_at": now_iso,
        "pipeline": {
            "total_events": total_events,
            "events_this_month": events_this_month,
            "events_by_status": events_by_status,
            "quarantine_rate_pct": quarantine_rate_pct,
            "avg_latency_seconds": avg_latency_seconds,
        },
        "redaction": {
            "total_pii_entities": total_pii_entities,
            "avg_pii_per_event": avg_pii_per_event,
            "entities_by_type": entities_by_type,
        },
        "duplicates": {
            "total_candidates": total_candidates,
            "duplicate_rate_pct": duplicate_rate_pct,
            "by_method": by_method,
        },
        "llm": {
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "model_usage": model_usage,
        },
        "shadow_accuracy": shadow_accuracy,
    }
