from typing import Any, Dict
import time

def get_header(request: Any, name: str) -> str:
    """Safely read a request header in Workers and tests"""
    headers = getattr(request, "headers", None)
    if headers and hasattr(headers, "get"):
        value = headers.get(name)
        return str(value) if value is not None else ""
    return ""


def get_client_ip(request: Any) -> str:
    """Extract the real client IP from headers"""
    ip = get_header(request, "CF-Connecting-IP").strip()
    if not ip:
        xff = get_header(request, "X-Forwarded-For")
        ip = xff.split(",")[0].strip() if xff else ""
    return ip or "unknown"

def is_rate_limited(client_key: str, rate_limit_dict: Dict[str, list], rate_limit_window_seconds: int, rate_limit_max_requests: int) -> bool:
    """Sliding-window in-memory rate limiter"""
    now = time.time()
    window_start = now - rate_limit_window_seconds

    attempts = rate_limit_dict.get(client_key, [])
    attempts = [ts for ts in attempts if ts >= window_start]

    stale_keys = [key for key, timestamps in rate_limit_dict.items() if not timestamps or timestamps[-1] < window_start]
    for key in stale_keys:
        if key != client_key:
            rate_limit_dict.pop(key, None)

    if len(attempts) >= rate_limit_max_requests:
        rate_limit_dict[client_key] = attempts
        return True

    attempts.append(now)
    rate_limit_dict[client_key] = attempts
    return False

