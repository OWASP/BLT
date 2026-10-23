#!/usr/bin/env python3
"""Screenshot each project's live site into public/screenshots/ for the Worker's KV.

Reads the ``live_url`` of every repo in public/forge_data.json (scripts/generate_forge_data.py)
and asks Cloudflare Browser Rendering (``/accounts/<id>/browser-rendering/screenshot``) for a
1280x800 JPEG of each, one at a time. Writes ``screenshots/<folder>.jpg`` and
``screenshots/index.json`` under SCREENSHOT_OUT (default public/). The daily workflow then
writes them to KV (scripts/worker-data/kv-put.sh) and the Worker serves them at
/screenshots/*.

A site that fails keeps yesterday's image: its entry is copied from the index.json currently
served (SCREENSHOT_PREVIOUS_INDEX, default https://waypoint.owaspblt.org/screenshots/index.json)
and its JPEG is not rewritten. SCREENSHOT_BUDGET_SECONDS (default 600) bounds the run; a 429
waits for Retry-After (or 20 s) and tries once more. Needs CLOUDFLARE_API_TOKEN (Browser
Rendering: Edit) and CLOUDFLARE_ACCOUNT_ID.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DATA = os.getenv("FORGE_DATA_OUT", os.path.join(PROJECT, "public", "forge_data.json"))
OUT = os.getenv("SCREENSHOT_OUT", os.path.join(PROJECT, "public"))
PREVIOUS = os.getenv("SCREENSHOT_PREVIOUS_INDEX", "https://waypoint.owaspblt.org/screenshots/index.json")
BUDGET = float(os.getenv("SCREENSHOT_BUDGET_SECONDS", "600"))
API = "https://api.cloudflare.com/client/v4/accounts/{account}/browser-rendering/screenshot"
WIDTH, HEIGHT = 1280, 800


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def targets(data):
    """[(folder, live_url)] for repos with a live site, in folder order."""
    rows = []
    for repo in data.get("repos") or []:
        folder, url = repo.get("folder"), repo.get("live_url")
        if folder and isinstance(url, str) and url.startswith("https://"):
            rows.append((folder, url))
    return sorted(rows)


def previous_index(url=PREVIOUS):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("shots") or {} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def request_body(url):
    return json.dumps({
        "url": url,
        "viewport": {"width": WIDTH, "height": HEIGHT},
        "screenshotOptions": {"type": "jpeg", "quality": 70},
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": 30000},
    }).encode("utf-8")


def capture(url, token, account, timeout=60):
    """JPEG bytes, or raises RetryLater(seconds) on 429, or OSError/ValueError."""
    request = urllib.request.Request(
        API.format(account=account), data=request_body(url), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise RetryLater(float(error.headers.get("Retry-After") or 20))
        raise
    if not body.startswith(b"\xff\xd8"):
        raise ValueError(f"not a JPEG ({body[:120]!r})")
    return body


class RetryLater(Exception):
    def __init__(self, seconds):
        super().__init__(seconds)
        self.seconds = min(max(seconds, 1.0), 60.0)


def run(data, token, account, out=OUT, budget=BUDGET, previous=None, clock=time.monotonic,
        sleep=time.sleep, shoot=capture):
    """Capture every target; returns (index payload, captured folders, failed folders)."""
    deadline = clock() + budget
    previous = previous if previous is not None else previous_index()
    folder_dir = os.path.join(out, "screenshots")
    os.makedirs(folder_dir, exist_ok=True)
    shots, captured, failed = {}, [], []
    for folder, url in targets(data):
        image = None
        for attempt in (1, 2):
            if clock() >= deadline:
                break
            try:
                image = shoot(url, token, account)
                break
            except RetryLater as wait:
                if attempt == 2 or clock() + wait.seconds >= deadline:
                    break
                sleep(wait.seconds)
            except (OSError, ValueError) as error:
                print(f"screenshots: {folder} ({url}) failed: {error}", file=sys.stderr)
                break
        if image:
            with open(os.path.join(folder_dir, f"{folder}.jpg"), "wb") as handle:
                handle.write(image)
            shots[folder] = {"url": f"/screenshots/{folder}.jpg", "captured_at": now_iso(),
                             "live_url": url, "width": WIDTH, "height": HEIGHT}
            captured.append(folder)
        else:
            failed.append(folder)
            if folder in previous:
                shots[folder] = previous[folder]
    payload = {"generated_at": now_iso(), "shots": dict(sorted(shots.items()))}
    with open(os.path.join(folder_dir, "index.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
        handle.write("\n")
    return payload, captured, failed


def main():
    token, account = os.getenv("CLOUDFLARE_API_TOKEN"), os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account:
        print("screenshots: CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID are required", file=sys.stderr)
        return 2
    with open(DATA, encoding="utf-8") as handle:
        data = json.load(handle)
    payload, captured, failed = run(data, token, account)
    print(f"screenshots: {len(captured)} captured, {len(failed)} kept from before or missing"
          f"{' (' + ', '.join(failed) + ')' if failed else ''}; {len(payload['shots'])} in the index")
    return 0 if captured else 1


if __name__ == "__main__":
    sys.exit(main())
