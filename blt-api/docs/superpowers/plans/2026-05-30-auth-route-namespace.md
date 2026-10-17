# Auth Route Namespace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate browser auth pages from JSON auth API routes so `/auth` can serve UI while `/api/auth/*` owns authentication API calls.

**Architecture:** Keep the current auth handlers as the business-logic layer and register new canonical API routes under `/api/auth/*`. Add a dedicated auth page handler for `GET /auth`; update homepage/auth-page JavaScript, email verification links, API-key gate rules, tests, and docs to use `/api/auth/*`. Preserve existing `/auth/*` and `/v2/auth/*` API routes as temporary compatibility aliases so already-shipped clients and existing email verification links do not break.

**Tech Stack:** Cloudflare Workers Python, existing custom `Router`, existing auth handlers in `src/handlers/auth.py`, static HTML/JS pages under `src/pages`, pytest.

---

## Route Decision

Canonical browser routes:
- `GET /auth`: sign in, sign up, email verification state, API-key management UI.
- `GET /`: API docs/homepage that links to `/auth`; it may keep a compact auth panel, but any full auth experience should live on `/auth`.

Canonical JSON API routes:
- `POST /api/auth/signup`
- `POST /api/auth/signin`
- `GET /api/auth/verify-email`
- `GET /api/auth/api-keys`
- `POST /api/auth/api-keys`
- `DELETE /api/auth/api-keys/{id}`

Compatibility aliases for one release:
- Existing `/auth/signup`, `/auth/signin`, `/auth/verify-email`, `/auth/api-keys`, `/auth/api-keys/{id}`
- Existing `/v2/auth/signup`, `/v2/auth/signin`, `/v2/auth/verify-email`, `/v2/auth/api-keys`, `/v2/auth/api-keys/{id}`

Recommended verification link:
- New email links should point to `/auth?verify_token=<token>`.
- The auth page should call `GET /api/auth/verify-email?token=<token>` and render the result.
- Keep `GET /auth/verify-email?token=<token>` working as a legacy JSON endpoint for already-sent emails.

---

## File Structure

- Modify: `src/main.py`
  - Register `GET /auth` for the auth page.
  - Register canonical `/api/auth/*` routes.
  - Keep old `/auth/*` and `/v2/auth/*` route aliases.

- Create: `src/handlers/auth_page.py`
  - Serve `src/pages/auth.html`.
  - Inject `[[API_BASE_URL]]` as the origin only, not `/v2`, so the UI calls canonical `/api/auth/*`.

- Modify: `src/handlers/__init__.py`
  - Export `handle_auth_page`.

- Create: `src/pages/auth.html`
  - Browser UI for signin, signup, email verification, and API-key management.
  - Use `fetch(baseUrl + "/api/auth/...")` for JSON calls.

- Modify: `src/pages/index.html`
  - Link to `/auth`.
  - If the embedded auth section remains, update all auth fetch calls from `/auth/*` to `/api/auth/*`.

- Modify: `src/libs/api_key.py`
  - Make `GET /auth` public.
  - Make `/api/auth/signup`, `/api/auth/signin`, and `/api/auth/verify-email` public.
  - Make `/api/auth/api-keys` JWT-only, not `X-BLT-API-Key` gated.
  - Keep legacy exemptions for old auth paths.

- Modify: `src/services/email_service.py`
  - Generate browser verification links as `/auth?verify_token=<token>`.

- Modify: `README.md`
  - Document `/auth` as the browser page.
  - Document `/api/auth/*` as canonical API endpoints.
  - Mark `/auth/*` API endpoints as temporary compatibility aliases.

- Test: `tests/test_auth_page.py`
  - New auth page handler tests.

- Modify: `tests/test_main_api_key.py`
  - API-key gate tests for new canonical routes and `/auth` page.

- Modify: `tests/test_homepage.py`
  - Homepage link and fetch path tests.

- Modify: `tests/test_api_key.py`
  - Public/JWT-only route classification tests.

- Modify: `tests/test_auth.py`
  - Route path expectations only if any assertions depend on `/auth/*` strings.

---

### Task 1: Add failing route namespace tests

**Files:**
- Create: `tests/test_auth_page.py`
- Modify: `tests/test_main_api_key.py`
- Modify: `tests/test_api_key.py`
- Modify: `tests/test_homepage.py`

