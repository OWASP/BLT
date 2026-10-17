# GitHub OAuth Setup

BLT-Leaf supports per-user GitHub OAuth tokens so each signed-in user consumes their own GitHub API rate limit.

## Token Modes

BLT-Leaf resolves GitHub tokens in this order:

1. `user_oauth` from encrypted `HttpOnly` session cookie
2. `header_token` from `x-github-token` request header
3. `shared_token` from worker secret `GITHUB_TOKEN`
4. `unauthenticated` (public API limits)

This allows gradual rollout: OAuth users get isolated limits while non-signed-in users can still use shared fallback if configured.

## 1. Register a GitHub OAuth App

In GitHub:

1. Go to `Settings -> Developer settings -> OAuth Apps -> New OAuth App`
2. Set `Authorization callback URL` to:
   - `https://<your-worker-domain>/api/auth/callback`
   - or, if deployed with `/leaf` prefix: `https://<your-worker-domain>/leaf/api/auth/callback`
3. Save and copy:
   - `Client ID`
   - `Client Secret`

Recommended scope: `repo read:user`

## 2. Configure Worker Secrets

Set required OAuth secrets:

```bash
wrangler secret put GITHUB_OAUTH_CLIENT_ID
wrangler secret put GITHUB_OAUTH_CLIENT_SECRET
wrangler secret put ENCRYPTION_KEY
```

Optional fallback shared token:

```bash
wrangler secret put GITHUB_TOKEN
```

Optional scope override (default is `repo read:user`):

```bash
wrangler secret put GITHUB_OAUTH_SCOPE
```

`ENCRYPTION_KEY` must be base64-encoded 32-byte random data.

Example generator:

```bash
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

## 3. Verify End-to-End Flow

1. Open BLT-Leaf in browser.
2. Click `Sign In` and authorize in GitHub.
3. Call `GET /api/auth/user` and verify:
   - `authenticated: true`
   - `token_source: "user_oauth"`
4. Trigger PR actions (`/api/prs`, `/api/refresh`, `/api/prs/{id}/readiness`).
5. Call `GET /api/rate-limit` and verify token metadata:
   - `token_source: "user_oauth"` for logged-in users
   - `token_source: "shared_token"` when fallback token is used

## 4. Security Notes

- OAuth access tokens are encrypted at rest in cookie payloads (AES-GCM).
- Session cookie flags: `HttpOnly`, `Secure`, `SameSite=Lax`.
- OAuth session data is not written to D1.
- Logout (`POST /api/auth/logout`) clears both state and session cookies.
- If cookie decryption fails (tampered/expired/key changed), BLT-Leaf treats the session as logged out.

## 5. Troubleshooting

- `503 GitHub OAuth is not configured`: verify all required secrets are set.
- `401 Invalid OAuth state`: browser lost/blocked state cookie or callback mismatch.
- Sign-in loop after callback: confirm callback URL exactly matches GitHub app config.
- Local `http://` testing can block `Secure` cookies; use deployed HTTPS for reliable OAuth validation.
