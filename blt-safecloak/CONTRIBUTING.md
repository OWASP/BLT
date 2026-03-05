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
# Auto-format Python code
npm run format

# Check formatting without modifying
npm run format:check

# Type checking
npm run typecheck

# Run all checks
npm run check
```

### Testing Changes

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

## Project Structure

### Adding New Pages

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

- [Cloudflare Workers Discord](https://discord.gg/cloudflaredev)
- [Cloudflare Community Forum](https://community.cloudflare.com/c/developers/workers/40)
- [Workers GitHub Examples](https://github.com/cloudflare/workers-sdk/tree/main/templates)

## Common Tasks

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