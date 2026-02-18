# Contributing to BLT-Preflight

Thank you for your interest in contributing to BLT-Preflight! This document explains how to work with the advisory system as a contributor.

## Understanding the Advisory System

BLT-Preflight is an **advisory system** that provides security guidance when you open a pull request or issue. It's designed to:

- Help you understand security expectations
- Prevent common security mistakes
- Link you to relevant documentation
- Improve your security knowledge

**Important**: The advisory is **not enforcement**. You won't be blocked from contributing, and maintainers have the final say. The guidance is meant to help, not hinder.

## How It Works

### 1. Open a Pull Request

When you open a PR, the advisory system:

1. Analyzes the files you've changed
2. Checks the labels on your PR
3. Evaluates security patterns
4. Generates personalized security guidance
5. Posts a comment on your PR

### 2. Review the Advisory

The advisory comment includes:

- **Severity levels**: Critical (🔴), Warning (🟡), Info (🔵)
- **Plain-language guidance**: Clear explanation of security considerations
- **Recommendations**: Specific actions you can take
- **Documentation links**: OWASP and security resources

### 3. Take Action (Optional)

Based on the advisory, you can:

- Review and update your code
- Read the linked documentation
- Ask questions in the PR comments
- Provide feedback on the advisory

### 4. Provide Feedback

Help us improve! Let us know if the advisory was helpful:

```bash
# Provide feedback via CLI
python3 src/blt_preflight.py feedback \
  --pattern "Security Advisory: Authentication" \
  --helpful yes \
  --comments "The recommendations were very clear"
```

Or add a comment in your PR: "The security advisory was helpful!" or "The advisory could be improved by..."

## Examples of Advisory Responses

### Example 1: Authentication Changes

If you modify authentication files:

```
# 🛡️ BLT Preflight Security Advisory

## 🔴 Critical Security Considerations

### Security Advisory: Authentication

Authentication changes require careful review

**Recommendations:**
- Use multi-factor authentication where possible
- Implement proper session management
- Hash passwords with bcrypt or Argon2
- Add rate limiting to prevent brute force attacks

**Learn more:**
- [OWASP Authentication Cheat Sheet]
- [OWASP Broken Authentication]
```

**What to do:**
1. Review the recommendations
2. Check if your code implements these security practices
3. Read the linked OWASP documentation
4. Update your code if needed

### Example 2: API Changes

If you add or modify API endpoints:

```
## 🟡 Security Warnings

### Security Advisory: Api Endpoints

API endpoints should include proper input validation, rate limiting,
authentication, and authorization checks.
```

**What to do:**
1. Ensure your API validates all inputs
2. Add rate limiting if not present
3. Verify authentication requirements
4. Review the OWASP API Security documentation

## Improving Your Advisory

You can get more targeted guidance by:

### 1. Adding Relevant Labels

Apply appropriate labels to your PR:
- `security` - Security-related changes
- `authentication` - Authentication work
- `api` - API changes
- `data-privacy` - Data privacy considerations

### 2. Stating Your Intent

In your PR description, clearly state what you're trying to accomplish:

```markdown
**Intent**: Adding OAuth2 support for third-party authentication

This PR implements OAuth2 authentication flow using...
```

The system uses this to provide more relevant guidance.

### 3. Being Specific About Changes

In your PR description, mention:
- What security aspects you've considered
- What security measures you've implemented
- Any questions you have about security

## Common Advisory Patterns

### 🔐 Authentication
- **Triggered by**: Files in `auth/`, `login/`, `password/` directories
- **Focus**: Password hashing, session management, MFA
- **Documentation**: OWASP Authentication Cheat Sheet

### 🔑 API Keys & Secrets
- **Triggered by**: Files with `secret`, `key`, `token` in name, `.env` files
- **Focus**: Never commit secrets, use environment variables
- **Documentation**: OWASP Secrets Management

### 🗄️ Database
- **Triggered by**: Database files, migrations, SQL files
- **Focus**: SQL injection prevention, parameterized queries
- **Documentation**: OWASP SQL Injection Prevention

### 🔒 Encryption
- **Triggered by**: Files with `crypto`, `encrypt`, `hash` in name
- **Focus**: Use established libraries, strong key lengths
- **Documentation**: OWASP Cryptographic Storage

### 🌐 API Endpoints
- **Triggered by**: API files, routes, endpoints
- **Focus**: Input validation, rate limiting, authentication
- **Documentation**: OWASP API Security

## What If I Disagree?

The advisory system is not perfect. If you believe the guidance doesn't apply:

1. **Explain in comments**: Let maintainers know why the advisory doesn't apply
2. **Provide context**: Explain your security approach
3. **Ask questions**: Maintainers can provide additional guidance
4. **Provide feedback**: Help us improve the system

Remember: Maintainers have the final say, not the advisory system.

## Testing Your Changes Locally

Before opening a PR, you can test what advisory you'll receive:

```bash
# Clone the repo
git clone https://github.com/OWASP-BLT/BLT-Preflight.git
cd BLT-Preflight

# Get advisory for your changes
python3 src/blt_preflight.py advise \
  --files "$(git diff --name-only origin/main...HEAD | tr '\n' ',')" \
  --labels "security,api"
```

## Security Best Practices

While contributing, keep these security principles in mind:

### 1. Never Commit Secrets
- Use environment variables
- Add `.env` to `.gitignore`
- Use secrets managers in production

### 2. Validate All Input
- Never trust user input
- Use allowlists, not denylists
- Validate on the server side

### 3. Use Strong Cryptography
- Use well-tested libraries
- Don't create custom encryption
- Use strong key lengths (AES-256, RSA-2048+)

### 4. Implement Proper Authentication
- Use established authentication methods
- Hash passwords with bcrypt or Argon2
- Implement rate limiting

### 5. Follow OWASP Guidelines
- Review [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- Use [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- Consider security from the start

## Getting Help

### Questions About Security
- Ask in PR comments
- Check [SECURITY_GUIDANCE.md](docs/SECURITY_GUIDANCE.md)
- Review [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)

### Questions About the Advisory System
- Open an issue with the `question` label
- Check [CONFIGURATION.md](docs/CONFIGURATION.md)
- Ask maintainers

### Reporting Security Issues
- **Never** open a public issue for security vulnerabilities
- Email: security@owasp.org
- Follow responsible disclosure practices

## Code of Conduct

- Be respectful and constructive
- Assume good intentions
- Focus on improving security together
- Help others learn

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Security Guidance](docs/SECURITY_GUIDANCE.md)
- [Configuration Guide](docs/CONFIGURATION.md)

## Thank You!

Your contributions help make BLT more secure. The advisory system is here to help you succeed. If you have suggestions for improving it, please let us know!

---

*Remember: Security is a journey, not a destination. Every contribution is an opportunity to learn and improve.*
