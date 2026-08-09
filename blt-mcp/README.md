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
- `blt://rewards` - Rewards and contributor points

### Tools
Perform actions on BLT:
- **submit_issue** - Report new bugs and vulnerabilities directly to the platform
- **add_comment** - Add comments to issues
- **triage_vulnerability** - Use Cloudflare Workers AI to automatically triage vulnerability severity
- **draft_vision_issue** - Process screenshots through Cloudflare AI and auto-draft GitLab issues

### Prompts
AI-guided workflows for common security tasks:
- **plan_remediation** - Create comprehensive remediation plans for security issues
- **review_contribution** - Evaluate contributions with quality assessment and reward recommendations

## Core Features

- **JSON-RPC 2.0** - Standard protocol for reliable communication
- **Authentication** - Secure access to BLT endpoints via API Keys
- **Cloudflare AI Integration** - Leverages Cloudflare Workers AI for image processing and vulnerability triage
- **GitLab Vision-to-Issue Pipeline** - Automatically drafts rich Markdown issues from vulnerability screenshots
- **Interactive TUI (BLT-CLI)** - A rich terminal UI featuring Leaderboards and bulk triage
- **Gamification Support** - Built-in support for BLT's point system with pending verifications

## Installation

### Prerequisites
- Python 3.12.x
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`
- Rust/Cargo (for the BLT-CLI)

### Using uv (Recommended)

```bash
git clone https://gitlab.com/owasp-blt/blt-mcp.git
cd BLT-MCP

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
git clone https://gitlab.com/owasp-blt/blt-mcp.git
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

## Local Development (Full Stack)

This section walks you through running the **complete BLT stack locally**: `blt-api` (Cloudflare Worker + D1) → `BLT-MCP` (Python MCP server) → `blt-cli` (Rust TUI).

> **Platform note:** The CLI and MCP server must be run from **WSL** (or Linux/macOS) to avoid `.venv` symlink issues on Windows.

---

### Step 1 — Set Up the Local API (`blt-api`)

Clone the `blt-api` repository alongside this one:

```bash
git clone https://gitlab.com/owasp-blt/blt-api.git
cd blt-api
npm install
```

#### 1a — Configure the D1 Database Binding

Open `wrangler.toml` and update the `[[d1_databases]]` block to point to your local database name. For example, if you created a local D1 called `team_db`:

```toml
[[d1_databases]]
binding = "team_db"
database_name = "team_db"
database_id = "<your-local-database-id>"
migrations_dir = "migrations"
migrations_table = "d1_migrations"
```

Then open `blt-api/src/libs/db.py` and make sure `team_db` is included in the binding name lookup list:

```python
# src/libs/db.py
for name in ['blt_api', 'DB', 'team_db']:   # add your binding name here
```

#### 1b — Apply Migrations

```bash
# From the blt-api directory
npx wrangler d1 migrations apply team_db --local
```

#### 1c — Seed Test Data

```bash
npx wrangler d1 execute team_db --local --file=test_data.sql
```

#### 1d — Start the Local API Server

```bash
npm run dev
# or: npx wrangler dev
```

The API will be available at `http://localhost:8787`. Verify with:

```bash
curl -H "X-BLT-API-Key: f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051" \
     http://localhost:8787/v2/bugs
```

The static public API key for local development is:
```
f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051
```

---

### Step 2 — Configure BLT-MCP

In the `BLT-MCP` directory, create/update your `.env` file to point at the local API:

```env
BLT_API_BASE=http://localhost:8787
BLT_API_KEY=f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051
```

Install dependencies (from WSL):

```bash
cd /path/to/BLT-MCP
uv sync
```

Verify the MCP server starts cleanly:

```bash
uv run blt-mcp
# Should hang on stdin waiting for JSON-RPC — that's correct. Ctrl+C to stop.
```

---

### Step 3 — Run the CLI via MCP

From WSL, inside the `BLT-MCP` root directory:

```bash
cargo run --manifest-path blt-cli/Cargo.toml -- --mcp-path "uv run blt-mcp"
```

Or from inside `blt-cli/`:

```bash
cd blt-cli
cargo run -- --mcp-path "uv run blt-mcp"
```

The CLI will:
1. Spawn `uv run blt-mcp` as a subprocess
2. Perform the MCP handshake over stdio
3. Fetch resources (`blt://issues`, `blt://repos`, etc.) from the MCP server
4. The MCP server calls `http://localhost:8787` using your `.env` key
5. The TUI renders your local seeded data

---

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `500 Database not configured` | Binding name mismatch | Add your binding to the `for name in [...]` list in `db.py` |
| `500 Database is not initialized` | Migrations not applied | Run `npx wrangler d1 migrations apply <db> --local` |
| `401 Invalid API key` | Using a `blt_live_` key not in the local DB | Use the static public key above |
| `EOF reached on subprocess stdout` | MCP server crashed on start | Run `uv run blt-mcp` standalone to see the Python traceback |
| `MCP Subprocess read timeout` | Wrong `uv` (Windows vs WSL) | Run `cargo run` from WSL, not PowerShell |
| Issues show 0 in TUI | Empty DB or parse mismatch | Check the curl response from `/v2/bugs` matches the `Issue` struct fields |

---

## Testing

BLT-MCP uses `pytest` for unit testing and `mcp-vcr` for deterministic integration testing of JSON-RPC sessions.

### Running Tests

To run the complete test suite:
```bash
uv run pytest
```

The test suite will execute the unit tests and then automatically run the `mcp-vcr` verification hook against all golden snapshots in the `snapshots/` directory.

### Deterministic & Offline Testing

To ensure testing is 100% deterministic and runs offline without making real network requests to Cloudflare or the live OWASP BLT API, a mock HTTP layer is automatically activated during `pytest` runs using the environment variable:
```env
BLT_MOCK_HTTP=true
```
This intercepts all external requests made by `httpx.AsyncClient` inside the server subprocesses and returns stubbed mock data.

### How to Use `mcp-vcr`

`mcp-vcr` records and replays the JSON-RPC communication between the MCP client and the server.

* **Golden Snapshots**: Stored in the `snapshots/` directory.
* **Recording/Updating Snapshots**:
  You can create a new `.yaml` template manually inside `snapshots/` with the client-to-server (`c2s`) messages and a meta block (specifying a unique 8-character hex `session_id` like `'00000005'`), and then run the update command to auto-generate the server-to-client (`s2c`) responses:
  ```bash
  # Unix/macOS/WSL:
  export BLT_MOCK_HTTP="true"
  # PowerShell:
  # $env:BLT_MOCK_HTTP = "true"
  uv run mcp-vcr verify snapshots/ --update -- uv run -m blt_mcp.server
  ```
  Alternatively, you can record a live session interactively:
  ```bash
  uv run mcp-vcr record --name my_test_session -- uv run -m blt_mcp.server
  ```
  This will save a recording to `sessions/`, which you can then move to `snapshots/`.

---

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
- GitLab: [https://gitlab.com/owasp-blt/BLT-MCP](https://gitlab.com/owasp-blt/BLT-MCP)
- OWASP BLT: [https://owasp.org/www-project-bug-logging-tool/](https://owasp.org/www-project-bug-logging-tool/)
