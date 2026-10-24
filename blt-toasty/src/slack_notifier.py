"""
Slack notifications for finished Toasty triage.

Posts a Block Kit message to a Slack incoming webhook when an event finishes
triage (after duplicate detection) or is quarantined.  The message carries
only triage metadata: the issue number, CWE classification, a severity,
whether the event was quarantined, and duplicate findings.  It never
includes the issue title, body, summary or evidence snippets, so unredacted
text cannot reach Slack.

Trust boundary
--------------
Every value interpolated into Slack mrkdwn is validated against its
expected format first (issue number, event IDs, CWE IDs, scores, severity
tiers); anything else is replaced by a fixed placeholder.  All interpolated
text is also escaped (``&``, ``<``, ``>``) so crafted input cannot form
Slack links, mentions or formatting.

Severity
--------
Unless the caller passes a validated ``assessed_severity``, the severity is
an estimate looked up from the CWE type and is labelled as such.  CWEs the
table does not know give "unrated, needs review" rather than a guessed tier.

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
import math
import re
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
MAX_CWES_SHOWN = 10
MAX_ISSUE_IID = 10**9

# Expected formats of everything interpolated into the message.  Event IDs
# are ``secrets.token_hex(16)``, optionally prefixed (``shadow:``).
_CWE_ID_RE = re.compile(r"^CWE-(?:[0-9]{1,5}|UNKNOWN)$")
_EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_:-]{1,64}$")

INVALID_ID = "[invalid id]"
UNRATED = "unrated"
ESTIMATE_NOTE = "Severity is estimated from the CWE type, not an assessment of this report."

# Estimated severity tier per CWE, from the impact the weakness usually
# allows.  It is a heuristic, not an assessment of a specific report: CWEs
# missing here are "unrated" and need review.
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
}

_SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]
_SEVERITY_EMOJI = {
    "critical": ":red_circle:",
    "high": ":large_orange_circle:",
    "medium": ":large_yellow_circle:",
    "low": ":large_blue_circle:",
    "info": ":white_circle:",
    UNRATED: ":grey_question:",
}


def severity_for_cwes(cwe_ids: list[str]) -> str:
    """Return the highest estimated tier among *cwe_ids*, or ``"unrated"``.

    Only CWEs in ``SEVERITY_BY_CWE`` count; with none of them the report is
    unrated and needs review.
    """
    tiers = [SEVERITY_BY_CWE[c] for c in cwe_ids if c in SEVERITY_BY_CWE]
    return max(tiers, key=_SEVERITY_ORDER.index) if tiers else UNRATED


def escape_mrkdwn(text: str) -> str:
    """Escape Slack's control characters so text cannot form links or mentions."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def safe_issue_iid(value: Any) -> int | None:
    """Return *value* as a positive issue number, or None if it is not one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    if isinstance(value, int) and 0 < value <= MAX_ISSUE_IID:
        return value
    return None


def safe_event_id(value: Any) -> str | None:
    """Return *value* if it looks like a triage event ID, else None."""
    if isinstance(value, str) and _EVENT_ID_RE.match(value):
        return value
    return None


def safe_cwe_ids(values: Any) -> list[str]:
    """Keep well-formed, distinct CWE IDs (``CWE-<digits>`` or ``CWE-UNKNOWN``)."""
    if not isinstance(values, (list, tuple)):
        return []
    seen: list[str] = []
    for v in values:
        if isinstance(v, str) and _CWE_ID_RE.match(v) and v not in seen:
            seen.append(v)
    return seen[:MAX_CWES_SHOWN]


def safe_score(value: Any) -> float | None:
    """Return *value* as a similarity score in [0, 1], or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    score = float(value)
    return score if math.isfinite(score) and 0.0 <= score <= 1.0 else None


def safe_severity(value: Any) -> str | None:
    """Return *value* if it is one of the known severity tiers, else None."""
    if isinstance(value, str) and value.lower() in _SEVERITY_ORDER:
        return value.lower()
    return None


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


def _id_text(value: Any) -> str:
    event_id = safe_event_id(value)
    return f"`{event_id}`" if event_id else INVALID_ID


