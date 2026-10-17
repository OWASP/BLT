import hashlib
import hmac
import re


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def normalize_email(email):
    if not isinstance(email, str):
        return ""

    return email.strip().lower()


def is_valid_email(email):
    normalized = normalize_email(email)
    if not normalized or len(normalized) > 254:
        return False

    if not EMAIL_PATTERN.match(normalized):
        return False

    local_part, domain = normalized.rsplit("@", 1)
    if len(local_part) > 64 or local_part.startswith(".") or local_part.endswith("."):
        return False

    if ".." in local_part or ".." in domain:
        return False

    return all(not label.startswith("-") and not label.endswith("-") for label in domain.split("."))


def email_hash(normalized_email, secret):
    if not secret:
        raise ValueError("email hash secret is required")

    email_value = normalize_email(normalized_email)
    return hmac.new(
        str(secret).encode("utf-8"),
        email_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def clean_name(name, max_length=120):
    if not isinstance(name, str):
        return None

    without_controls = re.sub(r"[\x00-\x1f\x7f]", " ", name)
    cleaned = re.sub(r"\s+", " ", without_controls).strip()
    if not cleaned:
        return None

    return cleaned[:max_length]
