"""Semgrep JSON → ``ztr-finding-1`` findings.

Semgrep is invoked out of band (``semgrep --json --output results.json``) and its
report is parsed here. Shelling out is intentionally *not* this module's job:
the scan may run in CI, on a developer machine, or in a container, and parsing
stays a pure function over the report so it is testable without the binary
installed.

Severity mapping keeps both Semgrep's classic ``ERROR/WARNING/INFO`` scale and
the newer ``CRITICAL/HIGH/...`` values working, since rule registries emit both.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Optional

from detect.normalize import DetectionFinding

SEMGREP_SEVERITY_MAP = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "INFO_ONLY": "info",
}

_MAX_EVIDENCE_CHARS = 240


def parse_semgrep_json(raw: str | bytes) -> list[dict]:
    """Return the ``results`` array from a Semgrep JSON report."""
    try:
        report = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("semgrep report is not valid JSON") from exc
    if not isinstance(report, Mapping):
        raise ValueError("semgrep report must be a JSON object")
    results = report.get("results")
    if results is None:
        return []
    if not isinstance(results, list):
        raise ValueError("semgrep 'results' must be an array")
    return [r for r in results if isinstance(r, Mapping)]


def _map_severity(extra: Mapping[str, Any]) -> str:
    raw = str(extra.get("severity") or "").strip().upper()
    if raw in SEMGREP_SEVERITY_MAP:
        return SEMGREP_SEVERITY_MAP[raw]
    metadata = extra.get("metadata")
    if isinstance(metadata, Mapping):
        meta_raw = str(metadata.get("severity") or "").strip().upper()
        if meta_raw in SEMGREP_SEVERITY_MAP:
            return SEMGREP_SEVERITY_MAP[meta_raw]
    return "info"


def _extract_cve(extra: Mapping[str, Any]) -> Optional[str]:
    metadata = extra.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    candidate = metadata.get("cve")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    if isinstance(candidate, list):
        for item in candidate:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def _short_title(check_id: str, message: str) -> str:
    """Prefer Semgrep's message; fall back to the rule's last path segment."""
    text = " ".join(str(message or "").split())
    if not text:
        text = check_id.rsplit(".", 1)[-1].replace("-", " ").replace("_", " ").strip()
    if len(text) > 160:
        text = text[:157].rstrip() + "..."
    return text or check_id


def scan_semgrep_results(
    results: Iterable[Mapping[str, Any]],
    *,
    target: str,
) -> list[DetectionFinding]:
    """Normalize Semgrep results for one scanned project/repository."""
    findings: list[DetectionFinding] = []
    for result in results:
        check_id = str(result.get("check_id") or "").strip()
        if not check_id:
            continue

        extra = result.get("extra")
        extra = extra if isinstance(extra, Mapping) else {}

        path = str(result.get("path") or "").strip()
        start = result.get("start")
        line = 0
        if isinstance(start, Mapping):
            try:
                line = int(start.get("line") or 0)
            except (TypeError, ValueError):
                line = 0
        if line < 1:
            end = result.get("end")
            if isinstance(end, Mapping):
                try:
                    line = int(end.get("line") or 0)
                except (TypeError, ValueError):
                    line = 0

        # Never invent path:0 — that collapses distinct line-less matches into one
        # fingerprint. Prefer path:line; otherwise a stable per-match digest.
        if not path:
            continue
        if line >= 1:
            locator = f"{path}:{line}"
        else:
            snippet = str((extra.get("lines") if isinstance(extra, Mapping) else "") or "")
            col = 0
            if isinstance(start, Mapping):
                try:
                    col = int(start.get("col") or 0)
                except (TypeError, ValueError):
                    col = 0
            material = f"{check_id}\0{col}\0{snippet}"
            locator = f"{path}#{hashlib.sha256(material.encode()).hexdigest()[:12]}"

        evidence: dict[str, Any] = {}
        snippet = extra.get("lines")
        if isinstance(snippet, str) and snippet.strip():
            evidence["lines"] = snippet.strip()[:_MAX_EVIDENCE_CHARS]
        metadata = extra.get("metadata")
        if isinstance(metadata, Mapping):
            for key in ("cwe", "owasp"):
                if metadata.get(key):
                    evidence[key] = metadata[key]

        findings.append(DetectionFinding(
            rule_id=f"semgrep.{check_id}",
            severity=_map_severity(extra),
            title=_short_title(check_id, extra.get("message", "")),
            target=target,
            locator=locator,
            cve_id=_extract_cve(extra),
            evidence=evidence,
            remediation=str(extra.get("fix") or "").strip(),
        ))
    return findings
