# BLT Byte 🤖🐛

**AI assistant, orchestrator and security agent for [OWASP BLT](https://github.com/OWASP-BLT/BLT)**

Byte is a Python [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) application that sits on the BLT website and acts as:

- **FAQ agent** – answers common questions about OWASP BLT
- **Onboarding assistant** – step-by-step guides for contributors, bug hunters, and organisations
- **Security scan orchestrator** – AI-generated checklists for any URL (OWASP Top 10 focus)
- **MCP server** – exposes BLT capabilities as [Model Context Protocol](https://modelcontextprotocol.io/) tools for AI IDEs

---

## Project structure

```
.
├── src/
│   └── entry.py          # Cloudflare Worker entrypoint (Python)
├── public/
│   └── index.html        # Landing page (served via CF Assets binding)
├── tests/
│   ├── conftest.py       # Workers runtime stubs for pytest
│   └── test_entry.py     # Unit tests for pure-Python helpers
├── wrangler.toml         # Cloudflare Workers configuration
└── pyproject.toml        # Python project metadata & dev dependencies
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/chat` | FAQ + onboarding chat agent |
| `POST` | `/api/scan` | Security scan orchestrator |
| `GET` | `/api/mcp` | MCP manifest (tool discovery) |
| `POST` | `/api/mcp` | MCP tool invocation |

### Chat (`POST /api/chat`)

```json
{
  "message": "How do I report a bug on BLT?",
  "history": []
}
```

### Security scan (`POST /api/scan`)

```json
{
  "url": "https://example.com",
  "scan_type": "quick"
}
```

`scan_type` is `quick` (default) or `full`.

### MCP tool call (`POST /api/mcp`)

```json
{
  "tool": "get_onboarding_guide",
  "params": { "role": "contributor" }
}
```

Available tools: `chat`, `scan_url`, `get_onboarding_guide`.

---

## Local development

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18 (for Wrangler)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) ≥ 3.x
- Python ≥ 3.12

### Install Wrangler

```bash
npm install -g wrangler
```

### Run locally

```bash
wrangler dev
```

The Worker runs at `http://localhost:8787`.

### Run tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

---

## Deployment

### 1. Authenticate with Cloudflare

```bash
wrangler login
```

### 2. Enable Workers AI

Workers AI is enabled by default for all Cloudflare accounts. No extra configuration is needed – the `[ai]` binding in `wrangler.toml` handles it.

### 3. Deploy

```bash
wrangler deploy
```

Wrangler will output the deployed URL (e.g. `https://blt-byte.<account>.workers.dev`).

---

## MCP integration (AI IDEs)

Point your AI IDE at the deployed Worker's MCP endpoint:

**Cursor / `mcp.json`:**
```json
{
  "servers": {
    "blt-byte": {
      "url": "https://blt-byte.<account>.workers.dev/api/mcp",
      "transport": "http"
    }
  }
}
```

---

## Contributing

This project follows the same contribution process as [OWASP BLT](https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md).

1. Fork and clone this repository.
2. Make your changes in a feature branch.
3. Ensure all tests pass (`python -m pytest tests/ -v`).
4. Open a pull request.

---

## License

[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) – © OWASP BLT contributors.
