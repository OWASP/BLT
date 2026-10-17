# BLT Sizzle Two-Phase Product/UI Refactor Plan

> **For Hermes:** Build this with strict TDD for backend/integration work and frontend contract tests for every UI route. Phase 1 is UI-first and mostly mock/local interaction. Phase 2 wires the UI to real Cloudflare Worker + D1 APIs.

**Goal:** Finish BLT Sizzle as a generic organization daily check-in app with credential signup/login, email verification, profile verification, organization discovery/creation/management, join/check-in requests, member check-ins, and admin dashboards.

**Architecture:** Keep the current Cloudflare Python Worker + D1 + static HTML/Tailwind/vanilla JS architecture. Use the BLT-Newsletter dashboard as the dashboard inspiration: left sidebar, white/gray cards, red primary action color, metric cards, tables, status badges, slide-over sheets, modals, and toasts. Do UI first so the product flow can be reviewed before finishing backend integration.

**Tech Stack:** Cloudflare Python Workers, D1 migrations, vanilla HTML/Tailwind CDN, shared static dashboard shell/components, SendGrid-style email service, PBKDF2 password hashing, HttpOnly session cookies, unittest contract tests.

---

## Current State

Already completed / in progress on branch `feat/app-refactor`:

- Public landing page exists at `/`.
- Signup/login page exists at `/login`.
- Current auth direction is now credential-based:
  - first-time signup with name, email, password
  - email verification code
  - later login with email/password
- Email service diagnostics were improved and support both `EMAIL_*` and legacy `SENDGRID_*` env names.
- New auth/session foundations exist:
  - `workers/auth_utils.py`
  - `workers/email_service.py`
  - `auth_sessions`
  - `email_otps`
  - `auth_login_attempts`
- Existing visible pages still need a full UI pass:
  - `src/pages/app.html`
  - `src/pages/check-ins.html`
  - `src/pages/settings.html`
  - `src/pages/leaderboard.html`
- Known backend debt still remains:
  - some check-in/settings APIs still trust user-supplied `userId`
  - legacy GitHub OAuth routes still exist during transition
  - organization model is still partially GitHub-shaped internally
  - settings page has duplicated trailing HTML/scripts

---

## Design Direction: BLT-Newsletter Dashboard Inspiration

Reference file:

- `/Users/mdkaifansari04/code/open-source/owasp/BLT-Newsletter/public/dashboard.html`

Use these patterns:

- App shell with persistent left sidebar.
- Sidebar items with active red indicator bar.
- Top header per page with title, short description, and primary action.
- White cards on `#f8fafc` background.
- Primary red `#dc2626`, hover/dark red `#b91c1c`.
- Neutral border `#e2e8f0`.
- Metric cards for overview numbers.
- Status badges:
  - verified / active / approved: green
  - pending: amber
  - rejected / blocked: red
  - neutral/inactive: slate
- Tables with compact rows and right-side actions.
- Slide-over sheet for details/editing.
- Modal for create/confirm actions.
- Toast notifications for mock actions and later real API responses.
- Keep the UI clean and production-like; avoid over-styled gradients except existing primary buttons where already used.

Shared dashboard shell should be reused across app pages instead of every page inventing its own header/nav.

---

## Product Features We Are Building

### 1. Account and Profile

- User signs up with:
  - name
  - email
  - password
- Signup sends email verification code.
- User cannot fully use protected app flows until email is verified.
- User logs in later with email/password.
- Sidebar has `Profile`.
- Profile page includes:
  - name
  - email
  - verification status
  - resend verification code action
  - verify email form/code entry
  - session/account summary
  - future notification preferences

### 2. Organizations

- Sizzle has multiple organizations.
- Any verified user can create an organization.
- Creator becomes owner.
- A user can belong to multiple organizations.
- User can browse/list organizations available in Sizzle.
- User can request to join an organization.
- User can see membership status:
  - pending
  - approved
  - rejected
  - removed
- User can check in only for organizations where membership is approved and check-ins are enabled.

### 3. Organization Administration

- Organization owner/admin can manage organization.
- Multiple admins per organization.
- Roles:
  - owner
  - admin
  - member
- Admins can:
  - approve/reject join requests
  - view members
  - promote/demote admins, except owner safety rules
  - remove members
  - edit organization settings
  - enable/disable check-ins

### 4. Daily Check-ins

- User chooses organization before check-in.
- Check-in fields:
  - work completed / yesterday
  - today plan
  - blockers
  - mood
  - goal accomplished
