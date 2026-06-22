#!/usr/bin/env python3
"""Local dev runner for BLT-NetGuardian (NOT deployed).

Cloudflare runs the real Python Worker via `wrangler dev`. This machine's Node is
too old for wrangler, so this stdlib-only server lets you launch and click through
the app locally. It serves `public/` and bridges every `/api/*` request to the
REAL `BLTWorker` logic backed by an in-memory SQLite stand-in for D1.

Usage:
    python3 local_dev/serve.py
Then open http://localhost:8787/triage.html and connect with token: triage-token
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from canonicalize import body_digest_hex  # noqa: E402
from envelope import prepare_signed_envelope  # noqa: E402
from ingest_service import process_ingest  # noqa: E402
from ingest_store import IngestStore  # noqa: E402
from netguardian_db import open_netguardian_db  # noqa: E402
from worker import BLTWorker  # noqa: E402

HOST = "localhost"
PORT = 8787
PUBLIC = (ROOT / "public").resolve()

DEMO_SECRET_HEX = "736563726574"
DEMO_TOKEN = "triage-token"
DEMO_ORG = "org-demo"

DB = open_netguardian_db(ROOT)
ENV = SimpleNamespace(
    DB=DB,
    ENVIRONMENT="development",
    NG_SENDER_SECRETS=json.dumps({f"{DEMO_ORG}:scanner-1:k1": DEMO_SECRET_HEX}),
    NG_ORG_API_TOKENS=json.dumps({DEMO_TOKEN: DEMO_ORG}),
    NG_INGEST_RPM="6000",
    AUTHENTICATE_READ_ENDPOINTS="false",
    CORS_ALLOWED_ORIGINS=f"http://{HOST}:{PORT},http://127.0.0.1:{PORT}",
)
WORKER = BLTWorker(ENV)

DEMO_FINDINGS = [
    {
        "rule_id": "semgrep.python.sql-injection",
        "severity": "critical",
        "title": "SQL injection in reporting export",
        "target": "https://api.acme.example/reports",
        "fingerprint": "fp-sqli-1",
        "cve_id": "CVE-2024-0001",
        "password": "should-be-redacted",
        "evidence": {"snippet": "SELECT * FROM x WHERE id=' + req.id", "token": "redact-me"},
    },
    {
        "rule_id": "nuclei.tls.weak-cipher",
        "severity": "medium",
        "title": "Weak TLS cipher suite accepted",
        "target": "https://acme.example",
        "fingerprint": "fp-tls-1",
    },
    {
        "rule_id": "semgrep.js.xss",
        "severity": "high",
        "title": "Reflected XSS in search box",
        "target": "https://shop.acme.example/search",
        "fingerprint": "fp-xss-1",
    },
]


def _seed_demo_data() -> None:
    secret = bytes.fromhex(DEMO_SECRET_HEX)

    async def seed_one(index: int, payload: dict) -> None:
        now = datetime.now(timezone.utc)
        body = {
            "version": "ztr-finding-1",
            "org_id": DEMO_ORG,
            "sender_id": "scanner-1",
            "kid": "k1",
            "alg": "hmac-sha256",
            "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "nonce": f"seed-{index}-{int(now.timestamp())}",
            "plaintext_mode": True,
            "payload_plaintext": payload,
        }
        signed = prepare_signed_envelope(body, secret)
        raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
        await process_ingest(
            raw_body=raw,
            body_digest_header=f"sha256={body_digest_hex(raw)}",
            envelope=signed,
            env=ENV,
            db=DB,
            store=IngestStore(DB),
            new_id=lambda label: f"{label}-seed-{index}",
        )

    async def seed_all() -> None:
        for index, payload in enumerate(DEMO_FINDINGS):
            await seed_one(index, payload)

    asyncio.run(seed_all())


class _Request:
    """Minimal request shim matching what BLTWorker expects."""

    def __init__(self, method: str, url: str, headers: dict, body: bytes):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

    async def text(self) -> str:
        return self.body.decode("utf-8") if self.body else ""

    async def json(self):
        return json.loads(self.body or b"{}")


class Handler(BaseHTTPRequestHandler):
    server_version = "NetGuardianLocalDev/0.1"

    def _is_api(self) -> bool:
        return self.path.split("?")[0].startswith("/api/")

    def _serve_static(self) -> None:
        rel = self.path.split("?")[0].lstrip("/") or "index.html"
        target = (PUBLIC / rel).resolve()
        if not str(target).startswith(str(PUBLIC)) or not target.is_file():
            self.send_error(404, "Not found")
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_api(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        headers = {key: value for key, value in self.headers.items()}
        url = f"http://{HOST}:{PORT}{self.path}"
        request = _Request(self.command, url, headers, body)
        try:
            response = asyncio.run(WORKER.handle_request(request))
        except Exception as exc:  # pragma: no cover - dev convenience
            payload = json.dumps({"error": "dev_server_error", "message": str(exc)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        out = response.body
        if isinstance(out, (dict, list)):
            out = json.dumps(out)
        if isinstance(out, str):
            out = out.encode("utf-8")
        elif out is None:
            out = b""

        resp_headers = dict(response.headers or {})
        self.send_response(response.status)
        for key, value in resp_headers.items():
            self.send_header(key, value)
        if not any(k.lower() == "content-type" for k in resp_headers):
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        if self._is_api():
            self._handle_api()
        else:
            self._serve_static()

    def do_POST(self):
        self._handle_api()

    def do_OPTIONS(self):
        self._handle_api()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def main() -> None:
    _seed_demo_data()
    server = HTTPServer((HOST, PORT), Handler)
    print("=" * 64)
    print("  BLT-NetGuardian local dev server (bridges real BLTWorker)")
    print("=" * 64)
    print(f"  App:    http://{HOST}:{PORT}/index.html")
    print(f"  Triage: http://{HOST}:{PORT}/triage.html")
    print(f"  Token:  {DEMO_TOKEN}   (org {DEMO_ORG})")
    print(f"  Seeded: {len(DEMO_FINDINGS)} demo findings")
    print("  Ctrl+C to stop.")
    print("=" * 64)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
