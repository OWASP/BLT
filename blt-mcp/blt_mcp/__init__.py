"""
Package Initialization for the OWASP BLT Model Context Protocol (MCP) Server.

This module initializes the `blt_mcp` Python package, exposing the core components that implement the MCP
specification to communicate with OWASP BLT (Build Security In) API backend systems.

Features:
- Package-level entrypoint registration and namespace configuration.
- Serves as the configuration context for code checks, linters, and python execution environments.
- Integrates submodules such as `auth`, `cli`, `server`, `server_base`, `tools`, `validation`, and v2 schemas.

Directives:
- `# pyrefly: ignore [missing-import]`: Tells the pyrefly static analysis tool to ignore missing imports at initialization.
"""

# pyrefly: ignore [missing-import]
