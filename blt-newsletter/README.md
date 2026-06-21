# BLT Newsletter

BLT Newsletter is the OWASP BLT newsletter platform. It runs as a Python Cloudflare Worker with static assets, D1-backed subscriber/admin/campaign storage, a browser admin dashboard, and SendGrid delivery.

## What it does

- Public newsletter landing page and private D1-backed subscribe/unsubscribe API.
- One-time first-admin setup UI at `/signup` for fresh D1 databases.
- Admin login with HttpOnly session cookies.
- Admin dashboard for subscribers, newsletter issues, campaigns, test sends, and delivery jobs.
- Public archive API for published issues.
- SendGrid Web API integration without the SendGrid package dependency.
- Cloudflare Queue foundation for asynchronous campaign delivery.

## Architecture

```text
Browser
  ├─ public landing page -> POST /api/subscribe
  ├─ login/signup UI -> /api/admin/setup + /api/admin/login
  └─ dashboard -> /api/admin/*

Python Cloudflare Worker (src/entry.py)
  ├─ static assets from public/
  ├─ D1 binding DB
  ├─ optional Queue binding NEWSLETTER_QUEUE
  └─ SendGrid Web API via src/email_service.py

D1
  ├─ newsletter_subscribers
  ├─ newsletter_admins
  ├─ newsletter_admin_sessions
  ├─ newsletter_issues
  ├─ newsletter_send_jobs
  ├─ newsletter_delivery_events
  └─ newsletter_rate_limits
```

The old public issue-based subscriber storage model has been replaced by private D1 storage.

## Main routes

Public:

- `GET /`
- `POST /api/subscribe`
- `POST /api/unsubscribe`
- `GET /api/issues`
- `GET /api/issues/:slug`

Admin/setup:

- `GET /signup`
- `GET /login`
- `GET /dashboard`
- `GET /api/admin/setup/status`
- `POST /api/admin/setup`
- `POST /api/admin/login`
- `POST /api/admin/logout`
- `GET /api/admin/me`
- `GET /api/admin/stats`
- `GET /api/admin/subscribers`
- `GET /api/admin/issues`
- `POST /api/admin/issues`
- `PATCH /api/admin/issues/:id`
- `POST /api/admin/issues/:id/send-test`
- `POST /api/admin/issues/:id/send`
- `GET /api/admin/jobs`
- `GET /api/admin/jobs/:id`
- `POST /api/admin/jobs/:id/cancel`

## Local development

```bash
cd BLT-Newsletter
wrangler d1 migrations apply blt-newsletter --local
wrangler dev --local --port 8794
```

Open:

```text
http://localhost:8794/
http://localhost:8794/login
```

Fresh local D1 behavior:

1. `/login` redirects to `/signup`.
2. Create the first admin in the browser.
3. The Worker stores the admin, creates an HttpOnly cookie, and opens `/dashboard`.
4. After one admin exists, `/signup` redirects to `/login` and the setup API returns `409`.

## Required Cloudflare resources

D1 database:

```toml
[[d1_databases]]
binding = "DB"
database_name = "blt-newsletter"
migrations_dir = "migrations"
```

Queue binding:

```toml
[[queues.producers]]
binding = "NEWSLETTER_QUEUE"
queue = "blt-newsletter-send"

[[queues.consumers]]
queue = "blt-newsletter-send"
```

Before production deploy, replace the placeholder D1 `database_id` in `wrangler.toml`.

## Required secrets / vars

Set these as Cloudflare secrets or environment variables before production campaign sends:

- `EMAIL_HASH_SECRET` — HMAC key for subscriber/admin email hashes.
- `ADMIN_SESSION_SECRET` — HMAC key for admin session tokens.
- `SENDGRID_API_KEY` — SendGrid Mail Send API key.
- `SENDGRID_FROM_EMAIL` — verified sender email.
- `SENDGRID_FROM_NAME` — optional sender display name.
- `PUBLIC_BASE_URL` — optional public base URL used in email links.

Local development has deterministic fallback secrets for tests only. Do not rely on fallback secrets in production.

## Manual testing

```bash
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/private/tmp/blt-newsletter-pycache python3 -m py_compile src/*.py scripts/*.py
```

Then run Wrangler and test:

- Public subscribe/unsubscribe from `/`.
- First-admin setup from `/login` on a fresh D1.
- Admin login/logout.
- Dashboard subscriber/issue/job tables.
- Draft issue create/update.
- Test send behavior. Without SendGrid secrets, it should return a clear configuration error.
- Campaign queue behavior. It should create a job and queued delivery events; queue delivery requires the `NEWSLETTER_QUEUE` binding.

See `TESTING.md` and `docs/plans/first-admin-setup-flow.md` for fuller QA steps.

## Notes for contributors

- Use plain HTML, Tailwind CSS, and vanilla JavaScript for UI changes.
- Use stdlib `unittest` for regression coverage.
- Do not commit secrets, API keys, real cookies, or real SendGrid responses.
- Keep subscriber storage private in D1; do not reintroduce public issue-based email storage.
- Prefer small reviewable slices and run local Wrangler smoke tests for Worker runtime changes.

## License

This project is licensed under the AGPL-3.0 License. See `LICENSE` for details.

## Related projects

- OWASP BLT: https://github.com/OWASP-BLT/BLT
- BLT Design: https://github.com/OWASP-BLT/BLT-Design
- BLT Newsletter canonical project: https://gitlab.com/owasp-blt/blt-newsletter
