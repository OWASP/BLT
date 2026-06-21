import datetime
import json
import re
import uuid
from urllib.parse import quote, unquote

from js import Headers, Request, Response, URL
try:
    from pyodide.ffi import to_js
except ImportError:  # pragma: no cover - local syntax checks outside Workers runtime.
    to_js = None
from workers import WorkerEntrypoint

try:
    from .admin_auth import (
        SESSION_COOKIE_NAME,
        build_clear_session_cookie,
        build_session_cookie,
        generate_session_token,
        hash_password,
        parse_cookie,
        session_hash,
        verify_password,
    )
    from .email_campaigns import (
        build_delivery_event_record,
        build_queue_message,
        build_send_job_record,
    )
    from .email_service import SendGridEmailService
    from .email_templates import render_newsletter_issue_email
    from .newsletter_service import subscribe, unsubscribe
    from .newsletter_validation import email_hash, is_valid_email, normalize_email
    from .newsletter_issue_schema import (
        issue_insert_columns_and_params,
        issue_order_expression,
        issue_select_columns,
        issue_slug_column,
        map_issue_update_fields,
    )
except ImportError:  # pragma: no cover - used when the Worker loads src/ as its root.
    from admin_auth import (
        SESSION_COOKIE_NAME,
        build_clear_session_cookie,
        build_session_cookie,
        generate_session_token,
        hash_password,
        parse_cookie,
        session_hash,
        verify_password,
    )
    from email_campaigns import (
        build_delivery_event_record,
        build_queue_message,
        build_send_job_record,
    )
    from email_service import SendGridEmailService
    from email_templates import render_newsletter_issue_email
    from newsletter_service import subscribe, unsubscribe
    from newsletter_validation import email_hash, is_valid_email, normalize_email
    from newsletter_issue_schema import (
        issue_insert_columns_and_params,
        issue_order_expression,
        issue_select_columns,
        issue_slug_column,
        map_issue_update_fields,
    )


ROUTES = {
    "/": "index.html",
    "/dashboard": "dashboard.html",
    "/login": "login.html",
    "/signup": "signup.html",
    "/docs": "docs.html",
}

CANONICAL_REDIRECTS = {
    "/dashboard.html": "/dashboard",
    "/login.html": "/login",
    "/signup.html": "/signup",
    "/docs.html": "/docs",
}

API_ROUTES = {
    "/api/subscribe",
    "/api/unsubscribe",
    "/unsubscribe",
    "/api/admin/login",
    "/api/admin/setup/status",
    "/api/admin/setup",
    "/api/admin/logout",
    "/api/admin/me",
    "/api/admin/stats",
    "/api/admin/subscribers",
    "/api/admin/issues",
    "/api/admin/jobs",
    "/api/issues",
}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
}

