# Contributing to BLT-SafeCloak

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/BLT-SafeCloak.git`
3. Install dependencies: `npm install && npm run setup`
4. Create a branch: `git checkout -b feature/your-feature-name`
5. Make your changes
6. Run checks: `npm run check`
7. Commit and push your changes
8. Open a pull request

## Development Workflow

### Setup Environment

```bash
# Install all dependencies
npm install
npm run setup

# Verify installation
npm run check
```

### Running Locally

```bash
# Start development server with hot reload
npm run dev
```

Access the application at `http://localhost:8787`.

### Code Quality

Before submitting a PR, ensure your code passes all checks:

```bash
# Auto-format all code (Python + HTML/CSS/JS)
npm run format

# Check formatting without modifying files
npm run format:check

# Type checking (Python)
npm run typecheck

# Run all checks (format check + type check)
npm run check
```

**Format Tools Used:**
- **Python**: yapf (PEP 8, 100 char line limit)
- **HTML/CSS/JS**: Prettier (consistent web formatting)

### Testing Changes

#### E2E Video Chat Tests

The repository includes automated end-to-end tests for the video chat feature.  
These tests use a **local PeerJS signaling server** (no dependency on the public
`0.peerjs.com` server) for reliability in CI and local development.

**Prerequisites:**

```bash
# Install all Node and Python dependencies
npm install
pip install -r requirements-dev.txt

# Install the Playwright browser driver
playwright install chromium --with-deps
```

**Running the tests:**

```bash
pytest tests/ -v
```

The test suite will automatically:
1. Start a local PeerJS signaling server (port chosen dynamically)
2. Spin up a lightweight HTTP server to serve the app pages
3. Launch headless Chromium with fake camera/microphone devices
4. Tear everything down after the tests complete

No network access to external signaling or backend services is required.
The served pages load static assets (Tailwind CSS, Google Fonts, Font Awesome)
from their public CDNs; the test server strips those CDN tags so the E2E test
runs without any external network dependency.

1. Test all affected pages manually
2. Verify WebRTC functionality in multiple browsers
3. Test consent flow end-to-end
4. Verify encryption/decryption works correctly

## Code Style

### Python

- Follow PEP 8 guidelines
- Use type hints for all functions
- Maximum line length: 100 characters
- Use meaningful variable names
- Add docstrings for complex functions

### JavaScript

- Use modern ES6+ syntax
- Prefer `const` over `let`, avoid `var`
- Use async/await for asynchronous operations
- Comment complex logic
- Keep functions small and focused

### HTML/CSS

- Semantic HTML5 elements
- Accessible markup (ARIA labels where needed)
- Mobile-first responsive design
- BEM naming convention for CSS classes

## Project Structure (e.g., `feature.html`)
2. Add route to `PAGES_MAP` dictionary in `src/main.py`:
   ```python
   PAGES_MAP = {
       '/': 'index.html',
       '/feature': 'feature.html',  # Add your route
   }
   ```
3. Add corresponding JavaScript in `public/js/` if needed
4. Update navigation in all HTML pages with clean URL (e.g., `/feature`)
1. Create HTML file in `src/pages/`
2. Add corresponding JavaScript in `public/js/`
3. Add route handler in `src/main.py`
4. Update navigation if needed

### Adding New Features

1. Discuss in GitHub issues first
2. Update documentation
3. Add necessary tests
4. Update README if user-facing

## Cloudflare Workers Resources

### Official Documentation

- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [Python Workers Guide](https://developers.cloudflare.com/workers/languages/python/)
- [Wrangler CLI Documentation](https://developers.cloudflare.com/workers/wrangler/)
- [Workers Examples](https://developers.cloudflare.com/workers/examples/)

### Python Workers Specific

- [Python Workers Runtime API](https://developers.cloudflare.com/workers/languages/python/runtime-apis/)
- [Python Workers Bindings](https://developers.cloudflare.com/workers/languages/python/bindings/)
- [Migrating from JavaScript to Python](https://developers.cloudflare.com/workers/languages/python/how-it-works/)

### Key Concepts

- [Request/Response Objects](https://developers.cloudflare.com/workers/runtime-apis/request/)
- [Workers Assets](https://developers.cloudflare.com/workers/static-assets/)
- [Environment Variables](https://developers.cloudflare.com/workers/configuration/environment-variables/)
- [KV Storage](https://developers.cloudflare.com/kv/)
- [Durable Objects](https://developers.cloudflare.com/durable-objects/)

### WebRTC & Real-time Communication

- [Workers WebSockets](https://developers.cloudflare.com/workers/runtime-apis/websockets/)
- [Durable Objects for Real-time](https://developers.cloudflare.com/durable-objects/examples/websocket-server/)
- [WebRTC Signaling Server Pattern](https://developers.cloudflare.com/calls/turn/)

### Performance & Best Practices

- [Workers Best Practices](https://developers.cloudflare.com/workers/best-practices/)
- [Performance Tips](https://developers.cloudflare.com/workers/best-practices/performance/)
- [Security Best Practices](https://developers.cloudflare.com/workers/best-practices/security/)

### Tutorials & Learning

- [Workers Interactive Tutorial](https://workers.cloudflare.com/)
- [Build a WebSocket Server](https://developers.cloudflare.com/durable-objects/examples/websocket-server/)
- [Static Site Hosting](https://developers.cloudflare.com/workers/static-assets/get-started/)

### Community Resources
 - Add to PAGES_MAP dictionary
PAGES_MAP = {
    '/': 'index.html',
    '/video-chat': 'video-chat.html',
    '/notes': 'notes.html',
    '/consent': 'consent.html',
    '/new-page': 'new-page.html',  # Add your new route here
}
```

The routing is handled automatically by the `PAGES_MAP` dictionary. Create the HTML file in `src/pages/` and add the mapping.

### Creating Response Utilities

Use helper functions from `src/libs/utils.py`:

```python
from libs.utils import html_response, json_response, cors_response

# Return HTML
return html_response("<h1>Hello</h1>")

# Return JSON
return json_response({"status": "success"})

# CORS preflight
return cors_response(mmon Tasks

### Adding a New Route

```python
# In src/main.py
if path == '/new-page':
    html_content = Path(__file__).parent / 'pages' / 'new-page.html'
    return Response.new(html_content.read_text(), {
        'headers': {'Content-Type': 'text/html'}
    })
```

### Debugging

```bash
# View logs in real-time
wrangler tail

# Debug with local inspector
npm run dev
# Open: chrome://inspect
```

### Environment Variables

```bash
# Set secrets (production)
wrangler secret put SECRET_NAME

# Local development
# Add to .dev.vars file (gitignored)
```

## Pull Request Guidelines

### PR Checklist

- [ ] Code follows style guidelines
- [ ] All checks pass (`npm run check`)
- [ ] Changes are documented
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] Tested in development environment

### PR Title Format

```
feat: Add new feature
fix: Fix bug in component
docs: Update documentation
refactor: Refactor code
style: Format code
test: Add tests
chore: Update dependencies
```

### Description Template

```markdown
## Changes
Brief description of what changed

## Motivation
Why this change is needed

## Testing
How to test the changes

## Screenshots (if applicable)
Add screenshots for UI changes
```

## Questions?

- Open an issue for bugs or feature requests
- Join discussions in existing issues
- Tag maintainers for urgent matters

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow OWASP community guidelines