# BLT-MCP

An MCP (Model Context Protocol) server that provides AI agents and developers with structured access to the BLT (Bug Logging Tool) ecosystem. This server enables seamless integration with IDEs and chat interfaces to log bugs, triage issues, query data, and manage security workflows.

## Overview

BLT-MCP implements the MCP standard, giving AI agents structured access to BLT through three powerful layers:

### 🔗 Resources (blt:// URIs)
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

### 🛠️ Tools
Perform actions on BLT:
- **submit_issue** - Report new bugs and vulnerabilities
- **award_bacon** - Award bacon points to contributors (gamification)
- **update_issue_status** - Change issue status (open, in_progress, resolved, closed, wont_fix)
- **add_comment** - Add comments to issues

### 💡 Prompts
AI-guided workflows for common security tasks:
- **triage_vulnerability** - Guide AI through vulnerability triage and severity assessment
- **plan_remediation** - Create comprehensive remediation plans for security issues
- **review_contribution** - Evaluate contributions with quality assessment and bacon point recommendations

## Features

- ✅ **JSON-RPC 2.0** - Standard protocol for reliable communication
- ✅ **OAuth/API Key Authentication** - Secure access to BLT endpoints
- ✅ **Unified Interface** - Single agent-friendly interface to all BLT functionality
- ✅ **Autonomous Workflows** - Enable AI agents to work independently
- ✅ **Gamification Support** - Built-in support for BLT's bacon point system
- ✅ **Security-First** - Designed for vulnerability management and security workflows

## Installation

### Prerequisites
- Python 3.12.x
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-MCP.git
cd BLT-MCP

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-MCP.git
cd BLT-MCP

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Configure the following variables:

```env
BLT_API_BASE=https://blt.owasp.org/api
BLT_API_KEY=your_api_key_here
```

### MCP Client Configuration

To use this server with an MCP client (like Claude Desktop or Cline), add it to your MCP settings:

#### Using uv (Best for performance)

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
        "BLT_API_BASE": "https://blt.owasp.org/api",
        "BLT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### Using Python directly

```json
{
  "mcpServers": {
    "blt": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "blt_mcp.server"],
      "env": {
        "BLT_API_BASE": "https://blt.owasp.org/api",
        "BLT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Usage

### Running the Server Locally

The server runs using stdio transport for MCP communication:

```bash
# Using the installed script
blt-mcp

# Or using python directly
python -m blt_mcp.server
```

### Project Structure

```
BLT-MCP/
├── blt_mcp/
│   ├── __init__.py
│   └── server.py         # Main server implementation
├── tests/                # Test suite
├── pyproject.toml        # Project metadata and dependencies
├── .env.example          # Example environment configuration
```

## Security Considerations

- **API Keys**: Never commit API keys to version control. Use environment variables.
- **Access Control**: Ensure proper authentication is configured for production use.
- **Rate Limiting**: Be mindful of API rate limits when making requests.
- **Input Validation**: The server validates all inputs before sending to the BLT API.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

GNU AGPL v3 - see [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please visit:
- GitHub: [https://github.com/OWASP-BLT/BLT-MCP](https://github.com/OWASP-BLT/BLT-MCP)
- OWASP BLT: [https://owasp.org/www-project-bug-logging-tool/](https://owasp.org/www-project-bug-logging-tool/)
