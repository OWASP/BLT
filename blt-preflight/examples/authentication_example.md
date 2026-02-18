# Example: Authentication Changes

This example shows how BLT-Preflight provides guidance for authentication-related changes.

## Scenario

A contributor creates a PR that modifies authentication files:
- `src/auth/login.py`
- `src/auth/password_reset.py`

The PR has the following labels:
- `security`
- `authentication`

## Generated Advisory

```markdown
# 🛡️ BLT Preflight Security Advisory

This advisory system helps you understand security expectations before contributing.

---

## 🔴 Critical Security Considerations

### Security Advisory: Security

Security-related changes require thorough review and testing. Follow security best practices and consider potential attack vectors.

**Recommendations:**
- Follow the principle of least privilege
- Implement defense in depth
- Keep security dependencies up to date
- Conduct security testing

**Learn more:**
- https://owasp.org/www-project-top-ten/
- https://cheatsheetseries.owasp.org/

### Security Advisory: Authentication

Authentication changes must follow security best practices including MFA support, secure session management, and protection against common attacks.

**Recommendations:**
- Use multi-factor authentication where possible
- Implement proper session management
- Hash passwords with bcrypt or Argon2
- Add rate limiting to prevent brute force attacks

**Learn more:**
- https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication

### Security Advisory: Authentication

Authentication changes require careful review

**Recommendations:**
- Use multi-factor authentication where possible
- Implement proper session management
- Hash passwords with bcrypt or Argon2
- Add rate limiting to prevent brute force attacks

**Learn more:**
- https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication

---

*This is an advisory system - not enforcement. These suggestions help prevent common security issues.*
*Questions? Check our [documentation](docs/SECURITY_GUIDANCE.md) or ask a maintainer.*
```

## Testing Locally

You can generate this advisory locally:

```bash
python3 src/blt_preflight.py advise \
  --labels "security,authentication" \
  --files "src/auth/login.py,src/auth/password_reset.py" \
  --repo "OWASP-BLT/BLT" \
  --output examples/advisory_authentication.md
```

## Contributor Response

The contributor can:
1. Review the recommendations
2. Follow the OWASP documentation links
3. Update their code accordingly
4. Provide feedback on the advisory

## Providing Feedback

```bash
python3 src/blt_preflight.py feedback \
  --pattern "Security Advisory: Authentication" \
  --helpful yes \
  --comments "Clear recommendations, the OWASP links were very helpful"
```
