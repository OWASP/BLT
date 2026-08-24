#!/usr/bin/env python3
"""Minimal /analyze for the hook + VS Code (proposal localhost:8000)."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from hooks.preflight_hook import offline


class H(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/analyze":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n) or b"{}")
        files = body.get("changed_files") or []
        adv = offline(files)
        raw = json.dumps(adv).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        print("[analyze]", fmt % args)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), H).serve_forever()