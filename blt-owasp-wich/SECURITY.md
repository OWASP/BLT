# Security Policy

## Supported Versions

We currently support the latest version of OWASP-Wich with security updates.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in OWASP-Wich, please report it responsibly.

### How to Report

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Email the OWASP BLT team at: security@blt.owasp.org
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 7-14 days
  - High: 14-30 days
  - Medium/Low: 30-90 days

### Disclosure Policy

- We follow responsible disclosure practices
- We will acknowledge your contribution (if desired)
- We will provide credit in security advisories
- Please allow us time to fix the issue before public disclosure

## Security Best Practices

When using OWASP-Wich:

1. **GitHub Tokens**: Store your GitHub token in environment variables, never in code
2. **Rate Limits**: Be aware of GitHub API rate limits
3. **Dependencies**: Keep dependencies up to date
4. **Python Version**: Use Python 3.7 or higher
5. **Network Security**: Ensure secure network connections when scanning repositories

## Security Features

- HTTPS-only connections to GitHub API
- No storage of sensitive data
- Read-only repository access
- Input validation for URLs
- Safe HTML parsing with BeautifulSoup

## Known Limitations

- GitHub API rate limiting applies
- Some checks require manual verification
- Not a replacement for comprehensive security audits
- Limited checks for non-GitHub repositories

## Questions?

For security-related questions, contact: security@blt.owasp.org
