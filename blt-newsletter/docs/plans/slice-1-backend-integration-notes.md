# Slice 1 Backend Integration Notes

Implemented: 2026-06-14

## Scope completed

Slice 1 is now implemented locally on branch `feat/backend-integration`:

- D1 binding configured as `DB` in `wrangler.toml`.
- D1 migration added at `migrations/0001_newsletter_schema.sql`.
- Public API routes added:
  - `POST /api/subscribe`
  - `POST /api/unsubscribe`
  - `OPTIONS` preflight support
- Testable helper modules added:
  - `src/newsletter_validation.py`
  - `src/newsletter_service.py`
- Worker glue added in `src/entry.py`.
- Landing form in `public/index.html` now posts to `/api/subscribe` instead of GitLab Issues.
- GitHub/GitLab issue-subscription copy was removed from the public signup flow language.

## Privacy model used for speed-first MVP

As approved, this implementation prioritizes speed:

- Normalize email with lowercase + trim.
- Store normalized email in D1.
- Store `email_hash` using HMAC-SHA256 for duplicate lookup.
- Do not implement encrypted email ciphertext yet.

Production should set:

```text
EMAIL_HASH_SECRET
```

A deterministic development fallback exists for local development only.

## D1 tables scaffolded

- `newsletter_subscribers`
- `newsletter_admins`
- `newsletter_admin_sessions`
- `newsletter_issues`
- `newsletter_send_jobs`
- `newsletter_delivery_events`
- `newsletter_rate_limits`

## Behavior

Subscribe:

- Requires valid email.
- Requires `consent: true`.
- Active duplicate returns idempotent success.
- Unsubscribed/bounced/suppressed existing records are reactivated for MVP speed.
- Safe JSON responses only; no raw exception text.

Unsubscribe:

- Requires valid email.
- Marks existing record as unsubscribed.
- Unknown email returns the same privacy-safe success message.

## Important implementation note

Cloudflare D1 rejects JavaScript `undefined` values. Python `None` can cross the Pyodide vararg boundary as `undefined` in D1 prepared-statement binds. The implementation avoids this for subscriber insert records by storing empty strings for optional string fields during Slice 1.

`src/entry.py` also uses `Headers.new(list(headers.items()))` for Worker JSON responses because passing a plain Python dict to the Worker `Headers` constructor caused runtime errors in local Wrangler.

## Verification run

Commands run:

```bash
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/private/tmp/blt-newsletter-pycache python3 -m py_compile src/entry.py src/newsletter_service.py src/newsletter_validation.py
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
for p in sorted(Path('public').glob('*.html')):
    HTMLParser().feed(p.read_text())
    print('ok', p)
PY
wrangler d1 migrations apply blt-newsletter --local
wrangler dev --local --port 8795
curl -i -X POST http://127.0.0.1:8795/api/subscribe -H 'Content-Type: application/json' --data '{"email":"test4@example.com","name":"Test User","consent":true}'
curl -i -X POST http://127.0.0.1:8795/api/subscribe -H 'Content-Type: application/json' --data '{"email":"TEST4@example.com","consent":true}'
curl -i -X POST http://127.0.0.1:8795/api/unsubscribe -H 'Content-Type: application/json' --data '{"email":"unknown4@example.com"}'
curl -i -X OPTIONS http://127.0.0.1:8795/api/subscribe
git diff --check
```

Results:

- Unit tests passed: 13 tests.
- Python compile passed.
- HTML parser smoke passed for all public HTML files.
- D1 local migration applied successfully.
- `/api/subscribe` valid request returned `201 Created`.
- Duplicate subscription returned `200 OK` with already-subscribed message.
- Unknown unsubscribe returned `200 OK` with privacy-safe message.
- Invalid email and missing consent return safe `400` responses.
- CORS preflight returned `204`.
- `git diff --check` passed.

## Known follow-ups

- Replace placeholder D1 `database_id` before remote deploy.
- Set `EMAIL_HASH_SECRET` in Cloudflare before production.
- Admin auth and dashboard API wiring are still Slice 2.
- SendGrid service and queue-backed campaigns are still Slice 3.
- Dashboard dark-mode polish remains a frontend follow-up.
- Hidden right-side sheets should be hidden from the accessibility tree when closed.
