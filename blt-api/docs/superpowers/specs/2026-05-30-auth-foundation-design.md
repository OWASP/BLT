# Auth Foundation Design

## Goal

Build the phase-one authentication foundation for BLT-API using local username/email/password registration, email verification through the existing SendGrid email service, and JWT access tokens returned as Bearer tokens.

## Scope

Phase one includes local authentication only. GitHub login is intentionally deferred because it requires OAuth redirect handling, callback state validation, account linking, GitHub email verification handling, and provider collision rules. The schema will still include a provider identity table so GitHub can be added later without reshaping the user model.

## API Behavior

- `POST /auth/signup` remains the canonical public registration endpoint.
- Signup accepts `username`, `email`, and `password`.
- Signup stores username and email encrypted, stores blind indexes for equality lookup, stores a PBKDF2 password hash, creates the user inactive, creates a local auth identity row, and sends a verification email.
- Verification links use `/auth/verify-email?token=...` and expire after 24 hours.
- `GET /auth/verify-email` decodes a purpose-scoped JWT, activates the user, and records `email_verified_at`.
- `POST /auth/signin` accepts `identifier` plus `password`; `identifier` can be either username or email.
- For backwards compatibility, `POST /auth/signin` also accepts the existing `username` field.
- Successful signin returns `access_token`, `token_type: Bearer`, and `expires_in`. The legacy `token` field can remain as a compatibility alias during phase one.

## Data Model

The `users` table remains the canonical profile table. It stores encrypted sensitive fields and blind indexes:

- `username_encrypted`
- `username_hash`
- `email_encrypted`
- `email_hash`
- `password`
- `is_active`
- `email_verified_at`

A new `user_auth_identities` table records login/provider identity:

- `user_id`
- `provider` such as `local` now and `github` later
- `provider_user_id`
- encrypted provider username/email metadata
- provider email blind index
- timestamps for creation and last login

For local auth, `provider_user_id` is the BLT user id string.

## Email Service

Use the existing `EmailService` in `src/services/email_service.py`. It sends through SendGrid Web API v3 and renders the existing HTML verification template. The current code already sends verification emails during signup; phase one will align the token expiry with the email copy and update docs/config names to the active SendGrid service.

## Security

- Passwords stay hashed with PBKDF2-SHA256 and per-user salt.
- Email and username lookup use blind indexes rather than plaintext.
- JWTs remain HS256 with `JWT_SECRET`.
- Email verification tokens include a purpose claim so access tokens cannot be reused as verification tokens.
- Signin errors remain generic for missing users and invalid passwords.
- Inactive users cannot sign in.

## Testing

Focused tests will cover:

- signup sends verification email with a 24-hour expiry and creates a local identity row
- signin by email
- signin by username remains supported
- signin response includes Bearer token fields
- verification rejects non-verification JWTs
- verification activates the user and records `email_verified_at`
- client auth headers use `Authorization: Bearer ...`