def build_payload(
    event_id: str,
    issue_iid: Any,
    cwe_ids: list[str],
    quarantined: bool,
    quarantine_reason: str | None = None,
    duplicates: list[dict] | None = None,
    assessed_severity: str | None = None,
) -> dict:
    """Build the Slack Block Kit payload for one triage event.

    Every argument is untrusted: values that do not match their expected
    format are replaced by placeholders (see the module docstring).

    Args:
        event_id: The triage event ID.
        issue_iid: The forge issue number, or None.
        cwe_ids: CWE identifiers from the triage summary.
        quarantined: Whether the event was quarantined.
        quarantine_reason: Raw reason; only its category is sent.
        duplicates: Confirmed duplicate candidates as
            ``{"event_id": str, "score": float}`` dicts.
        assessed_severity: A severity tier assessed for this report by the
            triage pipeline.  When valid it is shown instead of the CWE
            estimate.

    Returns:
        A JSON-serialisable dict for the Slack webhook.
    """
    iid = safe_issue_iid(issue_iid)
    issue_ref = f"<{issue_url(iid)}|#{iid}>" if iid else "unknown issue"
    headline = "Toasty quarantined an issue" if quarantined else "Toasty triaged an issue"
    cwes = safe_cwe_ids(cwe_ids)

    assessed = safe_severity(assessed_severity)
    if assessed:
        severity, severity_label, summary_severity = assessed, "Severity (assessed)", f"severity {assessed}"
    else:
        severity = severity_for_cwes(cwes)
        severity_label = "Est. severity (from CWE type)"
        summary_severity = "unrated, needs review" if severity == UNRATED else f"est. severity {severity}"
    severity_text = "unrated, needs review" if severity == UNRATED else severity

    cwe_text = ", ".join(f"{c} ({escape_mrkdwn(CWE_LABELS.get(c, 'Unknown'))})" for c in cwes) or "none"
    quarantine_text = f"yes ({quarantine_category(quarantine_reason)})" if quarantined else "no"

    dup_lines = []
    for d in (duplicates if isinstance(duplicates, list) else [])[:MAX_DUPLICATES_SHOWN]:
        d = d if isinstance(d, dict) else {}
        score = safe_score(d.get("score"))
        score_text = f"similarity {score:.2f}" if score is not None else "similarity n/a"
        dup_lines.append(f"• {_id_text(d.get('event_id'))} ({score_text})")
    dup_text = "\n".join(dup_lines) or "none"

    fields = [
        {"type": "mrkdwn", "text": f"*Issue*\n{issue_ref}"},
        {"type": "mrkdwn", "text": f"*{severity_label}*\n{_SEVERITY_EMOJI[severity]} {severity_text}"},
        {"type": "mrkdwn", "text": f"*CWE*\n{cwe_text}"},
        {"type": "mrkdwn", "text": f"*Quarantined*\n{quarantine_text}"},
    ]
    context = [{"type": "mrkdwn", "text": f"Triage ID {_id_text(event_id)}"}]
    if not assessed:
        context.append({"type": "mrkdwn", "text": ESTIMATE_NOTE})

    return {
        "text": f"{headline}: {issue_ref} ({summary_severity})",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": headline}},
            {"type": "section", "fields": fields},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Possible duplicates*\n{dup_text}"}},
            {"type": "context", "elements": context},
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
        cwe_ids = safe_cwe_ids(json.loads(cwe_raw)) if cwe_raw else []
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
    assessed_severity: str | None = None,
) -> bool:
    """Send the Slack notification for *event_id*. Never raises.

    ``assessed_severity`` is for a future triage stage that assesses the
    report itself; until then callers omit it and the CWE estimate is shown.

    Returns:
        True if Slack accepted the message, False if skipped or failed.
    """
    webhook_url = getattr(env, "SLACK_WEBHOOK_URL", None) if env is not None else None
    if not webhook_url or not isinstance(webhook_url, str):
        return False
    try:
        issue_iid, cwe_ids, reason = await _load_event_context(db, event_id)
        payload = build_payload(event_id, issue_iid, cwe_ids, quarantined, reason, duplicates, assessed_severity)
        return await post_to_slack(webhook_url, payload, env)
    except Exception as exc:
        logger.error("Slack notification failed for %s: %s", event_id, type(exc).__name__)
        return False