- One check-in per org/user/day, editable for today.
- Check-in is attached to selected organization.
- Admin dashboard shows today’s org check-ins.

### 5. Dashboard / Reporting

- Overview shows:
  - organizations user belongs to
  - pending requests
  - checked-in today
  - missing members for selected org
  - blockers
  - streak leader / participation rate
- Admin org dashboard shows:
  - today’s check-ins
  - missing members
  - blockers
  - mood distribution
  - pending join requests
  - member list and roles

---

# Phase 1 — UI-First Product Shell and Mock Dashboard

**Objective:** Build the full user-facing interface based on the final feature set before finishing backend integration. This phase is reviewable UI only, using static/mock data and small local JS interactions where needed.

**Do not do in Phase 1:**

- Do not rewrite all backend organization logic yet.
- Do not finish session-secured check-in APIs yet.
- Do not fully remove legacy backend routes yet.
- Do not trust mock UI as production behavior.

## Phase 1 Files

Create / replace:

- `src/pages/dashboard.html` — main dashboard shell inspired by BLT-Newsletter.
- `src/pages/profile.html` — profile + email verification UI, or implement as a section in dashboard shell.
- `src/pages/organizations.html` — org discovery/create/join/manage UI, or implement as a section in dashboard shell.
- `src/pages/app.html` — member daily check-in UI in the new shell.
- `src/pages/check-ins.html` — check-in history UI in the new shell.
- `src/pages/settings.html` — either replace with profile/settings shell or redirect visually to profile/settings section.
- `src/pages/leaderboard.html` — either replace with org insights/streaks UI or keep as a dashboard section.
- `src/styles/sizzle-dashboard.css` — shared dashboard tokens/components if avoiding repeated inline CSS.
- `src/scripts/sizzle-ui.js` — shared mock dashboard navigation, tabs, modals, sheets, toasts.
- `tests/test_dashboard_ui_contract.py` or expand `tests/test_frontend_contract.py`.

Modify:

- `workers/main.py` static route mapping:
  - `/dashboard`
  - `/profile`
  - `/organizations`
  - keep `/app`, `/check-ins`, `/settings`, `/leaderboard`
- `src/index.html` CTAs:
  - primary app CTA should lead to `/login` or `/dashboard` depending auth later.
- `src/pages/login.html` after verification/login should land at `/dashboard` instead of old scattered pages when Phase 1 shell is ready.

## Phase 1 UI Routes

### `/dashboard`

Main signed-in home.

Sidebar items:

- Overview
- Daily Check-in
- Organizations
- Requests
- Members
- Check-ins
- Profile
- Settings

Overview cards:

- Checked in today
- Pending join requests
- Active blockers
- Organizations
- Email verification status

Mock panels:

- Today’s organization activity
- My pending organization requests
- Admin action queue
- Blockers needing attention

### `/profile`

Profile and email verification.

Must include:

- Display name card
- Email card
- Badge: Verified / Not verified
- Verify email code form
- Resend verification code button
- Password/account area placeholder
- Session/security note

### `/organizations`

Organization discovery and management.

Must include:

- Search/list all organizations in Sizzle.
- Create organization modal.
- My organizations tabs:
  - approved
  - pending
  - owned/admin
- Request to join button.
- Membership status badges.
- Organization detail slide-over:
  - description
  - members count
  - check-in enabled status
  - my role
  - request/leave/manage actions

### `/app`

Daily check-in page using new dashboard shell.

Must include:

- Organization selector with approved organizations only.
- Warning empty state if no approved organizations.
- Link to organizations page to request access.
- Check-in form card.
- Today’s previous saved check-in preview.
- Save draft / submit check-in UI states as mock.

### `/check-ins`

History page.

Must include:

- Filter by organization.
- Date range controls.
- Timeline/list of check-ins.
- Status chips for blockers/mood/goal accomplished.
- Detail sheet for one check-in.

### `/settings`

For Phase 1, simplify and align visually.

Must include:

- Notification settings mock.
- Timezone.
- Email reminders placeholder.
- Slack/webhook legacy settings only if still intentionally supported.
- No duplicated HTML/script blocks.

### `/leaderboard`

Reframe as team insights, not GitHub leaderboard.

Must include:

- Streak leaders.
- Participation rate.
- Most helpful blockers resolved.
- Organization filter.
- No “GitHub User” copy.

## Phase 1 Contract Tests

Add/extend frontend tests to assert:

