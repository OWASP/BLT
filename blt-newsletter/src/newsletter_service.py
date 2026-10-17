import datetime
import json
import uuid

try:
    from .newsletter_validation import clean_name, email_hash, is_valid_email, normalize_email
except ImportError:  # pragma: no cover - used when the Worker loads src/ as its root.
    from newsletter_validation import clean_name, email_hash, is_valid_email, normalize_email


DEFAULT_CONSENT_VERSION = "2026-06-14"
DEFAULT_SOURCE = "landing_page"
PRIVACY_SAFE_UNSUBSCRIBE_MESSAGE = "If this email is subscribed, it has been unsubscribed."


def utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_subscriber_id():
    return "sub_" + uuid.uuid4().hex


async def subscribe(
    store,
    payload,
    secret,
    now_func=utc_timestamp,
    id_factory=new_subscriber_id,
):
    normalized = normalize_email(payload.get("email") if isinstance(payload, dict) else "")
    if not is_valid_email(normalized):
        return {
            "success": False,
            "error": "A valid email address is required.",
            "status_code": 400,
        }

    if not isinstance(payload, dict) or payload.get("consent") is not True:
        return {
            "success": False,
            "error": "Consent is required to subscribe.",
            "status_code": 400,
        }

    subscriber_hash = email_hash(normalized, secret)
    existing = await store.find_by_hash(subscriber_hash)
    if existing and existing.get("status") == "active":
        return {
            "success": True,
            "status": "active",
            "message": "You are already subscribed.",
            "status_code": 200,
        }

    timestamp = now_func()
    source = payload.get("source") or DEFAULT_SOURCE
    consent_version = payload.get("consent_version") or DEFAULT_CONSENT_VERSION
    subscriber_name = clean_name(payload.get("name"))

    if existing:
        await store.reactivate_subscriber(
            subscriber_hash,
            {
                "email": normalized,
                "name": subscriber_name if subscriber_name is not None else (existing.get("name") or ""),
                "status": "active",
                "source": source,
                "consent_version": consent_version,
                "subscribed_at": timestamp,
                "unsubscribed_at": None,
            },
        )
        return {
            "success": True,
            "status": "active",
            "message": "Subscription reactivated.",
            "status_code": 200,
        }

    await store.insert_subscriber(
        {
            "id": id_factory(),
            "email": normalized,
            "email_hash": subscriber_hash,
            "name": subscriber_name or "",
            "status": "active",
            "source": source,
            "consent_version": consent_version,
            "subscribed_at": timestamp,
            "unsubscribed_at": "",
            "last_sent_at": "",
            "bounce_count": 0,
            "metadata_json": json.dumps({}, separators=(",", ":")),
        }
    )
    return {
        "success": True,
        "status": "active",
        "message": "Subscription confirmed.",
        "status_code": 201,
    }


async def unsubscribe(store, payload, secret, now_func=utc_timestamp):
    normalized = normalize_email(payload.get("email") if isinstance(payload, dict) else "")
    if not is_valid_email(normalized):
        return {
            "success": False,
            "error": "A valid email address is required.",
            "status_code": 400,
        }

    subscriber_hash = email_hash(normalized, secret)
    await store.mark_unsubscribed(subscriber_hash, now_func())

    return {
        "success": True,
        "status": "unsubscribed",
        "message": PRIVACY_SAFE_UNSUBSCRIBE_MESSAGE,
        "status_code": 200,
    }