- [ ] **Step 1: Add auth page handler tests**

Create `tests/test_auth_page.py`:

```python
"""Tests for the browser auth page."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from handlers.auth_page import handle_auth_page  # noqa: E402


class MockRequest:
    def __init__(self, url="https://api.example.com/auth"):
        self.url = url
        self.method = "GET"


class MockEnv:
    pass


async def test_auth_page_returns_html():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert response.status == 200
    assert "text/html" in response.headers["Content-Type"]
    assert "authSigninForm" in response.body
    assert "authSignupForm" in response.body


async def test_auth_page_uses_api_auth_routes():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert "/api/auth/signin" in response.body
    assert "/api/auth/signup" in response.body
    assert "/api/auth/api-keys" in response.body
    assert "baseUrl + '/auth/signin'" not in response.body
```

- [ ] **Step 2: Add API-key gate route tests**

In `tests/test_api_key.py`, extend the public route parametrization with:

```python
("GET", "https://api.example.com/auth"),
("POST", "https://api.example.com/api/auth/signup"),
("POST", "https://api.example.com/api/auth/signin"),
("GET", "https://api.example.com/api/auth/verify-email?token=abc"),
```

Extend the JWT-only route assertions with:

```python
("GET", "https://api.example.com/api/auth/api-keys"),
("POST", "https://api.example.com/api/auth/api-keys"),
("DELETE", "https://api.example.com/api/auth/api-keys/1"),
```

- [ ] **Step 3: Add Worker route registration tests**

In `tests/test_main_api_key.py`, add tests that assert:

```python
assert not is_api_key_required("GET", "https://api.example.com/auth")
assert not is_api_key_required("POST", "https://api.example.com/api/auth/signin")
assert not is_api_key_required("POST", "https://api.example.com/api/auth/signup")
assert not is_api_key_required("GET", "https://api.example.com/api/auth/verify-email?token=abc")
assert not is_api_key_required("GET", "https://api.example.com/api/auth/api-keys")
```

- [ ] **Step 4: Add homepage path expectations**

In `tests/test_homepage.py`, add assertions against the rendered homepage:

```python
assert 'href="/auth"' in content or "href='/auth'" in content
assert "/api/auth/signin" in content
assert "/api/auth/signup" in content
assert "/api/auth/api-keys" in content
```

- [ ] **Step 5: Run tests to verify failure**

Run:

```bash
uv run --extra dev pytest tests/test_auth_page.py tests/test_api_key.py tests/test_main_api_key.py tests/test_homepage.py -q
```

Expected: FAIL because `handlers.auth_page` does not exist yet and `/api/auth/*` is not registered/exempted.

---

### Task 2: Add the `/auth` browser page

**Files:**
- Create: `src/handlers/auth_page.py`
- Create: `src/pages/auth.html`
- Modify: `src/handlers/__init__.py`
- Modify: `src/main.py`

- [ ] **Step 1: Create `handle_auth_page`**

Create `src/handlers/auth_page.py`:

```python
"""Browser auth page handler."""

from pathlib import Path
from typing import Any, Dict

try:
    from js import Response, Headers
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    from utils import Response, Headers


async def handle_auth_page(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    url = str(request.url)
    if "://" in url:
        scheme, rest = url.split("://", 1)
        host = rest.split("/", 1)[0]
        base_url = f"{scheme}://{host}"
    else:
        base_url = "https://blt-api.workers.dev"

    html_file = Path(__file__).resolve().parent.parent / "pages" / "auth.html"
    html_content = html_file.read_text(encoding="utf-8").replace("[[API_BASE_URL]]", base_url)

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-BLT-API-Key",
    }

    if _WORKERS_RUNTIME:
        return Response.new(html_content, status=200, headers=Headers.new(list(headers.items())))

    return Response.new(html_content, {"status": 200, "headers": headers})
```

- [ ] **Step 2: Create `src/pages/auth.html`**

Use the existing auth UI from `src/pages/index.html`, but make these path changes:

```javascript
const authApi = {
    signin: '/api/auth/signin',
    signup: '/api/auth/signup',
    verifyEmail: '/api/auth/verify-email',
    apiKeys: '/api/auth/api-keys'
};
```

