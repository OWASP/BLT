# BLT--Byte 🤖

AI-powered chatbot for BugHeist (BLT) built with Python Workers and Cloudflare Workers AI.

## Overview

BLT--Byte is an intelligent chatbot assistant that helps users with bug bounty hunting, vulnerability reporting, and understanding the BugHeist platform. It's powered by Cloudflare Workers AI and runs as a Python worker at the edge.

## Features

- 🤖 AI-powered responses using Llama 3.1 8B model
- ⚡ Lightning-fast responses from the edge
- 🔒 Secure and scalable
- 🌐 CORS-enabled for web integration
- 💬 Context-aware about BLT and bug bounty processes

## Prerequisites

- [uv](https://github.com/astral-sh/uv) - Python package manager
- [Wrangler](https://developers.cloudflare.com/workers/wrangler/) - Cloudflare Workers CLI
- Cloudflare account with Workers AI enabled

## Installation

1. Install dependencies:
```bash
npm install
```

2. Install Python dependencies (handled automatically by uv):
```bash
uv sync
```

## Development

Start the development server:

```bash
npm run dev
```

The chatbot will be available at `http://localhost:8787`

## Usage

Send a POST request to the worker with a JSON body:

```bash
curl -X POST http://localhost:8787 \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I report a bug on BugHeist?"}'
```

Response:
```json
{
  "success": true,
  "message": "To report a bug on BugHeist...",
  "user_message": "How do I report a bug on BugHeist?"
}
```

## API Reference

### POST /

Send a message to the chatbot.

**Request Body:**
```json
{
  "message": "Your question here"
}
```

**Response:**
```json
{
  "success": true,
  "message": "AI response",
  "user_message": "Your question"
}
```

## Deployment

Deploy to Cloudflare Workers:

```bash
npm run deploy
```

## Tech Stack

- **Runtime**: Cloudflare Workers (Python)
- **AI Model**: Llama 3.1 8B Instruct
- **Framework**: Workers AI
- **Language**: Python 3.12+

## Project Structure

```
BLT--Byte/
├── src/
│   └── entry.py          # Main worker entry point
├── package.json          # Node dependencies and scripts
├── pyproject.toml        # Python dependencies
├── wrangler.jsonc        # Cloudflare Workers configuration
└── README.md             # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See [LICENSE](LICENSE) file for details.
AI assistant, orchestrator and agent
