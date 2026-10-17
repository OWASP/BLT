# First Admin Setup Flow

## Purpose

BLT-Newsletter now supports a one-time browser-based first-admin setup flow for local and fresh deployments.

Maintainers should only need to run the D1 migration, start Wrangler, and open the app. No manual SQL seed is required for the first admin account.

## Routes

Public/admin setup routes:

- `GET /signup` — first-admin signup UI.
- `GET /api/admin/setup/status` — returns whether setup is still required.
- `POST /api/admin/setup` — creates the first admin only when no admin rows exist.

Existing login/admin routes continue to work:

- `GET /login`
- `POST /api/admin/login`
- `GET /dashboard`

## Behavior

Fresh D1 with zero admin rows:

1. Open `/login`.
2. Worker redirects to `/signup`.
3. Signup page checks `/api/admin/setup/status`.
4. Maintainer creates the first admin through the form.
5. Worker stores the admin with a hashed password, creates an HttpOnly session cookie, and returns success.
6. Browser redirects to `/dashboard`.

D1 with one or more admin rows:

1. `/signup` redirects to `/login` server-side.
2. `/api/admin/setup` returns `409` with `First admin is already configured.`
3. Login is the only normal entry point.

## Manual local test

```bash
cd ~/code/open-source/owasp/BLT-Newsletter
wrangler d1 migrations apply blt-newsletter --local
wrangler dev --local --port 8794
```

Open:

```text
http://localhost:8794/login
```

If no admin exists, it should redirect to:

```text
http://localhost:8794/signup
```

Create the first admin in the UI. After success, it should redirect to:

```text
http://localhost:8794/dashboard
```

Then verify the one-time lock:

```bash
curl -i http://localhost:8794/signup
curl -i -X POST http://localhost:8794/api/admin/setup \
  -H 'Content-Type: application/json' \
  -d '{"name":"Second Admin","email":"second@example.com","password":"example-password"}'
```

Expected after the first admin exists:

- `/signup` redirects to `/login`.
- setup POST returns `409`.

## Notes

- The setup endpoint counts all rows in `newsletter_admins`, not just active admins. If any admin row exists, first-admin setup is permanently closed for that D1 database.
- Passwords are stored with the existing PBKDF2 helper from `src/admin_auth.py`; raw passwords are not stored.
- The browser signup path creates the same HttpOnly admin session cookie as normal login.
- For production, set real Cloudflare secrets such as `EMAIL_HASH_SECRET` and `ADMIN_SESSION_SECRET` before deployment.
