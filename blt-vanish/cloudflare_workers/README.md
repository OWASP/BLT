# BLT-Vanish Cloudflare Workers

Stateless Python edge functions that serve **public data only**. No user PII is ever processed or stored.

## Purpose

Cloudflare Workers provide:
- Public broker metadata (lists, details, categories)
- Broker health checks (website availability)
- Opt-out request templates
- Update notifications

## Privacy Guarantee

✅ **NO USER PII IS EVER TRANSMITTED OR STORED**

Workers only handle:
- Public broker information
- Template text
- Health check results
- Metadata updates

## Endpoints

### `GET /api/brokers`
Returns list of all data brokers (public information).

### `GET /api/brokers/:id`
Returns details for a specific broker.

### `GET /api/health/:id`
Checks if a broker's website is accessible.

### `GET /api/templates/:id`
Returns an opt-out request template.

### `GET /api/categories`
Returns list of broker categories.

## Development

### Prerequisites

- Python 3
- Node.js 22+
- Cloudflare account (for deployment)
- Wrangler CLI

### Setup

```bash
# Install dependencies
npm install

# Run locally
npm run dev

# Check Python syntax
npm run check

# Deploy to Cloudflare
npm run deploy
```

### Testing

```bash
# Check Python syntax
npm run check
```

## Configuration

Edit `wrangler.toml`:
- Set your Cloudflare account credentials through Wrangler
- Configure routes (optional)
- Set environment variables (if needed)

Python Workers currently require the `python_workers` compatibility flag. The
flag is configured in `wrangler.toml`.

## Security

- CORS headers configured
- HTTPS only
- No logging of requests (privacy mode)
- Rate limiting enabled
- Security headers enforced

## Deployment

```bash
# Deploy to production
npm run deploy

# Deploy to development
wrangler deploy --env development
```

## Architecture

```
src/
├── index.py       # Main router and handlers
├── brokers.py     # Broker data endpoints
├── health.py      # Health check logic
├── responses.py   # Shared response headers and helpers
└── templates.py   # Template serving
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md).

## License

AGPL-3.0 - See [LICENSE](../LICENSE)
