#!/usr/bin/env python3
"""Minimal local BLT-API stub for NetGuardian convert-to-issue demos.

Implements POST /bugs and POST /v2/bugs only. Run on port 8788 while NetGuardian
uses port 8787:

    python3 local_dev/blt_api_stub.py

Then start NetGuardian with BLT_API_BASE_URL=http://localhost:8788/v2
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "localhost"
PORT = 8788
_next_id = 1000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[blt-api-stub] {self.address_string()} - {fmt % args}")

    def do_POST(self) -> None:
        global _next_id
        path = self.path.split("?", 1)[0]
        if path not in ("/bugs", "/v2/bugs"):
            self.send_error(404, "not found")
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(400, "invalid json")
            return

        if not body.get("url") or not body.get("description"):
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "message": "Missing required fields: url, description",
            }).encode())
            return

        bug_id = _next_id
        _next_id += 1
        payload = {
            "success": True,
            "message": "Bug created successfully",
            "data": {
                "id": bug_id,
                "url": body["url"],
                "description": body["description"],
                "status": "open",
            },
        }
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_GET(self) -> None:
        if self.path.rstrip("/") in ("/health", "/v2/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        self.send_error(404)


def main() -> None:
    server = HTTPServer((HOST, PORT), Handler)
    print(f"BLT-API stub on http://{HOST}:{PORT} (POST /v2/bugs)")
    server.serve_forever()


if __name__ == "__main__":
    main()
