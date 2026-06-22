# BLT Newsletter Testing Guide

## Automated checks

Run these before opening an MR:

```bash
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/private/tmp/blt-newsletter-pycache python3 -m py_compile src/*.py scripts/*.py
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
for path in sorted(Path('public').glob('*.html')):
    parser = HTMLParser()
    parser.feed(path.read_text())
    print('html ok', path)
PY
python3 - <<'PY'
from pathlib import Path
for name in ['dashboard', 'login', 'signup']:
    page = Path(f'public/{name}.html').read_text()
    start = page.rindex('    <script>') + len('    <script>')
    end = page.rindex('    </script>')
    Path(f'/tmp/blt_newsletter_{name}.js').write_text(page[start:end])
PY
node --check /tmp/blt_newsletter_dashboard.js
node --check /tmp/blt_newsletter_login.js
node --check /tmp/blt_newsletter_signup.js
git diff --check
```

## Local Worker smoke

```bash
wrangler d1 migrations apply blt-newsletter --local
wrangler dev --local --port 8794
```

Open:

```text
http://localhost:8794/
http://localhost:8794/login
http://localhost:8794/dashboard
```

## Public subscribe flow

1. Open `/`.
2. Enter a valid email and optional name.
3. Check consent.
4. Submit.

Expected:

- First subscribe returns success.
- Duplicate subscribe is idempotent.
- Invalid email shows an error.
- Missing consent shows an error.

Curl checks:

```bash
curl -sS -X POST http://localhost:8794/api/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"email":"manual-test@example.com","name":"Manual Test","consent":true}'

curl -sS -X POST http://localhost:8794/api/unsubscribe \
  -H 'Content-Type: application/json' \
  -d '{"email":"manual-test@example.com"}'
```

## First-admin setup flow

Use a fresh local D1 for the full first-run flow.

Expected with zero admins:

1. `/login` redirects to `/signup`.
2. `/api/admin/setup/status` returns `setup_required: true`.
3. The signup form creates the first admin.
4. Browser redirects to `/dashboard`.
5. `/signup` is closed after that and redirects to `/login`.

Checks:

```bash
curl -i http://localhost:8794/api/admin/setup/status
curl -i http://localhost:8794/login
curl -i http://localhost:8794/signup
```

Expected after admin exists:

```text
/api/admin/setup/status -> setup_required false
/signup -> 302 /login
POST /api/admin/setup -> 409 First admin is already configured.
```

## Admin dashboard flow

After login:

- Overview stats load from `/api/admin/stats`.
- Subscribers table loads from `/api/admin/subscribers`.
- Campaigns table loads from `/api/admin/campaigns`.
- Deliveries table loads from `/api/admin/jobs`.
- Browser console has no red errors.

Manual campaign test:

1. Open Campaigns.
2. Click New campaign.
3. Fill title, slug, subject, summary, and Markdown body.
4. Save draft.
5. Refresh dashboard and confirm the campaign remains.

## SendGrid test-send flow

Without SendGrid secrets:

1. Open a campaign in the dashboard.
2. Click Send test email.
3. Enter a recipient.
4. Submit.

Expected: clear configuration error asking for `SENDGRID_API_KEY` and `SENDGRID_FROM_EMAIL`.

With SendGrid secrets configured:

- `POST /api/admin/campaigns/:id/send-test` should return success for a verified sender and valid recipient.
- Confirm the email uses BLT branding and includes an unsubscribe footer.

## Campaign publish flow

1. Ensure at least one active subscriber exists.
2. Create or open a newsletter campaign.
3. Confirm Publish campaign.

Expected:

- `POST /api/admin/campaigns/:id/publish` returns `202`.
- A `newsletter_send_jobs` row is created.
- One queued `newsletter_delivery_events` row is created per active subscriber.
- Dashboard Deliveries table shows the job.
- If `NEWSLETTER_QUEUE` is configured, queue messages contain IDs only, not raw emails.

## Runtime API expectations

Unauthenticated admin APIs should return `401`:

```bash
curl -i http://localhost:8794/api/admin/me
curl -i http://localhost:8794/api/admin/jobs
```

Public archive should return only published campaigns:

```bash
curl -sS http://localhost:8794/api/campaigns
```

## Visual QA

Check desktop and mobile widths:

- Landing page layout and subscribe form.
- Login and signup pages.
- Dashboard sidebar/topbar.
- Dashboard tables and right-side sheets.

## Security QA

- Confirm no API keys or session tokens appear in page source.
- Confirm admin session cookie is HttpOnly.
- Confirm public APIs never list draft campaigns.
- Confirm queue payloads do not include raw emails.
- Confirm setup closes after the first admin exists.

## Troubleshooting

### Setup page says migrations are missing

Run:

```bash
wrangler d1 migrations apply blt-newsletter --local
```

### Campaign creation fails locally

If an old local migration was applied before the campaign schema changed, your local D1 may be stale. Use a fresh local D1 when you are okay losing local test data.

### Test email fails

Check:

- `SENDGRID_API_KEY`
- `SENDGRID_FROM_EMAIL`
- SendGrid sender verification
- Worker logs

### Campaign stays queued

Check:

- `NEWSLETTER_QUEUE` binding exists.
- SendGrid secrets are configured.
- The subscriber is still active.
- Worker queue consumer logs.
