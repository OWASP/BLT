# Contributing to BLT-CVE

Thank you for your interest in contributing to the BLT-CVE vulnerability registry! This document provides guidelines for contributing to the project.

## Code of Conduct

This project follows the OWASP Code of Conduct. Please be respectful and constructive in all interactions.

## How to Contribute

### Submitting a Vulnerability Entry

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/BLT-CVE.git
   cd BLT-CVE
   ```

2. **Create a branch**
   ```bash
   git checkout -b add/BLT-YYYY-NNNN
   ```

3. **Create a new CVE entry** following the schema in `/schema/blt-cve-schema.json`.
   Place the file at `cves/YYYY/BLT-YYYY-DRAFT.json` (maintainers will assign the final ID).

4. **Validate your entry locally**
   ```bash
   pip install jsonschema
   python scripts/validate_cves.py
   ```

5. **Commit and open a Pull Request**
   ```bash
   git add .
   git commit -m "add: BLT-YYYY-DRAFT – short vulnerability summary"
   git push origin add/BLT-YYYY-NNNN
   ```

### Reporting Bugs / Suggesting Enhancements

1. Check if the issue already exists in [GitHub Issues](https://github.com/OWASP-BLT/BLT-CVE/issues)
2. If not, create a new issue with a clear title and description.

## Documentation

Files to update when relevant:
- `README.md` – overview and usage
- `docs/PROTOCOL.md` – data format & ID rules
- `docs/GOVERNANCE.md` – maintainer & disclosure policy

## Commit Messages

```
add: BLT-2026-0002 – SQL injection in ExampleApp 1.2

fix: correct CVSS vector for BLT-2026-0001
docs: update FEDERATION.md with new mirror endpoint
```

Prefixes: `add:`, `fix:`, `docs:`, `chore:`

## Review Process

1. Automated schema validation runs on all PRs targeting `cves/**`.
2. Code review by maintainers.
3. Maintainer assigns the final sequential ID, renames the file, and merges.
4. The index is regenerated automatically after merge.

Typical timeline: 3-7 days for review.

## Getting Help

- **Questions**: Create a GitHub issue with the "question" label.
- **Discussions**: Use GitHub Discussions.
- **OWASP BLT**: Join the OWASP BLT community.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

Thank you for contributing to BLT-CVE! 🎉
