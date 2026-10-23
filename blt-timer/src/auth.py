import hashlib
import hmac
import re
import secrets
from http.cookies import SimpleCookie
from urllib.parse import quote


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260000
SESSION_COOKIE_NAME = "blt_timer_session"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")


def hash_password(password, iterations=PASSWORD_HASH_ITERATIONS, salt=None):
    if not isinstance(password, str) or not password:
        raise ValueError("password is required")

    salt_bytes = salt if salt is not None else secrets.token_bytes(16)
    if isinstance(salt_bytes, str):
        salt_bytes = bytes.fromhex(salt_bytes)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        int(iterations),
    )
    return "$".join(
        [
            PASSWORD_HASH_ALGORITHM,
            str(int(iterations)),
            salt_bytes.hex(),
            password_hash.hex(),
        ]
    )


def verify_password(password, stored_hash):
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False

    try:
        algorithm, iterations, salt_hex, _expected_hex = stored_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        candidate = hash_password(password, int(iterations), salt_hex)
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(candidate, stored_hash)


def generate_session_token():
    return secrets.token_urlsafe(48)


def session_hash(token, secret):
    if not token or not secret:
        raise ValueError("session token and secret are required")

    return hmac.new(
        str(secret).encode("utf-8"),
        str(token).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def parse_cookie(header):
    if not header:
        return {}

    cookie = SimpleCookie()
    try:
        cookie.load(header)
    except Exception:
        return {}

    return {key: morsel.value for key, morsel in cookie.items()}


def build_session_cookie(token, max_age_seconds, secure=False):
    parts = [
        f"{SESSION_COOKIE_NAME}={quote(str(token), safe='')}",
        f"Max-Age={int(max_age_seconds)}",
        "HttpOnly",
        "SameSite=Lax",
        "Path=/",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def build_clear_session_cookie(secure=False):
    parts = [
        f"{SESSION_COOKIE_NAME}=",
        "Max-Age=0",
        "Expires=Thu, 01 Jan 1970 00:00:00 GMT",
        "HttpOnly",
        "SameSite=Lax",
        "Path=/",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def normalize_email(email):
    if not isinstance(email, str):
        raise ValueError("email is required")

    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise ValueError("valid email is required")
    return normalized


def normalize_username(username):
    if not isinstance(username, str):
        raise ValueError("username is required")

    normalized = username.strip().lower()
    if not USERNAME_RE.match(normalized):
        raise ValueError("username must be 3-32 characters and use letters, numbers, hyphens, or underscores")
    return normalized
