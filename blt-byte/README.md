# BLT Byte

AI-powered assistant for bug bounty hunting and security research on the BLT (Bug Logging Tool) platform.

## Overview

BLT Byte provides intelligent assistance to security researchers working with the OWASP BLT platform. Built on Cloudflare Workers with Python runtime, it leverages Cloudflare Workers AI to deliver real-time guidance on vulnerability reporting, bug bounty methodologies, and responsible disclosure practices.

Byte acts as:
- **FAQ agent** – instant answers about OWASP BLT
- **Onboarding assistant** – step-by-step guides for contributors, bug hunters, and organisations
- **Security scan orchestrator** – AI-generated checklists for any URL (OWASP Top 10 focus)
- **MCP server** – exposes BLT capabilities as [Model Context Protocol](https://modelcontextprotocol.io/) tools for AI IDEs

## Prerequisites

- Node.js and npm
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)
- Cloudflare account with Workers AI enabled

## Quick Start

Install dependencies:
```bash
npm install
```

Start development server:
```bash
npm run dev
```

Access the application at `http://localhost:8787`

## Deployment

```bash
npm run deploy
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/chat` | Chat interface |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/chat` | FAQ + onboarding agent |
| `POST` | `/api/scan` | Security scan orchestrator |
| `GET` | `/api/mcp` | MCP manifest (tool discovery) |
| `POST` | `/api/mcp` | MCP tool invocation |

### Chat (`POST /api/chat`)

```json
{
  "message": "How do I report a bug on OWASP BLT?",
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

### MCP tool call (`POST /api/mcp`)

```json
{
  "tool": "get_onboarding_guide",
  "params": { "role": "contributor" }
}
```

Available tools: `chat`, `scan_url`, `get_onboarding_guide`.

### POST /

Send a chat message to the AI assistant.

**Request:**
```json
{
  "message": "How do I report a bug on OWASP BLT?"
}
```

**Response:**
```json
{
  "success": true,
  "message": "AI response",
  "user_message": "How do I report a bug on OWASP BLT?"
}
```

## Project Structure

```
BLT--Byte/
├── src/
│   ├── main.py              # Python worker entry point
│   └── pages/
│       ├── index.html       # Landing page
│       └── chat.html        # Chat interface
├── static/
│   └── logo.png             # BLT branding assets
├── tests/
│   ├── conftest.py          # Workers runtime stubs for pytest
│   └── test_entry.py        # Unit tests
│       └── index.html       # Chat interface
├── public/
│   └── images/
│       └── logo.png         # BLT branding assets
├── package.json
├── pyproject.toml
└── wrangler.toml
```

## Technology Stack

- Cloudflare Workers (Python runtime)
- Cloudflare Workers AI (`@cf/openai/gpt-oss-120b` model)
- Tailwind CSS
- Vanilla JavaScript

## Running Tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## MCP Integration (AI IDEs)

Point your AI IDE at the deployed Worker's MCP endpoint:

**Cursor / `mcp.json`:**
```json
{
  "servers": {
    "blt-byte": {
      "url": "https://blt-byte-chatbot.<account>.workers.dev/api/mcp",
      "transport": "http"
    }
  }
}
```

- Cloudflare Workers AI (@cf/openai/gpt-oss-120b model)
- Tailwind CSS
- Vanilla JavaScript

## License

See [LICENSE](LICENSE) file for details.
