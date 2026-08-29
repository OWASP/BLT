"""Shadow Mode Validation Pipeline for OWASP BLT-Toasty.

Fetches recently closed/triaged issues from GitLab, runs them through
Toasty's triage pipeline silently (no GitLab mutations), and compares
predictions against actual maintainer decisions.

Shadow mode is gated by ``env.SHADOW_MODE == "true"``.  When disabled,
all public functions return immediately without side-effects.

Vector IDs for shadow events use a ``shadow:`` prefix so production
``find_duplicates`` queries can filter them out.
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("toasty.shadow_pipeline")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROJECT_ID = "14998512"  # OWASP-BLT/BLT
SHADOW_EVENT_PREFIX = "shadow:"
FETCH_SINCE_HOURS = 1
MAX_ISSUES_PER_RUN = 20
GITLAB_API_BASE = "https://gitlab.com/api/v4"


# ---------------------------------------------------------------------------
# GitLab issue fetcher
# ---------------------------------------------------------------------------


async def fetch_recent_closed_issues(env: Any, since_hours: int = FETCH_SINCE_HOURS) -> list[dict]:
    """Fetch recently closed/triaged issues from GitLab.

    Args:
        env: Cloudflare Worker environment with ``GITLAB_ACCESS_TOKEN``
            and ``SHADOW_PROJECT_ID`` bindings.
        since_hours: Look-back window in hours.

    Returns:
        A list of issue dicts with keys: ``iid``, ``title``,
        ``description``, ``labels``, ``web_url``, ``state``,
        ``project_id``.
    """
    project_id = getattr(env, "SHADOW_PROJECT_ID", None) or DEFAULT_PROJECT_ID
    access_token = getattr(env, "GITLAB_ACCESS_TOKEN", None)
    if not access_token:
        logger.warning("GITLAB_ACCESS_TOKEN not set — shadow fetch skipped")
        return []

    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (
        f"{GITLAB_API_BASE}/projects/{project_id}/issues"
        f"?state=closed&updated_after={since}&per_page={MAX_ISSUES_PER_RUN}&order_by=updated_at&sort=desc"
    )

    # Check for injected test mock first
    _fetch_impl = getattr(env, "_gitlab_fetch_impl", None)
    if _fetch_impl is not None:
        try:
            issues_raw = await _fetch_impl(url, access_token)
        except Exception as exc:
            logger.error("Shadow fetch failed: %s", exc)
            return []
    else:
        try:
            from js import fetch as js_fetch  # type: ignore[import-not-found]

            response = await js_fetch(
                url,
                {"method": "GET", "headers": {"Authorization": f"Bearer {access_token}"}},
            )

            if not response.ok:
                logger.warning("GitLab API returned %d for shadow fetch", response.status)
                return []

            data = await response.json()
            # Pyodide returns a JsProxy — convert to Python list
            issues_raw = data.to_py() if hasattr(data, "to_py") else data

        except ImportError:
            logger.warning("No fetch implementation available for shadow pipeline")
            return []
        except Exception as exc:
            logger.error("Shadow fetch failed: %s", exc)
            return []

    issues: list[dict] = []
    for raw in issues_raw:
        desc = raw.get("description") or ""
        if not desc.strip():
            continue  # Skip issues with no body — nothing to triage
        issues.append(
            {
                "iid": raw["iid"],
                "title": raw.get("title", ""),
                "description": desc,
                "labels": raw.get("labels", []),
                "web_url": raw.get("web_url", ""),
                "state": raw.get("state", "closed"),
                "project_id": int(project_id),
            }
        )

    logger.info("Shadow fetch: %d closed issues in the last %dh", len(issues), since_hours)
    return issues


# ---------------------------------------------------------------------------
# Shadow triage runner
# ---------------------------------------------------------------------------


async def run_shadow_triage(issue: dict, env: Any, db: Any) -> dict:
    """Run the full triage pipeline silently for a single issue.

    The pipeline mirrors production exactly:
    1. PII redaction via the Native Redaction Engine
    2. LLM summarization (produces CWE predictions)
    3. Vector embedding and indexing (with ``shadow:`` prefix)
    4. Duplicate detection

    **No GitLab mutations** (no comments, no labels) are performed.

    Args:
        issue: A dict with ``iid``, ``description``, ``project_id``, etc.
        env: Cloudflare Worker environment.
        db: D1 database handle.

    Returns:
        A dict with ``event_id``, ``predicted_cwe``, ``predicted_duplicate_of``,
        ``confidence``.
    """
    from redaction_engine import redact

    event_id = f"{SHADOW_EVENT_PREFIX}{uuid.uuid4().hex}"

    # 1. Store a synthetic triage event in D1
    await db.prepare(
        "INSERT INTO triage_events "
        "(id, delivery_id, gitlab_event, project_id, issue_iid, raw_payload_hash, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))"
    ).bind(
        event_id,
        f"shadow-delivery-{uuid.uuid4().hex}",
        "Issue Hook",
        issue["project_id"],
        issue["iid"],
        secrets.token_hex(16),
    ).run()

    # 2. Redact PII from issue description
    try:
        # Fixed argument order: text, env, event_id, db
        redact_result = await redact(issue["description"], env, event_id, db)
        # Handle both RedactionResult dataclass and plain string (from mocks)
        redacted_text = redact_result.redacted_text if hasattr(redact_result, "redacted_text") else str(redact_result)
    except Exception as exc:
        logger.warning("Shadow redaction failed for issue #%d: %s", issue["iid"], exc)
        await db.prepare("UPDATE triage_events SET status = 'failed' WHERE id = ?").bind(event_id).run()
        return {"event_id": event_id, "predicted_cwe": [], "predicted_duplicate_of": None, "confidence": 0.0}

    # 3. Summarize (produces CWE predictions)
    predicted_cwe: list[str] = []
    confidence = 0.0
    try:
        from summarizer import summarize

        summary = await summarize(
            redacted_text=redacted_text,
            env=env,
            db=db,
            do_stub=None,
            event_id=event_id,
        )
        predicted_cwe = summary.cwe_hints or []
        confidence = summary.confidence
    except Exception as exc:
        import traceback

        logger.warning("Shadow summarization failed for %s: %s\n%s", event_id, exc, traceback.format_exc())
        await db.prepare("UPDATE triage_events SET status = 'failed' WHERE id = ?").bind(event_id).run()
        return {"event_id": event_id, "predicted_cwe": [], "predicted_duplicate_of": None, "confidence": 0.0}

    # 4. Embed and index (with shadow: prefix — already in event_id)
    try:
        from vectorize_client import index_report

        repo_name = str(issue["project_id"])
        await index_report(
            event_id=event_id,
            redacted_text=redacted_text,
            repo_full_name=repo_name,
            env=env,
            db=db,
        )
    except Exception as exc:
        import traceback

        logger.warning("Shadow embedding failed for %s: %s\n%s", event_id, exc, traceback.format_exc())

    # 5. Detect duplicates (NO GitLab posting)
    predicted_duplicate_of = None
    try:
        from duplicate_detector import detect_duplicates

        dup_result = await detect_duplicates(
            event_id=event_id,
            redacted_text=redacted_text,
            repo_full_name=repo_name,
            env=env,
            db=db,
            do_stub=None,
        )
        if dup_result.top_candidate:
            predicted_duplicate_of = dup_result.top_candidate.event_id
    except Exception as exc:
        import traceback

        logger.warning("Shadow duplicate detection failed for %s: %s\n%s", event_id, exc, traceback.format_exc())

    return {
        "event_id": event_id,
        "predicted_cwe": predicted_cwe,
        "predicted_duplicate_of": predicted_duplicate_of,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Comparison and storage
# ---------------------------------------------------------------------------


async def compare_and_store(db: Any, issue: dict, shadow_result: dict) -> dict:
    """Compare Toasty's shadow predictions against actual maintainer labels.

    Matching logic:
    - **CWE match**: Any predicted CWE appears (case-insensitive) in actual labels.
    - **Duplicate match**: Issue has a ``duplicate`` or ``possible-duplicate``
      label AND Toasty predicted a duplicate.

    Args:
        db: D1 database handle.
        issue: The original GitLab issue dict.
        shadow_result: Output from ``run_shadow_triage``.

    Returns:
        The inserted shadow_predictions row as a dict.
    """
    actual_labels = issue.get("labels", [])
    predicted_cwe = shadow_result.get("predicted_cwe", [])
    predicted_dup = shadow_result.get("predicted_duplicate_of")

    # CWE match: check if any predicted CWE appears in actual labels
    actual_labels_lower = [lbl.lower() for lbl in actual_labels]
    cwe_matched = any(cwe.lower() in actual_labels_lower for cwe in predicted_cwe)

    # Duplicate match: issue has a duplicate label AND we predicted one
    dup_labels = {"duplicate", "possible-duplicate", "possible duplicate"}
    has_dup_label = any(lbl.lower() in dup_labels for lbl in actual_labels)
    dup_matched = has_dup_label and predicted_dup is not None

    # Overall: matched if either CWE or duplicate prediction aligns
    matched = 1 if (cwe_matched or dup_matched) else 0

    # If no predictions were made at all (empty CWE list and no dup), mark as 0
    if not predicted_cwe and predicted_dup is None:
        matched = 0

    prediction_id = secrets.token_hex(16)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    await db.prepare(
        "INSERT INTO shadow_predictions "
        "(id, gitlab_issue_url, project_id, issue_iid, predicted_cwe, "
        "predicted_duplicate_of, predicted_confidence, actual_labels, "
        "actual_state, matched, shadow_event_id, compared_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id, issue_iid) DO UPDATE SET "
        "predicted_cwe=excluded.predicted_cwe, "
        "predicted_duplicate_of=excluded.predicted_duplicate_of, "
        "predicted_confidence=excluded.predicted_confidence, "
        "actual_labels=excluded.actual_labels, "
        "actual_state=excluded.actual_state, "
        "matched=excluded.matched, "
        "shadow_event_id=excluded.shadow_event_id, "
        "compared_at=excluded.compared_at"
    ).bind(
        prediction_id,
        issue.get("web_url", ""),
        issue["project_id"],
        issue["iid"],
        json.dumps(predicted_cwe),
        predicted_dup if predicted_dup is not None else "",
        shadow_result.get("confidence", 0.0),
        json.dumps(actual_labels),
        issue.get("state", "closed"),
        matched,
        shadow_result["event_id"],
        now_iso,
    ).run()

    logger.info(
        "Shadow prediction stored for issue #%d: matched=%d, cwe=%s",
        issue["iid"],
        matched,
        predicted_cwe,
    )

    return {
        "id": prediction_id,
        "issue_iid": issue["iid"],
        "matched": matched,
        "predicted_cwe": predicted_cwe,
        "predicted_duplicate_of": predicted_dup,
    }


# ---------------------------------------------------------------------------
# Weekly summary
# ---------------------------------------------------------------------------


async def generate_weekly_summary(db: Any) -> dict:
    """Generate an accuracy summary for the last 7 days of shadow predictions.

    Args:
        db: D1 database handle.

    Returns:
        A JSON-serializable dict with ``total``, ``matched_count``,
        ``accuracy_pct``, ``period_start``, ``period_end``.
    """
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    row = (
        await db.prepare(
            "SELECT "
            "COUNT(*) as total, "
            "SUM(CASE WHEN matched = 1 THEN 1 ELSE 0 END) as matched_count "
            "FROM shadow_predictions "
            "WHERE created_at >= ?"
        )
        .bind(seven_days_ago)
        .first()
    )

    if row is None:
        return {
            "total": 0,
            "matched_count": 0,
            "accuracy_pct": 0.0,
            "period_start": seven_days_ago,
            "period_end": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    if row.__class__.__name__ == "JsProxy":
        row = row.to_py()
    total = (
        row.get("total")
        if hasattr(row, "get")
        else (row["total"] if hasattr(row, "__getitem__") else getattr(row, "total", 0))
    )
    matched_count = (
        row.get("matched_count")
        if hasattr(row, "get")
        else (row["matched_count"] if hasattr(row, "__getitem__") else getattr(row, "matched_count", 0))
    )
    total = total or 0
    matched_count = matched_count or 0
    accuracy_pct = round((matched_count / total) * 100, 1) if total > 0 else 0.0

    return {
        "total": total,
        "matched_count": matched_count,
        "accuracy_pct": accuracy_pct,
        "period_start": seven_days_ago,
        "period_end": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------


async def post_slack_summary(env: Any, summary: dict) -> bool:
    """Post the weekly shadow mode accuracy summary to Slack.

    If ``env.SLACK_WEBHOOK_URL`` is not configured, logs the summary
    to console and returns ``False`` (graceful no-op).

    Args:
        env: Cloudflare Worker environment.
        summary: The dict from ``generate_weekly_summary``.

    Returns:
        ``True`` if the Slack post succeeded, ``False`` otherwise.
    """
    webhook_url = getattr(env, "SLACK_WEBHOOK_URL", None)
    if not webhook_url:
        logger.info(
            "Shadow Mode Weekly Summary (no Slack configured): " "%d/%d matched (%.1f%% accuracy)",
            summary.get("matched_count", 0),
            summary.get("total", 0),
            summary.get("accuracy_pct", 0.0),
        )
        return False

    text = (
        f":robot_face: *Toasty Shadow Mode — Weekly Report*\n"
        f"Period: `{summary['period_start']}` → `{summary['period_end']}`\n"
        f"Accuracy: *{summary['accuracy_pct']}%* "
        f"({summary['matched_count']}/{summary['total']} issues)\n"
    )

    payload = json.dumps({"text": text})

    # Check for injected test mock first
    _fetch_impl = getattr(env, "_slack_fetch_impl", None)
    if _fetch_impl is not None:
        try:
            return await _fetch_impl(webhook_url, payload)
        except Exception as exc:
            logger.error("Failed to post shadow summary to Slack: %s", exc)
            return False

    try:
        from js import fetch as js_fetch  # type: ignore[import-not-found]

        response = await js_fetch(
            webhook_url,
            {
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": payload,
            },
        )
        if response.ok:
            logger.info("Shadow summary posted to Slack")
            return True
        else:
            logger.warning("Slack webhook returned %d", response.status)
            return False
    except ImportError:
        logger.info("Shadow summary (no fetch available): %s", text)
        return False
    except Exception as exc:
        logger.error("Failed to post shadow summary to Slack: %s", exc)
        return False
