"""Server-side HTTP header scan for web clients (avoids browser CORS)."""

from __future__ import annotations

import asyncio
import urllib.error
import urllib.request
from typing import Any, Mapping, Optional

from detect.http_headers import scan_headers


def _urllib_head_status_and_headers(url: str) -> tuple[int, dict[str, str]]:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "blt-netguardian-detect"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            status = int(getattr(resp, "status", 200) or 200)
            headers = {k: v for k, v in resp.headers.items()}
            return status, headers
    except urllib.error.HTTPError as exc:
        headers = {k: v for k, v in exc.headers.items()} if exc.headers else {}
        return int(exc.code), headers


async def _default_fetch(url: str) -> tuple[int, dict[str, str]]:
    try:
        from js import fetch  # type: ignore[import-not-found]

        resp = await fetch(url, {"method": "GET", "headers": {"User-Agent": "blt-netguardian-detect"}})
        status = int(resp.status)
        headers: dict[str, str] = {}
        try:
            raw = resp.headers
            if hasattr(raw, "entries"):
                for entry in raw.entries():
                    headers[str(entry[0])] = str(entry[1])
        except Exception:  # noqa: BLE001
            pass
        return status, headers
    except ImportError:
        return await asyncio.to_thread(_urllib_head_status_and_headers, url)


async def scan_url_remote(
    url: str,
    *,
    fetch_impl: Any = None,
) -> list[dict[str, Any]]:
    """Fetch [url] server-side and return finding payloads."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("url is required")
    if "://" not in raw:
        raw = "https://" + raw.lstrip("/")
    fetch = fetch_impl or _default_fetch
    status, headers = await fetch(raw)
    findings = scan_headers(raw, headers, status=status)
    return [f.to_payload() for f in findings]


async def detect_headers_for_request(
    query_params: Mapping[str, str],
    *,
    fetch_impl: Any = None,
) -> tuple[int, dict[str, Any]]:
    url = (query_params.get("url") or "").strip()
    if not url:
        return 400, {"error": "invalid_query", "message": "url parameter is required"}
    try:
        payloads = await scan_url_remote(url, fetch_impl=fetch_impl)
    except ValueError as exc:
        return 400, {"error": "invalid_query", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 502, {"error": "fetch_failed", "message": str(exc)[:500]}
    return 200, {"url": url, "findings": payloads, "count": len(payloads)}