ADMIN_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
DEFAULT_EMAIL_HASH_SECRET = "development-email-hash-secret"
DEFAULT_ADMIN_SESSION_SECRET = "development-admin-session-secret"
ISSUE_STATUSES = {"draft", "published", "scheduled", "sent"}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = URL.new(request.url)
        path = normalize_path(url.pathname)

        if request.method == "OPTIONS":
            return cors_preflight_response()

        if path == "/api/subscribe":
            if request.method != "POST":
                return json_error("Method not allowed.", 405)
            return await self.handle_subscribe(request)

        if path == "/api/unsubscribe":
            if request.method != "POST":
                return json_error("Method not allowed.", 405)
            return await self.handle_unsubscribe(request)

        if path == "/unsubscribe":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_public_unsubscribe_page(request, url)

        if path == "/api/admin/setup/status":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_setup_status(request)

        if path == "/api/admin/setup":
            if request.method != "POST":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_setup(request)

        if path == "/api/admin/login":
            if request.method != "POST":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_login(request)

        if path == "/api/admin/logout":
            if request.method != "POST":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_logout(request)

        if path == "/api/admin/me":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_me(request)

        if path == "/api/admin/stats":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_stats(request)

        if path == "/api/admin/subscribers":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_subscribers(request)

        if path == "/api/admin/jobs":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_admin_jobs(request)

        if path.startswith("/api/admin/jobs/"):
            job_action = path[len("/api/admin/jobs/") :]
            if job_action.endswith("/cancel"):
                if request.method != "POST":
                    return json_error("Method not allowed.", 405)
                job_id = unquote(job_action[: -len("/cancel")])
                return await self.handle_admin_cancel_job(request, job_id)

            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            job_id = unquote(job_action)
            return await self.handle_admin_job_detail(request, job_id)

        if path == "/api/admin/issues":
            if request.method == "GET":
                return await self.handle_admin_issues(request)
            if request.method == "POST":
                return await self.handle_admin_create_issue(request)
            return json_error("Method not allowed.", 405)

        if path.startswith("/api/admin/issues/"):
            issue_action = path[len("/api/admin/issues/") :]
            if issue_action.endswith("/send-test"):
                if request.method != "POST":
                    return json_error("Method not allowed.", 405)
                issue_id = unquote(issue_action[: -len("/send-test")])
                return await self.handle_admin_send_test(request, issue_id)

            if issue_action.endswith("/send"):
                if request.method != "POST":
                    return json_error("Method not allowed.", 405)
                issue_id = unquote(issue_action[: -len("/send")])
                return await self.handle_admin_send_issue(request, issue_id)

            if request.method != "PATCH":
                return json_error("Method not allowed.", 405)
            issue_id = unquote(issue_action)
            return await self.handle_admin_patch_issue(request, issue_id)

        if path == "/api/issues":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_public_issues(request)

        if path.startswith("/api/issues/"):
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            slug = unquote(path[len("/api/issues/") :])
            return await self.handle_public_issue_detail(request, slug)

        if path == "/login":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_login_page(request)

        if path == "/signup":
            if request.method != "GET":
                return json_error("Method not allowed.", 405)
            return await self.handle_signup_page(request)

        if path in CANONICAL_REDIRECTS:
            return redirect_to(request, CANONICAL_REDIRECTS[path], 308)

        asset_name = ROUTES.get(path)
        if asset_name is not None:
            return await self.serve_asset(request, "/" + asset_name)

        return await self.env.ASSETS.fetch(request)

    async def handle_subscribe(self, request):
        return await self.handle_newsletter_request(request, subscribe)

    async def handle_unsubscribe(self, request):
        return await self.handle_newsletter_request(request, unsubscribe)

    async def handle_newsletter_request(self, request, action):
        payload = await safe_json(request)
        if payload is None:
            return json_error("Invalid JSON request body.", 400)

        db = get_db_binding(self.env)
        if db is None:
            return json_error("Newsletter service is temporarily unavailable.", 503)

        # Production should set EMAIL_HASH_SECRET as a Cloudflare secret. The
        # deterministic fallback keeps local development and tests repeatable.
        secret = get_env_value(self.env, "EMAIL_HASH_SECRET") or "development-email-hash-secret"
        store = D1SubscriberStore(db)

        try:
            result = await action(store, payload, secret)
        except Exception:
            return json_error("Newsletter request could not be processed.", 500)

        status_code = result.pop("status_code", 200)
        if not result.get("success"):
            return json_response(result, status_code)

        return json_response(result, status_code)

    async def handle_login_page(self, request):
        db = get_db_binding(self.env)
        if db is not None:
            try:
                admin_count = await D1SubscriberStore(db).admin_count()
                if admin_count == 0:
                    return redirect_to(request, "/signup", 302)
            except Exception:
                pass

        return await self.serve_asset(request, "/login.html")

    async def handle_signup_page(self, request):
        db = get_db_binding(self.env)
        if db is not None:
            try:
                admin_count = await D1SubscriberStore(db).admin_count()
                if admin_count > 0:
                    return redirect_to(request, "/login", 302)
            except Exception:
                pass

        return await self.serve_asset(request, "/signup.html")

    async def handle_admin_setup_status(self, request):
        db = get_db_binding(self.env)
        if db is None:
            return json_error("Admin setup is temporarily unavailable.", 503)

        try:
            admin_count = await D1SubscriberStore(db).admin_count()
        except Exception:
            return json_error("Admin setup status could not be loaded. Run D1 migrations first.", 503)

        return json_response(
            {
                "success": True,
                "setup_required": admin_count == 0,
                "admin_count": admin_count,
            }
        )

    async def handle_admin_setup(self, request):
        payload = await safe_json(request)
        if payload is None:
            return json_error("Invalid JSON request body.", 400)

        db = get_db_binding(self.env)
        if db is None:
            return json_error("Admin setup is temporarily unavailable.", 503)

        store = D1SubscriberStore(db)
        try:
            admin_count = await store.admin_count()
            if admin_count > 0:
                return json_error("First admin is already configured.", 409)

            now = utc_timestamp()
            admin, validation_error = build_admin_setup_record(
                payload,
                get_email_hash_secret(self.env),
                now,
            )
            if validation_error is not None:
                return json_error(validation_error, 400)

            await store.insert_first_admin_if_none(admin)
            created_admin = await store.find_admin_by_email_hash(admin["email_hash"])
            if not created_admin or created_admin.get("id") != admin["id"]:
                return json_error("First admin is already configured.", 409)
            admin = created_admin
            token = generate_session_token()
            await store.insert_admin_session(
                {
                    "id": new_session_id(),
                    "admin_id": admin["id"],
                    "session_hash": session_hash(token, get_admin_session_secret(self.env)),
                    "created_at": now,
                    "expires_at": utc_timestamp_after(ADMIN_SESSION_MAX_AGE_SECONDS),
                    "last_seen_at": now,
                    "metadata_json": "{}",
                }
            )
        except Exception:
            return json_error("First admin could not be created.", 500)

        cookie = build_session_cookie(
            token,
            ADMIN_SESSION_MAX_AGE_SECONDS,
            secure=should_use_secure_cookie(request, self.env),
        )
        return json_response(
            {"success": True, "admin": safe_admin_summary(admin)},
            status=201,
            extra_headers={"Set-Cookie": cookie},
        )

    async def handle_public_unsubscribe_page(self, request, url):
        subscriber_id = clean_issue_text(url.searchParams.get("subscriber_id"))
        token = clean_issue_text(url.searchParams.get("token"))
        if not subscriber_id or not token:
            return html_response(
                "Unsubscribe link invalid",
                "This unsubscribe link is missing required information.",
                status=400,
            )

        if not verify_unsubscribe_token(subscriber_id, token, get_admin_session_secret(self.env)):
            return html_response(
                "Unsubscribe link invalid",
                "This unsubscribe link is invalid or expired. Please contact the BLT team if you need help.",
                status=400,
            )

        db = get_db_binding(self.env)
        if db is None:
            return html_response(
                "Unsubscribe unavailable",
                "Newsletter unsubscribe is temporarily unavailable. Please try again later.",
                status=503,
            )

        try:
            await D1SubscriberStore(db).mark_subscriber_unsubscribed_by_id(subscriber_id, utc_timestamp())
        except Exception:
            return html_response(
                "Unsubscribe failed",
                "We could not process this unsubscribe request. Please try again later.",
                status=500,
            )

        return html_response(
            "You are unsubscribed",
            "This email has been removed from future BLT Newsletter campaigns.",
        )

    async def handle_admin_login(self, request):
        payload = await safe_json(request)
        if payload is None:
            return invalid_admin_login()

        normalized = normalize_email(payload.get("email"))
        password = payload.get("password")
        if not is_valid_email(normalized) or not isinstance(password, str):
            return invalid_admin_login()

        db = get_db_binding(self.env)
        if db is None:
            return json_error("Admin service is temporarily unavailable.", 503)

        store = D1SubscriberStore(db)
        email_secret = get_email_hash_secret(self.env)
        admin_hash = email_hash(normalized, email_secret)

        try:
            admin = await store.find_admin_by_email_hash(admin_hash)
            if (
                not admin
                or admin.get("status") != "active"
                or not verify_password(password, admin.get("password_hash"))
            ):
                return invalid_admin_login()

            now = utc_timestamp()
            expires_at = utc_timestamp_after(ADMIN_SESSION_MAX_AGE_SECONDS)
            token = generate_session_token()
            await store.insert_admin_session(
                {
                    "id": new_session_id(),
                    "admin_id": admin["id"],
                    "session_hash": session_hash(token, get_admin_session_secret(self.env)),
                    "created_at": now,
                    "expires_at": expires_at,
                    "last_seen_at": now,
                    "metadata_json": "{}",
                }
            )
            await store.update_admin_last_login(admin["id"], now)
            admin["last_login_at"] = now
        except Exception:
            return json_error("Admin login could not be processed.", 500)

        cookie = build_session_cookie(
            token,
            ADMIN_SESSION_MAX_AGE_SECONDS,
            secure=should_use_secure_cookie(request, self.env),
        )
        return json_response(
            {"success": True, "admin": safe_admin_summary(admin)},
            extra_headers={"Set-Cookie": cookie},
        )

    async def handle_admin_logout(self, request):
        db = get_db_binding(self.env)
        token = get_session_token(request)
        if db is not None and token:
            store = D1SubscriberStore(db)
            try:
                await store.revoke_session(
                    session_hash(token, get_admin_session_secret(self.env)),
                    utc_timestamp(),
                )
            except Exception:
                pass

        return json_response(
            {"success": True},
            extra_headers={
                "Set-Cookie": build_clear_session_cookie(
                    secure=should_use_secure_cookie(request, self.env)
                )
            },
        )

    async def handle_admin_me(self, request):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        return json_response({"success": True, "admin": context["admin"]})

    async def handle_admin_stats(self, request):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        try:
            stats = await context["store"].newsletter_stats()
        except Exception:
            return json_error("Admin stats could not be loaded.", 500)

        return json_response({"success": True, "stats": stats or {}})

    async def handle_admin_subscribers(self, request):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        try:
            subscribers = await context["store"].list_subscribers()
        except Exception:
            return json_error("Subscribers could not be loaded.", 500)

        return json_response({"success": True, "subscribers": subscribers})

    async def handle_admin_issues(self, request):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        try:
            issues = await context["store"].list_admin_issues()
        except Exception:
            return json_error("Issues could not be loaded.", 500)

        return json_response({"success": True, "issues": issues})

    async def handle_admin_create_issue(self, request):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        payload = await safe_json(request)
        if payload is None:
            return json_error("Invalid JSON request body.", 400)

        issue_data, validation_error = build_issue_create_record(payload, context["admin"]["id"])
        if validation_error is not None:
            return json_error(validation_error, 400)

        try:
            await context["store"].insert_issue(issue_data)
        except Exception:
            return json_error("Issue could not be created.", 500)

        return json_response({"success": True, "issue": issue_data}, status=201)

    async def handle_admin_send_test(self, request, issue_id):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        if not issue_id:
            return json_error("Issue id is required.", 400)

        payload = await safe_json(request)
        if payload is None:
            return json_error("Invalid JSON request body.", 400)

        to_email = normalize_email(payload.get("email"))
        if not is_valid_email(to_email):
            return json_error("A valid test recipient email is required.", 400)

        api_key, from_email, from_name = get_sendgrid_config(self.env)
        if not api_key or not from_email:
            return json_error(
                "Email sending is not configured. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL.",
                503,
            )

        try:
            issue = await context["store"].find_issue_by_id(issue_id)
        except Exception:
            return json_error("Issue could not be loaded.", 500)

        if not issue:
            return json_error("Issue not found.", 404)

        html = render_issue_email_html(
            issue,
            build_issue_archive_url(issue, request=request),
            build_unsubscribe_url(request=request),
        )
        service = SendGridEmailService(api_key, from_email, from_name)
        result = await service.send_email(
            to_email,
            issue_email_subject(issue),
            html,
            custom_args={
                "issue_id": issue_id,
                "admin_id": context["admin"]["id"],
                "message_type": "test",
            },
        )

        if result.get("success"):
            return json_response(
                {
                    "success": True,
                    "status": result.get("status"),
                    "provider": "sendgrid",
                }
            )

        return json_error(result.get("error") or "Test email could not be sent.", 502)

    async def handle_admin_send_issue(self, request, issue_id):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        if not issue_id:
            return json_error("Issue id is required.", 400)

        api_key, from_email, from_name = get_sendgrid_config(self.env)
        if not api_key or not from_email:
            return json_error(
                "Email sending is not configured. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL.",
                503,
            )

        try:
            issue = await context["store"].find_issue_by_id(issue_id)
            if not issue:
                return json_error("Issue not found.", 404)

            open_job = await context["store"].find_open_send_job_by_issue(issue_id)
            if open_job:
                return json_error("Campaign already queued for this issue.", 409)

            now = utc_timestamp()
            if issue.get("status") != "published":
                await context["store"].update_issue(
                    issue_id,
                    {
                        "status": "published",
                        "published_at": issue.get("published_at") or now,
                        "updated_at": now,
                    },
                )
                issue = await context["store"].find_issue_by_id(issue_id)

            subscribers = await context["store"].list_active_subscribers()
            job = build_send_job_record(issue_id, len(subscribers), context["admin"]["id"])
            if not subscribers:
                job["status"] = "completed"
                job["completed_at"] = utc_timestamp()

            await context["store"].insert_send_job(job)

            queue = get_queue_binding(self.env)
            queue_configured = queue is not None
            queued_messages = 0
            for subscriber in subscribers:
                delivery_event = build_delivery_event_record(
                    job["id"],
                    subscriber.get("id"),
                    "queued",
                    metadata={"issue_id": issue_id},
                )
                await context["store"].insert_delivery_event(delivery_event)
                if queue_configured:
                    message = build_queue_message(
                        job["id"],
                        issue_id,
                        delivery_event["id"],
                        subscriber.get("id"),
                    )
                    await send_queue_message(queue, message)
                    queued_messages += 1
        except Exception:
            return json_error("Campaign could not be queued.", 500)

        return json_response(
            {
                "success": True,
                "job": job,
                "queue_configured": queue_configured,
                "queued_messages": queued_messages,
            },
            status=202,
        )

    async def handle_admin_jobs(self, request):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        try:
            jobs = await context["store"].list_send_jobs()
        except Exception:
            return json_error("Campaign jobs could not be loaded.", 500)

        return json_response({"success": True, "jobs": jobs})

    async def handle_admin_job_detail(self, request, job_id):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        if not job_id:
            return json_error("Job id is required.", 400)

        try:
            job = await context["store"].find_send_job_by_id(job_id)
            if not job:
                return json_error("Job not found.", 404)
            events = await context["store"].list_delivery_events_for_job(job_id)
        except Exception:
            return json_error("Campaign job could not be loaded.", 500)

        return json_response({"success": True, "job": job, "events": events})

    async def handle_admin_cancel_job(self, request, job_id):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        if not job_id:
            return json_error("Job id is required.", 400)

        try:
            job = await context["store"].find_send_job_by_id(job_id)
            if not job:
                return json_error("Job not found.", 404)

            if job.get("status") not in {"queued", "running", "sending"}:
                return json_error("Only queued or running jobs can be canceled.", 409)

            await context["store"].update_send_job_status(job_id, "canceled")
            job = await context["store"].find_send_job_by_id(job_id)
        except Exception:
            return json_error("Campaign job could not be canceled.", 500)

        return json_response({"success": True, "job": job})

    async def handle_admin_patch_issue(self, request, issue_id):
        context, error_response = await self.require_admin(request)
        if error_response is not None:
            return error_response

        if not issue_id:
            return json_error("Issue id is required.", 400)

        payload = await safe_json(request)
        if payload is None:
            return json_error("Invalid JSON request body.", 400)

        updates, validation_error = build_issue_updates(payload)
        if validation_error is not None:
            return json_error(validation_error, 400)

        try:
            existing = await context["store"].find_issue_by_id(issue_id)
            if not existing:
                return json_error("Issue not found.", 404)

            await context["store"].update_issue(issue_id, updates)
            issue = await context["store"].find_issue_by_id(issue_id)
        except Exception:
            return json_error("Issue could not be updated.", 500)

        return json_response({"success": True, "issue": issue})

    async def handle_public_issues(self, request):
        db = get_db_binding(self.env)
        if db is None:
            return json_error("Newsletter archive is temporarily unavailable.", 503)

        try:
            issues = await D1SubscriberStore(db).list_published_issues()
        except Exception:
            return json_error("Newsletter archive could not be loaded.", 500)

        return json_response({"success": True, "issues": issues})

    async def handle_public_issue_detail(self, request, slug):
        db = get_db_binding(self.env)
        if db is None:
            return json_error("Newsletter archive is temporarily unavailable.", 503)

        if not slug:
            return json_error("Issue not found.", 404)

        try:
            issue = await D1SubscriberStore(db).find_published_issue_by_slug(slug)
        except Exception:
            return json_error("Newsletter issue could not be loaded.", 500)

        if not issue:
            return json_error("Issue not found.", 404)

        return json_response({"success": True, "issue": issue})

    async def require_admin(self, request):
        db = get_db_binding(self.env)
        if db is None:
            return None, json_error("Admin service is temporarily unavailable.", 503)

        token = get_session_token(request)
        if not token:
            return None, json_error("Authentication required.", 401)

        store = D1SubscriberStore(db)
        try:
            session = await store.find_active_session(
                session_hash(token, get_admin_session_secret(self.env)),
                utc_timestamp(),
            )
        except Exception:
            return None, json_error("Authentication required.", 401)

        if not session:
            return None, json_error("Authentication required.", 401)

        return {"store": store, "session": session, "admin": safe_admin_summary(session)}, None

    async def queue(self, batch):
        db = get_db_binding(self.env)
        messages = get_queue_batch_messages(batch)
        if db is None:
            for message in messages:
                await retry_queue_message(message)
            return

        store = D1SubscriberStore(db)
        for message in messages:
            try:
                await self.process_queue_message(store, message)
            except Exception:
                await retry_queue_message(message)

    async def process_queue_message(self, store, message):
        body = get_queue_message_body(message)
        job_id = body.get("job_id") or ""
        issue_id = body.get("issue_id") or ""
        subscriber_id = body.get("subscriber_id") or ""

        if not job_id or not issue_id or not subscriber_id:
            await ack_queue_message(message)
            return

        job = await store.find_send_job_by_id(job_id)
        if not job or job.get("status") in {"canceled", "completed"}:
            await ack_queue_message(message)
            return

        issue = await store.find_issue_by_id(issue_id)
        subscriber = await store.find_subscriber_by_id(subscriber_id)
        if not issue or not subscriber:
            await ack_queue_message(message)
            return

        if subscriber.get("status") != "active" or not subscriber.get("email"):
            skipped_event = build_delivery_event_record(
                job_id,
                subscriber_id,
                "skipped",
                metadata={"reason": "subscriber_not_active"},
            )
            await store.insert_delivery_event(skipped_event)
            await ack_queue_message(message)
            return

        api_key, from_email, from_name = get_sendgrid_config(self.env)
        if not api_key or not from_email:
            await retry_queue_message(message)
            return

        html = render_issue_email_html(
            issue,
            build_issue_archive_url(issue, env=self.env),
            build_unsubscribe_url(subscriber_id=subscriber_id, env=self.env),
        )
        service = SendGridEmailService(api_key, from_email, from_name)
        result = await service.send_email(
            subscriber["email"],
            issue_email_subject(issue),
            html,
            custom_args={"job_id": job_id, "issue_id": issue_id, "subscriber_id": subscriber_id},
        )

        event_type = "sent" if result.get("success") else "failed"
        event = build_delivery_event_record(
            job_id,
            subscriber_id,
            event_type,
            metadata={
                "sendgrid_status": result.get("status", 0),
                "retryable": bool(result.get("retryable")),
            },
        )
        event["provider_message_id"] = result.get("provider_message_id") or ""
        await store.insert_delivery_event(event)

        if result.get("success"):
            await store.increment_send_job_counts(job_id, sent_delta=1, failed_delta=0)
            await store.mark_subscriber_sent(subscriber_id, utc_timestamp())
            await ack_queue_message(message)
            return

        if result.get("retryable"):
            await retry_queue_message(message)
            return

        await store.increment_send_job_counts(job_id, sent_delta=0, failed_delta=1)
        await ack_queue_message(message)

    async def serve_asset(self, request, pathname):
        url = URL.new(request.url)
        url.pathname = pathname
        url.search = ""
        asset_request = Request.new(url.toString())

        return await self.env.ASSETS.fetch(asset_request)


