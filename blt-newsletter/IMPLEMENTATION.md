# BLT Newsletter Implementation Summary

## Current architecture

BLT Newsletter is now a Python Cloudflare Worker application with static assets, D1 persistence, admin auth, newsletter campaign management, and SendGrid/Queue campaign foundations.

The previous public GitHub Issues subscriber storage and GitHub Actions sender model has been superseded by private D1 tables and Worker APIs.

## Runtime pieces

### Worker entrypoint

- `src/entry.py`
- Serves static assets from `public/`.
- Handles public subscription/archive APIs.
- Handles first-admin setup, login/logout, session checks, dashboard APIs, campaign draft/publish, test sends, campaign jobs, and queue consumption.

### D1 schema

- `migrations/0001_newsletter_schema.sql`

Tables:

- `newsletter_subscribers`
- `newsletter_admins`
- `newsletter_admin_sessions`
- `newsletter_campaigns`
- `newsletter_send_jobs`
- `newsletter_delivery_events`
- `newsletter_rate_limits`

### Admin auth

- `src/admin_auth.py`
- PBKDF2 password hashes.
- HMAC session token hashes.
- HttpOnly/SameSite session cookie helpers.

### Subscription logic

- `src/newsletter_validation.py`
- `src/newsletter_service.py`

Implemented behavior:

- normalize email
- HMAC email hash for lookup
- D1 subscriber insert
- idempotent duplicate subscribe
- reactivation after unsubscribe
- privacy-safe unsubscribe response

### Email and campaigns

- `src/email_service.py`
- `src/email_templates.py`
- `src/email_campaigns.py`

Implemented behavior:

- SendGrid Web API v3 payloads and sender wrapper.
- BLT-branded newsletter HTML email renderer.
- Lightweight Markdown rendering for email body.
- Visible unsubscribe footer.
- Campaign job and delivery-event record builders.
- Queue message records with IDs only, no raw email.

### UI assets

- `public/index.html` — public landing/subscribe page.
- `public/login.html` — admin login.
- `public/signup.html` — one-time first-admin setup page.
- `public/dashboard.html` — admin dashboard.
- `public/docs.html` — docs/help page.

## Important routes

Public:

```text
GET  /
POST /api/subscribe
POST /api/unsubscribe
GET  /api/campaigns
GET  /api/campaigns/:slug
```

Setup/auth:

```text
GET  /signup
GET  /login
GET  /dashboard
GET  /api/admin/setup/status
POST /api/admin/setup
POST /api/admin/login
POST /api/admin/logout
GET  /api/admin/me
```

Admin data:

```text
GET  /api/admin/stats
GET  /api/admin/subscribers
GET  /api/admin/campaigns
POST /api/admin/campaigns
PATCH /api/admin/campaigns/:id
```

Publish/campaigns:

```text
POST /api/admin/campaigns/:id/send-test
POST /api/admin/campaigns/:id/publish
GET  /api/admin/jobs
GET  /api/admin/jobs/:id
POST /api/admin/jobs/:id/cancel
```

Queue consumer:

```text
async def queue(self, batch)
```

## First-admin setup

Fresh D1 behavior:

1. `/login` redirects to `/signup` when `newsletter_admins` is empty.
2. Signup creates the first admin with a hashed password.
3. Worker creates an HttpOnly session cookie.
4. Browser opens `/dashboard`.
5. `/signup` closes permanently for that D1 once any admin row exists.

## SendGrid/Queue campaign flow

1. Admin creates a newsletter campaign.
2. Admin can send a test email via SendGrid.
3. Admin publishes the campaign.
4. Worker creates one `newsletter_send_jobs` row for that campaign.
5. Worker creates queued `newsletter_delivery_events` for active subscribers.
6. If `NEWSLETTER_QUEUE` exists, Worker enqueues ID-only messages.
7. Queue consumer loads D1 rows, renders email HTML, sends through SendGrid, and records sent/failed events.

## Current verification baseline

```bash
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/private/tmp/blt-newsletter-pycache python3 -m py_compile src/*.py scripts/*.py
node --check /tmp/blt_newsletter_dashboard.js
node --check /tmp/blt_newsletter_login.js
node --check /tmp/blt_newsletter_signup.js
git diff --check
```

Wrangler smoke has verified:

- `/api/admin/setup/status` responds locally.
- unauthenticated `/api/admin/jobs` returns 401.
- `/dashboard` HTML includes campaign/test-send dashboard wiring.
- dashboard unauthenticated guard redirects to `/login` with no console errors.

## Production configuration still required

Before production campaign sends:

- Replace placeholder D1 `database_id` in `wrangler.toml`.
- Create the Cloudflare queue `blt-newsletter-send`.
- Set Cloudflare secrets/vars:
  - `EMAIL_HASH_SECRET`
  - `ADMIN_SESSION_SECRET`
  - `SENDGRID_API_KEY`
  - `SENDGRID_FROM_EMAIL`
  - optional `SENDGRID_FROM_NAME`
  - optional `PUBLIC_BASE_URL`

## Remaining hardening backlog

- Signed GET-based unsubscribe/preference-center links.
- SendGrid Event Webhook verification and suppression sync.
- CSRF protection for cookie-auth admin POSTs.
- Rate-limit enforcement on login/setup/subscribe.
- Encrypted email-at-rest before production campaign scale.
- Queue retry/dead-letter policy tuning.
- Accessibility polish for hidden dashboard sheets/modals.
