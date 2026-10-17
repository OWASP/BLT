"""Normalize domains for the shared crawl queue."""

from __future__ import annotations

from urllib.parse import urlparse

_DEFAULT_PORTS = {("http", 80), ("https", 443)}


def strip_www(host: str) -> str:
    host = host.lower().rstrip(".")
    if host.startswith("www."):
        return host[4:]
    return host


def normalize_domain(raw: str) -> tuple[str, str] | None:
    """Return ``(host_key, seed_url)`` or None if [raw] is not an http(s) host.

    host_key is lowercase, no leading ``www.``, no port unless non-default.
    seed_url is always ``https://{host_key}/`` (https preferred for scanning).
    """
    text = (raw or "").strip()
    if not text:
        return None
    if "://" in text:
        try:
            parsed = urlparse(text)
        except ValueError:
            return None
    else:
        head = text.split("/", 1)[0]
        if ":" in head:
            return None
        try:
            parsed = urlparse("https://" + text)
        except ValueError:
            return None
    if parsed.scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in {"localhost", "127.0.0.1", "::1"}:
        return None
    host = strip_www(host)
    if not host or "." not in host:
        return None
    port = parsed.port
    if port and (parsed.scheme, port) not in _DEFAULT_PORTS:
        host_key = f"{host}:{port}"
        seed_url = f"https://{host}:{port}/"
    else:
        host_key = host
        seed_url = f"https://{host}/"
    return host_key, seed_url
