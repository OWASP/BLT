# 🛡️ BLT-Preflight

> A pre-contribution advisory system that helps contributors understand security expectations before opening pull requests.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![OWASP Project](https://img.shields.io/badge/OWASP-Project-orange.svg)](https://owasp.org/www-project-bug-logging-tool/)

## Overview

BLT-Preflight provides security intent and risk guidance before contributors submit code, helping to:

- ✅ Prevent common security mistakes
- 📚 Educate contributors on security best practices
- ⚡ Reduce maintainer workload by catching issues early
- 🔗 Provide plain-language guidance with documentation links
- 📊 Learn and improve over time through feedback

**Important**: This is a purely advisory system, not enforcement. It aims to help contributors understand security considerations without blocking contributions.

## Features

### 🎯 Context-Aware Guidance

The system evaluates:
- **Issue Labels**: Detects security-related labels and provides relevant guidance
- **File Patterns**: Identifies sensitive files (auth, database, encryption, etc.)
- **Repository Metadata**: Considers project context
- **Past Patterns**: Learns from historical contributions

### 📖 Plain-Language Advice

Every advisory includes:
- Clear, actionable security recommendations
- Links to OWASP and security documentation
- Severity levels (Info, Warning, Critical)
- Context-specific best practices

### 💬 Optional Intent Capture

Contributors can share their intent, helping the system provide more targeted guidance:
```
Intent: Adding OAuth2 support for third-party authentication
```

### 📊 Maintainer Dashboard

Track advisory effectiveness:
- Feedback statistics and patterns
- Advisory helpfulness rates
- Contributor intent analysis
- Recommendations for improvement

### 🔄 Learning Loop

The system improves over time by:
- Collecting feedback on advisory helpfulness
- Analyzing contributor intent patterns
- Refining guidance based on effectiveness
- Adapting to project-specific patterns

## Quick Start

### As a Contributor

#### Local pre-commit check

Install the `pf` command once and run it before every commit:

```bash
# Install
git clone https://github.com/OWASP-BLT/BLT-Preflight.git
cd BLT-Preflight
./install.sh          # sets up the 'pf' command

# Run before committing (checks your staged files)
pf
```

When you open a PR, BLT-Preflight also runs automatically via GitHub Actions:
1. Analyzes your changes and labels
2. Generates relevant security guidance
3. Posts an advisory comment on your PR
4. Provides recommendations and documentation links

You can optionally:
- Include your intent in the PR description
- Provide feedback on advisory helpfulness

### As a Maintainer

1. **Enable the GitHub Action** (already configured in `.github/workflows/advisory.yml`)
2. **Review the configuration** in `config/security_patterns.json`
3. **Check the dashboard** periodically:
   ```bash
   pf dashboard --output docs/MAINTAINER_DASHBOARD.md
   ```

## Installation

### `pf` Command (Recommended for local use)

Use the included installer to set up the `pf` command:

```bash
git clone https://github.com/OWASP-BLT/BLT-Preflight.git
cd BLT-Preflight
./install.sh
```

Options:

```bash
./install.sh            # install for the current user (default)
./install.sh --system   # install system-wide (requires sudo)
./install.sh --uninstall
```

Or install directly with pip:

```bash
pip install -e .
```

### GitHub Action (Recommended for CI)

The advisory system runs automatically via GitHub Actions. No installation required!

Just ensure the workflow file exists: `.github/workflows/advisory.yml`

## Usage

### `pf` CLI Commands

#### Pre-commit check (default)

```bash
# Check all staged files before committing
pf

# Check specific files
pf check --files "src/auth.py,src/login.py"
```

`pf` exits with code **1** when critical security advisories are found (matching
git hook / CI pipeline conventions) and **0** otherwise.

#### Use as a git pre-commit hook

```bash
echo '#!/bin/sh\npf' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

#### Generate Advisory

```bash
pf advise \
  --labels "security,authentication" \
  --files "src/auth.py,src/login.py" \
  --repo "OWASP-BLT/BLT" \
  --output advisory.md
```

#### Provide Feedback

```bash
pf feedback \
  --pattern "Security Advisory: Authentication" \
  --helpful yes \
  --comments "Very clear and actionable!"
```

#### Capture Intent

```bash
pf intent \
  --intent "Adding two-factor authentication support" \
  --labels "security,authentication" \
  --files "src/auth/mfa.py"
```

#### Generate Dashboard

```bash
pf dashboard --output docs/MAINTAINER_DASHBOARD.md
```

### GitHub Action

The action runs automatically on:
- Pull requests (opened, synchronized, reopened)
- Issues (opened, labeled)

Configure triggers in `.github/workflows/advisory.yml`

## Configuration

### Security Patterns

Edit `config/security_patterns.json` to customize:

```json
{
  "file_patterns": {
    "authentication": {
      "patterns": ["**/auth/**", "**/login/**"],
      "severity": "critical",
      "guidance": "Authentication changes require careful review"
    }
  },
  "label_patterns": {
    "security": {
      "severity": "critical",
      "guidance": "Security-related changes need thorough review"
    }
  }
}
```

See [Configuration Guide](docs/CONFIGURATION.md) for detailed instructions.

## Documentation

- **[Security Guidance](docs/SECURITY_GUIDANCE.md)**: Comprehensive security best practices
- **[Configuration Guide](docs/CONFIGURATION.md)**: How to customize the advisory system
- **[Maintainer Dashboard](docs/MAINTAINER_DASHBOARD.md)**: View advisory statistics (generated)

## Architecture

```
BLT-Preflight/
├── src/
│   ├── advisory_engine/
│   │   ├── __init__.py
│   │   ├── core.py              # Core advisory engine
│   │   ├── github_integration.py # GitHub API integration
│   │   └── dashboard.py          # Maintainer dashboard
│   └── blt_preflight.py          # CLI interface
├── config/
│   ├── security_patterns.json    # Pattern definitions
│   └── learning_data.json        # Learning loop data (generated)
├── docs/
│   ├── SECURITY_GUIDANCE.md      # Security best practices
│   ├── CONFIGURATION.md          # Configuration guide
│   └── MAINTAINER_DASHBOARD.md   # Statistics (generated)
└── .github/
    └── workflows/
        └── advisory.yml          # GitHub Action workflow
```

## Examples

### Example Advisory

```markdown
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
- https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication
```

### Example Dashboard Metrics

- **Total Advisory Feedback**: 42
- **Helpful Rate**: 85.7%
- **Total Intents Captured**: 28
- **Feedback (Last 7 Days)**: 8

## Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

BLT-Preflight will automatically provide security guidance on your PR!

## Security

For security concerns or to report vulnerabilities:
- Email: security@owasp.org
- See our security policy

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OWASP Bug Logging Tool (BLT) Project
- OWASP Security Cheat Sheet Series
- All contributors and security researchers

## Support

- **Questions**: Open an issue with the `question` label
- **Bug Reports**: Open an issue with the `bug` label
- **Feature Requests**: Open an issue with the `enhancement` label

---

**Part of the [OWASP Bug Logging Tool (BLT)](https://owasp.org/www-project-bug-logging-tool/) project**
