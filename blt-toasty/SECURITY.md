# Security Documentation

Welcome to the security documentation for OWASP BLT-Toasty. This document outlines the security architecture, mechanisms, and policies that ensure the confidentiality, integrity, and availability of the service.

## 1. Authentication & Authorization

All MCP and administrative endpoints require strict authentication using JSON Web Tokens (JWT).

- **Authentication Method**: RS256 JWT Bearer token via the `Authorization: Bearer <token>` header.
- **Validation Logic**: Handled by `verify_agent_jwt()` in `src/auth.py`. The token must meet the following criteria:
  - Algorithm: RS256
  - Issuer (`iss`): `owasp-blt-service`
  - Audience (`aud`): `toasty-mcp`
  - Subject (`sub`): A valid agent ID (string)
  - Expiration (`exp`): Must not be expired
- **Key Management**: The public key for verification is loaded from the `MCP_PUBLIC_KEY` environment variable (configured securely via `wrangler secret put`).
- **Endpoint Protection**:
  - Requires valid JWT: `/mcp/triage/*`, `/conversations/*`, `/admin/shadow-report`
  - Requires valid JWT and `role=admin`: `/admin/dashboard`

## 2. Webhook Ingress Security

Webhook endpoints are secured to prevent unauthorized access and replay attacks.

- **Token Verification**: Handled by `verify_gitlab_token()` in `src/webhook_handler.py`. It uses the `X-Gitlab-Token` header for verification.
- **Constant-Time Comparison**: Employs `hmac.compare_digest(secret, provided_token)` to prevent timing attacks.
- **Secret Storage**: The token secret is securely stored in the `GITLAB_WEBHOOK_SECRET` environment variable.
- **Replay Prevention**: The `X-Gitlab-Event-UUID` is recorded in `TOASTY_KV` with an 86,400 second (24-hour) Time-To-Live (TTL). If a duplicate `delivery_id` is encountered, the server immediately returns a `409 Conflict`.

## 3. PII & Secret Redaction Guarantee

Protecting Personally Identifiable Information (PII) and sensitive secrets is a core component of the system, implemented via a fail-closed architecture. If redaction cannot be proven complete, the event is quarantined.

- **Redaction Execution**: PII and secrets are redacted **before** any embedding or LLM processing occurs.
- **Entity Detection**: `src/native_recognizers.py` processes over 17 entity types, including: `EMAIL_ADDRESS`, `IP_ADDRESS`, `JWT_TOKEN`, `AUTH_TOKEN`, `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `AWS_ARN`, `GITHUB_TOKEN`, `API_KEY`, `API_TOKEN`, `DOMAIN`, `HOSTNAME`, `DB_CONNECTION`, `MONGODB_URI`, `USERNAME`, `PASSWORD`, `CREDIT_CARD`, `PRIVATE_KEY`, `BEARER_TOKEN`, and `MD5_HASH`.
- **Confidence Threshold**: The baseline threshold is `0.70`, though native patterns return a confidence of `0.99`.
- **Adversarial Hardening**: Zero-width characters are actively stripped from inputs to prevent evasion.
- **False Positive Mitigation**: A deny-list is employed to suppress false positives (e.g., preserving `CVE-*`, `CWE-*`, and `OWASP-*` formatting).
- **Output Types**:
  - `redacted_text`: Replaces sensitive data with typed placeholders (e.g., `[EMAIL_ADDRESS]`).
  - `safe_preview_text`: Uses a uniform `[REDACTED]` placeholder for external or lower-trust views.
- **Auditing**: All redaction actions are securely logged in the `redaction_audit` D1 database table.

## 4. Rate Limiting & Abuse Prevention

To protect backend resources and prevent abuse, rate limiting is enforced on all API consumers.

- **Mechanism**: Implemented via a `RateLimiterDO` (Durable Object) utilizing a sliding window algorithm based on the `agent_id`.
- **Threshold**: Limited to 100 requests per 60-second window per agent.
- **Enforcement**: Requests exceeding this threshold receive a `429 Too Many Requests` response containing a `retry_after` header.

## 5. Input Validation & Request Safety

All incoming requests are strictly validated to maintain request safety and data integrity.

- **Payload Size Limits**: The maximum body size for any request is strictly enforced at 1MB (1,048,576 bytes).
- **Schema Validation**: Comprehensive JSON schema validation is performed on all API endpoints.
- **Path Traversal Prevention**: The system explicitly rejects paths containing unauthorized characters (e.g., rejecting any `triage_id` that contains a `/`).
- **CORS Support**: Handled gracefully via an `OPTIONS` handler, providing `Access-Control-Allow-Origin: *`.

## 6. Vulnerability Reporting Policy

As part of the OWASP foundation, BLT-Toasty takes security vulnerabilities seriously.

If you believe you have found a security vulnerability in this project, please do not report it via public GitHub issues. Instead, adhere to the standard OWASP vulnerability disclosure procedures. Reach out to the project maintainers directly via official OWASP communication channels (such as the official project mailing list or designated security contact) to report the issue responsibly. All reports will be handled promptly and confidentially.
