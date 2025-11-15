# SelfErase Cloudflare Workers

Stateless edge functions that serve **public data only**. No user PII is ever processed or stored.

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

- Node.js 18+
- Cloudflare account (for deployment)
- Wrangler CLI

### Setup

```bash
# Install dependencies
npm install

# Configure Wrangler
# Edit wrangler.toml with your account_id

# Run locally
npm run dev

# Deploy to Cloudflare
npm run deploy
```

### Testing

```bash
# Run tests
npm test

# Lint code
npm run lint

# Format code
npm run format
```

## Configuration

Edit `wrangler.toml`:
- Set your `account_id`
- Configure routes (optional)
- Set environment variables (if needed)

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
├── index.ts       # Main router and handlers
├── brokers.ts     # Broker data endpoints
├── health.ts      # Health check logic
└── templates.ts   # Template serving
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md).

## License

AGPL-3.0 - See [LICENSE](../LICENSE)
