#!/usr/bin/env python3
"""Seed a realistic demo dataset into a running NetGuardian instance.

Every finding is posted through the REAL signed `ztr-finding-1` ingest pipeline
(HMAC-SHA256 signed, body-digested, nonce'd), exactly like a scanner would. A
subset is AES-256-GCM encrypted at rest so the triage UI can demo the
decrypt-on-view + audit-log flow.

Usage (from the BLT-NetGuardian repo root):

    .venv/bin/python local_dev/seed_demo.py                      # local :8787
    .venv/bin/python local_dev/seed_demo.py --base-url https://blt-netguardian.preethampujari395.workers.dev

This script does not delete existing data. To reset a remote D1 first, run each
statement separately and in this order (findings<->envelopes have a circular
foreign key, so the reference must be nulled before deleting):

    W=(npx wrangler@3 d1 execute blt-netguardian --remote --command)
    "${W[@]}" "DELETE FROM access_logs;"
    "${W[@]}" "DELETE FROM ng_metrics;"
    "${W[@]}" "UPDATE envelopes SET finding_id = NULL;"
    "${W[@]}" "DELETE FROM findings;"
    "${W[@]}" "DELETE FROM envelopes;"
"""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canonicalize import body_digest_hex  # noqa: E402
from envelope import prepare_signed_envelope  # noqa: E402
from payload_crypto import encrypt_payload  # noqa: E402

API_PATH = "/api/ingest"
DEMO_SECRET_HEX = "736563726574"
DEMO_ORG = "org-demo"
DEMO_PAYLOAD_KEY = b"netguardian-demo-aesgcm-key-0032"

# (payload, encrypt?) — a spread of severities, a couple encrypted with secrets.
DEMO_FINDINGS = [
    (
        {
            "rule_id": "zap.ssrf",
            "severity": "critical",
            "title": "Server-side request forgery in webhook handler",
            "target": "https://api.acme.example/webhook",
            "cve_id": "CVE-2024-0002",
            "password": "s3cr3t-prod-db-pw",
            "evidence": {"snippet": "requests.get(user_url)", "token": "ghp_live_should_redact"},
        },
        True,
    ),
    (
        {
            "rule_id": "semgrep.python.sql-injection",
            "severity": "critical",
            "title": "SQL injection via unsanitized query parameter",
            "target": "https://api.acme.example/app/api/users.py",
            "cve_id": "CVE-2023-9911",
            "password": "admin:admin",
            "evidence": {"snippet": "cursor.execute(f\"SELECT * FROM users WHERE id={uid}\")"},
        },
        True,
    ),
    (
        {
            "rule_id": "nuclei.exposed-env-file",
            "severity": "high",
            "title": "Publicly accessible .env file",
            "target": "https://staging.acme.example/.env",
            "evidence": {"snippet": "GET /.env -> 200 OK"},
        },
        False,
    ),
    (
        {
            "rule_id": "zap.xss-reflected",
            "severity": "high",
            "title": "Reflected XSS in search parameter",
            "target": "https://acme.example/search?q=",
            "evidence": {"snippet": "<script>alert(1)</script> reflected unescaped"},
        },
        False,
    ),
    (
        {
            "rule_id": "trivy.outdated-dependency",
            "severity": "medium",
            "title": "Vulnerable dependency: lodash < 4.17.21",
            "target": "https://acme.example/package-lock.json",
            "cve_id": "CVE-2021-23337",
            "evidence": {"snippet": "lodash 4.17.15 (prototype pollution)"},
        },
        False,
    ),
    (
        {
            "rule_id": "zap.missing-security-headers",
            "severity": "medium",
            "title": "Missing Content-Security-Policy header",
            "target": "https://acme.example/",
            "evidence": {"snippet": "No CSP header present on responses"},
        },
        False,
    ),
    (
        {
            "rule_id": "semgrep.weak-hash",
            "severity": "low",
            "title": "Use of weak MD5 hash for password storage",
            "target": "https://api.acme.example/app/auth/hashing.py",
            "evidence": {"snippet": "hashlib.md5(password.encode())"},
        },
        False,
    ),
    (
        {
            "rule_id": "gitleaks.info-disclosure",
            "severity": "info",
            "title": "Verbose error stack trace exposed",
            "target": "https://acme.example/api/debug",
            "evidence": {"snippet": "Traceback (most recent call last) in JSON response"},
        },
        False,
    ),
]


def _post(base_url: str, raw: bytes) -> tuple[int, str]:
    parsed = urlparse(base_url.rstrip("/"))
    host = parsed.hostname or "localhost"
    is_https = parsed.scheme == "https"
    port = parsed.port or (443 if is_https else 8787)
    if is_https:
        import ssl

        conn = http.client.HTTPSConnection(host, port, timeout=15, context=ssl.create_default_context())
    else:
        conn = http.client.HTTPConnection(host, port, timeout=15)
    conn.putrequest("POST", API_PATH, skip_host=False, skip_accept_encoding=True)
    conn.putheader("Content-Type", "application/json")
    conn.putheader("X-BLT-Body-Digest", f"sha256={body_digest_hex(raw)}")
    conn.putheader("Content-Length", str(len(raw)))
    conn.endheaders()
    conn.send(raw)
    resp = conn.getresponse()
    status = resp.status
    body = resp.read().decode("utf-8")
    conn.close()
    return status, body


def build_envelope(payload: dict, encrypt: bool, seq: int) -> bytes:
    now = datetime.now(timezone.utc)
    stamp = int(now.timestamp())
    payload = dict(payload)
    payload["fingerprint"] = f"fp-seed-{stamp}-{seq}"
    body = {
        "version": "ztr-finding-1",
        "org_id": DEMO_ORG,
        "sender_id": "scanner-1",
        "kid": "k1",
        "alg": "hmac-sha256",
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nonce": f"seed-{stamp}-{seq}",
    }
    if encrypt:
        body["payload_ciphertext"] = encrypt_payload(DEMO_PAYLOAD_KEY, payload, aad=DEMO_ORG.encode())
    else:
        body["plaintext_mode"] = True
        body["payload_plaintext"] = payload
    signed = prepare_signed_envelope(body, bytes.fromhex(DEMO_SECRET_HEX))
    return json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8787")
    args = parser.parse_args()

    print(f"Seeding {len(DEMO_FINDINGS)} findings -> {args.base_url}{API_PATH}\n")
    ok = 0
    for seq, (payload, encrypt) in enumerate(DEMO_FINDINGS):
        raw = build_envelope(payload, encrypt, seq)
        try:
            status, body = _post(args.base_url, raw)
        except OSError as exc:
            print(f"  [{seq}] FAILED to reach server: {exc}")
            return 1
        tag = "ENC" if encrypt else "plain"
        mark = "ok" if status in (200, 201) else "FAIL"
        print(f"  [{mark}] {status} {tag:5s} {payload['severity']:8s} {payload['rule_id']}")
        if status in (200, 201):
            ok += 1
        time.sleep(0.15)  # keep nonces/timestamps distinct, stay under rate limits

    print(f"\nSeeded {ok}/{len(DEMO_FINDINGS)}. Open the triage UI and click Refresh.")
    return 0 if ok == len(DEMO_FINDINGS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
