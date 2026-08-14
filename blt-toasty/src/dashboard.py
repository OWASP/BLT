from datetime import datetime, timezone
from typing import Any


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
    total_events_res = await db.prepare("SELECT COUNT(*) as count FROM triage_events").first()
    total_events = total_events_res.get("count", 0) if total_events_res else 0

    # Events this month
    month_res = await db.prepare(
        "SELECT COUNT(*) as count FROM triage_events WHERE created_at >= date('now', 'start of month')"
    ).first()
    events_this_month = month_res.get("count", 0) if month_res else 0

    # Status distribution
    status_res = await db.prepare("SELECT status, COUNT(*) as count FROM triage_events GROUP BY status").all()
    events_by_status = {}
    if status_res and hasattr(status_res, "results"):
        for row in status_res.results:
            events_by_status[row["status"]] = row["count"]

    quarantined = events_by_status.get("quarantined", 0)
    quarantine_rate_pct = round((quarantined / total_events * 100) if total_events > 0 else 0.0, 2)

    # Average latency (seconds) for exported events
    latency_res = await db.prepare(
        "SELECT AVG((julianday(updated_at) - julianday(created_at)) * 86400) as avg_lat "
        "FROM triage_events WHERE status = 'exported'"
    ).first()
    avg_latency_seconds = round(latency_res.get("avg_lat") or 0.0, 2) if latency_res else 0.0

    # 2. Redaction Metrics (redaction_audit)
    pii_total_res = await db.prepare("SELECT COUNT(*) as count FROM redaction_audit").first()
    total_pii_entities = pii_total_res.get("count", 0) if pii_total_res else 0

    avg_pii_per_event = round((total_pii_entities / total_events) if total_events > 0 else 0.0, 2)

    pii_type_res = await db.prepare(
        "SELECT entity_type, COUNT(*) as count FROM redaction_audit GROUP BY entity_type"
    ).all()
    entities_by_type = {}
    if pii_type_res and hasattr(pii_type_res, "results"):
        for row in pii_type_res.results:
            entities_by_type[row["entity_type"]] = row["count"]

    # 3. Duplicate Candidates (duplicate_candidates)
    dup_total_res = await db.prepare("SELECT COUNT(*) as count FROM duplicate_candidates").first()
    total_candidates = dup_total_res.get("count", 0) if dup_total_res else 0

    # Duplicate rate (% of exported events that had at least one candidate)
    exported_count = events_by_status.get("exported", 0)
    dup_events_res = await db.prepare(
        "SELECT COUNT(DISTINCT triage_event_id) as count FROM duplicate_candidates dc "
        "JOIN triage_events te ON dc.triage_event_id = te.id "
        "WHERE te.status = 'exported'"
    ).first()
    dup_events_count = dup_events_res.get("count", 0) if dup_events_res else 0
    duplicate_rate_pct = round((dup_events_count / exported_count * 100) if exported_count > 0 else 0.0, 2)

    dup_method_res = await db.prepare(
        "SELECT detection_method, COUNT(*) as count FROM duplicate_candidates GROUP BY detection_method"
    ).all()
    by_method = {}
    if dup_method_res and hasattr(dup_method_res, "results"):
        for row in dup_method_res.results:
            by_method[row["detection_method"]] = row["count"]

    # 4. LLM / Summarizer Metrics (triage_summaries)
    llm_tokens_res = await db.prepare(
        "SELECT SUM(prompt_tokens) as p_tok, SUM(completion_tokens) as c_tok FROM triage_summaries"
    ).first()
    total_prompt_tokens = llm_tokens_res.get("p_tok") or 0 if llm_tokens_res else 0
    total_completion_tokens = llm_tokens_res.get("c_tok") or 0 if llm_tokens_res else 0

    model_usage_res = await db.prepare(
        "SELECT model_used, COUNT(*) as count FROM triage_summaries GROUP BY model_used"
    ).all()
    model_usage = {}
    if model_usage_res and hasattr(model_usage_res, "results"):
        for row in model_usage_res.results:
            model_usage[row["model_used"]] = row["count"]

    # 5. Shadow Validation Pipeline Accuracy (shadow_predictions)
    shadow_accuracy = {"total": 0, "matched": 0, "accuracy_pct": 0.0}
    try:
        shadow_res = await db.prepare(
            "SELECT COUNT(*) as total, SUM(CASE WHEN matched = 1 THEN 1 ELSE 0 END) as matched "
            "FROM shadow_predictions WHERE matched IS NOT NULL"
        ).first()
        if shadow_res:
            s_total = shadow_res.get("total", 0)
            s_matched = shadow_res.get("matched") or 0
            shadow_accuracy["total"] = s_total
            shadow_accuracy["matched"] = s_matched
            shadow_accuracy["accuracy_pct"] = round((s_matched / s_total * 100) if s_total > 0 else 0.0, 2)
    except Exception:
        # Table might not exist yet if shadow mode isn't fully merged/deployed in upstream/main
        pass  # nosec B110

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
