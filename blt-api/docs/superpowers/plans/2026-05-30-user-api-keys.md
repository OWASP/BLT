# User API Keys Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-owned API keys that can be managed from the authenticated homepage UI and used through `X-BLT-API-Key`.

**Architecture:** Keep JWT Bearer tokens for UI sessions and account-management calls. Add a D1-backed `user_api_keys` table storing only keyed hashes, update the Worker API-key gate to accept dynamic keys, and add `/auth/api-keys` endpoints for key lifecycle management.

**Tech Stack:** Cloudflare Workers Python, D1/SQLite migrations, stdlib HMAC/secrets, existing JWT utilities, existing homepage HTML/JS, pytest.

---

### Task 1: Tests First

**Files:**
- Modify: `tests/test_api_key.py`
- Modify: `tests/test_main_api_key.py`
- Modify: `tests/test_auth.py`
- Modify: `tests/test_homepage.py`

- [ ] Add tests that auth signup/signin/verify routes do not require `X-BLT-API-Key`.
- [ ] Add tests that dynamic `blt_live_...` keys validate against stored hashes and attach `request.user_id`.
- [ ] Add tests for `GET`, `POST`, and `DELETE /auth/api-keys` requiring JWT.
- [ ] Add homepage tests for signin/signup UI and API-key management controls.
- [ ] Run targeted tests and confirm they fail for missing behavior.

### Task 2: Schema and Models

**Files:**
- Create: `migrations/0011_user_api_keys.sql`
- Modify: `src/models.py`

- [ ] Add `user_api_keys` table.
- [ ] Add lookup indexes for `user_id`, `key_hash`, and active keys.
- [ ] Add `UserApiKey` model.

### Task 3: Auth Helpers and API-Key Validation

**Files:**
- Create: `src/libs/auth_context.py`
- Modify: `src/libs/api_key.py`
- Modify: `src/main.py`

- [ ] Add Bearer JWT parsing helper that returns a user id and rejects purpose-scoped verification tokens.
- [ ] Add API-key generation, prefixing, and keyed hashing helpers.
- [ ] Update API-key validation to accept active dynamic keys.
- [ ] Keep static key compatibility.
- [ ] Exempt auth and API-key-management routes from the static API-key gate.

### Task 4: API-Key Management Endpoints

**Files:**
- Modify: `src/handlers/auth.py`
- Modify: `src/handlers/__init__.py`
- Modify: `src/main.py`

- [ ] Add `handle_api_keys`.
- [ ] Implement JWT-required list/create/revoke behavior.
- [ ] Register unversioned and `/v2` routes.
- [ ] Ensure raw key is returned only on create.

### Task 5: Homepage UI

**Files:**
- Modify: `src/pages/index.html`
- Modify: `tests/test_homepage.py`

- [ ] Add sign in/sign up controls.
- [ ] Store JWT session in `sessionStorage`.
- [ ] Add API-key list/create/revoke controls.
- [ ] Include Bearer token and selected/generated API key in Try-it requests.
- [ ] Remove hard-coded-key-first messaging from the main auth section.

### Task 6: Verify

**Files:**
- Test: `tests/test_api_key.py`
- Test: `tests/test_main_api_key.py`
- Test: `tests/test_auth.py`
- Test: `tests/test_homepage.py`

- [ ] Run targeted auth/API-key/homepage tests.
- [ ] Run `uv run --extra dev pytest`.
- [ ] Review `git diff` and confirm `wrangler.toml` remains untouched by this work.

