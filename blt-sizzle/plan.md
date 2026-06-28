# BLT Sizzle App Refactor Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task when work is split across agents. For direct implementation, follow strict TDD: write failing tests first, verify red, implement minimal code, verify green, then refactor.

**Goal:** Refactor BLT Sizzle from a GitHub OAuth check-in prototype into a generic organization-based daily check-in app with first-class email OTP authentication, email verification, admin-managed organizations, and a new landing/dashboard UI.

**Architecture:** Keep the Cloudflare Python Worker + D1 + static HTML/Tailwind architecture, but decouple identity and organizations from GitHub. Add local-testable helper modules for auth, OTP, email, and HTML rendering. Backend APIs must derive identity from the HttpOnly session cookie, not from user-supplied `userId` fields. The home route becomes a public landing page; authenticated users use `/app` for check-in and `/dashboard` for organization/admin workflows.

**Tech Stack:** Cloudflare Python Workers, D1 SQLite migrations, vanilla HTML/Tailwind/JS, SendGrid-style email service adapted from BLT-Newsletter, PBKDF2 password/session helpers adapted from BLT-Newsletter, unittest-based local tests.

---

## Reference Inputs and Notes

### Branch
- Current working branch: `feat/app-refactor`.

### Landing page inspiration
- Source file: `/Users/mdkaifansari04/code/open-source/owasp/inspiration-lading-page.html`.
- Use its style language, not its API-specific content:
  - fixed translucent header
  - red/white/gray palette
  - dot-field hero background
  - large bold hero typography
  - pill status badge
  - gradient red primary CTA
  - compact feature cards
  - black oversized footer panel
- Adapt copy for Sizzle:
  - hero: async daily check-ins for organizations
  - CTA: Log in / verify email
  - secondary CTA: See how it works
  - feature cards: daily check-ins, org approvals, admin dashboard, reminders

### Email service source
- Source repo: `/Users/mdkaifansari04/code/open-source/owasp/BLT-Newsletter`.
- Reuse/adapt:
  - `src/email_service.py`: `SendGridEmailService`, `build_sendgrid_payload`, worker `fetch` fallback pattern.
  - `src/admin_auth.py`: PBKDF2 password hashing, session token generation, session cookie helpers.
- Sizzle email use case:
  - email OTP verification during login/signup
  - future reminders and admin/member notifications
- Environment variables to support:
  - `EMAIL_API_KEY`
  - `EMAIL_FROM`
  - `EMAIL_FROM_NAME` default `BLT Sizzle`
  - `EMAIL_PROVIDER` default `sendgrid`
  - `SESSION_SECRET`
  - `OTP_SECRET`

### Dashboard UI source
- Source file: `/Users/mdkaifansari04/code/open-source/owasp/BLT-Newsletter/public/dashboard.html`.
- Reuse/adapt UI concepts:
  - sidebar shell
  - overview metric cards
  - page sections toggled with vanilla JS
  - status badges
  - slide-over/detail sheet pattern
  - toast notifications
- Adapt sections for Sizzle:
  - Overview
  - Today’s Check-ins
  - Members
  - Join Requests
  - Organizations
  - Settings

### Existing Sizzle implementation to preserve where useful
- Existing daily check-in fields: previous work, today plan, blockers, mood, goal accomplished.
- Existing organization membership approval flow is a useful base, but needs roles and non-GitHub orgs.
- Existing org check-in endpoint is a useful base, but should become admin/member scoped and date-filterable.
- Existing scheduler/reminder logic should remain available, but email delivery should use the BLT-Newsletter-style email service.

### Existing problems to fix before feature expansion
- `src/pages/settings.html` contains duplicated trailing HTML/scripts and two closing `</html>` tags.
- GitHub OAuth and GitHub org coupling must be removed.
- Several endpoints trust `userId` from request body/query; this must stop once session auth is introduced.
- Pending organizations are currently eligible to appear in the check-in selector; only approved memberships should be selectable.
- README and tests are stale relative to the app direction.
- `package.json` references `schema.sql`, but the repo uses migrations.

---

## Target Product Behavior

