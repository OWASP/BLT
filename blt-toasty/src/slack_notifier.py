"""
Slack notifications for finished Toasty triage.

Posts a Block Kit message to a Slack incoming webhook when an event finishes
triage (after duplicate detection) or is quarantined.  The message carries
only triage metadata: the issue number, CWE classification, a severity tier
derived from the CWE, whether the event was quarantined, and duplicate
findings.  It never includes the issue title, body, summary or evidence
snippets, so unredacted text cannot reach Slack.

Runtime notes
-------------
* Uses the Workers ``fetch`` (``from js import fetch``) and reads the webhook
  URL from the ``SLACK_WEBHOOK_URL`` secret on ``env``.  Under CPython
  (pytest) ``fetch`` is ``None`` and tests inject a mock via ``env._fetch``.
* The timeout is ``AbortSignal.timeout``, which runs entirely in JS.  A Python
  ``setTimeout`` callback would be a borrowed proxy that Pyodide destroys
  when ``setTimeout`` returns, so the abort would never fire.
* Notifications are best effort: a missing webhook URL skips silently, and
  any delivery error is logged and swallowed so triage never fails because
  Slack is down.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from forge_links import issue_url
from rationale_builder import CWE_LABELS

logger = logging.getLogger("toasty.slack_notifier")

try:
    from js import fetch  # type: ignore[import-not-found]
except ImportError:
    fetch = None  # type: ignore[assignment]

SLACK_TIMEOUT_SECONDS = 5
MAX_DUPLICATES_SHOWN = 3

# Severity tier per CWE, roughly following the impact the weakness usually
# allows.  Unlisted CWEs fall back to "medium"; no CWE at all is "info".
SEVERITY_BY_CWE: dict[str, str] = {
    "CWE-77": "critical",
    "CWE-78": "critical",
    "CWE-89": "critical",
    "CWE-94": "critical",
    "CWE-502": "critical",
    "CWE-787": "critical",
    "CWE-416": "critical",
    "CWE-119": "high",
    "CWE-22": "high",
    "CWE-125": "high",
    "CWE-190": "high",
    "CWE-269": "high",
    "CWE-287": "high",
    "CWE-306": "high",
    "CWE-434": "high",
    "CWE-611": "high",
    "CWE-798": "high",
    "CWE-862": "high",
    "CWE-863": "high",
    "CWE-918": "high",
    "CWE-79": "medium",
    "CWE-200": "medium",
    "CWE-352": "medium",
    "CWE-362": "medium",
    "CWE-20": "medium",
    "CWE-116": "medium",
    "CWE-276": "medium",
    "CWE-476": "low",
    "CWE-UNKNOWN": "info",
}

_SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]
_SEVERITY_EMOJI = {
    "critical": ":red_circle:",
    "high": ":large_orange_circle:",
    "medium": ":large_yellow_circle:",
    "low": ":large_blue_circle:",
    "info": ":white_circle:",
}


def severity_for_cwes(cwe_ids: list[str]) -> str:
    """Return the highest severity tier among *cwe_ids*."""
    if not cwe_ids:
        return "info"
    tiers = [SEVERITY_BY_CWE.get(c, "medium") for c in cwe_ids]
    return max(tiers, key=_SEVERITY_ORDER.index)


def quarantine_category(reason: str | None) -> str:
    """Map a quarantine reason to a fixed category.

    The raw reason can embed exception text, so only the category is sent.
    """
    if not reason:
        return "unspecified"
    if reason.startswith(("Residual PII", "Entity ")):
        return "PII leak (redaction gate)"
    if reason.startswith("Unexpected error during redaction"):
        return "redaction error"
    return "other"


def build_payload(
    event_id: str,
    issue_iid: Any,
    cwe_ids: list[str],
    quarantined: bool,
    quarantine_reason: str | None = None,
    duplicates: list[dict] | None = None,
) -> dict:
    """Build the Slack Block Kit payload for one triage event.

    Args:
        event_id: The triage event ID.
        issue_iid: The forge issue number, or None.
        cwe_ids: CWE identifiers from the triage summary.
        quarantined: Whether the event was quarantined.
        quarantine_reason: Raw reason; only its category is sent.
        duplicates: Confirmed duplicate candidates as
            ``{"event_id": str, "score": float}`` dicts.

    Returns:
        A JSON-serialisable dict for the Slack webhook.
    """
    duplicates = duplicates or []
    severity = severity_for_cwes(cwe_ids)
    issue_ref = f"<{issue_url(issue_iid)}|#{issue_iid}>" if issue_iid else "unknown issue"
    headline = "Toasty quarantined an issue" if quarantined else "Toasty triaged an issue"

    cwe_text = ", ".join(f"{c} ({CWE_LABELS.get(c, 'Unknown')})" for c in cwe_ids) or "none"
    quarantine_text = f"yes ({quarantine_category(quarantine_reason)})" if quarantined else "no"
    if duplicates:
        dup_text = "\n".join(
            f"• `{d['event_id']}` (similarity {float(d['score']):.2f})" for d in duplicates[:MAX_DUPLICATES_SHOWN]
        )
    else:
        dup_text = "none"

    fields = [
        {"type": "mrkdwn", "text": f"*Issue*\n{issue_ref}"},
        {"type": "mrkdwn", "text": f"*Severity*\n{_SEVERITY_EMOJI[severity]} {severity}"},
        {"type": "mrkdwn", "text": f"*CWE*\n{cwe_text}"},
        {"type": "mrkdwn", "text": f"*Quarantined*\n{quarantine_text}"},
    ]

    return {
        "text": f"{headline}: {issue_ref} (severity {severity})",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": headline}},
            {"type": "section", "fields": fields},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Possible duplicates*\n{dup_text}"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Triage ID `{event_id}`"}]},
        ],
    }


def _row_get(row: Any, key: str) -> Any:
    if row is None:
        return None
    if hasattr(row, "to_py"):
        row = row.to_py()
    if hasattr(row, "get"):
        return row.get(key)
    return getattr(row, key, None)


async def _load_event_context(db: Any, event_id: str) -> tuple[Any, list[str], str | None]:
    """Read issue number, CWE hints and quarantine reason from D1."""
    event_row = (
        await db.prepare("SELECT issue_iid, quarantine_reason FROM triage_events WHERE id = ?").bind(event_id).first()
    )
    summary_row = (
        await db.prepare("SELECT cwe_hints FROM triage_summaries WHERE triage_event_id = ?").bind(event_id).first()
    )
    cwe_raw = _row_get(summary_row, "cwe_hints")
    try:
        cwe_ids = [c for c in json.loads(cwe_raw) if isinstance(c, str)] if cwe_raw else []
    except (TypeError, ValueError):
        cwe_ids = []
    return _row_get(event_row, "issue_iid"), cwe_ids, _row_get(event_row, "quarantine_reason")


async def post_to_slack(webhook_url: str, payload: dict, env: Any) -> bool:
    """POST *payload* to the Slack webhook. Returns True on a 2xx response."""
    _fetch = fetch or getattr(env, "_fetch", None)
    if _fetch is None:
        logger.warning("fetch unavailable; Slack notification skipped")
        return False

    options: Any = {
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }
    try:
        from js import AbortSignal, Object  # type: ignore[import-not-found]
        from pyodide.ffi import to_js  # type: ignore[import-not-found]

        options["signal"] = AbortSignal.timeout(SLACK_TIMEOUT_SECONDS * 1000)
        options = to_js(options, dict_converter=Object.fromEntries)
    except ImportError:
        pass  # CPython tests — the mock fetch takes the plain dict.

    response = await _fetch(webhook_url, options)
    ok = 200 <= int(response.status) < 300
    if not ok:
        logger.warning("Slack webhook returned HTTP %s", response.status)
    return ok


async def notify_triage(
    env: Any,
    db: Any,
    event_id: str,
    quarantined: bool = False,
    duplicates: list[dict] | None = None,
) -> bool:
    """Send the Slack notification for *event_id*. Never raises.

    Returns:
        True if Slack accepted the message, False if skipped or failed.
    """
    webhook_url = getattr(env, "SLACK_WEBHOOK_URL", None) if env is not None else None
    if not webhook_url or not isinstance(webhook_url, str):
        return False
    try:
        issue_iid, cwe_ids, reason = await _load_event_context(db, event_id)
        payload = build_payload(event_id, issue_iid, cwe_ids, quarantined, reason, duplicates)
        return await post_to_slack(webhook_url, payload, env)
    except Exception as exc:
        logger.error("Slack notification failed for %s: %s", event_id, type(exc).__name__)
        return False
