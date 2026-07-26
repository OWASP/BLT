"""Detector output → ``ztr-finding-1`` payload normalization.

Detectors (HTTP header checks, Semgrep, future packs) each speak their own
vocabulary. This module is the single place that turns any of them into the
payload shape ``POST /api/ingest`` accepts, so adding a detector never means
touching the ingest contract.

Two properties matter here:

* **Deterministic fingerprints.** ``fingerprint`` is derived from the stable
  identity of an issue (rule + target + location), never from a timestamp or
  scan id. Re-scanning an unfixed target therefore produces the *same*
  fingerprint, and ``process_ingest`` merges it into the existing finding
  instead of creating a duplicate row.
* **Severity normalization.** Detectors use their own scales (Semgrep's
  ERROR/WARNING/INFO, header checks' own judgement). Everything is mapped onto
  the five severities the findings store ranks and the triage UI renders.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

SEVERITIES = ("critical", "high", "medium", "low", "info")
DEFAULT_SEVERITY = "info"

_FINGERPRINT_HEX_LEN = 32


def normalize_severity(value: Any) -> str:
    """Coerce any detector severity onto the canonical five-level scale."""
    text = str(value or "").strip().lower()
    return text if text in SEVERITIES else DEFAULT_SEVERITY


def compute_fingerprint(*, rule_id: str, target: str, locator: str = "") -> str:
    """Stable identity for an issue: same issue on same target → same value.

    Parts are NUL-joined so a rule id containing the separator cannot collide
    with a different (rule, target) pair.
    """
    material = "\x00".join((rule_id.strip(), target.strip(), locator.strip()))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"fp-{digest[:_FINGERPRINT_HEX_LEN]}"


@dataclass
class DetectionFinding:
    """One normalized detector result, ready to become an ingest payload."""

    rule_id: str
    severity: str
    title: str
    target: str
    locator: str = ""
    cve_id: Optional[str] = None
    evidence: dict = field(default_factory=dict)
    remediation: str = ""

    def __post_init__(self) -> None:
        self.severity = normalize_severity(self.severity)
        if not self.rule_id:
            raise ValueError("rule_id is required")
        if not self.title:
            raise ValueError("title is required")

    @property
    def fingerprint(self) -> str:
        return compute_fingerprint(
            rule_id=self.rule_id, target=self.target, locator=self.locator
        )

    def to_payload(self) -> dict:
        """Render the ``ztr-finding-1`` payload body.

        Optional keys are omitted rather than sent as null: the ingest store
        skips absent columns, and D1 rejects a bound Python ``None``.
        """
        payload: dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "fingerprint": self.fingerprint,
        }
        if self.target:
            payload["target"] = self.target
        if self.cve_id:
            payload["cve_id"] = self.cve_id
        if self.locator:
            payload["locator"] = self.locator
        if self.remediation:
            payload["remediation"] = self.remediation
        if self.evidence:
            payload["evidence"] = self.evidence
        return payload