- Every protected page uses shared dashboard shell classes/tokens.
- Sidebar contains `Overview`, `Daily Check-in`, `Organizations`, `Requests`, `Members`, `Check-ins`, `Profile`, `Settings`.
- Profile page contains verification UI:
  - `Verify email`
  - `Resend verification code`
  - `/api/auth/verify-email`
  - `/api/auth/resend-verification`
- Organizations page contains:
  - `Create organization`
  - `Request to join`
  - `Membership status`
  - `owner`, `admin`, `member`
- App page contains approved-org selector and no client-supplied `userId` in mock UI plan.
- Old pages do not contain:
  - `Login with GitHub`
  - `href="/api/auth/login"`
  - `GitHub User`
- Settings page has one `</html>` and one main script block after cleanup.
- Route mapping includes `/dashboard`, `/profile`, `/organizations`.

## Phase 1 Verification

Run:

```bash
python -m unittest tests.test_frontend_contract -v
python -m py_compile workers/*.py
git diff --check
```

Manual browser/smoke:

- `/dashboard` loads and sidebar switches sections.
- `/profile` shows verification UI.
- `/organizations` shows create/join/manage mock flows.
- `/app` shows check-in UI with organization context.
- `/check-ins`, `/settings`, `/leaderboard` are visually consistent.

## Phase 1 Acceptance Criteria

- The entire app feels like one dashboard product inspired by BLT-Newsletter.
- User can review the intended final flows without backend integration being complete.
- All primary feature areas are visible:
  - profile verification
  - organizations list
  - create/manage organization
  - request to join/check in
  - check-in form
  - admin/member dashboard
- No visible primary UI still points users to GitHub OAuth.
- Plan clearly marks backend integration as Phase 2.

---

# Phase 2 — Backend Integration and Production Behavior

**Objective:** Wire Phase 1 UI to real APIs, enforce security, finish organization membership/admin flows, and make daily check-ins production-safe.

## Phase 2 Backend Tasks

### Task 2.1: Finalize auth/profile behavior

Files:

- `workers/main.py`
- `tests/test_auth_routes_contract.py`
- `tests/test_profile_contract.py` if split out

Work:

- Ensure signup creates unverified user and sends verification code.
- Ensure unverified users cannot use protected app flows until verified, except profile verification/resend.
- Ensure `/api/auth/me` includes:
  - `emailVerified`
  - `needsEmailVerification`
  - `displayName`
  - `roles` or org summary later
- Add `POST /api/profile` for name/timezone settings if needed.
- Add `POST /api/auth/resend-verification` and `POST /api/auth/verify-email` final runtime tests/contracts.

### Task 2.2: Generic organizations backend

Files:

- `workers/main.py`
- `migrations/0006_generic_organizations.sql` if needed
- `tests/test_org_routes_contract.py`

Endpoints:

- `GET /api/orgs/discover`
- `POST /api/orgs`
- `GET /api/orgs`
- `GET /api/orgs/:slug`
- `POST /api/orgs/:slug/join`
- `DELETE /api/orgs/:slug/membership`
- `POST /api/orgs/:slug/settings`

Rules:

- Verified user can create organization.
- Creator is `owner` and approved.
- User can request join.
- Membership defaults to pending unless user is creator.
- Slug is unique and not GitHub-dependent.
- Organization can enable/disable check-ins.

### Task 2.3: Admin/member management backend

Files:

- `workers/main.py`
- `tests/test_org_admin_contract.py`

Endpoints:

- `GET /api/orgs/:slug/members`
- `GET /api/orgs/:slug/requests`
- `POST /api/orgs/:slug/members/:userId/approve`
- `POST /api/orgs/:slug/members/:userId/reject`
- `POST /api/orgs/:slug/members/:userId/role`
- `DELETE /api/orgs/:slug/members/:userId`

Rules:

- Only owner/admin can approve/reject.
- Only owner/admin can change roles.
- Owner cannot remove last owner.
- Multiple admins supported.
- Member list must not expose sensitive data.

### Task 2.4: Session-secured check-ins

Files:

- `workers/main.py`
- `src/pages/app.html`
- `src/pages/check-ins.html`
- `tests/test_checkin_security_contract.py`

Work:

- Stop trusting request body/query `userId`.
- Derive user from `sizzle_session` only.
- Require email verified user.
- Require approved membership in selected organization.
- Require org check-ins enabled.
- Upsert today’s check-in for `(org_id, user_id, checkin_date)`.
- Support edit today’s check-in.
- Return 401/403 correctly.

