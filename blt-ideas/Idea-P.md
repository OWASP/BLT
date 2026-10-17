Secure API Development & Migration to Django Ninja (v2 API)

## Goal
Deliver a secure, fast, maintainable **v2 API on Django Ninja** alongside the existing **DRF v1**, then deprecate v1. Tighten security, standardize validation/pagination/filtering, publish OpenAPI-first SDKs, and provide a smooth migration path.

---

## Why this matters (from code scan)
- **Current stack:** DRF (APIView/ViewSets), TokenAuthentication, multiple serializers, mixed auth (some no-auth views), app-level URLs, `/api/v1` patterns in tests.
- **Gaps to address:** unified auth + scopes, typed request validation, consistent pagination/filtering, rate limiting + quotas, complete OpenAPI, and first-party SDKs.

---

## Scope and phases

### Phase 0 — Planning and baseline (~15 hrs)
- Inventory endpoints and dependencies; classify by auth/public.
- Agree on migration plan and success metrics (latency, error rate, coverage).

### Phase 1 — Stand up Ninja v2 alongside DRF v1 (~60–70 hrs)
- Add `django-ninja`, create v2 router, define Pydantic schemas for:
  - Users / UserProfile
  - Issues (+ screenshots)
  - Projects / Repos
  - Organizations
  - Hunts
- Map DRF serializers → Ninja schemas; normalize pagination and filtering.
- Shared auth adapter: keep TokenAuth for now; design pluggable auth for Phase 3.

### Phase 2 — Port high-traffic endpoints + parity tests (~70–80 hrs)
- Implement v2 for: **Issues, Projects, Organizations, Users, Hunts**.
- Add contract/parity tests to assert v1 ↔ v2 response parity where intended.
- Uniform error model and idempotent writes (where applicable).
- Deprecation headers on v1 responses; migration guide draft.

### Phase 3 — Security hardening (to reach 350 hrs) (~60–90 hrs)
- OAuth2/JWT with scopes (replace TokenAuth progressively).
- Per-endpoint permission matrix; consistent CSRF/CORS posture.
- Rate limiting/quotas (e.g., `django-ratelimit`) with org/user keys.
- Webhook security: enforce HMAC-SHA256 verification + replay guards.
- Audit logs for write operations (who/when/what).

### Phase 4 — DX & adoption (to reach 350 hrs) (~60–90 hrs)
- OpenAPI 3.1 with examples; linting CI gate.
- SDKs generated from OpenAPI (Python + TypeScript) + smoke tests.
- API Explorer page and “try it” tokens for org admins.
- Backwards-compat helpers: response mappers, deprecation schedule, migration cookbook.

### Phase 5 — Performance & observability (optional) (~30–50 hrs)
- Caching strategy (per-object GETs with ETag/Last-Modified).
- OTel metrics/tracing for top endpoints; SLO dashboards; structured logs.

---

## Deliverables and acceptance criteria

### Deliverables
- v2 Ninja endpoints for **Issues, Projects, Organizations, Users, Hunts** with parity tests vs v1 where applicable.
- Security upgrades:
  - OAuth2/JWT with scopes
  - rate limits/quotas
  - webhook HMAC enforcement
  - consistent CORS/CSRF rules
- DX improvements:
  - OpenAPI 3.1 spec
  - generated SDKs (Python + TypeScript)
  - migration guide, deprecation policy + headers
- Quality and performance:
  - high test coverage for v2
  - improved read latency vs v1
  - zero high-severity security findings in review

### Acceptance criteria
- **Parity:** v2 responses match v1 where intended (validated by contract tests).
- **Security:** scopes enforced; rate limiting in place; webhook signatures verified; audit logs for write actions.
- **DX:** OpenAPI 3.1 generated and validated in CI; SDKs generated and smoke-tested; migration guide published.
- **Quality:** ≥90% v2 endpoint test coverage; measurable latency improvement for key read endpoints.

---

## Notes on scope flexibility (AI + cross-project synergy)
- **AI acceleration:** Some tasks (schema generation, contract test scaffolding, docs, and OpenAPI examples) can become significantly faster with AI-assisted development, potentially reducing total effort and compressing later phases.
- **Mergeability / clubbing with other projects:** This proposal can be **paired or partially merged** with related initiatives (e.g., **Idea K**) by sharing OpenAPI tooling, auth/scopes groundwork, SDK generation pipelines, and common security hardening patterns—making both projects easier to deliver with less duplicated work.
