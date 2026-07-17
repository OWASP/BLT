# BLT-MCP

An MCP (Model Context Protocol) server that provides AI agents and developers with structured access to the OWASP BLT (Bug Logging Tool) ecosystem. This server enables seamless integration with IDEs and chat interfaces to log bugs, triage issues, query data, and manage security workflows.

## Overview

BLT-MCP implements the MCP standard, giving AI agents structured access to BLT through three powerful layers:

### Resources (blt:// URIs)
Access BLT data through standardized URIs:
- `blt://issues` - All issues in the system
- `blt://issues/{id}` - Specific issue details
- `blt://repos` - Tracked repositories
- `blt://repos/{id}` - Specific repository details
- `blt://contributors` - All contributors
- `blt://contributors/{id}` - Specific contributor details
- `blt://workflows` - All workflows
- `blt://workflows/{id}` - Specific workflow details
- `blt://leaderboards` - Leaderboard rankings and statistics
- `blt://rewards` - Rewards and bacon points

### Tools
Perform actions on BLT:
- **submit_issue** - Report new bugs and vulnerabilities directly to the platform
- **award_bacon** - Award bacon points to contributors (gamification)
- **update_issue_status** - Change issue status (open, in_progress, resolved, closed, wont_fix)
- **add_comment** - Add comments to issues
- **triage_vulnerability** - Use Cloudflare Workers AI to automatically triage vulnerability severity
- **draft_vision_issue** - Process screenshots through Cloudflare AI and auto-draft GitLab issues

### Prompts
AI-guided workflows for common security tasks:
- **plan_remediation** - Create comprehensive remediation plans for security issues
- **review_contribution** - Evaluate contributions with quality assessment and bacon point recommendations

## Core Features

- **JSON-RPC 2.0** - Standard protocol for reliable communication
- **Authentication** - Secure access to BLT endpoints via API Keys
- **Cloudflare AI Integration** - Leverages Cloudflare Workers AI for image processing and vulnerability triage
- **GitLab Vision-to-Issue Pipeline** - Automatically drafts rich Markdown issues from vulnerability screenshots
- **Interactive TUI (BLT-CLI)** - A rich terminal UI featuring Leaderboards, Issue Onboarding, and bulk triage
- **Gamification Support** - Built-in support for BLT's bacon point system with pending verifications

## Installation

### Prerequisites
- Python 3.12.x
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`
- Rust/Cargo (for the BLT-CLI)

### Using uv (Recommended)

```bash
git clone https://gitlab.com/AEMphil/BLT-MCP.git
cd BLT-MCP

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
git clone https://gitlab.com/OWASP-BLT/BLT-MCP.git
cd BLT-MCP

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Configure the following variables in your `.env` file:

```env
BLT_API_BASE=https://api.owaspblt.org
BLT_API_KEY=your_api_key_here
```

### MCP Client Integration

To use this server with an MCP client (like Claude Desktop, Cursor, or Cline), add it to your MCP settings.

#### Using uv (Best Performance)

```json
{
  "mcpServers": {
    "blt": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/BLT-MCP",
        "run",
        "blt-mcp"
      ],
      "env": {
        "BLT_API_BASE": "https://api.owaspblt.org",
        "BLT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### Using Python Directly

```json
{
  "mcpServers": {
    "blt": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["-m", "blt_mcp.server"],
      "env": {
        "BLT_API_BASE": "https://api.owaspblt.org",
        "BLT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Usage & Workflows

### Running the Server Locally

The server runs using stdio transport for MCP communication:

```bash
# Using the installed script
blt-mcp

# Or using Python directly
python -m blt_mcp.server
```

### Bug Reporting Workflows

BLT-MCP supports two distinct workflows for reporting bugs and processing vulnerability images:

#### 1. IDE / MCP Integration (GitLab & API)
When running within an IDE, the MCP server can execute complex tasks across both BLT and external services:
- **Vision Pipeline:** Use the `draft_vision_issue` tool to process vulnerability screenshots via Cloudflare Vision AI, drafting rich Markdown vulnerability reports. If a `gitlab_project_id` is provided, the image is automatically uploaded to GitLab and linked in the Markdown.
- **Direct Submission:** Use the `submit_issue` tool to submit structured vulnerabilities (including titles, severities, bug types, and steps to reproduce) directly to the centralized `api.owaspblt.org/v2/bugs` endpoint.

#### 2. Terminal UI (BLT-CLI)
The high-performance Rust TUI offers a built-in form to interface directly with the BLT backend:
- **Launching:** Run `cargo run --manifest-path blt-cli/Cargo.toml -- --mcp-path "uv run -m blt_mcp.server"`
- **Direct API Submission:** Press `Ctrl+S` or `s` anywhere in the CLI to open the "Report a Bug" form. The CLI prompts for Title, URL, Severity, Bug Type, Description, Steps to Reproduce, and a Screenshot.
- **Local Image Upload:** Providing a local file path (e.g., `./screenshot.png`) in the `Screenshot` field automatically Base64-encodes the image and securely submits it into the JSON payload for the BLT API `/bugs` endpoint.
- **CLI AI Vision Pipeline:** Open the Command Palette (`Ctrl+P`) and type `vision /path/to/screenshot.png` to leverage the MCP server's Cloudflare Vision AI pipeline from entirely within the terminal.

### Project Structure

```
BLT-MCP/
├── blt_mcp/
│   ├── __init__.py
│   └── server.py         # Main server implementation
├── blt-cli/              # Rust Terminal UI application
├── tests/                # Test suite
├── pyproject.toml        # Project metadata and dependencies
├── .env.example          # Example environment configuration
```

## Security Considerations

- **API Keys**: Never commit API keys to version control. Always use environment variables.
- **Access Control**: Ensure proper authentication is configured for production use.
- **Rate Limiting**: Be mindful of API rate limits when making requests to the BLT ecosystem.
- **Input Validation**: The server validates all inputs before sending them to the BLT API.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

See `CONTRIBUTING.md` for more details.

## License

GNU AGPL v3 - see the `LICENSE` file for details.

## Support

For issues, questions, or contributions, please visit:
- GitLab: [https://gitlab.com/AEMphil/BLT-MCP](https://gitlab.com/AEMphil/BLT-MCP)
- OWASP BLT: [https://owasp.org/www-project-bug-logging-tool/](https://owasp.org/www-project-bug-logging-tool/)
