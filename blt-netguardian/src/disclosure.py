"""security.txt (RFC 9116) discovery helpers for disclosure workflows."""

from __future__ import annotations

import asyncio
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from d1_compat import row_get

_FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.+?)\s*$")
INTERESTING = frozenset(
    {
        "Contact",
        "Expires",
        "Encryption",
        "Acknowledgments",
        "Preferred-Languages",
        "Canonical",
        "Policy",
        "Hiring",
    }
)


@dataclass
class DisclosureResult:
    status: int
    body: dict


def target_origin(target: Optional[str]) -> Optional[str]:
    raw = str(target or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw.lstrip("/")
    parsed = urllib.parse.urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def security_txt_urls(origin: str) -> list[str]:
    base = origin.rstrip("/")
    return [f"{base}/.well-known/security.txt", f"{base}/security.txt"]


def parse_security_txt(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _FIELD.match(stripped)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key not in INTERESTING:
            continue
        fields.setdefault(key, []).append(value)
    return fields


def build_disclosure_hints(fields: Mapping[str, list[str]], *, source_url: str) -> dict[str, Any]:
    contacts = list(fields.get("Contact") or [])
    return {
        "found": bool(fields),
        "source_url": source_url,
        "contacts": contacts,
        "policy": list(fields.get("Policy") or []),
        "encryption": list(fields.get("Encryption") or []),
        "expires": (fields.get("Expires") or [None])[0],
        "preferred_languages": list(fields.get("Preferred-Languages") or []),
        "canonical": list(fields.get("Canonical") or []),
        "fields": {k: list(v) for k, v in fields.items()},
        "convert_hint": (
            f"Disclose via {contacts[0]}" if contacts else "No Contact field in security.txt"
        ),
    }


def _urllib_get_text(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "blt-netguardian-disclosure"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - target chosen from finding
            return int(getattr(resp, "status", 200) or 200), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


async def fetch_text(url: str, *, fetch_impl: Any = None) -> tuple[int, str]:
    if fetch_impl is not None:
        return await fetch_impl(url)
    try:
        from js import fetch  # type: ignore[import-not-found]

        resp = await fetch(url, {"method": "GET", "headers": {"User-Agent": "blt-netguardian-disclosure"}})
        return int(resp.status), str(await resp.text())
    except ImportError:
        return await asyncio.to_thread(_urllib_get_text, url)


async def discover_security_txt(
    target: Optional[str],
    *,
    fetch_impl: Any = None,
) -> dict[str, Any]:
    origin = target_origin(target)
    if not origin:
        return {
            "found": False,
            "error": "invalid_target",
            "message": "target has no usable origin",
            "contacts": [],
            "fields": {},
        }

    last_error = None
    for url in security_txt_urls(origin):
        try:
            status, text = await fetch_text(url, fetch_impl=fetch_impl)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue
        if status == 200 and text.strip():
            fields = parse_security_txt(text)
            if fields:
                return build_disclosure_hints(fields, source_url=url)
            last_error = "empty_or_unparsed"
            continue
        last_error = f"http_{status}"
    return {
        "found": False,
        "origin": origin,
        "error": "not_found",
        "message": last_error or "security.txt not found",
        "contacts": [],
        "fields": {},
        "convert_hint": "No security.txt discovered; use org contact process.",
    }


async def disclosure_for_finding_row(
    row: Mapping[str, Any],
    *,
    fetch_impl: Any = None,
) -> dict[str, Any]:
    target = row_get(row, "target")
    result = await discover_security_txt(target, fetch_impl=fetch_impl)
    result["finding_id"] = row_get(row, "id")
    result["target"] = target
    return result