### Public visitor
1. Visits `/` and sees the new landing page.
2. Clicks login/signup CTA.
3. Enters email.
4. Receives OTP by email.
5. Enters OTP.
6. Gets a secure HttpOnly session cookie.
7. Lands in `/app` or `/dashboard` depending on context.

### Member
1. Can belong to multiple organizations.
2. Can request to join an organization.
3. Can see pending/approved/rejected membership state.
4. Can check in only for approved organizations.
5. Chooses organization at check-in time.
6. Can view own check-in history by organization.
7. Can edit today’s check-in.

### Organization admin
1. Can create an organization.
2. Creator becomes owner.
3. Owner/admin can approve or reject join requests.
4. Owner/admin can view daily check-ins for the organization.
5. Owner/admin can see who checked in, who is missing, blockers, mood, and streaks.
6. Owner can promote/demote admins and remove members.
7. Multiple admins are supported.

---

## Data Model Plan

### New / changed tables

#### users
Target columns:
- `id TEXT PRIMARY KEY`
- `email TEXT UNIQUE NOT NULL`
- `email_hash TEXT`
- `display_name TEXT`
- `password_hash TEXT` nullable for OTP-only login
- `email_verified INTEGER DEFAULT 0`
- `status TEXT DEFAULT 'active'`
- `current_streak INTEGER DEFAULT 0`
- `longest_streak INTEGER DEFAULT 0`
- `last_check_in DATE`
- `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
- `updated_at DATETIME DEFAULT CURRENT_TIMESTAMP`

Migration path:
- Keep legacy `user_id` during transition if needed.
- New APIs should use `id` and `email`.
- Do not depend on `github_id`.

#### auth_sessions
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `session_hash TEXT UNIQUE NOT NULL`
- `user_id TEXT NOT NULL`
- `expires_at DATETIME NOT NULL`
- `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
- `last_seen_at DATETIME`

#### email_otps
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `email TEXT NOT NULL`
- `otp_hash TEXT NOT NULL`
- `purpose TEXT NOT NULL DEFAULT 'login'`
- `attempts INTEGER DEFAULT 0`
- `expires_at DATETIME NOT NULL`
- `consumed_at DATETIME`
- `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`

