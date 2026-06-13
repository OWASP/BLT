"""User-owned jobs API handlers."""

import logging
from typing import Any, Dict

from libs.api_key import require_scope, SCOPE_WRITE_JOBS
from libs.db import get_db_safe
from libs.db_errors import database_error_response
from libs.user_context import get_request_user_id
from models import Job
from utils import error_response, json_response, paginated_response, parse_json_body, parse_pagination_params


logger = logging.getLogger(__name__)

_JOB_CREATE_REQUIRED = {"title", "description"}
_JOB_CREATE_FIELDS = {
    "title",
    "description",
    "company_name",
    "location",
    "url",
    "apply_url",
    "job_type",
    "salary_range",
    "status",
    "is_active",
    "expires_at",
}
_JOB_UPDATE_FIELDS = _JOB_CREATE_FIELDS - {"title"}
_JOB_STATUSES = {"draft", "open", "closed"}
_JOB_TYPES = {"full-time", "part-time", "contract", "internship", "other"}


def _normalize_bool(value: Any, field: str) -> int:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return 1 if value else 0


def _validate_job_payload(body: Dict[str, Any], *, partial: bool = False) -> Dict[str, Any]:
    if not partial:
        missing = sorted(field for field in _JOB_CREATE_REQUIRED if not body.get(field))
        if missing:
            raise ValueError("Missing required fields: " + ", ".join(missing))

    allowed = _JOB_UPDATE_FIELDS if partial else _JOB_CREATE_FIELDS
    forbidden = sorted(set(body) - allowed)
    if forbidden:
        raise ValueError("The following fields are not allowed: " + ", ".join(forbidden))

    updates: Dict[str, Any] = {}
    for field, value in body.items():
        if field not in allowed:
            continue

        if field in {"title", "description", "company_name", "location", "url", "apply_url", "job_type", "salary_range", "status", "expires_at"}:
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field} must be a string or null")
            if isinstance(value, str):
                value = value.strip()

        if field in {"title", "description"} and not value:
            raise ValueError(f"{field} is required")

        if field == "status" and value is not None and value not in _JOB_STATUSES:
            raise ValueError("status must be one of: " + ", ".join(sorted(_JOB_STATUSES)))

        if field == "job_type" and value is not None and value not in _JOB_TYPES:
            raise ValueError("job_type must be one of: " + ", ".join(sorted(_JOB_TYPES)))

        if field == "is_active":
            value = _normalize_bool(value, field)

        updates[field] = value

    if partial and not updates:
        raise ValueError("No valid fields to update")

    if not partial:
        updates.setdefault("status", "open")
        updates.setdefault("is_active", 1)
        updates.setdefault("views", 0)

    return updates


async def handle_jobs(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Handle user-owned jobs routes under /v2/jobs."""
    method = str(request.method).upper()
    user_id = get_request_user_id(request)
    if user_id is None:
        return error_response("User API key required", status=401)

    try:
        db = await get_db_safe(env)
    except Exception as exc:
        logger.error("Database connection error in jobs handler: %s", str(exc))
        return error_response("Database connection failed", status=503)

    try:
        if path.endswith("/stats") and method == "GET":
            return await _job_stats(db, user_id)

        if path.endswith("/view") and method == "POST":
            return await _view_job(db, path_params.get("id", ""), user_id)

        if "id" in path_params:
            return await _job_detail_or_update(db, request, method, path_params["id"], user_id)

        if method == "POST":
            err = require_scope(request, SCOPE_WRITE_JOBS)
            if err:
                return err
            body = await parse_json_body(request)
            if not body:
                return error_response("Request body is required", status=400)
            try:
                fields = _validate_job_payload(body, partial=False)
            except ValueError as exc:
                return error_response(str(exc), status=400)
            job = await Job.create(db, created_by_user_id=user_id, **fields)
            return json_response({"success": True, "message": "Job created successfully", "data": job}, status=201)

        if method != "GET":
            return error_response("Method Not Allowed", status=405, headers={"Allow": "GET, POST, PATCH"})

        page, per_page = parse_pagination_params(query_params)
        queryset = Job.objects(db).filter(created_by_user_id=user_id)
        status = query_params.get("status", "").strip()
        if status:
            if status not in _JOB_STATUSES:
                return error_response("Invalid status", status=400)
            queryset = queryset.filter(status=status)
        total = await queryset.count()
        jobs = await queryset.order_by("-created").paginate(page, per_page).all()
        return paginated_response(jobs, page=page, per_page=per_page, total=total)
    except Exception as exc:
        mapped_response = database_error_response(exc)
        if mapped_response is not None:
            logger.warning("Handled jobs database error: %s", str(exc))
            return mapped_response
        logger.error("Unexpected jobs handler error: %s", str(exc))
        return error_response("An internal error occurred", status=500)


async def _job_detail_or_update(db: Any, request: Any, method: str, job_id_str: str, user_id: int) -> Any:
    if not job_id_str.isdigit():
        return error_response("Invalid job ID", status=400)
    job_id = int(job_id_str)

    job = await Job.objects(db).get(id=job_id, created_by_user_id=user_id)
    if not job:
        return error_response("Job not found", status=404)

    if method == "GET":
        return json_response({"success": True, "data": job})

    if method != "PATCH":
        return error_response("Method Not Allowed", status=405, headers={"Allow": "GET, PATCH"})

    err = require_scope(request, SCOPE_WRITE_JOBS)
    if err:
        return err

    body = await parse_json_body(request)
    if not body:
        return error_response("Request body is required", status=400)
    try:
        updates = _validate_job_payload(body, partial=True)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    await Job.objects(db).filter(id=job_id, created_by_user_id=user_id).update(**updates)
    updated = await Job.objects(db).get(id=job_id, created_by_user_id=user_id)
    return json_response({"success": True, "message": "Job updated successfully", "data": updated})


async def _view_job(db: Any, job_id_str: str, user_id: int) -> Any:
    if not job_id_str.isdigit():
        return error_response("Invalid job ID", status=400)
    job_id = int(job_id_str)
    job = await Job.objects(db).get(id=job_id, created_by_user_id=user_id)
    if not job:
        return error_response("Job not found", status=404)

    views = int(job.get("views") or 0) + 1
    await Job.objects(db).filter(id=job_id, created_by_user_id=user_id).update(views=views)
    job["views"] = views
    return json_response({"success": True, "message": "Job view recorded", "data": {"id": job_id, "views": views}})


async def _job_stats(db: Any, user_id: int) -> Any:
    total = await Job.objects(db).filter(created_by_user_id=user_id).count()
    active = await Job.objects(db).filter(created_by_user_id=user_id, is_active=1).count()
    open_jobs = await Job.objects(db).filter(created_by_user_id=user_id, status="open").count()
    closed = await Job.objects(db).filter(created_by_user_id=user_id, status="closed").count()
    return json_response({
        "success": True,
        "data": {
            "total_jobs": total,
            "active_jobs": active,
            "open_jobs": open_jobs,
            "closed_jobs": closed,
        },
    })
