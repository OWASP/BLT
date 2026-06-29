"""HTTP client for BLT-API bug (issue) creation."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any, Awaitable, Callable, Mapping, Optional

API_KEY_HEADER = "X-BLT-API-Key"

_SEV_SCORE = {
    "critical": 90,
    "high": 75,
    "medium": 50,
    "low": 25,
    "info": 10,
}


class BltApiError(Exception):
    """BLT-API request failed."""

    def __init__(self, message: str, *, status: Optional[int] = None, body: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.body = body


class BltApiNotConfigured(BltApiError):
    """BLT_API_BASE_URL is not set."""


HttpPostJson = Callable[[str, Mapping[str, str], dict], Awaitable[tuple[int, dict]]]


def get_blt_config(env: Any) -> tuple[str, str]:
    base_url = str(getattr(env, "BLT_API_BASE_URL", None) or "").strip()
    api_key = str(getattr(env, "BLT_API_KEY", None) or "").strip()
    return base_url, api_key


def is_blt_api_configured(env: Any) -> bool:
    base_url, _ = get_blt_config(env)
    return bool(base_url)


def bugs_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/bugs"):
        return base
    return f"{base}/bugs"


def normalize_target_url(target: Optional[str]) -> str:
    raw = str(target or "").strip()
    if not raw:
        return "https://netguardian.local/finding"
    if raw.startswith(("http://", "https://")):
        url = raw
    else:
        url = f"https://{raw.lstrip('/')}"
    return url[:200]


def severity_score(severity: Optional[str]) -> int:
    key = str(severity or "info").lower()
    return _SEV_SCORE.get(key, 10)


def build_bug_create_body(finding: Mapping[str, Any]) -> dict:
    """Map a NetGuardian finding row to BLT-API POST /bugs JSON."""
    finding_id = finding.get("id") or "unknown"
    rule_id = finding.get("rule_id") or "netguardian-rule"
    title = finding.get("title") or rule_id
    severity = finding.get("severity") or "info"
    target = finding.get("target")

    description = str(title).strip() or str(rule_id)
    if len(description) > 500:
        description = description[:497] + "..."

    markdown = (
        f"# NetGuardian finding {finding_id}\n\n"
        f"- **Rule:** {rule_id}\n"
        f"- **Severity:** {severity}\n"
        f"- **Target:** {target or '—'}\n"
        f"- **Fingerprint:** {finding.get('fingerprint') or '—'}\n"
        f"- **Org:** {finding.get('org_id') or '—'}\n"
    )

    body: dict[str, Any] = {
        "url": normalize_target_url(target),
        "description": description,
        "markdown_description": markdown,
        "label": "netguardian",
        "score": severity_score(severity),
    }

    cve_id = finding.get("cve_id")
    if cve_id:
        body["cve_id"] = str(cve_id)

    cve_score = finding.get("cve_score")
    if cve_score is not None:
        try:
            body["cve_score"] = float(cve_score)
        except (TypeError, ValueError):
            pass

    return body


def _urllib_post_json(url: str, headers: Mapping[str, str], payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for key, value in headers.items():
        req.add_header(key, value)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        raw = exc.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"raw": raw}
    if not isinstance(parsed, dict):
        parsed = {"data": parsed}
    return status, parsed


async def _js_fetch_post_json(url: str, headers: Mapping[str, str], payload: dict) -> tuple[int, dict]:
    from js import fetch  # type: ignore[import-not-found]

    hdrs = dict(headers)
    hdrs.setdefault("Content-Type", "application/json")
    resp = await fetch(url, {
        "method": "POST",
        "headers": hdrs,
        "body": json.dumps(payload),
    })
    status = int(resp.status)
    raw = await resp.text()
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"raw": raw}
    if not isinstance(parsed, dict):
        parsed = {"data": parsed}
    return status, parsed


async def post_json(
    url: str,
    headers: Mapping[str, str],
    payload: dict,
    *,
    fetch_impl: Optional[HttpPostJson] = None,
) -> tuple[int, dict]:
    if fetch_impl is not None:
        return await fetch_impl(url, headers, payload)
    try:
        from js import fetch  # noqa: F401
        return await _js_fetch_post_json(url, headers, payload)
    except ImportError:
        return await asyncio.to_thread(_urllib_post_json, url, headers, payload)


def parse_bug_id(response_body: Mapping[str, Any]) -> str:
    data = response_body.get("data")
    if isinstance(data, dict) and data.get("id") is not None:
        return str(data["id"])
    if response_body.get("id") is not None:
        return str(response_body["id"])
    raise BltApiError("BLT-API response missing bug id", body=json.dumps(response_body))


async def create_bug_from_finding(
    env: Any,
    finding: Mapping[str, Any],
    *,
    fetch_impl: Optional[HttpPostJson] = None,
) -> str:
    base_url, api_key = get_blt_config(env)
    if not base_url:
        raise BltApiNotConfigured("BLT_API_BASE_URL is not configured")

    url = bugs_endpoint(base_url)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers[API_KEY_HEADER] = api_key

    payload = build_bug_create_body(finding)
    status, body = await post_json(url, headers, payload, fetch_impl=fetch_impl)

    if status < 200 or status >= 300:
        message = body.get("message") or body.get("error") or f"BLT-API returned HTTP {status}"
        raise BltApiError(str(message), status=status, body=json.dumps(body))

    if body.get("success") is False:
        message = body.get("message") or body.get("error") or "BLT-API reported failure"
        raise BltApiError(str(message), status=status, body=json.dumps(body))

    return parse_bug_id(body)
