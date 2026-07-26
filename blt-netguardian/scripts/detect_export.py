#!/usr/bin/env python3
"""Run detection packs and submit results to ``POST /api/ingest``.

This is the thin end of the detection MVP: detectors produce normalized
findings, this script wraps each one in a signed (and by default AES-256-GCM
encrypted) ``ztr-finding-1`` envelope and posts it to the same endpoint any
third-party scanner would use. There is no privileged back door — detection is
just another authenticated sender.

Examples::

    # Header checks against a live URL, previewing payloads only
    python scripts/detect_export.py --url https://example.com --dry-run

    # Semgrep report for a repo, submitted to the local dev server
    semgrep --config auto --json --output sg.json
    python scripts/detect_export.py --semgrep-json sg.json \\
        --target github.com/owasp-blt/blt --base-url http://localhost:8787

Demo credentials are loopback-only; remote destinations must pass
``--secret-hex`` and ``--payload-key-b64`` explicitly.
"""

from __future__ import annotations

import argparse
import base64
import json
import ssl
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canonicalize import body_digest_hex  # noqa: E402
from detect.http_headers import scan_headers  # noqa: E402
from detect.normalize import DetectionFinding  # noqa: E402
from detect.semgrep import parse_semgrep_json, scan_semgrep_results  # noqa: E402
from envelope import prepare_signed_envelope  # noqa: E402
from payload_crypto import encrypt_payload  # noqa: E402

DEMO_SECRET_HEX = "736563726574"
DEMO_PAYLOAD_KEY = b"netguardian-demo-aesgcm-key-0032"
DEFAULT_ORG = "org-demo"
DEFAULT_SENDER = "scanner-1"
DEFAULT_KID = "k1"
API_PATH = "/api/ingest"


