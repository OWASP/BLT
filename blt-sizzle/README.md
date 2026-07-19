# BLT Sizzle

BLT Sizzle is an async daily check-in app for organization-based teams. It helps contributors share progress, surface blockers, and give admins a quick view of daily activity without adding another meeting.

The current app is built for the OWASP BLT / GSoC workflow, but the model is generic: users join organizations, admins approve access, and members submit check-ins for the organization they are working with.

## Current product flow

1. Create an account with name, email, and password.
2. Verify email with the code sent by the app.
3. Create organization, or request access to an existing one.
4. Admins approve members and manage organization access.
5. Approved members submit a daily check-in for a selected organization.
6. Dashboard pages show participation, blockers, pending requests, and recent check-ins.

## Features

- Email/password signup and login.
- Email verification code flow.
- PBKDF2 password hashing.
- HttpOnly session cookies backed by D1 auth sessions.
- Organization creation and membership requests.
- Owner/admin/member roles.
- Daily check-ins tied to organization membership.
- One check-in per user/org/day, editable during the same day.
- Dashboard, profile, organizations, settings, and check-in history pages.
- Timezone-aware settings with IANA timezone options.
- SendGrid-compatible email delivery.

## Stack

- Cloudflare Python Workers
- Cloudflare D1
- Static HTML, CSS, Tailwind CDN, and vanilla JavaScript
- Python unittest contract tests
- Wrangler for local development and deployment

## Setup

```bash
npm install
npx wrangler login
cp .env.example .env
```

Create the D1 database if it does not exist yet:

```bash
npm run db:create
```

Copy the created database id into `wrangler.toml` under `[[d1_databases]]`.

Apply local migrations:

```bash
npm run db:migrate:dev
```

Start local development:

```bash
npm run dev
```

The app runs at:

```text
http://localhost:8787
```

## Environment variables

Use `.env.example` as the local template. Do not commit real secrets.

Required or commonly used values:

| Variable | Purpose |
|---|---|
| `APP_NAME` | Display name used by email templates |
| `APP_URL` | Local or deployed app URL |
| `WORKER_HOST` | Host used by Worker links |
| `ENCRYPTION_KEY` | Secret used for encrypted app data |
| `OTP_SECRET` | Secret used to hash verification codes |
| `SESSION_SECRET` | Secret used to hash session tokens |
| `EMAIL_PROVIDER` | Currently `sendgrid` |
| `EMAIL_API_KEY` | SendGrid API key |
| `EMAIL_FROM` | Sender email address |
| `EMAIL_FROM_NAME` | Sender display name |
| `DEFAULT_TIMEZONE` | Default timezone for new users |

For production, set secrets through Wrangler:

```bash
openssl rand -base64 32
npx wrangler secret put ENCRYPTION_KEY
npx wrangler secret put OTP_SECRET
npx wrangler secret put SESSION_SECRET
npx wrangler secret put EMAIL_API_KEY
```

Non-secret values such as `EMAIL_FROM`, `EMAIL_FROM_NAME`, `APP_URL`, and `DEFAULT_TIMEZONE` can live in Worker vars.

## SendGrid setup and debugging

1. Verify the sender identity or domain in SendGrid.
2. Set `EMAIL_PROVIDER=sendgrid`.
3. Set `EMAIL_API_KEY` as a Cloudflare secret.
4. Set `EMAIL_FROM` to the verified sender.
5. Run the signup flow locally or on the deployed Worker.
6. If email does not arrive, check Wrangler logs:

```bash
npm run tail
```

The Worker supports the current `EMAIL_*` names and legacy `SENDGRID_*` names during migration, but new setups should use `EMAIL_*`.

## Database migrations

Local development:

```bash
npm run db:migrate:dev
```

Production requires an explicit confirmation guard:

```bash
CONFIRM_PROD_MIGRATION=1 npm run db:migrate:prod
```

You can override the database name if needed:

```bash
D1_DATABASE=sizzle-db npm run db:migrate:dev
```

The migration script lives at:

```text
scripts/migrate.sh
```

## Useful commands

```bash
npm run dev
npm run deploy
npm run tail
npm run test
npm run db:query "SELECT name FROM sqlite_master WHERE type='table'"
```

`npm run deploy` calls `deploy.sh`. The script requires `CLOUDFLARE_ACCOUNT_ID` or `CF_ACCOUNT_ID`, checks Wrangler authentication, runs the test suite unless `SKIP_TESTS=1` is set, and then deploys with `wrangler.toml`.

Python-only verification:

```bash
python -m unittest discover tests -v
python -m py_compile workers/*.py
git diff --check
```

## Manual smoke flow

Use this before opening a merge request or deploying:

1. Create an account.
2. Verify email.
3. Log in.
4. Create organization.
5. Create or use another account to request access.
6. Approve the request as owner/admin.
7. Submit a check-in as an approved member.
8. Confirm dashboard metrics and check-in history update.
9. Confirm unverified or unapproved users cannot check in.

## API surface

Main app routes:

| Route | Purpose |
|---|---|
| `/` | Public landing page |
| `/login` | Signup, login, and email verification |
| `/dashboard` | Signed-in dashboard |
| `/app` | Daily check-in form |
| `/organizations` | Organization discovery and management |
| `/profile` | Profile and verification state |
| `/settings` | Reminder and timezone settings |
| `/check-ins` | Check-in history |

Core API routes:

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/auth/signup` | Create account and send verification code |
| `POST` | `/api/auth/login` | Password login |
| `POST` | `/api/auth/verify-email` | Verify email code |
| `POST` | `/api/auth/resend-verification` | Resend verification code |
| `GET` | `/api/auth/me` | Current session user |
| `GET` | `/api/profile` | Profile state |
| `POST` | `/api/profile` | Save profile settings |
| `GET` | `/api/orgs` | User organizations |
| `GET` | `/api/orgs/discover` | Discover organizations |
| `POST` | `/api/orgs` | Create organization |
| `POST` | `/api/orgs/:slug/join` | Request to join organization |
| `GET` | `/api/checkins` | Check-in history |
| `GET` | `/api/checkin/latest` | Latest check-in for selected org |
| `POST` | `/api/checkin` | Create or update today's check-in |
| `GET` | `/api/dashboard` | Dashboard metrics |
| `GET` | `/api/timezones` | IANA timezone list |

## Security notes

Implemented:

- Password hashes use PBKDF2.
- Session cookies are HttpOnly and SameSite-aware.
- Session tokens are hashed before storage.
- Verification codes are hashed before storage.
- Authenticated actions use the current session identity instead of trusting client-provided `userId`.
- Organization and check-in flows enforce verified users and approved membership.

Still worth hardening before broad production use:

- Current encrypted check-in fields still use the legacy base64 placeholder approach, not production-grade AES-GCM encryption. Keep this limitation visible until the encrypted field strategy is replaced with real Web Crypto AES-GCM.
- Add stronger CSRF protection for state-changing authenticated requests.
- Review rate limits for login, verification, and organization actions.
- Confirm encrypted field strategy against current production requirements.
- Add audit logging for admin actions.

## Contributing

Use focused commits and keep each change reviewable.

Before committing:

```bash
python -m unittest discover tests -v
python -m py_compile workers/*.py
git diff --check
```

Repository:

```text
https://gitlab.com/owasp-blt/blt-sizzle
```

## License

This project is part of OWASP BLT and follows the project license terms.
