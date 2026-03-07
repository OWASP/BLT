# GitHub Copilot Instructions

## Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to enforce code quality standards. All contributors must install and run the pre-commit hooks before pushing code.

### Setup

Install and activate the pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

### Hooks Configured

The following hooks run automatically on every commit (see `.pre-commit-config.yaml`):

- **check-ast** – Validates Python files parse as valid AST
- **check-builtin-literals** – Enforces use of literal syntax for built-in types
- **check-yaml** – Validates YAML files
- **fix-encoding-pragma** – Removes `# -*- coding: utf-8 -*-` pragmas
- **mixed-line-ending** – Normalizes line endings to LF
- **isort** – Sorts Python imports automatically
- **ruff** – Lints Python code and applies auto-fixes
- **ruff-format** – Formats Python code

### Running Manually

To run all hooks against all files at any time:

```bash
pre-commit run --all-files
```

To run a specific hook:

```bash
pre-commit run <hook-id>
# e.g.
pre-commit run ruff
```

### Skipping Hooks (not recommended)

In exceptional circumstances you can bypass the hooks with:

```bash
git commit --no-verify -m "your message"
```

> **Note:** Bypassing hooks is strongly discouraged. CI will run the same checks and will fail if the hooks are not satisfied.