class D1SubscriberStore:
    def __init__(self, db):
        self.db = db
        self._issue_columns = None

    async def find_by_hash(self, subscriber_hash):
        row = await self._first(
            """
            SELECT id, email, email_hash, name, status, source, consent_version,
                   subscribed_at, unsubscribed_at, last_sent_at, bounce_count,
                   metadata_json
            FROM newsletter_subscribers
            WHERE email_hash = ?
            LIMIT 1
            """,
            subscriber_hash,
        )
        return js_to_py(row)

    async def insert_subscriber(self, record):
        await self._run(
            """
            INSERT INTO newsletter_subscribers (
              id, email, email_hash, name, status, source, consent_version,
              subscribed_at, unsubscribed_at, last_sent_at, bounce_count,
              metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            record["id"],
            record["email"],
            record["email_hash"],
            record.get("name"),
            record["status"],
            record["source"],
            record["consent_version"],
            record["subscribed_at"],
            record.get("unsubscribed_at"),
            record.get("last_sent_at"),
            record["bounce_count"],
            record["metadata_json"],
        )

    async def reactivate_subscriber(self, subscriber_hash, updates):
        await self._run(
            """
            UPDATE newsletter_subscribers
            SET email = ?,
                name = COALESCE(?, name),
                status = 'active',
                source = ?,
                consent_version = ?,
                subscribed_at = ?,
                unsubscribed_at = NULL
            WHERE email_hash = ?
            """,
            updates["email"],
            updates.get("name"),
            updates["source"],
            updates["consent_version"],
            updates["subscribed_at"],
            subscriber_hash,
        )

    async def mark_unsubscribed(self, subscriber_hash, unsubscribed_at):
        await self._run(
            """
            UPDATE newsletter_subscribers
            SET status = 'unsubscribed',
                unsubscribed_at = ?
            WHERE email_hash = ?
            """,
            unsubscribed_at,
            subscriber_hash,
        )

    async def admin_count(self):
        row = await self._first(
            """
            SELECT COUNT(*) AS total_admins
            FROM newsletter_admins
            """
        )
        value = js_to_py(row) or {}
        return int(value.get("total_admins") or 0)

    async def insert_admin(self, record):
        await self._run(
            """
            INSERT INTO newsletter_admins (
              id, email, email_hash, name, role, password_hash, status,
              created_at, updated_at, last_login_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            record["id"],
            record["email"],
            record["email_hash"],
            record["name"],
            record["role"],
            record["password_hash"],
            record["status"],
            record["created_at"],
            record["updated_at"],
            record["last_login_at"],
            record["metadata_json"],
        )

    async def insert_first_admin_if_none(self, record):
        await self._run(
            """
            INSERT INTO newsletter_admins (
              id, email, email_hash, name, role, password_hash, status,
              created_at, updated_at, last_login_at, metadata_json
            )
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM newsletter_admins LIMIT 1)
            """,
            record["id"],
            record["email"],
            record["email_hash"],
            record["name"],
            record["role"],
            record["password_hash"],
            record["status"],
            record["created_at"],
            record["updated_at"],
            record["last_login_at"],
            record["metadata_json"],
        )

    async def find_admin_by_email_hash(self, admin_email_hash):
        row = await self._first(
            """
            SELECT id, email, email_hash, name, role, password_hash, status,
                   created_at, updated_at, last_login_at, metadata_json
            FROM newsletter_admins
            WHERE email_hash = ?
            LIMIT 1
            """,
            admin_email_hash,
        )
        return js_to_py(row)

    async def update_admin_last_login(self, admin_id, last_login_at):
        await self._run(
            """
            UPDATE newsletter_admins
            SET last_login_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            last_login_at,
            last_login_at,
            admin_id,
        )

    async def insert_admin_session(self, record):
        await self._run(
            """
            INSERT INTO newsletter_admin_sessions (
              id, admin_id, session_hash, created_at, expires_at,
              last_seen_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            record["id"],
            record["admin_id"],
            record["session_hash"],
            record["created_at"],
            record["expires_at"],
            record.get("last_seen_at"),
            record["metadata_json"],
        )

    async def find_active_session(self, admin_session_hash, now):
        row = await self._first(
            """
            SELECT s.id AS session_id, s.admin_id, s.expires_at, s.last_seen_at,
                   a.id, a.email, a.email_hash, a.name, a.role, a.status,
                   a.created_at, a.updated_at, a.last_login_at, a.metadata_json
            FROM newsletter_admin_sessions s
            JOIN newsletter_admins a ON a.id = s.admin_id
            WHERE s.session_hash = ?
              AND s.revoked_at IS NULL
              AND s.expires_at > ?
              AND a.status = 'active'
            LIMIT 1
            """,
            admin_session_hash,
            now,
        )
        return js_to_py(row)

    async def revoke_session(self, admin_session_hash, revoked_at):
        await self._run(
            """
            UPDATE newsletter_admin_sessions
            SET revoked_at = ?
            WHERE session_hash = ?
              AND revoked_at IS NULL
            """,
            revoked_at,
            admin_session_hash,
        )

    async def newsletter_stats(self):
        row = await self._first(
            """
            SELECT
              COUNT(*) AS total_subscribers,
              SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_subscribers,
              SUM(CASE WHEN status = 'unsubscribed' THEN 1 ELSE 0 END) AS unsubscribed_subscribers
            FROM newsletter_subscribers
            """
        )
        stats = js_to_py(row) or {}
        issue_stats = await self._first(
            """
            SELECT
              COUNT(*) AS total_issues,
              SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) AS published_issues,
              SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) AS draft_issues
            FROM newsletter_issues
            """
        )
        stats.update(js_to_py(issue_stats) or {})
        return stats

    async def list_subscribers(self, limit=100):
        return await self._all(
            """
            SELECT id, email, name, status, source, consent_version,
                   subscribed_at, unsubscribed_at, last_sent_at, bounce_count,
                   metadata_json
            FROM newsletter_subscribers
            ORDER BY subscribed_at DESC
            LIMIT ?
            """,
            limit,
        )

    async def list_active_subscribers(self, limit=10000):
        return await self._all(
            """
            SELECT id, email, email_hash, name, status, source, consent_version,
                   subscribed_at, unsubscribed_at, last_sent_at, bounce_count,
                   metadata_json
            FROM newsletter_subscribers
            WHERE status = 'active'
            ORDER BY subscribed_at ASC
            LIMIT ?
            """,
            limit,
        )

    async def find_subscriber_by_id(self, subscriber_id):
        row = await self._first(
            """
            SELECT id, email, email_hash, name, status, source, consent_version,
                   subscribed_at, unsubscribed_at, last_sent_at, bounce_count,
                   metadata_json
            FROM newsletter_subscribers
            WHERE id = ?
            LIMIT 1
            """,
            subscriber_id,
        )
        return js_to_py(row)

    async def mark_subscriber_sent(self, subscriber_id, last_sent_at):
        await self._run(
            """
            UPDATE newsletter_subscribers
            SET last_sent_at = ?
            WHERE id = ?
            """,
            last_sent_at,
            subscriber_id,
        )

    async def mark_subscriber_unsubscribed_by_id(self, subscriber_id, unsubscribed_at):
        await self._run(
            """
            UPDATE newsletter_subscribers
            SET status = 'unsubscribed',
                unsubscribed_at = ?
            WHERE id = ?
            """,
            unsubscribed_at,
            subscriber_id,
        )

    async def issue_table_columns(self):
        if self._issue_columns is not None:
            return self._issue_columns

        rows = await self._all("SELECT name FROM pragma_table_info('newsletter_issues')")
        self._issue_columns = [row.get("name") for row in rows if isinstance(row, dict) and row.get("name")]
        return self._issue_columns

    async def list_admin_issues(self, limit=100):
        columns = await self.issue_table_columns()
        select_columns = ", ".join(issue_select_columns(columns))
        return await self._all(
            f"""
            SELECT {select_columns}
            FROM newsletter_issues
            ORDER BY created_at DESC
            LIMIT ?
            """,
            limit,
        )

    async def list_published_issues(self, limit=50):
        columns = await self.issue_table_columns()
        select_columns = ", ".join(issue_select_columns(columns, include_created_by=False))
        order_expression = issue_order_expression(columns)
        return await self._all(
            f"""
            SELECT {select_columns}
            FROM newsletter_issues
            WHERE status = 'published'
            ORDER BY {order_expression} DESC
            LIMIT ?
            """,
            limit,
        )

    async def find_published_issue_by_slug(self, slug):
        columns = await self.issue_table_columns()
        select_columns = ", ".join(issue_select_columns(columns, include_created_by=False))
        slug_column = issue_slug_column(columns)
        row = await self._first(
            f"""
            SELECT {select_columns}
            FROM newsletter_issues
            WHERE status = 'published'
              AND {slug_column} = ?
            LIMIT 1
            """,
            slug,
        )
        return js_to_py(row)

    async def find_issue_by_id(self, issue_id):
        columns = await self.issue_table_columns()
        select_columns = ", ".join(issue_select_columns(columns))
        row = await self._first(
            f"""
            SELECT {select_columns}
            FROM newsletter_issues
            WHERE id = ?
            LIMIT 1
            """,
            issue_id,
        )
        return js_to_py(row)

    async def insert_issue(self, record):
        columns = await self.issue_table_columns()
        insert_columns, params = issue_insert_columns_and_params(record, columns)
        placeholders = ", ".join("?" for _ in insert_columns)
        await self._run(
            f"""
            INSERT INTO newsletter_issues (
              {", ".join(insert_columns)}
            )
            VALUES ({placeholders})
            """,
            *params,
        )

    async def insert_send_job(self, record):
        await self._run(
            """
            INSERT INTO newsletter_send_jobs (
              id, issue_id, status, provider, total_recipients, sent_count,
              failed_count, started_at, completed_at, created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            record["id"],
            record["issue_id"],
            record["status"],
            record["provider"],
            record["total_recipients"],
            record["sent_count"],
            record["failed_count"],
            record.get("started_at") or "",
            record.get("completed_at") or "",
            record["created_at"],
            record["metadata_json"],
        )

    async def find_open_send_job_by_issue(self, issue_id):
        row = await self._first(
            """
            SELECT id, issue_id, status, provider, total_recipients, sent_count,
                   failed_count, started_at, completed_at, created_at, metadata_json
            FROM newsletter_send_jobs
            WHERE issue_id = ?
              AND status IN ('queued', 'running', 'sending')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            issue_id,
        )
        return js_to_py(row)

    async def list_send_jobs(self, limit=100):
        return await self._all(
            """
            SELECT j.id, j.issue_id, i.title AS issue_title, i.subject AS issue_subject,
                   j.status, j.provider, j.total_recipients, j.sent_count,
                   j.failed_count, j.started_at, j.completed_at, j.created_at,
                   j.metadata_json
            FROM newsletter_send_jobs j
            LEFT JOIN newsletter_issues i ON i.id = j.issue_id
            ORDER BY j.created_at DESC
            LIMIT ?
            """,
            limit,
        )

    async def find_send_job_by_id(self, job_id):
        row = await self._first(
            """
            SELECT j.id, j.issue_id, i.title AS issue_title, i.subject AS issue_subject,
                   j.status, j.provider, j.total_recipients, j.sent_count,
                   j.failed_count, j.started_at, j.completed_at, j.created_at,
                   j.metadata_json
            FROM newsletter_send_jobs j
            LEFT JOIN newsletter_issues i ON i.id = j.issue_id
            WHERE j.id = ?
            LIMIT 1
            """,
            job_id,
        )
        return js_to_py(row)

    async def update_send_job_status(self, job_id, status):
        now = utc_timestamp()
        await self._run(
            """
            UPDATE newsletter_send_jobs
            SET status = ?,
                completed_at = CASE
                  WHEN ? IN ('canceled', 'completed') THEN ?
                  ELSE completed_at
                END
            WHERE id = ?
            """,
            status,
            status,
            now,
            job_id,
        )

    async def insert_delivery_event(self, record):
        await self._run(
            """
            INSERT INTO newsletter_delivery_events (
              id, job_id, subscriber_id, event_type, provider_message_id,
              occurred_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            record["id"],
            record.get("job_id") or "",
            record.get("subscriber_id") or "",
            record["event_type"],
            record.get("provider_message_id") or "",
            record.get("occurred_at") or utc_timestamp(),
            record.get("metadata_json") or "{}",
        )

    async def list_delivery_events_for_job(self, job_id, limit=200):
        return await self._all(
            """
            SELECT id, job_id, subscriber_id, event_type, provider_message_id,
                   occurred_at, metadata_json
            FROM newsletter_delivery_events
            WHERE job_id = ?
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            job_id,
            limit,
        )

    async def increment_send_job_counts(self, job_id, sent_delta=0, failed_delta=0):
        now = utc_timestamp()
        await self._run(
            """
            UPDATE newsletter_send_jobs
            SET sent_count = sent_count + ?,
                failed_count = failed_count + ?,
                started_at = CASE
                  WHEN started_at IS NULL OR started_at = '' THEN ?
                  ELSE started_at
                END,
                completed_at = CASE
                  WHEN sent_count + ? + failed_count + ? >= total_recipients THEN ?
                  ELSE completed_at
                END,
                status = CASE
                  WHEN sent_count + ? + failed_count + ? >= total_recipients THEN 'completed'
                  ELSE 'running'
                END
            WHERE id = ?
            """,
            int(sent_delta or 0),
            int(failed_delta or 0),
            now,
            int(sent_delta or 0),
            int(failed_delta or 0),
            now,
            int(sent_delta or 0),
            int(failed_delta or 0),
            job_id,
        )

    async def update_issue(self, issue_id, updates):
        columns = await self.issue_table_columns()
        mapped_updates = map_issue_update_fields(updates, columns)
        if not mapped_updates:
            return

        assignments = []
        params = []
        for column, value in mapped_updates.items():
            assignments.append(f"{column} = ?")
            params.append(value)

        params.append(issue_id)
        await self._run(
            f"""
            UPDATE newsletter_issues
            SET {", ".join(assignments)}
            WHERE id = ?
            """,
            *params,
        )

    async def _first(self, query, *params):
        statement = bind_statement(self.db.prepare(query), params)
        return await statement.first()

    async def _run(self, query, *params):
        statement = bind_statement(self.db.prepare(query), params)
        return await statement.run()

    async def _all(self, query, *params):
        statement = bind_statement(self.db.prepare(query), params)
        result = js_to_py(await statement.all())
        if isinstance(result, dict):
            rows = result.get("results")
            return rows if isinstance(rows, list) else []

        return result if isinstance(result, list) else []


def bind_statement(statement, params):
    if not params:
        return statement

    # Python None can cross the Pyodide boundary as JavaScript undefined in
    # some positional vararg calls. D1 rejects undefined values, so convert the
    # argument list explicitly; Pyodide maps Python None to JavaScript null.
    if to_js is not None:
        return statement.bind(*to_js(list(params)))

    return statement.bind(*params)


def normalize_path(path):
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")

    return path


def redirect_to(request, pathname, status=302):
    url = URL.new(request.url)
    url.pathname = pathname
    url.search = ""
    return Response.redirect(url.toString(), status)


def utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_timestamp_after(seconds):
    timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
    return timestamp.replace(microsecond=0).isoformat() + "Z"


def new_session_id():
    return "sess_" + uuid.uuid4().hex


def new_admin_id():
    return "adm_" + uuid.uuid4().hex


def new_issue_id():
    return "issue_" + uuid.uuid4().hex


def get_email_hash_secret(env):
    return get_env_value(env, "EMAIL_HASH_SECRET") or DEFAULT_EMAIL_HASH_SECRET


def get_admin_session_secret(env):
    return get_env_value(env, "ADMIN_SESSION_SECRET") or DEFAULT_ADMIN_SESSION_SECRET


def should_use_secure_cookie(request, env):
    configured = get_env_value(env, "ADMIN_COOKIE_SECURE")
    if isinstance(configured, str):
        return configured.lower() in {"1", "true", "yes", "on"}

    if configured is not None:
        return bool(configured)

    try:
        return str(request.url).startswith("https://")
    except Exception:
        return False


def get_request_header(request, name):
    try:
        return request.headers.get(name)
    except Exception:
        pass

    try:
        return request.headers[name]
    except Exception:
        return None


def get_session_token(request):
    cookies = parse_cookie(get_request_header(request, "Cookie"))
    return cookies.get(SESSION_COOKIE_NAME)


def safe_admin_summary(admin):
    return {
        "id": admin.get("id"),
        "email": admin.get("email"),
        "name": admin.get("name") or "",
        "role": admin.get("role") or "admin",
        "last_login_at": admin.get("last_login_at"),
    }


def invalid_admin_login():
    return json_error("Invalid email or password.", 401)


def build_admin_setup_record(payload, email_secret, now):
    normalized = normalize_email(payload.get("email"))
    password = payload.get("password")
    name = clean_optional_text(payload.get("name"))

    if not is_valid_email(normalized):
        return None, "A valid admin email is required."

    if not isinstance(password, str) or len(password) < 8:
        return None, "Password must be at least 8 characters."

    return {
        "id": new_admin_id(),
        "email": normalized,
        "email_hash": email_hash(normalized, email_secret),
        "name": name,
        "role": "admin",
        "password_hash": hash_password(password),
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "last_login_at": now,
        "metadata_json": "{}",
    }, None


def clean_issue_text(value):
    if not isinstance(value, str):
        return ""

    return value.strip()


def validate_issue_required_text(payload, field_name):
    value = clean_issue_text(payload.get(field_name))
    if not value:
        return None, f"{field_name} is required."

    return value, None


def validate_issue_slug(slug):
    value = clean_issue_text(slug)
    if not value:
        return None, "slug is required."

    if not SLUG_PATTERN.match(value):
        return None, "slug must use lowercase letters, numbers, and hyphens."

    return value, None


def build_issue_create_record(payload, admin_id):
    title, error = validate_issue_required_text(payload, "title")
    if error:
        return None, error

    slug, error = validate_issue_slug(payload.get("slug"))
    if error:
        return None, error

    subject, error = validate_issue_required_text(payload, "subject")
    if error:
        return None, error

    markdown_body, error = validate_issue_required_text(payload, "markdown_body")
    if error:
        return None, error

    now = utc_timestamp()
    return {
        "id": new_issue_id(),
        "slug": slug,
        "title": title,
        "subject": subject,
        "summary": clean_optional_text(payload.get("summary")) or "",
        "status": "draft",
        "markdown_body": markdown_body,
        "html_body": "",
        "scheduled_for": "",
        "published_at": "",
        "sent_at": "",
        "created_by_admin_id": admin_id,
        "created_at": now,
        "updated_at": now,
        "metadata_json": "{}",
    }, None


def build_issue_updates(payload):
    allowed_fields = {
        "title",
        "slug",
        "subject",
        "summary",
        "markdown_body",
        "status",
    }
    updates = {}

    for field_name in allowed_fields:
        if field_name not in payload:
            continue

        if field_name == "slug":
            value, error = validate_issue_slug(payload.get(field_name))
            if error:
                return None, error
        elif field_name == "status":
            value = clean_issue_text(payload.get(field_name))
            if value not in ISSUE_STATUSES:
                return None, "status is invalid."
        elif field_name == "summary":
            value = clean_optional_text(payload.get(field_name))
        else:
            value, error = validate_issue_required_text(payload, field_name)
            if error:
                return None, error

        updates[field_name] = value

    if not updates:
        return None, "At least one issue field is required."

    now = utc_timestamp()
    if updates.get("status") == "published":
        updates["published_at"] = now

    updates["updated_at"] = now
    return updates, None


def clean_optional_text(value):
    cleaned = clean_issue_text(value)
    return cleaned or ""


async def safe_json(request):
    try:
        payload = await request.json()
    except Exception:
        return None

    payload = js_to_py(payload)
    if not isinstance(payload, dict):
        return None

    return payload


def html_response(title, message, status=200):
    body = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>" + escape_html_text(title) + "</title>"
        "<style>body{font-family:Inter,Arial,sans-serif;background:#f8fafc;color:#0f172a;"
        "display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:24px}"
        "main{max-width:520px;background:white;border:1px solid #e2e8f0;border-radius:12px;"
        "box-shadow:0 24px 80px rgba(15,23,42,.12);padding:32px}"
        "h1{margin:0 0 12px;color:#dc2626}p{line-height:1.6;color:#475569}</style></head>"
        "<body><main><h1>" + escape_html_text(title) + "</h1><p>" + escape_html_text(message) + "</p>"
        "<p><a href='/' style='color:#dc2626;font-weight:600'>Return to BLT Newsletter</a></p>"
        "</main></body></html>"
    )
    return Response.new(
        body,
        status=status,
        headers=Headers.new([["Content-Type", "text/html; charset=utf-8"]]),
    )


def escape_html_text(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def json_response(payload, status=200, extra_headers=None):
    headers = dict(CORS_HEADERS)
    headers["Content-Type"] = "application/json; charset=utf-8"
    if extra_headers is not None:
        headers.update(extra_headers)
    return Response.new(
        json.dumps(payload, separators=(",", ":")),
        status=status,
        headers=Headers.new(list(headers.items())),
    )


def json_error(message, status):
    return json_response({"success": False, "error": message}, status)


def cors_preflight_response():
    return Response.new(None, status=204, headers=Headers.new(list(CORS_HEADERS.items())))


def js_to_py(value):
    if value is None:
        return None

    if hasattr(value, "to_py"):
        try:
            return value.to_py()
        except Exception:
            pass

    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        return [js_to_py(item) for item in value]

    try:
        return dict(value)
    except Exception:
        return value


def get_env_value(env, name):
    try:
        value = getattr(env, name)
    except Exception:
        value = None

    if value is not None:
        return value

    try:
        return env[name]
    except Exception:
        return None


def get_db_binding(env):
    try:
        return env.DB
    except Exception:
        return get_env_value(env, "DB")


def get_queue_binding(env):
    return get_env_value(env, "NEWSLETTER_QUEUE")


def get_sendgrid_config(env):
    api_key = clean_env_value(get_env_value(env, "SENDGRID_API_KEY"))
    from_email = clean_env_value(get_env_value(env, "SENDGRID_FROM_EMAIL"))
    from_name = clean_env_value(get_env_value(env, "SENDGRID_FROM_NAME")) or "OWASP BLT"
    return api_key, from_email, from_name


def clean_env_value(value):
    if value is None:
        return ""

    text = str(value).strip()
    return text


def issue_email_subject(issue):
    return issue.get("subject") or issue.get("title") or "BLT Newsletter"


def render_issue_email_html(issue, archive_url, unsubscribe_url):
    return render_newsletter_issue_email(
        issue.get("title") or "BLT Newsletter",
        issue.get("summary") or "",
        issue.get("markdown_body") or "",
        archive_url,
        unsubscribe_url,
    )


def build_issue_archive_url(issue, request=None, env=None):
    slug = issue.get("slug") or issue.get("id") or ""
    path = "/api/issues/" + quote(slug, safe="")
    if request is not None:
        return absolute_url_for(request, path)

    return join_public_url(env, path)


def build_unsubscribe_url(request=None, subscriber_id="", env=None):
    path = "/unsubscribe"
    if subscriber_id:
        token = build_unsubscribe_token(subscriber_id, get_admin_session_secret(env) if env is not None else DEFAULT_ADMIN_SESSION_SECRET)
        path += "?subscriber_id=" + quote(subscriber_id, safe="") + "&token=" + quote(token, safe="")

    if request is not None:
        return absolute_url_for(request, path)

    return join_public_url(env, path)


def build_unsubscribe_token(subscriber_id, secret):
    return email_hash("unsubscribe:" + str(subscriber_id), secret)


def verify_unsubscribe_token(subscriber_id, token, secret):
    expected = build_unsubscribe_token(subscriber_id, secret)
    return str(token or "") == expected


def absolute_url_for(request, path):
    url = URL.new(request.url)
    pathname, separator, query = path.partition("?")
    url.pathname = pathname
    url.search = ("?" + query) if separator else ""
    return url.toString()


def join_public_url(env, path):
    base_url = clean_env_value(get_env_value(env, "PUBLIC_BASE_URL")) or clean_env_value(
        get_env_value(env, "SITE_URL")
    )
    if not base_url:
        return path

    return base_url.rstrip("/") + "/" + path.lstrip("/")


async def send_queue_message(queue, message):
    sender = getattr(queue, "send", None)
    if not callable(sender):
        return False

    payload = to_js(message) if to_js is not None else message
    await maybe_await(sender(payload))
    return True


def get_queue_batch_messages(batch):
    messages = getattr(batch, "messages", None)
    if messages is None:
        try:
            messages = batch["messages"]
        except Exception:
            messages = batch

    if isinstance(messages, list):
        return messages

    try:
        return list(messages)
    except Exception:
        return []


def get_queue_message_body(message):
    body = getattr(message, "body", None)
    if body is None and isinstance(message, dict):
        body = message.get("body", message)

    body = js_to_py(body)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = {}

    return body if isinstance(body, dict) else {}


async def ack_queue_message(message):
    await call_queue_message_method(message, "ack")


async def retry_queue_message(message):
    retried = await call_queue_message_method(message, "retry")
    if not retried:
        await ack_queue_message(message)


async def call_queue_message_method(message, method_name):
    method = getattr(message, method_name, None)
    if not callable(method) and isinstance(message, dict):
        method = message.get(method_name)

    if not callable(method):
        return False

    await maybe_await(method())
    return True


async def maybe_await(value):
    if hasattr(value, "__await__"):
        return await value

    return value
