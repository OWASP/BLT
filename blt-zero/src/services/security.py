import hashlib
from datetime import datetime


def normalize_domain(input: str) -> str:
    """Normalize domain name to lowercase and trimmed."""
    return input.strip().lower()


def get_client_ip(req) -> str:
    """Get client IP from CF-Connecting-IP header."""
    return req.headers.get("CF-Connecting-IP", "0.0.0.0")


def minute_bucket_iso(date: datetime = None) -> str:
    """Generate a time bucket string for rate limiting (minute precision)."""
    if date is None:
        date = datetime.utcnow()
    
    return date.strftime("%Y-%m-%dT%H:%M")


async def sha256_hex(data: bytes) -> str:
    """Calculate SHA-256 hash and return as hex string."""
    return hashlib.sha256(data).hexdigest()
