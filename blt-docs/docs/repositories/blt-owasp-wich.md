# BLT-OWASP-Wich

**OWASP Project Compliance Checker**

- **Repository**: [OWASP-BLT/BLT-OWASP-Wich](https://github.com/OWASP-BLT/BLT-OWASP-Wich)
- **Live Web App**: [owasp-blt.github.io/OWASP-Wich](https://owasp-blt.github.io/OWASP-Wich/)
- **Language**: Python, JavaScript
- **License**: Apache 2.0

---

## Overview

OWASP-Wich is a comprehensive tool to check GitHub repositories and projects against OWASP standards and best practices. It evaluates **100 compliance points across 10 key categories** to ensure your project meets quality, security, and governance standards.

The web-based compliance checker runs entirely in your browser using JavaScript — simply paste a GitHub repository URL and get instant compliance results.

## Key Features

- ✅ **100-Point Compliance Checklist** — Comprehensive evaluation across all aspects of project quality
- 🔒 **Security-Focused** — Checks for OWASP Top 10, ASVS, and security best practices
- 📊 **Detailed Reporting** — Category-wise breakdown with specific recommendations
- 🔄 **GitHub Integration** — Direct repository analysis via GitHub API
- 🌐 **Browser-Based** — No installation required, works directly in your browser
- 💻 **CLI Support** — Also available as Python CLI tool for automation
- 📈 **Scoring System** — Clear percentage-based scoring for quick assessment

---

## Compliance Categories

The tool checks 100 points across these 10 categories:

| Category | Points | What It Checks |
|----------|--------|----------------|
| **General Compliance & Governance** | 10 | Project structure, licensing, governance |
| **Documentation & Usability** | 10 | README, guides, user documentation |
| **Code Quality & Best Practices** | 10 | Code standards and maintainability |
| **Security & OWASP Compliance** | 15 | Security practices and OWASP standards |
| **CI/CD & DevSecOps** | 10 | Automation and security integration |
| **Testing & Validation** | 10 | Test coverage and quality |
| **Performance & Scalability** | 10 | Performance optimization |
| **Logging & Monitoring** | 10 | Observability and logging practices |
| **Community & Support** | 10 | Community engagement and support |
| **Legal & Compliance** | 5 | Licensing and legal compliance |

---

## Understanding the Scores

| Score Range | Status |
|-------------|--------|
| **80–100%** | ✅ Excellent Compliance — Project follows OWASP standards comprehensively |
| **60–79%** | Good Compliance — Minor improvements recommended |
| **40–59%** | Needs Improvement — Several areas require attention |
| **0–39%** | Significant Improvements Needed — Major compliance gaps |

---

## Usage

### Web Application (Recommended)

Visit **[https://owasp-blt.github.io/OWASP-Wich/](https://owasp-blt.github.io/OWASP-Wich/)** and:

1. Enter a GitHub repository URL (e.g., `https://github.com/OWASP/owasp-mastg`)
2. (Optional) Provide a GitHub personal access token for higher API rate limits
3. Click **"Check Compliance"**
4. View your detailed compliance report with scores and recommendations

### Python CLI Tool

For automation and CI/CD integration:

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-OWASP-Wich.git
cd BLT-OWASP-Wich

# Install dependencies
pip install -r requirements.txt

# Set GitHub token for higher API rate limits (optional)
export GITHUB_TOKEN="your_github_token_here"
```

**CLI Usage:**

```bash
# Basic check
python compliance_checker.py https://github.com/OWASP/owasp-mastg

# Check with GitHub token
python compliance_checker.py https://github.com/OWASP/BLT --token YOUR_GITHUB_TOKEN

# Output as JSON
python compliance_checker.py https://github.com/OWASP/BLT --json
```

### As a Python Module

```python
from compliance_checker import OWASPComplianceChecker

checker = OWASPComplianceChecker(github_token="your_token")
results = checker.check_compliance("https://github.com/OWASP/owasp-mastg")

print(f"Score: {results['score']}/{results['max_score']}")
print(f"Percentage: {results['percentage']}%")

for category, data in results['categories'].items():
    print(f"{category}: {data['score']}/{data['max_score']}")
```

---

## Detailed Compliance Checks

### 1. General Compliance & Governance (10 points)

- Clearly defined project goal and scope
- Open-source license (MIT, Apache 2.0, GPL, etc.)
- README file provides project overview
- Under OWASP organization
- Clear contribution guidelines (CONTRIBUTING.md)
- Issue tracker is actively monitored
- Maintainers respond to pull requests
- Code of Conduct (CODE_OF_CONDUCT.md)
- Project roadmap or milestones documented
- Well-governed with active maintainers

### 2. Documentation & Usability (10 points)

- Well-structured README with installation guide
- Clear usage examples
- Wiki or detailed `docs/` directory
- API documentation (Swagger/OpenAPI)
- Proper inline code comments
- Scripts and configuration files documented
- FAQ section or troubleshooting guide
- Well-defined error messages
- Clear versioning strategy (SemVer)
- CHANGELOG maintained

### 3. Code Quality & Best Practices (10 points)

- Follows industry-standard style guides
- Uses linters (ESLint, Pylint, etc.)
- Code is modular and maintainable
- Adheres to DRY principle
- Secure coding practices
- No hardcoded credentials or secrets
- Uses parameterized queries
- Strong cryptographic algorithms
- Input validation and sanitization
- Output encoding for XSS prevention

### 4. Security & OWASP Compliance (15 points)

- No known security vulnerabilities
- OWASP Dependency-Check integration
- Secure headers (CSP, HSTS, X-Frame-Options)
- Input validation enforced
- RBAC implementation
- Secure authentication mechanisms
- Secrets stored securely
- HTTPS for all communication
- Adheres to OWASP ASVS
- Secure cookie attributes
- No unnecessary ports exposed
- Security event logging
- Least privilege principle
- No unsafe dependencies
- Complies with OWASP Top 10

### 5. CI/CD & DevSecOps (10 points)

- Automated unit tests
- Continuous Integration configured
- Security scanning in CI/CD pipeline
- Automated dependency scanning
- Code coverage reports
- Container security scanning
- IaC security checks
- Secure secrets management
- Environment-specific configurations
- Rollback mechanisms

### 6–10. Additional Categories

Each additional category (Testing, Performance, Logging, Community, Legal) similarly checks 5–10 specific best practices against your repository.

---

## API Rate Limits

The GitHub API has rate limits:

| Authentication | Limit |
|----------------|-------|
| Without token | 60 requests/hour |
| With token | 5,000 requests/hour |

```bash
# Create a token at: https://github.com/settings/tokens
export GITHUB_TOKEN="your_token_here"
```

---

## References

- [OWASP Project Handbook](https://owasp.org/www-committee-project/)
- [OWASP Application Security Verification Standard (ASVS)](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)

---

## Contributing

See [CONTRIBUTING.md](https://github.com/OWASP-BLT/BLT-OWASP-Wich/blob/main/CONTRIBUTING.md) for details on submitting issues and pull requests.
