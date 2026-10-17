# Contributing to BLT-MCP

Thank you for your interest in contributing to the BLT-MCP project. This repository contains the Python-based Model Context Protocol server. The Rust terminal client is maintained separately in [BLT-CLI](https://git.owaspblt.org/BLT/BLT-CLI).

This guide will help you get started with your first contribution.

## Development Environment Setup

1. **Fork and Clone**: Fork the repository on GitHub and clone it to your local machine.

### Python Server (`blt_mcp`)
2. **Python Version**: Ensure you have Python 3.12.x installed.
3. **Environment**: We recommend using [uv](https://github.com/astral-sh/uv) for dependency management.
   ```bash
   uv venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   uv pip install -e ".[dev]"
   ```
4. **Environment Variables**: Create a `.env` file from the example.
   ```bash
   cp .env.example .env
   ```

### Pre-Commit Hooks Setup

We use `pre-commit` to automatically run formatters and linters before each commit.

To set it up:
1. Ensure your virtual environment is active, then install `pre-commit`:
   ```bash
   pip install pre-commit
   # Or using uv:
   uv pip install pre-commit
   ```
2. Install the Git hooks:
   ```bash
   pre-commit install
   ```
3. (Optional) Run the hooks manually on all files:
   ```bash
   pre-commit run --all-files
   ```

## Development Workflow

### Python Coding Standards (`blt_mcp`)
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use type hints wherever possible.
- **MCP Components**:
  - Define new tools using the `@server.tool()` decorators.
  - Define new resources using the `@server.resource()` decorators.
  - Define new prompts using the `@server.prompt()` decorators.

## Testing

### Deterministic MCP Testing (`mcp-vcr`)
We use `mcp-vcr` to record and playback JSON-RPC sessions, allowing for deterministic tests without hitting the live BLT API.
- Recorded sessions meant for tests should be stored in the `snapshots/` directory.
- Temporary scratchpad recordings should be placed in `sessions/` (which is `.gitignore`d).
- **Updating Golden Snapshots**: If you deliberately change a prompt template, upgrade an AI model (e.g. from Llama 3 to Llama 3.1), or modify a tool's output structure, the snapshot verification will fail. You must update the snapshot manually by running the recording command:
  ```bash
  mcp-vcr record --name <snapshot_name> -- uv run -m blt_mcp.server
  ```
  For example, to re-record the triage vulnerability test session:
  ```bash
  mcp-vcr record --name test_triage_vulnerability -- uv run -m blt_mcp.server
  ```
  Once the session completes, verify the changes and commit the updated `.yaml` file inside the `snapshots/` directory.

Before submitting a PR for the Python server, ensure all Pytest tests pass:
```bash
pytest
```

## Pull Request Process

1. Create a new branch for your feature or bugfix: `git checkout -b feature/your-feature-name`.
2. Make your changes and commit them with descriptive messages.
3. Push your branch to your fork.
4. Open a Pull Request against the `main` branch of the original repository.
5. Provide a clear description of what your PR does and link any relevant issues.

## Security Considerations

- **Vulnerabilities**: If you find a security vulnerability, please do not report it via a public issue. Instead, follow the project's security policy.
- **API Keys**: Never commit your `.env` file, `credentials.json`, or any API keys to the repository.

## Community

Join the OWASP BLT community:
- Website: [https://owasp.org/www-project-bug-logging-tool/](https://owasp.org/www-project-bug-logging-tool/)
- GitHub: [https://git.owaspblt.org/BLT](https://git.owaspblt.org/BLT)
