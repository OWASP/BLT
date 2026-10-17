# Auth Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the phase-one local authentication foundation with email verification, Bearer JWT responses, and provider identity schema for future GitHub login.

**Architecture:** Keep `users` as the canonical profile table, use the existing SendGrid email service for verification, and add a separate `user_auth_identities` table for provider-specific login identities. Update auth handlers with minimal local-auth behavior and preserve backward compatibility where cheap.

**Tech Stack:** Cloudflare Workers Python, D1/SQLite migrations, stdlib JWT utilities, SendGrid Web API email service, pytest.

---

### Task 1: Add Failing Auth Tests

**Files:**
- Modify: `tests/test_auth.py`
- Modify: `tests/test_client.py`

- [ ] Add tests for signup creating a local auth identity and sending a 24-hour verification email.
- [ ] Add tests for signin by email and Bearer token response fields.
- [ ] Add tests for verification token purpose and `email_verified_at`.
- [ ] Add a client test expecting `Authorization: Bearer <token>`.
- [ ] Run targeted tests and confirm they fail for the missing behavior.

### Task 2: Add Schema and Model

**Files:**
- Create: `migrations/0010_auth_foundation.sql`
- Modify: `src/models.py`

- [ ] Add `email_verified_at` to `users`.
- [ ] Add `user_auth_identities`.
- [ ] Add uniqueness on `(provider, provider_user_id)`.
- [ ] Add lookup indexes for `user_id`, `provider`, and provider email blind index.
- [ ] Add `UserAuthIdentity` model.

### Task 3: Update Auth Handler

**Files:**
- Modify: `src/handlers/auth.py`

- [ ] Add 24-hour email verification token expiry.
- [ ] Add purpose claim to verification tokens.
- [ ] Create a `local` identity row during signup.
- [ ] Accept `identifier` or legacy `username` during signin.
- [ ] Look up by email blind index when identifier is an email.
- [ ] Return Bearer fields from signin while preserving legacy `token`.
- [ ] Record `email_verified_at` on verification.

### Task 4: Update Client and Docs

**Files:**
- Modify: `src/client.py`
- Modify: `README.md`
- Modify: `src/pages/index.html`

- [ ] Change client auth header to `Bearer`.
- [ ] Update README auth examples to `Bearer`.
- [ ] Replace stale email config docs with SendGrid config names.
- [ ] Update homepage auth text to show `Bearer`.

### Task 5: Verify

**Files:**
- Test: `tests/test_auth.py`
- Test: `tests/test_client.py`

- [ ] Run `uv run --extra dev pytest tests/test_auth.py tests/test_client.py -q`.
- [ ] Run full `uv run --extra dev pytest`.
- [ ] Review `git diff` for unrelated changes and avoid touching the existing `wrangler.toml` modification.
