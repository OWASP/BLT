"""User-owned hackathon API handlers."""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from libs.data_protection import blind_index, encrypt_sensitive
from libs.db_errors import database_error_response
from libs.db import get_db_safe
from libs.user_context import get_request_user_id
from models import Hackathon, HackathonRegistration
from utils import error_response, json_response, paginated_response, parse_json_body, parse_pagination_params


logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,98}[a-z0-9]$")
_HACKATHON_CREATE_REQUIRED = {"title", "slug", "starts_at", "ends_at"}
_HACKATHON_FIELDS = {
    "title",
    "slug",
    "description",
    "starts_at",
    "ends_at",
    "location",
    "url",
    "capacity",
    "is_published",
}


def _utc_now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = str(value).strip().replace("Z", "+00:00")
    if "T" not in normalized and "+" not in normalized:
        normalized = normalized.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hackathon_status(row: Dict[str, Any]) -> str:
    now = _parse_datetime(_utc_now()) or datetime.now(timezone.utc)
    starts_at = _parse_datetime(row.get("starts_at"))
    ends_at = _parse_datetime(row.get("ends_at"))
    if starts_at and now < starts_at:
        return "upcoming"
    if ends_at and now > ends_at:
        return "ended"
    return "ongoing"


def _with_status(row: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(row)
    enriched["status"] = _hackathon_status(enriched)
    return enriched


def _validate_hackathon_payload(body: Dict[str, Any], *, partial: bool = False) -> Dict[str, Any]:
    if not partial:
        missing = sorted(field for field in _HACKATHON_CREATE_REQUIRED if not body.get(field))
        if missing:
            raise ValueError("Missing required fields: " + ", ".join(missing))

    forbidden = sorted(set(body) - _HACKATHON_FIELDS)
    if forbidden:
        raise ValueError("The following fields are not allowed: " + ", ".join(forbidden))

    updates: Dict[str, Any] = {}
    for field, value in body.items():
        if field in {"title", "slug", "description", "starts_at", "ends_at", "location", "url"}:
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field} must be a string or null")
            if isinstance(value, str):
                value = value.strip()

        if field in {"title", "slug", "starts_at", "ends_at"} and not value:
            raise ValueError(f"{field} is required")

        if field == "slug" and value and not _SLUG_RE.match(value):
            raise ValueError("slug must be 3-100 lowercase letters, numbers, hyphens, or underscores")

        if field in {"starts_at", "ends_at"} and value and _parse_datetime(value) is None:
            raise ValueError(f"{field} must be an ISO datetime")

        if field == "capacity":
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                raise ValueError("capacity must be a positive integer or null")

        if field == "is_published":
            if not isinstance(value, bool):
                raise ValueError("is_published must be a boolean")
            value = 1 if value else 0

        updates[field] = value

    starts_at = updates.get("starts_at") if "starts_at" in updates else body.get("starts_at")
    ends_at = updates.get("ends_at") if "ends_at" in updates else body.get("ends_at")
    if starts_at and ends_at:
        parsed_start = _parse_datetime(starts_at)
        parsed_end = _parse_datetime(ends_at)
        if parsed_start and parsed_end and parsed_end <= parsed_start:
            raise ValueError("ends_at must be after starts_at")

    if partial and not updates:
        raise ValueError("No valid fields to update")

    if not partial:
        updates.setdefault("is_published", 1)

    return updates


