# BLT Byte 🤖

AI-powered chatbot for BugHeist (BLT) built with Python Workers and Cloudflare Workers AI.

## Overview

BLT Byte is an intelligent chatbot assistant that helps users with bug bounty hunting, vulnerability reporting, and understanding the BugHeist platform. It's powered by Cloudflare Workers AI using the Llama 3.1 8B model and runs as a Python worker at the edge.

## Features

- 🤖 AI-powered responses using Llama 3.1 8B Instruct model
- ⚡ Lightning-fast responses from the edge
- 🔒 Secure and scalable
- 🎨 Clean, modern UI inspired by BLT-GSOC design system
- 💬 Context-aware about BLT and bug bounty processes
- 📱 Fully responsive design

## Prerequisites

- [uv](https://github.com/astral-sh/uv) - Python package manager
- [Wrangler](https://developers.cloudflare.com/workers/wrangler/) - Cloudflare Workers CLI
- Cloudflare account with Workers AI enabled

## Installation

1. Install dependencies:
```bash
npm install
```

2. Python dependencies are handled automatically by uv when you run the dev server.

## Development

Start the development server:

```bash
npm run dev
```

The chatbot will be available at `http://localhost:8787`

The interface will automatically load, and you can start chatting with the AI assistant right away.

## Usage

Simply open your browser to `http://localhost:8787` and start chatting! The AI assistant is ready to help with:

- Bug reporting on BugHeist
- Understanding vulnerability types
- Bug bounty best practices
- Responsible disclosure guidelines
- Security research tips

### API Usage

You can also use the API directly by sending POST requests:

```bash
curl -X POST http://localhost:8787 \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I report a bug on BugHeist?"}'
```

Response:
```json
{
  "success": true,
  "message": "AI response here...",
  "user_message": "How do I report a bug on BugHeist?"
}
```

## Deployment

Deploy to Cloudflare Workers:

```bash
npm run deploy
```

After deployment, your chatbot will be live at your Cloudflare Workers URL.

## Tech Stack

- **Runtime**: Cloudflare Workers (Python)
- **AI Model**: Llama 3.1 8B Instruct
- **Framework**: Workers AI
- **Language**: Python 3.12+
- **Frontend**: Vanilla JavaScript with modern CSS

## Project Structure

```
BLT--Byte/
├── src/
│   └── entry.py          # Main worker entry point
├── public/
│   └── index.html        # Chat interface
├── package.json          # Node dependencies and scripts
├── pyproject.toml        # Python dependencies
├── wrangler.jsonc        # Cloudflare Workers configuration
├── .gitignore
└── README.md
```

## Design

The UI is inspired by the BLT-GSOC landing page, featuring:
- OWASP BLT brand colors (#E10101)
- Manrope font family
- Clean, minimal design
- Smooth animations and transitions
- Responsive layout for all devices

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See [LICENSE](LICENSE) file for details.
