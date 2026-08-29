#!/usr/bin/env python3
"""Vendor GitHub user-attachment media referenced by the static contest site."""

from __future__ import annotations

import mimetypes
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
ASSET_DIR = PUBLIC / "assets" / "entries"
PATTERN = re.compile(r"https://github\.com/user-attachments/assets/([A-Za-z0-9-]+)")
MIME_EXTENSIONS = {
    "image/avif": ".avif",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


def download(url: str, identifier: str) -> Path:
    existing = sorted(ASSET_DIR.glob(f"{identifier}.*"))
    if existing:
        # Prefer the checked-in, web-optimized representation. This is
        # especially important for QuickTime submissions transcoded to MP4.
        return existing[0]
    request = urllib.request.Request(url, headers={"User-Agent": "OWASP-BLT-asset-vendor/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        content_type = response.headers.get_content_type().lower()
        suffix = MIME_EXTENSIONS.get(content_type) or mimetypes.guess_extension(content_type) or ".bin"
        target = ASSET_DIR / f"{identifier}{suffix}"
        if not target.exists():
            target.write_bytes(response.read())
        return target


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    pages = sorted(PUBLIC.glob("*.html"))
    references: dict[str, str] = {}
    for page in pages:
        for match in PATTERN.finditer(page.read_text(encoding="utf-8")):
            references.setdefault(match.group(0), match.group(1))

    local: dict[str, str] = {}
    for number, (url, identifier) in enumerate(sorted(references.items()), 1):
        target = download(url, identifier)
        local[url] = f"assets/entries/{target.name}"
        print(f"[{number}/{len(references)}] {target.name}")

    for page in pages:
        source = page.read_text(encoding="utf-8")
        updated = source
        for remote, relative in local.items():
            updated = updated.replace(remote, relative)
        if updated != source:
            page.write_text(updated, encoding="utf-8")

    print(f"Vendored {len(local)} assets and updated {len(pages)} HTML pages")


if __name__ == "__main__":
    main()
