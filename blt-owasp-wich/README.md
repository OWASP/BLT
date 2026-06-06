# OWASP-Wich: OWASP Project Compliance Checker

A comprehensive tool to check GitHub repositories and projects against OWASP standards and best practices. This tool evaluates 100 compliance points across 10 key categories to ensure your project meets quality, security, and governance standards.

## 🌐 Live Web Application

**Try it now:** [https://owasp-blt.github.io/OWASP-Wich/](https://owasp-blt.github.io/OWASP-Wich/)

The web-based compliance checker runs entirely in your browser using JavaScript. Simply paste a GitHub repository URL and get instant compliance results!

![OWASP-Wich Interface](https://github.com/user-attachments/assets/b5fb2d43-0d0c-4bc2-9edf-d4e9e3c58a36)

### Features

- ✅ **100-Point Compliance Checklist** - Comprehensive evaluation across all aspects of project quality
- 🔒 **Security-Focused** - Checks for OWASP Top 10, ASVS, and security best practices
- 📊 **Detailed Reporting** - Category-wise breakdown with specific recommendations
- 🔄 **GitHub Integration** - Direct repository analysis via GitHub API
- 🌐 **Browser-Based** - No installation required, works directly in your browser
- 💻 **CLI Support** - Also available as Python CLI tool for automation
- 📈 **Scoring System** - Clear percentage-based scoring for quick assessment
- 🎨 **OWASP BLT Theme** - Follows official OWASP BLT branding and design

## Compliance Categories

The tool checks 100 points across these categories:

1. **General Compliance & Governance** (10 points) - Project structure, licensing, and governance
2. **Documentation & Usability** (10 points) - README, guides, and user documentation
3. **Code Quality & Best Practices** (10 points) - Code standards and maintainability
4. **Security & OWASP Compliance** (15 points) - Security practices and OWASP standards
5. **CI/CD & DevSecOps** (10 points) - Automation and security integration
6. **Testing & Validation** (10 points) - Test coverage and quality
7. **Performance & Scalability** (10 points) - Performance optimization
8. **Logging & Monitoring** (10 points) - Observability and logging practices
9. **Community & Support** (10 points) - Community engagement and support
10. **Legal & Compliance** (5 points) - Licensing and legal compliance

## Usage

### Web Application (Recommended)

Visit **[https://owasp-blt.github.io/OWASP-Wich/](https://owasp-blt.github.io/OWASP-Wich/)** and:

1. Enter a GitHub repository URL (e.g., `https://github.com/OWASP/owasp-mastg`)
2. (Optional) Provide a GitHub personal access token for higher API rate limits
3. Click "Check Compliance"
4. View your detailed compliance report with scores and recommendations

**Benefits:**
- No installation required
- Works in any modern browser
- Real-time results
- Interactive category exploration
- Visual scoring with color-coded status

### Cloudflare Deployment

The browser application is served from `public/`.

Cloudflare should use `wrangler.toml`, which points both `pages_build_output_dir` and `[assets].directory` at `./public`.

### Python CLI Tool

For automation and integration into CI/CD pipelines, you can also use the Python command-line tool.

#### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

#### Setup

1. Clone the repository:
```bash
git clone https://github.com/OWASP-BLT/OWASP-Wich.git
cd OWASP-Wich
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Set up GitHub token for higher API rate limits:
```bash
export GITHUB_TOKEN="your_github_token_here"
```

#### CLI Usage

Basic usage:
```bash
python compliance_checker.py <repository-url>
```

Examples:
```bash
# Check an OWASP project
python compliance_checker.py https://github.com/OWASP/owasp-mastg

# Check with GitHub token
python compliance_checker.py https://github.com/OWASP/BLT --token YOUR_GITHUB_TOKEN

# Output as JSON
python compliance_checker.py https://github.com/OWASP/BLT --json
```

#### As a Python Module

```python
from compliance_checker import OWASPComplianceChecker

# Initialize checker
checker = OWASPComplianceChecker(github_token="your_token")

# Run compliance check
results = checker.check_compliance("https://github.com/OWASP/owasp-mastg")

# Access results
print(f"Score: {results['score']}/{results['max_score']}")
print(f"Percentage: {results['percentage']}%")

# Check specific categories
for category, data in results['categories'].items():
    print(f"{category}: {data['score']}/{data['max_score']}")
```

## Detailed Compliance Checks

### 1. General Compliance & Governance (10 points)
- ✓ Clearly defined project goal and scope
- ✓ Open-source license (MIT, Apache 2.0, GPL, etc.)
- ✓ README file provides project overview
- ✓ Under OWASP organization
- ✓ Clear contribution guidelines (CONTRIBUTING.md)
- ✓ Issue tracker is actively monitored
- ✓ Maintainers respond to pull requests
- ✓ Code of Conduct (CODE_OF_CONDUCT.md)
- ✓ Project roadmap or milestones documented
- ✓ Well-governed with active maintainers

### 2. Documentation & Usability (10 points)
- ✓ Well-structured README with installation guide
- ✓ Clear usage examples
- ✓ Wiki or detailed docs/ directory
- ✓ API documentation (Swagger/OpenAPI)
- ✓ Proper inline code comments
- ✓ Scripts and configuration files documented
- ✓ FAQ section or troubleshooting guide
- ✓ Well-defined error messages
- ✓ Clear versioning strategy (SemVer)
- ✓ CHANGELOG maintained

### 3. Code Quality & Best Practices (10 points)
- ✓ Follows industry-standard style guides
- ✓ Uses linters (ESLint, Pylint, etc.)
- ✓ Code is modular and maintainable
- ✓ Adheres to DRY principle
- ✓ Secure coding practices
- ✓ No hardcoded credentials or secrets
- ✓ Uses parameterized queries
- ✓ Strong cryptographic algorithms
- ✓ Input validation and sanitization
- ✓ Output encoding for XSS prevention

### 4. Security & OWASP Compliance (15 points)
- ✓ No known security vulnerabilities
- ✓ OWASP Dependency-Check integration
- ✓ Secure headers (CSP, HSTS, X-Frame-Options)
- ✓ Input validation enforced
- ✓ RBAC implementation
- ✓ Secure authentication mechanisms
- ✓ Secrets stored securely
- ✓ HTTPS for all communication
- ✓ Adheres to OWASP ASVS
- ✓ Secure cookie attributes
- ✓ No unnecessary ports exposed
- ✓ Security event logging
- ✓ Least privilege principle
- ✓ No unsafe dependencies
- ✓ Complies with OWASP Top 10

### 5. CI/CD & DevSecOps (10 points)
- ✓ Automated unit tests
- ✓ Continuous Integration configured
- ✓ Security scanning in CI/CD pipeline
- ✓ Automated dependency scanning
- ✓ Code coverage reports
- ✓ Container security scanning
- ✓ IaC security checks
- ✓ Secure secrets management
- ✓ Environment-specific configurations
- ✓ Rollback mechanisms

### 6. Testing & Validation (10 points)
- ✓ Test cases cover edge cases
- ✓ Unit, integration, and E2E tests
- ✓ Mocks and stubs for external services
- ✓ 80%+ test coverage
- ✓ Tests validate input sanitization
- ✓ Automated fuzz testing
- ✓ Graceful failure with logging
- ✓ No sensitive data in logs
- ✓ Dependency injection
- ✓ Regression tests

### 7. Performance & Scalability (10 points)
- ✓ Code optimized for performance
- ✓ Asynchronous processing
- ✓ Caching strategies
- ✓ Optimized database queries
- ✓ Rate limiting
- ✓ No memory leaks
- ✓ Load testing
- ✓ Horizontal scaling support
- ✓ Lazy loading
- ✓ Pagination for large datasets

### 8. Logging & Monitoring (10 points)
- ✓ Logging implemented
- ✓ Configurable log levels
- ✓ No sensitive data in logs
- ✓ Monitoring tool integration
- ✓ Structured logging
- ✓ Audit logs for security actions
- ✓ Alerts configured
- ✓ Log rotation and archival
- ✓ Incident response playbook
- ✓ Logging configuration separate from code

### 9. Community & Support (10 points)
- ✓ Active maintainer engagement
- ✓ Security vulnerability reporting process
- ✓ Security policy file (SECURITY.md)
- ✓ Community guidelines
- ✓ Responsive to security issues
- ✓ Regular project updates (yearly minimum)
- ✓ Multiple support channels
- ✓ Clear escalation path
- ✓ PR reviews before merging
- ✓ Good issue tracking hygiene

### 10. Legal & Compliance (5 points)
- ✓ GDPR/CCPA compliance
- ✓ Third-party dependencies properly licensed
- ✓ No proprietary or restricted code
- ✓ Users informed of data collection
- ✓ Responsible disclosure policy

## Understanding the Scores

- **80-100%**: Excellent Compliance ✓ - Project follows OWASP standards comprehensively
- **60-79%**: Good Compliance - Minor improvements recommended
- **40-59%**: Needs Improvement - Several areas require attention
- **0-39%**: Significant Improvements Needed - Major compliance gaps

## API Rate Limits

The GitHub API has rate limits:
- **Without authentication**: 60 requests per hour
- **With authentication**: 5,000 requests per hour

We recommend using a GitHub token for better performance:
```bash
# Create a token at: https://github.com/settings/tokens
export GITHUB_TOKEN="your_token_here"
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- How to submit issues
- How to submit pull requests
- Code style guidelines
- Testing requirements

## References

This tool is based on:
- [OWASP Project Handbook](https://owasp.org/www-committee-project/)
- [OWASP Application Security Verification Standard (ASVS)](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 [Report Issues](https://github.com/OWASP-BLT/OWASP-Wich/issues)
- 💬 [Discussions](https://github.com/OWASP-BLT/OWASP-Wich/discussions)
- 📧 Contact: [OWASP BLT Team](https://blt.owasp.org)

## Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) - Bug Logging Tool
- [OWASP Projects](https://owasp.org/projects/) - All OWASP Projects

---

Made with ❤️ by the OWASP BLT Team
