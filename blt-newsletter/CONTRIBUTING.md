# Contributing to BLT Newsletter

Thank you for your interest in contributing to the OWASP BLT Newsletter project! This document provides guidelines for contributing.

## Code of Conduct

This project follows the [OWASP Code of Conduct](https://owasp.org/www-policy/operational/code-of-conduct). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/BLT-Newsletter.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes thoroughly
6. Commit with clear messages: `git commit -m "Add feature: description"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

See the [README.md](README.md) for installation and setup instructions.

## Areas for Contribution

### Features
- Rate limiting for API endpoints
- Unsubscribe functionality
- Admin dashboard for managing subscribers
- Email templates for different newsletters
- Analytics and tracking
- Multi-language support
- Newsletter archive page
- RSS feed integration

### Improvements
- Unit and integration tests
- Better error handling
- Logging system
- Performance optimizations
- Security enhancements
- Accessibility improvements
- Mobile app integration

### Documentation
- API documentation
- Deployment guides for various platforms
- Video tutorials
- Use case examples
- Troubleshooting guide

## Coding Standards

### JavaScript/Node.js
- Use ES6+ features
- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use async/await for asynchronous operations
- Add JSDoc comments for functions
- Keep functions small and focused

### HTML/CSS
- Use semantic HTML5 elements
- Follow BLT-Design guidelines
- Ensure responsive design
- Test cross-browser compatibility
- Maintain accessibility standards (WCAG 2.1 Level AA)

### Git Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line should be 50 characters or less
- Reference issues and pull requests when relevant

Example:
```
Add rate limiting to subscription endpoint

- Implement express-rate-limit middleware
- Add 5 requests per minute per IP limit
- Update tests and documentation

Fixes #123
```

## Testing

Before submitting a PR:
- Test all changes manually
- Ensure the server starts without errors
- Test API endpoints with curl or Postman
- Verify the UI works across browsers
- Check for console errors
- Test with and without SendGrid configured

See [TESTING.md](TESTING.md) for detailed testing procedures.

## Pull Request Guidelines

### PR Title
Use conventional commit format:
- `feat: Add new feature`
- `fix: Fix bug in subscription`
- `docs: Update README`
- `style: Format code`
- `refactor: Restructure server code`
- `test: Add unit tests`
- `chore: Update dependencies`

### PR Description
Include:
- What changes were made
- Why the changes were necessary
- How to test the changes
- Screenshots (for UI changes)
- Related issues

### PR Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings or errors
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] UI tested on multiple browsers (if applicable)
- [ ] Accessibility checked (if applicable)

## Security

If you discover a security vulnerability:
1. **Do NOT** open a public issue
2. Email security@owasp.org
3. Provide detailed information about the vulnerability
4. Wait for confirmation before disclosing publicly

## Questions?

- Join the [OWASP BLT Discord](https://discord.gg/owasp-blt)
- Check the [OWASP BLT Documentation](https://owasp-blt.github.io/documentation/)
- Open a [GitHub Discussion](https://github.com/OWASP-BLT/BLT-Newsletter/discussions)

## License

By contributing to BLT Newsletter, you agree that your contributions will be licensed under the AGPL-3.0 License.

---

Thank you for contributing to OWASP BLT! 🎉
