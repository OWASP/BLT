#!/usr/bin/env python3
"""Send ONE real, signed (and optionally encrypted) finding to the running local API.

This posts a genuine `ztr-finding-1` envelope — HMAC-SHA256 signed, body-digested,
nonce'd, AES-256-GCM encrypted — to the SAME `/api/ingest` endpoint a real scanner
would call. Use it during the demo to prove the pipeline is live: run this, then
click Refresh in the UI and watch the new finding appear.

Usage (from the BLT-NetGuardian repo root, with serve.py already running):

    .venv/bin/python local_dev/send_finding.py                # encrypted (default)
    .venv/bin/python local_dev/send_finding.py --plaintext    # plaintext at rest

Requires the local dev server on http://localhost:8787 (python local_dev/serve.py).
"""

from __future__ import annotations

import argparse
import http.client
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canonicalize import body_digest_hex  # noqa: E402
from envelope import prepare_signed_envelope  # noqa: E402
from payload_crypto import encrypt_payload  # noqa: E402

# Must match local_dev/serve.py demo config.
API_HOST = "localhost"
API_PORT = 8787
API_PATH = "/api/ingest"
DEMO_SECRET_HEX = "736563726574"
DEMO_ORG = "org-demo"
DEMO_PAYLOAD_KEY = b"netguardian-demo-aesgcm-key-0032"


def _is_loopback(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _resolve_credentials(base_url: str, *, secret_hex: str | None, payload_key: bytes | None):
    if _is_loopback(base_url):
        return secret_hex or DEMO_SECRET_HEX, payload_key or DEMO_PAYLOAD_KEY
    if not secret_hex or payload_key is None:
        raise SystemExit(
            "Remote destinations require --secret-hex and --payload-key-b64 "
            "(demo defaults are loopback-only)."
        )
    return secret_hex, payload_key


# A fresh, obviously-new finding so it stands out when it appears in the UI.
NEW_FINDING = {
    "rule_id": "zap.ssrf",
    "severity": "critical",
    "title": "Server-side request forgery in webhook handler",
    "target": "https://api.acme.example/webhook",
    "fingerprint": None,  # filled with a unique value per run below
    "cve_id": "CVE-2024-0002",
    "password": "should-be-redacted",
    "evidence": {"snippet": "requests.get(user_url)", "token": "redact-me"},
}


def build_signed_envelope(encrypt: bool, *, secret_hex: str, payload_key: bytes) -> tuple[dict, bytes]:
    now = datetime.now(timezone.utc)
    stamp = int(now.timestamp())

    payload = dict(NEW_FINDING)
    payload["fingerprint"] = f"fp-live-{stamp}"  # unique so it's not deduped

    body = {
        "version": "ztr-finding-1",
        "org_id": DEMO_ORG,
        "sender_id": "scanner-1",
        "kid": "k1",
        "alg": "hmac-sha256",
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nonce": f"live-{stamp}",
    }
    if encrypt:
        body["payload_ciphertext"] = encrypt_payload(
            payload_key, payload, aad=DEMO_ORG.encode()
        )
    else:
        body["plaintext_mode"] = True
        body["payload_plaintext"] = payload

    signed = prepare_signed_envelope(body, bytes.fromhex(secret_hex))
    raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
    return signed, raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost:8787",
        help="API base URL (e.g. https://blt-netguardian.preethampujari395.workers.dev)",
    )
    parser.add_argument(
        "--plaintext",
        action="store_true",
        help="Store payload as plaintext instead of AES-256-GCM encrypted.",
    )
    parser.add_argument(
        "--secret-hex",
        default=None,
        help="Sender HMAC secret hex (required for non-loopback destinations).",
    )
    parser.add_argument(
        "--payload-key-b64",
        default=None,
        help="AES-256 payload key, base64 (required for non-loopback destinations).",
    )
    args = parser.parse_args()
    encrypt = not args.plaintext

    import base64

    payload_key = base64.b64decode(args.payload_key_b64) if args.payload_key_b64 else None
    secret_hex, payload_key = _resolve_credentials(
        args.base_url, secret_hex=args.secret_hex, payload_key=payload_key
    )

    _signed, raw = build_signed_envelope(
        encrypt, secret_hex=secret_hex, payload_key=payload_key
    )
    parsed_url = urlparse(args.base_url.rstrip("/"))
    api_host = parsed_url.hostname or "localhost"
    api_port = parsed_url.port or (443 if parsed_url.scheme == "https" else 8787)
    api_path = API_PATH

    mode = "ENCRYPTED (AES-256-GCM)" if encrypt else "plaintext"
    print(f"Sending 1 signed finding [{mode}] -> {args.base_url}{api_path}")
    try:
        ctx = None
        if parsed_url.scheme == "https":
            import ssl
            ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(api_host, api_port, timeout=15, context=ctx) if parsed_url.scheme == "https" else http.client.HTTPConnection(api_host, api_port, timeout=15)
        conn.putrequest("POST", api_path, skip_host=False, skip_accept_encoding=True)
        conn.putheader("Content-Type", "application/json")
        conn.putheader("X-BLT-Body-Digest", f"sha256={body_digest_hex(raw)}")
        conn.putheader("Content-Length", str(len(raw)))
        conn.endheaders()
        conn.send(raw)
        resp = conn.getresponse()
        status = resp.status
        body = resp.read().decode("utf-8")
        conn.close()
    except OSError as exc:
        print(f"  FAILED: cannot reach {args.base_url} ({exc})")
        return 1

    try:
        parsed = json.loads(body)
        pretty = json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        pretty = body

    print(f"  HTTP {status}")
    print(pretty)
    if status in (200, 201):
        print("\n  Done. Switch to the browser and click Refresh — the new")
        print("  'zap.ssrf' critical finding should appear at the top.")
        return 0
    print("\n  Ingest did not succeed; see the response above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
