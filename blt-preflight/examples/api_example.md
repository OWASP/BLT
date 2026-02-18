# Example: API Development

This example shows how BLT-Preflight provides guidance for API changes.

## Scenario

A contributor creates a PR that adds new API endpoints:
- `src/api/v2/users.py`
- `src/routes/payment.py`

The PR has the label: `api`

## Generated Advisory

```markdown
# 🛡️ BLT Preflight Security Advisory

This advisory system helps you understand security expectations before contributing.

---

## 🟡 Security Warnings

### Security Advisory: Api

API changes should include proper input validation, rate limiting, versioning, and comprehensive documentation.

**Recommendations:**
- Review security implications carefully
- Consult security documentation
- Consider security testing

**Learn more:**
- https://owasp.org/www-project-top-ten/
- https://cheatsheetseries.owasp.org/

### Security Advisory: Api Endpoints

API endpoints should include proper input validation, rate limiting, authentication, and authorization checks.

**Recommendations:**
- Review security implications carefully
- Consult security documentation
- Consider security testing

**Learn more:**
- https://owasp.org/www-project-top-ten/
- https://cheatsheetseries.owasp.org/

---

*This is an advisory system - not enforcement. These suggestions help prevent common security issues.*
*Questions? Check our [documentation](docs/SECURITY_GUIDANCE.md) or ask a maintainer.*
```

## Key Security Considerations for APIs

When the contributor sees this advisory, they should consider:

1. **Input Validation**
   - Validate all request parameters
   - Use strict type checking
   - Implement request size limits

2. **Rate Limiting**
   - Add rate limiting to prevent abuse
   - Consider different limits for authenticated vs. unauthenticated requests

3. **Authentication & Authorization**
   - Ensure endpoints require proper authentication
   - Implement role-based access control
   - Use JWT or OAuth2 for API authentication

4. **Error Handling**
   - Don't leak sensitive information in error messages
   - Return appropriate HTTP status codes
   - Log errors securely

## Testing Locally

```bash
python3 src/blt_preflight.py advise \
  --labels "api" \
  --files "src/api/v2/users.py,src/routes/payment.py" \
  --repo "OWASP-BLT/BLT" \
  --output examples/advisory_api.md
```

## Including Intent

Contributors can improve advisory quality by stating their intent:

```bash
python3 src/blt_preflight.py advise \
  --labels "api" \
  --files "src/api/v2/users.py" \
  --intent "Adding new user management API endpoints with pagination" \
  --output examples/advisory_api_with_intent.md
```

This helps the system provide more targeted guidance.