All auth calls must use those constants:

```javascript
fetch(baseUrl + authApi.signin, { method: 'POST', headers, body });
fetch(baseUrl + authApi.signup, { method: 'POST', headers, body });
authFetch(authApi.apiKeys);
authFetch(`${authApi.apiKeys}/${id}`, { method: 'DELETE' });
```

Handle email verification query params:

```javascript
const params = new URLSearchParams(window.location.search);
const verifyToken = params.get('verify_token');
if (verifyToken) {
    fetch(`${baseUrl}${authApi.verifyEmail}?token=${encodeURIComponent(verifyToken)}`)
        .then((response) => response.json())
        .then((data) => setMessage('signinMessage', data.message || 'Email verification complete.', false))
        .catch((error) => setMessage('signinMessage', error.message, true));
}
```

- [ ] **Step 3: Export the handler**

Modify `src/handlers/__init__.py`:

```python
from .auth_page import handle_auth_page
```

Add `"handle_auth_page"` to `__all__`.

- [ ] **Step 4: Register the page route**

Modify `src/main.py` imports:

```python
handle_auth_page,
```

Register before auth API routes:

```python
router.add_route("GET", "/auth", handle_auth_page)
```

- [ ] **Step 5: Run auth page tests**

Run:

```bash
uv run --extra dev pytest tests/test_auth_page.py -q
```

Expected: PASS.

---

### Task 3: Add canonical `/api/auth/*` API routes

**Files:**
- Modify: `src/main.py`
- Modify: `src/libs/api_key.py`

- [ ] **Step 1: Register canonical auth API routes**

In `src/main.py`, add a small helper near the auth route registrations:

```python
def _add_auth_api_routes(prefix: str) -> None:
    router.add_route("POST", f"{prefix}/signup", handle_signup)
    router.add_route("POST", f"{prefix}/signin", handle_signin)
    router.add_route("GET", f"{prefix}/verify-email", handle_verify_email)
    router.add_route("GET", f"{prefix}/api-keys", handle_api_keys)
    router.add_route("POST", f"{prefix}/api-keys", handle_api_keys)
    router.add_route("DELETE", f"{prefix}/api-keys/{{id}}", handle_api_keys)
```

Call it for the canonical API namespace:

```python
_add_auth_api_routes("/api/auth")
```

Keep the current legacy route registrations for `/auth/*` and `/v2/auth/*`.

- [ ] **Step 2: Exempt canonical public auth routes from `X-BLT-API-Key`**

Modify `PUBLIC_API_KEY_PATHS` in `src/libs/api_key.py`:

```python
PUBLIC_API_KEY_PATHS = {
    "/",
    "/v2",
    "/auth",
    "/health",
    "/v2/health",
    "/api/auth/signup",
    "/api/auth/signin",
    "/api/auth/verify-email",
    "/auth/signup",
    "/v2/auth/signup",
    "/auth/signin",
    "/v2/auth/signin",
    "/auth/verify-email",
    "/v2/auth/verify-email",
}
```

- [ ] **Step 3: Exempt canonical API-key management from the API-key gate**

Modify `JWT_ONLY_PATH_PREFIXES` in `src/libs/api_key.py`:

```python
JWT_ONLY_PATH_PREFIXES = (
    "/api/auth/api-keys",
    "/auth/api-keys",
    "/v2/auth/api-keys",
)
```

- [ ] **Step 4: Run route and gate tests**

Run:

```bash
uv run --extra dev pytest tests/test_api_key.py tests/test_main_api_key.py -q
```

Expected: PASS.

---

### Task 4: Update pages to call `/api/auth/*`

**Files:**
- Modify: `src/pages/index.html`
- Modify: `tests/test_homepage.py`

- [ ] **Step 1: Add a homepage link to the auth page**

Add a visible link near the Authentication section or navbar:

```html
<a href="/auth" class="text-red-600 hover:underline">Open authentication page</a>
```

- [ ] **Step 2: Update homepage auth fetch paths**

Replace homepage auth calls:

```javascript
authFetch('/auth/api-keys')
authFetch(`/auth/api-keys/${id}`, { method: 'DELETE' })
fetch(baseUrl + '/auth/signin', ...)
fetch(baseUrl + '/auth/signup', ...)
```