#### organizations
Target columns:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `name TEXT NOT NULL`
- `slug TEXT UNIQUE NOT NULL`
- `description TEXT`
- `created_by_user_id TEXT`
- `default_timezone TEXT DEFAULT 'UTC'`
- `checkin_enabled INTEGER DEFAULT 1`
- `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
- `updated_at DATETIME DEFAULT CURRENT_TIMESTAMP`

Migration path:
- Rename conceptually from `github_org_name` to `slug`.
- Preserve old column until a full migration can safely rebuild the table if D1 cannot rename as desired.

#### user_organizations
Target columns:
- `user_id TEXT NOT NULL`
- `org_id INTEGER NOT NULL`
- `role TEXT NOT NULL DEFAULT 'member'` (`owner`, `admin`, `member`)
- `status TEXT NOT NULL DEFAULT 'pending'` (`pending`, `approved`, `rejected`, `removed`)
- `requested_at DATETIME DEFAULT CURRENT_TIMESTAMP`
- `approved_by_user_id TEXT`
- `approved_at DATETIME`
- `joined_at DATETIME`
- primary key `(user_id, org_id)`

#### checkins
Target changes:
- Require `org_id` for organization check-ins.
- Keep optional personal check-ins only if intentionally supported.
- Add/ensure `updated_at`.
- Add unique index on `(org_id, user_id, checkin_date)`.

---

## API Plan

### Auth APIs
- `POST /api/auth/request-otp`
  - Body: `{ "email": "user@example.com" }`
  - Normalizes email, creates OTP, stores hashed OTP, sends email.
  - Response: `{ "success": true, "message": "Verification code sent" }`
- `POST /api/auth/verify-otp`
  - Body: `{ "email": "user@example.com", "otp": "123456" }`
  - Verifies non-expired OTP, creates user if needed, marks email verified, creates session cookie.
  - Response: `{ "authenticated": true, "user": { ... } }`
- `GET /api/auth/me`
  - Returns session user or 401.
- `POST /api/auth/logout`
  - Clears current session.

### Organization APIs
- `POST /api/orgs`
  - Creates organization; creator becomes owner/admin approved.
- `GET /api/orgs`
  - Lists user memberships with roles/status.
- `POST /api/orgs/:slug/join`
  - Creates pending join request.
- `GET /api/orgs/:slug/members`
  - Admin/member scoped. Admin sees pending and approved; member sees approved members if allowed.
- `POST /api/orgs/:slug/members/:userId/approve`
- `POST /api/orgs/:slug/members/:userId/reject`
- `POST /api/orgs/:slug/members/:userId/role`

### Check-in APIs
- `POST /api/checkin`
  - Uses session user, never body `userId`.
  - Requires `orgSlug` for org check-in.
  - Validates approved membership.
  - Upserts today’s check-in for `(org_id, user_id, date)`.
- `GET /api/checkins`
  - Uses session user.
  - Optional `orgSlug` filter.
- `GET /api/checkin/latest?orgSlug=...`
  - Uses session user.
- `GET /api/orgs/:slug/checkins?date=YYYY-MM-DD`
  - Admin/member scoped org timeline.
- `GET /api/orgs/:slug/dashboard?date=YYYY-MM-DD`
  - Returns metrics: checked in count, missing count, blockers, mood distribution, streaks.

---

## UI Route Plan

### `/`
Public landing page.
- Inspired by `inspiration-lading-page.html`.
- Contains CTA to `/login`.
- No daily check-in form on home.

### `/login`
Email OTP login/signup page.
- Step 1: email form.
- Step 2: OTP form.
- Shows delivery and verification errors.

### `/app`
Member check-in page.
- Existing check-in form moved here.
- Shows approved org selector only.
- Shows pending org notice/CTA to dashboard/settings.

### `/check-ins`
Member history page.
- Uses session user only.
- Filter by org.

### `/dashboard`
Organization/admin dashboard.
- Inspired by BLT-Newsletter dashboard shell.
- Sections: Overview, Today’s Check-ins, Members, Join Requests, Organizations, Settings.

---

## Implementation Tasks

### Task 1: Add local-testable auth and email foundation

**Objective:** Create reusable helpers for password/session/OTP/email so later route work is safe and testable.

**Files:**
- Create: `workers/auth_utils.py`
- Create: `workers/email_service.py`
- Create: `tests/test_app_auth_email_foundation.py`

**Steps:**
1. Write failing tests for password hashing, session cookie, OTP hashing/verification, and SendGrid payload construction.
2. Run: `python -m unittest tests.test_app_auth_email_foundation -v` and verify failure because modules do not exist.
3. Implement helpers adapted from BLT-Newsletter.
4. Re-run the targeted test and then existing syntax tests.

### Task 2: Add migration for app refactor schema

**Objective:** Add D1 migration for OTP sessions, org roles, and generic org metadata.

**Files:**
- Create: `migrations/0004_app_refactor_auth_orgs.sql`
- Modify: `workers/main.py` `init_database` once route work begins
- Test: `tests/test_schema_contract.py`

**Steps:**
1. Write schema contract tests checking required table/column names exist in migration SQL.
2. Add migration SQL.
3. Run schema contract tests.

### Task 3: Add OTP request/verify backend APIs

**Objective:** Replace the GitHub entrypoint with email OTP login while keeping old routes temporarily non-primary.

**Files:**
- Modify: `workers/main.py`
- Test: `tests/test_auth_contract.py`

**Steps:**
1. Add tests for route strings and helper call behavior where possible without Cloudflare runtime.
2. Add `/api/auth/request-otp` and `/api/auth/verify-otp` route dispatch.
3. Store hashed OTP, enforce expiry/attempts, send email through `SendGridEmailService`.
4. Create session from verified OTP.
5. Update `/api/auth/me` to return email-based user.
6. Keep `/api/auth/logout` but use new cookie/session store.

### Task 4: Create landing page and login page

**Objective:** Make `/` public landing and move app check-in to `/app`.

**Files:**
- Replace: `src/index.html`
- Create: `src/pages/login.html`
- Create: `src/pages/app.html` from current check-in page
- Modify: `workers/main.py` static route mapping
- Test: frontend static contract tests

**Steps:**
1. Write tests checking home contains landing hero and no check-in form.
2. Write tests checking login contains email/OTP fields and APIs.
3. Write tests checking app page contains check-in form and approved-org selector.
4. Implement pages.

### Task 5: Remove GitHub coupling from org model and UI

**Objective:** Turn GitHub org membership into generic organization membership.

**Files:**
- Modify: `workers/main.py`
- Modify: `src/pages/settings.html` or replace with dashboard org settings
- Modify: `README.md`
- Test: org contract tests

**Steps:**
1. Remove GitHub membership API verification from org join.
2. Change copy from `GitHub organization` to `organization`.
3. Add role/status semantics.
4. First org creator is owner.
5. Join requests are pending.

### Task 6: Secure check-in APIs with session identity

**Objective:** Stop trusting `userId` from request body/query.

**Files:**
- Modify: `workers/main.py`
- Modify: `src/pages/app.html`
- Modify: `src/pages/check-ins.html`
- Test: check-in contract tests

**Steps:**
1. Tests verify `handle_checkin` requires session user.
2. Tests/static checks verify frontend no longer sends `userId`.
3. Backend uses `get_session_user` for check-in, latest, settings, history.
4. Org selector includes only `status === 'approved'`.
5. Check-in with unapproved org returns 403 instead of silently saving personal.

### Task 7: Build dashboard UI from BLT-Newsletter pattern

**Objective:** Replace scattered settings/admin workflows with a dashboard shell.

**Files:**
- Create: `src/pages/dashboard.html`
- Modify: `workers/main.py` route mapping
- Test: dashboard static contract tests

**Sections:**
- Overview metric cards
- Today’s Check-ins
- Members
- Join Requests
- Organizations
- Settings

### Task 8: Add org dashboard backend metrics

**Objective:** Support admin dashboard with one call for daily status.

**Files:**
- Modify: `workers/main.py`
- Test: backend route/static SQL contract tests

**Endpoint:**
- `GET /api/orgs/:slug/dashboard?date=YYYY-MM-DD`

**Metrics:**
- approved members count
- checked in today count
- missing members
- blockers list/count
- mood distribution
- streak leaders

### Task 9: Update docs and environment templates

**Objective:** Keep setup accurate for contributors.

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `package.json` if needed

**Updates:**
- Email OTP setup
- SendGrid env vars
- `SESSION_SECRET` / `OTP_SECRET`
- D1 migration commands
- New routes
- Remove GitHub OAuth setup from primary docs

### Task 10: Final verification

**Commands:**
- `python -m unittest discover tests -v`
- `python -m py_compile workers/*.py`
- `npm run dev` then manual smoke:
  - `/` landing loads
  - `/login` request OTP UI loads
  - `/app` requires auth
  - `/dashboard` requires auth

---

## Acceptance Criteria

- Home route `/` is a public landing page.
- Login uses email OTP verification through SendGrid-style email service.
- No primary UI says “Login with GitHub”.
- Users can belong to multiple organizations.
- Users can request organization access.
- Multiple admins per organization are supported through membership roles.
- Check-ins are associated with exactly the selected approved organization.
- Admins can review members and daily check-ins.
- Backend does not trust `userId` from body/query for authenticated user actions.
- Tests cover helper-level auth/email behavior and static route/page contracts.

---

## Implementation Status

- [x] Requirements and references audited.
- [x] Task 1 auth/email foundation.
- [x] Task 2 schema migration.
- [ ] Task 3 OTP backend.
- [ ] Task 4 landing/login/app pages.
- [ ] Task 5 generic organizations.
- [ ] Task 6 session-secured check-ins.
- [ ] Task 7 dashboard UI.
- [ ] Task 8 dashboard backend metrics.
- [ ] Task 9 docs/env updates.
- [ ] Task 10 final verification.
