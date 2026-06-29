# Slice 2 Backend Foundation Notes

Implemented: 2026-06-17

## Scope completed

Slice 2 backend foundations are implemented locally on branch `feat/backend-integration`:

- Admin auth helper module: `src/admin_auth.py`.
- HttpOnly admin session cookie helpers.
- Admin login/logout/me/stats/subscribers API routes.
- Admin issue list/create/update API foundations.
- Public published issue archive API foundations.
- Local admin seed SQL helper: `scripts/seed_admin.py`.
- Minimal login/logout frontend wiring:
  - `public/login.html` posts to `/api/admin/login`.
  - `public/dashboard.html` logout posts to `/api/admin/logout`.

## API routes added

```text
POST /api/admin/login
POST /api/admin/logout
GET  /api/admin/me
GET  /api/admin/stats
GET  /api/admin/subscribers
GET  /api/admin/campaigns
POST /api/admin/campaigns
PATCH /api/admin/campaigns/:id
GET  /api/campaigns
GET  /api/campaigns/:slug
```

## Auth model

- Admin login uses normalized email + HMAC `email_hash` lookup.
- Password hashes use `hashlib.pbkdf2_hmac('sha256', ...)` with format:

```text
pbkdf2_sha256$iterations$salt_hex$hash_hex
```

- Sessions use a random token stored in an HttpOnly cookie.
- D1 stores only `session_hash`, not the raw session token.
- Default cookie attributes:

```text
HttpOnly; SameSite=Lax; Path=/
```

- `Secure` is enabled when the request is HTTPS or `ADMIN_COOKIE_SECURE` is set.

Production should set:

```text
EMAIL_HASH_SECRET
ADMIN_SESSION_SECRET
```

Development fallbacks exist for local speed only.

## Seed helper

Generate local admin SQL:

```bash
EMAIL_HASH_SECRET=development-email-hash-secret \
python3 scripts/seed_admin.py \
  --email admin@example.com \
  --password 'change-me' \
  --name 'Site Admin' \
  > /tmp/blt_admin_seed.sql

wrangler d1 execute blt-newsletter --local --file /tmp/blt_admin_seed.sql
```

The script prints SQL only; it does not connect to D1 directly.

## Verification run

Commands run:

```bash
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/private/tmp/blt-newsletter-pycache python3 -m py_compile src/*.py scripts/*.py
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
for p in sorted(Path('public').glob('*.html')):
    HTMLParser().feed(p.read_text())
    print('ok', p)
PY
git diff --check
sqlite3 /tmp/blt_newsletter_schema_verify.sqlite < migrations/0001_newsletter_schema.sql
```

Results:

- Unit tests passed: 26 tests.
- Python compile passed.
- HTML parser smoke passed for all public HTML files.
- `git diff --check` passed.
- Migration SQL loaded into a temporary SQLite database successfully.

Runtime checks run with local Wrangler on port 8796:

```bash
curl -i http://127.0.0.1:8796/api/admin/me
python3 scripts/seed_admin.py --email admin-slice2@example.com --password 'CorrectHorse123!' --name 'Slice Two Admin' > /tmp/blt_admin_seed.sql
wrangler d1 execute blt-newsletter --local --file /tmp/blt_admin_seed.sql
curl -i -c /tmp/blt_admin_cookies.txt -X POST http://127.0.0.1:8796/api/admin/login -H 'Content-Type: application/json' --data '{"email":"admin-slice2@example.com","password":"CorrectHorse123!"}'
curl -i -b /tmp/blt_admin_cookies.txt http://127.0.0.1:8796/api/admin/me
curl -i -b /tmp/blt_admin_cookies.txt http://127.0.0.1:8796/api/admin/stats
```

Results:

- Unauthenticated `/api/admin/me` returned `401`.
- Seed SQL inserted a local admin.
- Login returned `200` and Set-Cookie with `HttpOnly; SameSite=Lax; Path=/`.
- Authenticated `/api/admin/me` returned safe admin summary.
- Authenticated `/api/admin/stats` returned subscriber/issue stats.

## Local D1 note

The local D1 database had already applied an earlier version of `0001_newsletter_schema.sql`, and a local destructive reset was denied. To avoid altering local state destructively, campaign create/update routes were not curl-tested against local D1 in this pass. The updated migration was validated separately in a temporary SQLite database and covered by unit/source tests.

For a clean local end-to-end campaign draft test, reset or recreate the local D1 state in a new environment, then re-run migrations before testing:

```bash
wrangler d1 migrations apply blt-newsletter --local
```

## Known follow-ups

- Wire dashboard Subscribers/Campaigns/Deliveries data tables to these APIs.
- Add CSRF protection if cookie-auth admin mutations become cross-origin or form-driven.
- Add remote D1 ID and production secrets before deploy.
- Start Slice 3: SendGrid service, send-test route, and queue-backed campaign delivery.
