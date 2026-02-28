# BLT Byte

AI-powered assistant for bug bounty hunting and security research on the BLT (Bug Logging Tool) platform.

## Overview

BLT Byte provides intelligent assistance to security researchers working with the BugHeist platform. Built on Cloudflare Workers with Python runtime, it leverages Cloudflare Workers AI to deliver real-time guidance on vulnerability reporting, bug bounty methodologies, and responsible disclosure practices.

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

### POST /

Send a chat message to the AI assistant.

**Request:**
```json
{
  "message": "How do I report a bug on BugHeist?"
}
```

**Response:**
```json
{
  "success": true,
  "message": "AI response",
  "user_message": "How do I report a bug on BugHeist?"
}
```

## Project Structure

```
BLT--Byte/
├── src/
│   ├── main.py              # Python worker entry point
│   └── pages/
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
- Cloudflare Workers AI (GPT-OSS-120B model)
- Tailwind CSS
- Vanilla JavaScript

## License

See [LICENSE](LICENSE) file for details.
