# GitHub OAuth + PKCE

Browser triage sessions via GitHub OAuth 2.0 Authorization Code + PKCE (`S256`). Bearer org tokens continue to work unchanged.

## Endpoints

| Method | Path | Notes |
|--------|------|------|
| GET | `/api/auth/github/login` | 302 → GitHub authorize |
| GET | `/api/auth/github/callback` | Exchange code, set `ng_session` cookie, 302 → `/triage.html` |
| GET | `/api/auth/me` | Current session (`org_id`, `github_login`) |
| POST/GET | `/api/auth/logout` | Revoke session + clear cookie |

## Env / secrets

- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_OAUTH_REDIRECT_URI` (optional; defaults to `{origin}/api/auth/github/callback`)
- `NG_GITHUB_ORG_MAP` JSON: `{"octocat":"org-demo"}`
- `NG_GITHUB_DEFAULT_ORG` fallback org when login is unmapped (optional)
- `NG_SESSION_TTL_SECONDS` (default 12h)

## Auth coexistence

Resolution order for findings APIs:

1. `Authorization: Bearer <org token>`
2. `Cookie: ng_session=<id>` (D1 `auth_sessions`)
3. Demo default org when `AUTHENTICATE_READ_ENDPOINTS=false` (reads only)

Mutations require Bearer **or** session (no demo fallback).

## Tables

See `migrations/0004_oauth_sessions.sql` (`oauth_states`, `auth_sessions`).


