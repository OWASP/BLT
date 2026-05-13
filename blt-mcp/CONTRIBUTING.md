# Contributing to BLT-MCP

Thank you for your interest in contributing to the BLT-MCP project! This guide will help you get started with your first contribution.

## Development Environment Setup

1. **Fork and Clone**: Fork the repository on GitHub and clone it to your local machine.
2. **Python Version**: Ensure you have Python 3.10 or higher installed.
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

## Development Workflow

### Coding Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use type hints wherever possible.
- Write descriptive docstrings for functions and classes.

### Implementing Features

The server is built using the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
- **Tools**: Define new tools using the `@server.call_tool()` decorator or the `Tool` registry.
- **Resources**: Define new resources using the `@server.read_resource()` decorator.
- **Prompts**: Define new prompts using the `@server.list_prompts()` and `@server.get_prompt()` decorators.

### Testing

Before submitting a pull request, ensure all tests pass:
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

- **Vulnerabilities**: If you find a security vulnerability, please do not report it via a public issue. Instead, follow the project's security policy or contact the maintainers directly.
- **API Keys**: Never commit your `.env` file or any API keys to the repository.

## Community

Join the OWASP BLT community:
- Website: [https://owasp.org/www-project-bug-logging-tool/](https://owasp.org/www-project-bug-logging-tool/)
- GitHub: [https://github.com/OWASP-BLT](https://github.com/OWASP-BLT)
