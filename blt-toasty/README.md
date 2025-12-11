# Toasty

The smart, context-aware AI code reviewer from OWASP BLT.

## Overview

Toasty is an AI-powered code review service designed to help developers improve code quality through automated analysis and intelligent suggestions.

## Project Structure

- **Django Application** (`/aibot`, `/toasty`) - Main Django-based application
- **Cloudflare Worker Backend** (`/cloudflare-worker`) - Serverless Python backend using Cloudflare Workers

## Components

### Django Application

The main Django application provides the core functionality for Toasty.

**Setup:**
```bash
# Install dependencies
poetry install

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

### Cloudflare Worker Backend

A serverless backend built with Cloudflare Workers and Python for globally distributed, low-latency API endpoints.

**Features:**
- Health monitoring endpoints
- Code review API
- Status monitoring
- CORS support
- Comprehensive error handling

**Quick Start:**
```bash
cd cloudflare-worker

# Install Wrangler CLI
npm install

# Run locally
npm run dev

# Deploy
npm run deploy
```

For detailed information, see [cloudflare-worker/README.md](cloudflare-worker/README.md).

## Development

### Prerequisites

- Python 3.13+
- Poetry (for Django app)
- Node.js and npm (for Cloudflare Worker)
- Wrangler CLI (for Cloudflare Worker deployment)

### Installation

1. Clone the repository
2. Install Django dependencies: `poetry install`
3. Install Worker dependencies: `cd cloudflare-worker && npm install`

## License

This project is part of OWASP BLT.

## Contributing

Contributions are welcome! Please ensure all changes are tested before submitting.
