# Static API Key Implementation Plan

> **For agentic workers:** Use this file as the working context and checklist for the static API-key feature. Keep the checkbox state current as implementation progresses.

**Goal:** Add a shared static API key gate to BLT API so external users include one documented key on API requests to `api.owaspblt.org`.

**Architecture:** Store the expected key in the Worker environment as `BLT_API_KEY`. Clients send it in `X-BLT-API-Key`. The Worker entrypoint validates the key before dispatching to the router, with only docs, health, and CORS preflight left public.

**Tech Stack:** Python 3.12, Cloudflare Workers Python runtime, existing custom router, pytest.

---

## Context

- Current entrypoint: `src/main.py`
- Current route dispatcher: `src/router.py`
- Current auth handlers: `src/handlers/auth.py`
- Current client wrapper: `src/client.py`
- Current public docs page: `src/pages/index.html`
- Current env sample: `.env.sample`
- Current README auth docs mention `Authorization: Token YOUR_API_TOKEN`, but there is no shared API-key enforcement yet.
- Baseline verification before feature work: `uv run --extra dev pytest -q` passed with `195 passed`.
- Current branch when this plan was created: `feat/add-api-key`.

## Product Decision

- Use maintainer-approved option 2: one shared/static API key for now.
- This is not per-user API-key management.
- Do not add database tables, migrations, user profile API-key screens, key creation, or key rotation endpoints in this pass.
- Keep JWT/user auth separate from this shared API-key gate.

## API Contract

Required request header:

```http
X-BLT-API-Key: <shared-static-key>
```

Expected environment variable:

```env
BLT_API_KEY=<shared-static-key>
```

Public routes that do not require the shared key:

- `OPTIONS` requests
- `GET /`
- `GET /v2`
- `GET /health`
- `GET /v2/health`

Protected routes:

- All other current and future routes, including `/routes`, `/auth/signup`, `/auth/signin`, and data endpoints.

Failure behavior:

- Missing key: `401` JSON error.
- Invalid key: `401` JSON error.
- `BLT_API_KEY` missing from env on a protected route: `500` JSON error, because the server is misconfigured.

## Implementation Checklist

- [x] Capture repo context and baseline state in this MD file.
- [x] Add failing tests for API-key helper behavior.
- [x] Add failing tests for Worker entrypoint enforcement.
- [x] Add failing tests for client header support.
- [x] Implement `src/libs/api_key.py`.
- [x] Wire API-key enforcement into `src/main.py` before router dispatch.
- [x] Update CORS allowed headers to include `X-BLT-API-Key`.
- [x] Update `BLTClient` to optionally send `X-BLT-API-Key`.
- [x] Update `.env.sample`.
- [x] Update README authentication documentation.
- [x] Update homepage authentication snippet.
- [x] Run focused tests.
- [x] Run full test suite.

## Out of Scope

- Per-user API keys.
- API-key persistence in D1.
- Admin UI for creating/revoking keys.
- Rate limiting keyed by API key.
- Multiple active keys or rotation windows.
- Replacing JWT auth.