def _is_loopback(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _resolve_credentials(
    base_url: str,
    *,
    secret_hex: str | None,
    payload_key: bytes | None,
    encrypt: bool,
):
    """Demo keys are committed, so they must never be used against a remote host.

    ``payload_key`` is only required when encryption is enabled; plaintext remote
    submissions still need ``secret_hex`` for HMAC.
    """
    if _is_loopback(base_url):
        return secret_hex or DEMO_SECRET_HEX, payload_key or (DEMO_PAYLOAD_KEY if encrypt else None)
    if not secret_hex or (encrypt and payload_key is None):
        raise SystemExit(
            "Remote destinations require --secret-hex"
            + (" and --payload-key-b64" if encrypt else "")
            + " (demo defaults are loopback-only)."
        )
    return secret_hex, payload_key


def fetch_response_headers(url: str, *, timeout: int = 10) -> tuple[int, dict[str, str]]:
    """GET a URL and return (status, headers). Header checks need no body."""
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "NetGuardian-Detect/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(getattr(response, "status", 200) or 200), dict(response.headers)
    except urllib.error.HTTPError as exc:
        # An error response still carries headers worth evaluating.
        return int(exc.code), dict(exc.headers or {})


def collect_findings(args: argparse.Namespace) -> list[DetectionFinding]:
    findings: list[DetectionFinding] = []

    if args.url:
        status, headers = fetch_response_headers(args.url)
        print(f"[http] {args.url} -> HTTP {status}, {len(headers)} headers")
        findings.extend(scan_headers(args.url, headers, status=status))

    if args.semgrep_json:
        report_path = Path(args.semgrep_json)
        results = parse_semgrep_json(report_path.read_text())
        target = args.target or report_path.stem
        print(f"[semgrep] {report_path} -> {len(results)} results (target={target})")
        findings.extend(scan_semgrep_results(results, target=target))

    return findings


def build_envelope(
    finding: DetectionFinding,
    *,
    org_id: str,
    sender_id: str,
    kid: str,
    secret_hex: str,
    payload_key: bytes,
    encrypt: bool,
) -> tuple[dict, bytes]:
    now = datetime.now(timezone.utc)
    payload = finding.to_payload()
    envelope: dict = {
        "version": "ztr-finding-1",
        "org_id": org_id,
        "sender_id": sender_id,
        "kid": kid,
        "alg": "hmac-sha256",
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Fresh nonce per submission: replay protection is per-envelope, while
        # duplicate suppression is handled by the deterministic fingerprint.
        "nonce": f"detect-{uuid.uuid4().hex[:16]}",
    }
    if encrypt:
        envelope["payload_ciphertext"] = encrypt_payload(
            payload_key, payload, aad=org_id.encode()
        )
    else:
        envelope["plaintext_mode"] = True
        envelope["payload_plaintext"] = payload

    signed = prepare_signed_envelope(envelope, bytes.fromhex(secret_hex), now=now)
    raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
    return signed, raw


def submit(base_url: str, raw: bytes, *, timeout: int = 15) -> tuple[int, str]:
    url = base_url.rstrip("/") + API_PATH
    request = urllib.request.Request(url, data=raw, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("X-BLT-Body-Digest", f"sha256={body_digest_hex(raw)}")
    context = ssl.create_default_context() if url.startswith("https://") else None
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return int(getattr(response, "status", 200) or 200), response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="URL to run HTTP security-header checks against.")
    parser.add_argument("--semgrep-json", help="Path to a `semgrep --json` report.")
    parser.add_argument("--target", help="Target identifier for Semgrep findings (e.g. repo slug).")
    parser.add_argument("--base-url", default="http://localhost:8787", help="NetGuardian API base URL.")
    parser.add_argument("--org-id", default=DEFAULT_ORG)
    parser.add_argument("--sender-id", default=DEFAULT_SENDER)
    parser.add_argument("--kid", default=DEFAULT_KID)
    parser.add_argument("--secret-hex", default=None, help="Sender HMAC secret (required for remote).")
    parser.add_argument("--payload-key-b64", default=None, help="AES-256 key, base64 (required for remote).")
    parser.add_argument("--plaintext", action="store_true", help="Submit payloads unencrypted.")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without submitting.")
    args = parser.parse_args()

    if not args.url and not args.semgrep_json:
        parser.error("provide --url and/or --semgrep-json")

    findings = collect_findings(args)
    if not findings:
        print("No findings produced; nothing to submit.")
        return 0

    print(f"\n{len(findings)} finding(s) normalized:")
    for finding in findings:
        print(f"  [{finding.severity:8}] {finding.rule_id}  {finding.fingerprint}")

    if args.dry_run:
        print("\n--dry-run: payloads below, nothing sent.\n")
        print(json.dumps([f.to_payload() for f in findings], indent=2))
        return 0

    payload_key = base64.b64decode(args.payload_key_b64) if args.payload_key_b64 else None
    encrypt = not args.plaintext
    secret_hex, payload_key = _resolve_credentials(
        args.base_url, secret_hex=args.secret_hex, payload_key=payload_key, encrypt=encrypt
    )

    created = duplicate = merged = failed = 0
    print(f"\nSubmitting to {args.base_url}{API_PATH} ({'encrypted' if encrypt else 'plaintext'}):")
    for finding in findings:
        _signed, raw = build_envelope(
            finding,
            org_id=args.org_id,
            sender_id=args.sender_id,
            kid=args.kid,
            secret_hex=secret_hex,
            payload_key=payload_key or b"",
            encrypt=encrypt,
        )
        try:
            status, body = submit(args.base_url, raw)
        except OSError as exc:
            print(f"  FAILED  {finding.rule_id}: cannot reach API ({exc})")
            failed += 1
            continue

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {}
        outcome = parsed.get("status") or parsed.get("error") or f"HTTP {status}"
        if outcome == "created":
            created += 1
        elif outcome == "duplicate":
            duplicate += 1
        elif outcome == "merged":
            merged += 1
        else:
            failed += 1
        print(f"  HTTP {status:3}  {outcome:10} {finding.rule_id}")

    print(f"\ncreated={created} merged={merged} duplicate={duplicate} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