async def handle_hackathons(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Handle user-owned hackathon routes under /v2/hackathons."""
    method = str(request.method).upper()
    user_id = get_request_user_id(request)
    if user_id is None:
        return error_response("User API key required", status=401)

    try:
        db = await get_db_safe(env)
    except Exception as exc:
        logger.error("Database connection error in hackathons handler: %s", str(exc))
        return error_response("Database connection failed", status=503)

    try:
        if path.endswith("/register") and method == "POST":
            return await _register_for_hackathon(db, request, env, path_params.get("id", ""), user_id)

        if method == "PATCH" and "id" in path_params:
            return await _update_hackathon(db, request, path_params["id"], user_id)

        if method == "GET" and "slug" in path_params:
            return await _get_hackathon(db, path_params["slug"], user_id)

        if method == "POST":
            body = await parse_json_body(request)
            if not body:
                return error_response("Request body is required", status=400)
            try:
                fields = _validate_hackathon_payload(body, partial=False)
            except ValueError as exc:
                return error_response(str(exc), status=400)
            hackathon = await Hackathon.create(db, created_by_user_id=user_id, **fields)
            return json_response({"success": True, "message": "Hackathon created successfully", "data": hackathon}, status=201)

        if method != "GET":
            return error_response("Method Not Allowed", status=405, headers={"Allow": "GET, POST, PATCH"})

        page, per_page = parse_pagination_params(query_params)
        queryset = Hackathon.objects(db).filter(created_by_user_id=user_id)
        total = await queryset.count()
        rows = await queryset.order_by("-starts_at").paginate(page, per_page).all()
        return paginated_response([_with_status(row) for row in rows], page=page, per_page=per_page, total=total)
    except Exception as exc:
        mapped_response = database_error_response(exc)
        if mapped_response is not None:
            logger.warning("Handled hackathons database error: %s", str(exc))
            return mapped_response
        logger.error("Unexpected hackathons handler error: %s", str(exc))
        return error_response("An internal error occurred", status=500)


async def _get_hackathon(db: Any, slug: str, user_id: int) -> Any:
    hackathon = await Hackathon.objects(db).get(slug=slug, created_by_user_id=user_id)
    if not hackathon:
        return error_response("Hackathon not found", status=404)
    registration_count = await HackathonRegistration.objects(db).filter(
        hackathon_id=hackathon["id"],
        status="registered",
    ).count()
    data = _with_status(hackathon)
    data["registration_count"] = registration_count
    return json_response({"success": True, "data": data})


async def _update_hackathon(db: Any, request: Any, hackathon_id_str: str, user_id: int) -> Any:
    if not hackathon_id_str.isdigit():
        return error_response("Invalid hackathon ID", status=400)
    hackathon_id = int(hackathon_id_str)
    existing = await Hackathon.objects(db).get(id=hackathon_id, created_by_user_id=user_id)
    if not existing:
        return error_response("Hackathon not found", status=404)

    body = await parse_json_body(request)
    if not body:
        return error_response("Request body is required", status=400)
    try:
        updates = _validate_hackathon_payload(body, partial=True)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    await Hackathon.objects(db).filter(id=hackathon_id, created_by_user_id=user_id).update(**updates)
    updated = await Hackathon.objects(db).get(id=hackathon_id, created_by_user_id=user_id)
    return json_response({"success": True, "message": "Hackathon updated successfully", "data": _with_status(updated or existing)})


async def _register_for_hackathon(db: Any, request: Any, env: Any, hackathon_id_str: str, user_id: int) -> Any:
    if not hackathon_id_str.isdigit():
        return error_response("Invalid hackathon ID", status=400)
    hackathon_id = int(hackathon_id_str)
    hackathon = await Hackathon.objects(db).get(id=hackathon_id, created_by_user_id=user_id)
    if not hackathon:
        return error_response("Hackathon not found", status=404)

    body = await parse_json_body(request)
    if not body:
        return error_response("Request body is required", status=400)

    email = str(body.get("email", "")).strip().lower()
    if "@" not in email or len(email) > 254:
        return error_response("Valid email is required", status=400)
    name = body.get("name")
    if name is not None and not isinstance(name, str):
        return error_response("name must be a string or null", status=400)
    if isinstance(name, str):
        name = name.strip() or None

    email_hash = blind_index(email, env, "hackathon_registrations.email")
    duplicate = await HackathonRegistration.objects(db).filter(
        hackathon_id=hackathon_id,
        participant_email_hash=email_hash,
    ).first()
    if duplicate:
        return error_response("Email is already registered for this hackathon", status=409)

    capacity = hackathon.get("capacity")
    if capacity is not None:
        registered_count = await HackathonRegistration.objects(db).filter(
            hackathon_id=hackathon_id,
            status="registered",
        ).count()
        if registered_count >= int(capacity):
            return error_response("Hackathon capacity has been reached", status=409)

    registration = await HackathonRegistration.create(
        db,
        hackathon_id=hackathon_id,
        created_by_user_id=user_id,
        participant_name=name,
        participant_email_encrypted=encrypt_sensitive(email, env),
        participant_email_hash=email_hash,
        status="registered",
    )
    safe_registration = dict(registration or {})
    safe_registration.pop("participant_email_encrypted", None)
    safe_registration.pop("participant_email_hash", None)
    return json_response({
        "success": True,
        "message": "Hackathon registration created successfully",
        "data": safe_registration,
    }, status=201)
