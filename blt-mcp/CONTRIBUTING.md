# Contributing to BLT-MCP & BLT-CLI

Thank you for your interest in contributing to the BLT-MCP project! This repository contains two major components:
1. **`blt_mcp`**: The Python-based Model Context Protocol (MCP) Server.
2. **`blt-cli`**: The high-performance Rust-based Terminal UI (TUI).

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

### Rust CLI (`blt-cli`)
5. **Rust Version**: Ensure you have the latest stable Rust toolchain installed via [rustup](https://rustup.rs/).
6. **Build**:
   ```bash
   cd blt-cli
   cargo build
   ```

## Development Workflow

### Python Coding Standards (`blt_mcp`)
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use type hints wherever possible.
- **MCP Components**:
  - Define new tools using the `@server.tool()` decorators.
  - Define new resources using the `@server.resource()` decorators.
  - Define new prompts using the `@server.prompt()` decorators.

### Rust Coding Standards (`blt-cli`)
- Format code using `cargo fmt`.
- Ensure no warnings are produced by `cargo clippy`.
- Keep TUI layout logic in `src/ui.rs` and event handling in `src/tui.rs`.

## Testing

### Deterministic MCP Testing (`mcp-vcr`)
We use `mcp-vcr` to record and playback JSON-RPC sessions, allowing for deterministic tests without hitting the live BLT API.
- Recorded sessions meant for tests should be stored in the `snapshots/` directory.
- Temporary scratchpad recordings should be placed in `sessions/` (which is `.gitignore`d).

Before submitting a PR for the Python server, ensure all Pytest tests pass:
```bash
pytest
```

Before submitting a PR for the Rust CLI, ensure the codebase compiles cleanly:
```bash
cd blt-cli
cargo check
cargo test
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
- GitHub: [https://github.com/OWASP-BLT](https://github.com/OWASP-BLT)
