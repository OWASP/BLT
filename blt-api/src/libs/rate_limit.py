from typing import Any, Dict
import logging
import time
import uuid


logger = logging.getLogger(__name__)

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
    if ip:
        return ip

    # Avoid a shared fallback bucket when IP headers are unavailable.
    request_id = get_header(request, "X-Request-ID").strip()
    remote_addr = str(getattr(request, "remote_addr", "") or "").strip()

    logger.warning(
        "Missing client IP headers: CF-Connecting-IP and X-Forwarded-For are absent"
    )

    if request_id:
        return request_id
    if remote_addr:
        return remote_addr

    existing_fallback = str(getattr(request, "_rate_limit_fallback_key", "") or "").strip()
    if existing_fallback:
        return existing_fallback

    fallback = f"anon-{uuid.uuid4().hex[:10]}"
    try:
        setattr(request, "_rate_limit_fallback_key", fallback)
    except Exception:
        # Some request implementations may not allow dynamic attributes.
        pass
    return fallback

def is_rate_limited(client_key: str, rate_limit_dict: Dict[str, list], rate_limit_window_seconds: int, rate_limit_max_requests: int) -> bool:
    """Sliding-window in-memory rate limiter"""
    now = time.time()
    window_start = now - rate_limit_window_seconds

    attempts = rate_limit_dict.get(client_key, [])
    attempts = [ts for ts in attempts if ts >= window_start]

    _SWEEP_KEY = "\x00__last_sweep__"
    last_sweep = rate_limit_dict.get(_SWEEP_KEY, [0.0])
    if now - last_sweep[0] >= rate_limit_window_seconds:
        stale_keys = [
            key for key, timestamps in rate_limit_dict.items()
            if key != _SWEEP_KEY and key != client_key
            and (not timestamps or timestamps[-1] < window_start)
        ]
        for key in stale_keys:
            rate_limit_dict.pop(key, None)
        rate_limit_dict[_SWEEP_KEY] = [now]

    if len(attempts) >= rate_limit_max_requests:
        rate_limit_dict[client_key] = attempts
        return True

    attempts.append(now)
    rate_limit_dict[client_key] = attempts
    return False

