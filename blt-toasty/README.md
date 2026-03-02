# Toasty

The smart, context-aware AI code reviewer from OWASP BLT.

## Overview

Toasty is an AI-powered code review service designed to help developers improve code quality through automated analysis and intelligent suggestions. It consists of a Django application for the main service and a Cloudflare Worker for serverless, globally distributed API endpoints.

## Project Structure

- **Django Application** (`/aibot`, `/toasty`) - Main Django-based application
- **Cloudflare Worker** (root directory) - Serverless Python backend using Cloudflare Workers
  - `worker.py` - Main worker handler
  - `wrangler.toml` - Cloudflare Workers configuration
  - `test_worker.py` - Worker tests

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
- CORS support with preflight handling
- Comprehensive error handling and validation

**Quick Start:**
```bash
# Install Node dependencies (including Wrangler CLI)
npm install

# Run locally
npm run dev

# Deploy
npm run deploy
```

## Development

### Prerequisites

- Python >=3.13,<4.0.0
- Poetry (for Django app)
- Node.js and npm (for Cloudflare Worker)

### Installation

1. Clone the repository
2. Install Django dependencies: `poetry install`
3. Install Worker dependencies: `npm install`

## API Endpoints

The Cloudflare Worker provides these REST endpoints:

- `GET /` - Service information
- `GET /health` - Health check
- `POST /api/review` - Submit code for review
- `GET /api/status` - Service status

See `worker.py` for detailed API documentation.

## License

This project is part of OWASP BLT.

## Contributing

Contributions are welcome! Please ensure all changes are tested before submitting.
