# BLT-API agent instructions

This file is for coding agents working on BLT-API, the Cloudflare Workers API for OWASP BLT. Keep README.md human-first: short, clear, polished, and complete. Put agent-specific operational detail here.

## Start here

1. Read README.md for the human overview and public API shape.
2. Read CONTRIBUTING.md for setup, local D1 workflow, and contribution rules.
3. Read docs/DATABASE.md before changing schema, D1 queries, or migrations.
4. Inspect the relevant handler and tests before editing code.

## Request flow map

- `src/main.py` is the Cloudflare Workers entrypoint and route registry.
- `Default.on_fetch` handles CORS preflight, checks the API gate, then dispatches to `src/router.py`.
- `src/router.py` parses paths/query strings and calls handlers with `request`, `env`, `path_params`, `query_params`, and `path`.
- `src/handlers/` contains endpoint behavior. Keep handler changes focused.
- `src/libs/db.py` resolves the Cloudflare D1 binding (`blt_api`).
- `migrations/` contains D1 schema migrations; prefer a new migration over editing applied history.
- `tests/` contains regression coverage. Add or update tests for every behavior change.

## Page and browser route map

- `GET /` -> `src/pages/index.html`: public landing page for humans.
- `GET /dashboard` -> `src/pages/dashboard.html`: interactive API explorer/docs UI.
- `GET /auth` -> `src/handlers/auth_page.py`: legacy browser alias that serves dashboard, not JSON auth.
- `GET /blt-api.png` -> `static/blt-api.png`: logo asset route.
- `src/pages/old-dashboard.html` is a gitignored local backup if present; do not treat it as routed or committed.

## Auth and API access

- `X-BLT-API-Key` is the protected API access gate. It is enforced before normal route dispatch through `src/libs/api_key.py`.
- JWT/Bearer tokens represent signed-in user identity and user session state.
- Do not conflate the shared/user API key gate with JWT identity.
- Do not change `X-BLT-API-Key` enforcement unless the issue explicitly asks for it.

## Routes and versions

- Existing unversioned routes remain backward compatible.
- `/v2` routes are registered in `src/main.py` and should be preferred by new API consumers where available.
- If you add or rename a route, update route registration, handler exports, route/discovery expectations, and tests together.

## D1, secrets, and integrations

- Use Wrangler and scripts from `scripts/` for local/remote D1 setup.
- Never commit secrets, real API keys, JWT secrets, Mailgun credentials, or production environment values.
- Keep examples secret-free and use placeholder values only.
- Check CORS behavior in `src/utils.py` before changing allowed headers.

## Agent guardrails

- Follow TDD for code changes: write the failing test, verify it fails, implement, verify it passes.
- Keep comments short and useful; avoid context dumps in source files.
- Avoid broad refactors while solving issue-scoped work.
- Anonymous report work is out of scope unless a current issue explicitly asks for it.
- Do not make README.md an agent manual. Link to focused docs instead.

## Useful commands

```bash
uv sync
uv tool install workers-py
bash scripts/setup_local_db.sh
wrangler dev --port 8787
uv run pytest
```

For temporary test runners, include missing test dependencies such as `pytest`, `pytest-asyncio`, and `requests`.
