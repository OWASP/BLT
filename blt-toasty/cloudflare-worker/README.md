# Toasty Cloudflare Worker Backend

This directory contains the Cloudflare Worker backend for Toasty, OWASP BLT's AI-powered code review service.

## Overview

The Toasty backend is built using Cloudflare Workers with Python, providing a serverless, globally distributed API for code analysis and review services.

## Features

- **Health Monitoring**: `/health` endpoint for service health checks
- **Code Review API**: `/api/review` endpoint for submitting code for AI-powered analysis
- **Status Monitoring**: `/api/status` endpoint for checking service operational status
- **CORS Support**: Cross-Origin Resource Sharing enabled for web clients
- **Error Handling**: Comprehensive error responses with proper HTTP status codes

## API Endpoints

### GET /
Returns service information and available endpoints.

**Response:**
```json
{
  "service": "Toasty AI Code Reviewer",
  "version": "1.0.0",
  "description": "Backend API for OWASP BLT's AI-powered code review service",
  "endpoints": {
    "/": "Service information",
    "/health": "Health check endpoint",
    "/api/review": "POST - Submit code for review",
    "/api/status": "GET - Check service status"
  }
}
```

### GET /health
Health check endpoint for monitoring service availability.

**Response:**
```json
{
  "status": "healthy",
  "service": "toasty-backend",
  "timestamp": null
}
```

### POST /api/review
Submit code for AI-powered review and analysis.

**Request Body:**
```json
{
  "code": "def hello():\n    print('world')",
  "language": "python",
  "context": "Optional context about the code"
}
```

**Response:**
```json
{
  "status": "success",
  "analysis": {
    "language": "python",
    "lines_of_code": 2,
    "issues": [],
    "suggestions": [],
    "summary": "Review completed successfully"
  },
  "metadata": {
    "processed_at": null,
    "worker_version": "1.0.0"
  }
}
```

### GET /api/status
Get detailed service status information.

**Response:**
```json
{
  "service": "toasty-backend",
  "status": "operational",
  "version": "1.0.0",
  "features": {
    "code_review": "available",
    "health_check": "available",
    "status_monitoring": "available"
  },
  "uptime": "available"
}
```

## Setup

### Prerequisites

1. **Cloudflare Account**: Sign up at [cloudflare.com](https://www.cloudflare.com/)
2. **Wrangler CLI**: Install the Cloudflare Workers CLI tool
   ```bash
   npm install -g wrangler
   ```
3. **Python**: Python 3.11+ (for local development and testing)

### Installation

1. Navigate to the cloudflare-worker directory:
   ```bash
   cd cloudflare-worker
   ```

2. Authenticate with Cloudflare:
   ```bash
   wrangler login
   ```

3. Configure your worker:
   - Edit `wrangler.toml` to set your account details
   - Add any required secrets:
     ```bash
     wrangler secret put SECRET_NAME
     ```

### Development

Run the worker locally for testing:
```bash
wrangler dev
```

This will start a local development server, typically at `http://localhost:8787`

### Deployment

Deploy to Cloudflare Workers:

1. **Development Environment:**
   ```bash
   wrangler deploy --env development
   ```

2. **Staging Environment:**
   ```bash
   wrangler deploy --env staging
   ```

3. **Production Environment:**
   ```bash
   wrangler deploy --env production
   ```

### Testing

Test the deployed worker:

```bash
# Health check
curl https://your-worker.your-subdomain.workers.dev/health

# Status check
curl https://your-worker.your-subdomain.workers.dev/api/status

# Code review (POST)
curl -X POST https://your-worker.your-subdomain.workers.dev/api/review \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello(): print(\"world\")",
    "language": "python",
    "context": "Simple function"
  }'
```

## Architecture

### Cloudflare Workers Python Runtime

This worker uses Cloudflare's Python Workers runtime, which provides:
- **Global Edge Deployment**: Workers run in Cloudflare's global network
- **Low Latency**: Execute close to users worldwide
- **Serverless**: No infrastructure to manage
- **Auto-scaling**: Handles traffic spikes automatically
- **Python Support**: Write workers in Python with access to standard libraries

### Request Flow

1. Client sends HTTP request to worker URL
2. `on_fetch()` function receives and routes the request
3. Appropriate handler function processes the request
4. Response is returned with proper headers and status codes
5. Cloudflare's edge network delivers the response globally

## Configuration

### Environment Variables

Configure in `wrangler.toml` under `[vars]`:
- `ENVIRONMENT`: Deployment environment (development/staging/production)
- `LOG_LEVEL`: Logging verbosity level

### Secrets

Store sensitive data using Wrangler secrets:
```bash
wrangler secret put API_KEY
wrangler secret put SECRET_KEY
```

Access secrets in code via the `env` parameter:
```python
api_key = env.API_KEY
```

## Future Enhancements

- [ ] Integration with Google GenAI for advanced code analysis
- [ ] Integration with Bandit for Python security scanning
- [ ] Persistent storage using Cloudflare KV or R2
- [ ] Rate limiting and authentication
- [ ] Webhook support for GitHub integration
- [ ] Batch processing for multiple files
- [ ] Real-time code analysis streaming
- [ ] Caching for improved performance
- [ ] Metrics and analytics collection
- [ ] Custom rulesets for code review

## Security Considerations

- Always validate and sanitize input data
- Use secrets management for sensitive configuration
- Implement rate limiting to prevent abuse
- Enable CORS only for trusted origins in production
- Monitor and log security events
- Keep dependencies updated

## Troubleshooting

### Common Issues

1. **Worker not responding:**
   - Check deployment status: `wrangler deployments list`
   - View logs: `wrangler tail`

2. **Authentication errors:**
   - Re-authenticate: `wrangler login`
   - Verify account access

3. **Python compatibility issues:**
   - Ensure code is compatible with Cloudflare Workers Python runtime
   - Check for unsupported libraries

### Logs

View real-time logs:
```bash
wrangler tail
```

View logs for specific deployment:
```bash
wrangler tail --env production
```

## Resources

- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Python Workers Guide](https://developers.cloudflare.com/workers/languages/python/)
- [Wrangler CLI Documentation](https://developers.cloudflare.com/workers/wrangler/)
- [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)

## Contributing

Contributions are welcome! Please follow the project's contribution guidelines and ensure all changes are tested before submitting.

## License

This project is part of OWASP BLT and follows the same license terms.