with:

```javascript
authFetch('/api/auth/api-keys')
authFetch(`/api/auth/api-keys/${id}`, { method: 'DELETE' })
fetch(baseUrl + '/api/auth/signin', ...)
fetch(baseUrl + '/api/auth/signup', ...)
```

- [ ] **Step 3: Run homepage tests**

Run:

```bash
uv run --extra dev pytest tests/test_homepage.py -q
```

Expected: PASS.

---

### Task 5: Update email verification links

**Files:**
- Modify: `src/services/email_service.py`
- Modify: `src/services/templates/README.md`
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Generate browser verification links**

Modify `src/services/email_service.py`:

```python
verification_link = f"{base_url}/auth?verify_token={verification_token}"
```

Keep the existing `handle_verify_email` JSON API unchanged because it will now be reached through `/api/auth/verify-email` by the browser page.

- [ ] **Step 2: Update template docs**

Replace example links in `src/services/templates/README.md`:

```text
https://api.owaspblt.org/auth?verify_token=abc123
```

- [ ] **Step 3: Update signup tests if they assert links**

If `tests/test_auth.py` asserts the email verification URL, expect `/auth?verify_token=` instead of `/auth/verify-email?token=`.

- [ ] **Step 4: Run auth tests**

Run:

```bash
uv run --extra dev pytest tests/test_auth.py -q
```

Expected: PASS.

---

### Task 6: Update docs and production guidance

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update endpoint table**

Change auth endpoint rows to:

```markdown
| POST | `/api/auth/signup` | Register a new user |
| POST | `/api/auth/signin` | Sign in and get Bearer JWT |
| GET | `/api/auth/verify-email` | Verify email address JSON API |
| GET | `/api/auth/api-keys` | List user API keys, Bearer JWT required |
| POST | `/api/auth/api-keys` | Create user API key, Bearer JWT required |
| DELETE | `/api/auth/api-keys/{id}` | Revoke user API key, Bearer JWT required |
```

- [ ] **Step 2: Add UI route docs**

Add:

```markdown
Open `/auth` in a browser to sign up, sign in, verify email links, and create user-owned `X-BLT-API-Key` values.
```

- [ ] **Step 3: Add compatibility note**

Add:

```markdown
Legacy `/auth/*` auth API paths are still accepted during the namespace migration, but new clients should use `/api/auth/*`.
```

- [ ] **Step 4: Run README-related tests if present**

Run:

```bash
uv run --extra dev pytest tests/test_homepage.py tests/test_api_key.py -q
```

Expected: PASS.

---

### Task 7: Full verification

**Files:**
- No code changes.

- [ ] **Step 1: Run the focused auth namespace suite**

Run:

```bash
uv run --extra dev pytest tests/test_auth_page.py tests/test_auth.py tests/test_api_key.py tests/test_main_api_key.py tests/test_homepage.py -q
```

Expected: all selected tests PASS.

- [ ] **Step 2: Run the full suite**

Run:

```bash
uv run --extra dev pytest
```

Expected: full suite PASS.

- [ ] **Step 3: Smoke test locally**

Run:

```bash
bunx wrangler dev --port 8788
```

Verify in a browser or with curl:

```bash
curl -s http://localhost:8788/auth
curl -s -X POST http://localhost:8788/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"identifier":"missing","password":"missing"}'
```

Expected:
- `/auth` returns HTML with the auth forms.
- `/api/auth/signin` returns JSON and does not ask for `X-BLT-API-Key`.

---

## Self-Review

Spec coverage:
- `/auth` is reserved for browser UI.
- `/api/auth/*` is the canonical auth API namespace.
- Existing auth API paths remain compatible for this iteration.
- Email verification gets a browser-friendly link without breaking old JSON verification links.
- API-key gate behavior is explicitly updated and tested.
- Homepage and auth page fetch paths are covered.

Placeholder scan:
- No TBD/TODO placeholders.
- Every task names files, concrete route paths, test commands, and expected results.

Type consistency:
- Route names use the existing `Router.add_route(method, pattern, handler)` convention.
- Handler signature matches existing page handlers.
- UI fetch paths consistently use `/api/auth/*`.