Endpoints:

- `POST /api/checkin`
- `GET /api/checkins?orgSlug=...`
- `GET /api/checkin/latest?orgSlug=...`

### Task 2.5: Dashboard metrics API

Files:

- `workers/main.py`
- `tests/test_dashboard_backend_contract.py`

Endpoints:

- `GET /api/dashboard`
- `GET /api/orgs/:slug/dashboard?date=YYYY-MM-DD`

Metrics:

- my organizations
- pending requests
- checked in today
- missing members
- blockers
- mood distribution
- streak leaders
- check-in participation percent

Rules:

- Member sees own/member-allowed org data.
- Admin sees admin metrics for orgs they manage.
- No cross-org data leaks.

### Task 2.6: Wire UI to APIs

Files:

- `src/scripts/sizzle-ui.js`
- all relevant `src/pages/*.html`
- `tests/test_frontend_contract.py`

Work:

- Replace mock data with fetch calls.
- Add loading/skeleton states.
- Add empty/error states.
- Add toasts for success/failure.
- Ensure all protected pages redirect unauthenticated users to `/login`.
- Ensure unverified users are routed to `/profile` verification flow.

### Task 2.7: Clean legacy GitHub/OAuth surface

Files:

- `workers/main.py`
- `wrangler.toml` / docs if needed
- `README.md`
- `.env.example`
- tests

Work:

- Remove GitHub OAuth from primary product/docs.
- Decide whether to fully delete legacy OAuth routes or keep hidden during migration.
- Remove GitHub UI copy/icons from all primary pages.
- Replace GitHub org naming in API response fields with generic `org.name`, `org.slug`.

### Task 2.8: Dev/prod operations and docs

Files:

- `scripts/migrate.sh`
- `package.json`
- `README.md`
- `.env.example`

Work:

- Add dev/prod migration script:
  - `bash scripts/migrate.sh dev`
  - `bash scripts/migrate.sh prod`
- Add package scripts:
  - `db:migrate:dev`
  - `db:migrate:prod`
- Document env setup:
  - `EMAIL_API_KEY`
  - `EMAIL_FROM`
  - `EMAIL_FROM_NAME`
  - `OTP_SECRET`
  - `SESSION_SECRET`
  - `ENCRYPTION_KEY`
- Document SendGrid verification/debug steps.
- Document local and production deployment flow.

## Phase 2 Verification

Run after each backend slice:

```bash
python -m unittest discover tests -v
python -m py_compile workers/*.py
git diff --check
```

Cloudflare smoke:

```bash
bash scripts/migrate.sh dev
npx wrangler dev
```

Manual smoke:

1. Create account.
2. Verify email.
3. Log in with credentials.
4. Create organization.
5. Request to join from another account.
6. Approve request as admin.
7. Submit check-in for approved org.
8. Confirm admin dashboard shows today’s check-in and missing/blocker metrics.
9. Confirm unapproved/unverified user cannot check in.

## Phase 2 Acceptance Criteria

- Signup/login/email verification is production-safe enough for MVP.
- Profile verification is available from sidebar.
- Verified users can create organizations.
- Users can request to join organizations.
- Admins can approve/reject/manage members.
- Users can check in only for approved organizations.
- Admin dashboard shows real D1-backed metrics.
- Backend never trusts user-supplied `userId` for authenticated actions.
- Old GitHub OAuth UI is gone from primary product surfaces.
- README/dev/prod migration docs are accurate.

---

## Final Two-Phase Definition of Done

### Phase 1 is done when:

- All pages are visually unified in the BLT-Newsletter-inspired dashboard shell.
- Profile verification, organizations, check-in, requests, members, and dashboard views exist as reviewable UI.
- Frontend contract tests pass.

### Phase 2 is done when:

- Every Phase 1 UI section is wired to real APIs.
- Organization/check-in/admin flows are enforced server-side.
- Dev/prod scripts and docs are complete.
- Full tests and Wrangler smoke pass.

---

## Current Implementation Status

- [x] Requirements and references audited.
- [x] Auth/email foundation.
- [x] App-refactor schema foundation.
- [x] Credential signup/login/email verification backend foundation.
- [x] Public landing and `/login` foundation.
- [x] Phase 1: UI-first dashboard shell and all pages (first reviewable mock UI pass complete; visual polish and browser/user review still open).
- [ ] Phase 2: backend integration and production behavior.
