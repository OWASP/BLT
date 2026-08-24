#!/usr/bin/env python3
"""Week 7 Tier-2 hook. Staged files → local server, else offline rules. Never uploads diffs."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = re.compile(r"(auth|login|session|password|oauth|jwt|mfa)", re.I)
DB = re.compile(r"(db|sql|migration|query|model)", re.I)
API = re.compile(r"(api|route|endpoint|controller|handler)", re.I)
SECRET = re.compile(r"(\.env|secret|credential|api.?key|id_rsa)", re.I)
DOC = re.compile(r"\.(md|mdx|rst|txt)$", re.I)

ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def staged() -> list[str]:
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def load_cfg() -> dict:
    p = ROOT / ".preflight.yaml"
    cfg = {
        "hook_mode": "advisory",
        "minimum_severity": "HIGH",
        "server": {"url": "http://127.0.0.1:8000", "timeout_seconds": 4},
    }
    if not p.exists():
        return cfg
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(p.read_text()) or {}
        cfg.update(data)
    except Exception:
        pass
    return cfg


def offline(files: list[str]) -> dict:
    if any(SECRET.search(f) for f in files):
        sev, cat = "CRITICAL", "A02:2021"
    elif any(AUTH.search(f) for f in files):
        sev, cat = "HIGH", "A07:2021"
    elif any(API.search(f) for f in files):
        sev, cat = "MEDIUM", "A01:2021"
    elif any(DB.search(f) for f in files):
        sev, cat = "MEDIUM", "A03:2021"
    elif files and all(DOC.search(f) for f in files):
        sev, cat = "INFO", "INFO"
    else:
        sev, cat = "LOW", "INFO"
    return {
        "severity": sev,
        "owasp_category": cat,
        "title": "Offline preflight (server unreachable)",
        "explanation": "Rule-based fallback. No LLM.",
        "files": files,
        "source": "offline",
    }


def analyze(files: list[str], cfg: dict) -> dict:
    url = str(cfg.get("server", {}).get("url", "http://127.0.0.1:8000")).rstrip("/")
    timeout = float(cfg.get("server", {}).get("timeout_seconds", 4))
    body = json.dumps({"changed_files": files, "source": "pre-commit"}).encode()
    req = urllib.request.Request(
        url + "/analyze",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            data["source"] = "server"
            return data
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return offline(files)


def main() -> int:
    files = staged()
    if not files:
        return 0
    cfg = load_cfg()
    adv = analyze(files, cfg)
    sev = str(adv.get("severity", "INFO"))
    print(f"[blt-preflight] {sev} {adv.get('owasp_category', '')} ({adv.get('source')})")
    print(f"  {adv.get('title', '')}")
    if adv.get("explanation"):
        print(f"  {adv['explanation']}")
    mode = str(cfg.get("hook_mode", "advisory"))
    min_sev = str(cfg.get("minimum_severity", "HIGH"))
    if mode == "blocking" and ORDER.index(sev) <= ORDER.index(min_sev):
        print("  hook_mode=blocking → commit aborted (advisory still non-merge-blocking on GitLab)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())