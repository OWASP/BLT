import datetime
import json
import uuid


def build_send_job_record(campaign_id, total_recipients, created_by_admin_id):
    now = utc_timestamp()
    created_by = created_by_admin_id or ""
    return {
        "id": "job_" + uuid.uuid4().hex,
        "campaign_id": campaign_id or "",
        "status": "queued",
        "provider": "sendgrid",
        "total_recipients": int(total_recipients or 0),
        "sent_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "started_at": "",
        "completed_at": "",
        "created_at": now,
        "created_by_admin_id": created_by,
        "metadata_json": json.dumps({"created_by_admin_id": created_by}, separators=(",", ":")),
    }


def build_delivery_event_record(job_id, subscriber_id, event_type, metadata=None):
    return {
        "id": "evt_" + uuid.uuid4().hex,
        "job_id": job_id or "",
        "subscriber_id": subscriber_id or "",
        "event_type": event_type or "",
        "provider_message_id": "",
        "occurred_at": utc_timestamp(),
        "metadata_json": json.dumps(safe_metadata(metadata), separators=(",", ":")),
    }


def build_queue_message(job_id, campaign_id, delivery_event_id, subscriber_id):
    return {
        "job_id": job_id or "",
        "campaign_id": campaign_id or "",
        "delivery_event_id": delivery_event_id or "",
        "subscriber_id": subscriber_id or "",
    }


def safe_metadata(metadata):
    if not isinstance(metadata, dict):
        return {}

    blocked = {"email", "api_key", "authorization", "password", "token"}
    safe = {}
    for key, value in metadata.items():
        key_text = str(key)
        if key_text.lower() in blocked:
            continue
        if value is None:
            safe[key_text] = ""
        elif isinstance(value, (str, int, float, bool)):
            safe[key_text] = value
        else:
            safe[key_text] = str(value)
    return safe


def utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
