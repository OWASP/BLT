# Contributing to Fresh Time Tracker

Thank you for your interest in contributing to Fresh Time Tracker! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/OWASP-BLT/Fresh/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Node version, etc.)
   - Screenshots if applicable

### Suggesting Features

1. Check [Discussions](https://github.com/OWASP-BLT/Fresh/discussions) for existing suggestions
2. Create a new discussion with:
   - Clear use case
   - Proposed solution
   - Benefits and potential drawbacks
   - Willingness to implement

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following our guidelines
4. Write/update tests if applicable
5. Update documentation
6. Commit with clear messages: `git commit -m 'Add amazing feature'`
7. Push to your fork: `git push origin feature/amazing-feature`
8. Open a Pull Request

## Development Guidelines

### Code Style

- Follow TypeScript best practices
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused
- Use async/await for asynchronous operations

### Testing

```bash
# Run tests
npm test

# Type checking
npm run type-check
```

### Documentation

- Update README.md for user-facing changes
- Update docs/ for detailed documentation
- Add JSDoc comments for public APIs
- Include examples for new features

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Build process or tooling changes

Example: `feat: add GitHub webhook support`

### Privacy Requirements

When contributing, ensure:
- No sensitive data logging
- No data sent to 3rd party services
- Screenshots processed locally only
- Encryption for sensitive data
- User consent for data collection

## Project Structure

```
Fresh/
├── src/
│   ├── api/              # API routes
│   ├── modules/          # Core tracking modules
│   ├── types/            # TypeScript types
│   ├── durable-objects/  # Durable Objects
│   └── utils/            # Utility functions
├── client/               # Client-side code
├── examples/             # Example implementations
├── docs/                 # Documentation
└── tests/                # Test files
```

## Review Process

1. Maintainers review PRs for:
   - Code quality
   - Test coverage
   - Documentation
   - Privacy compliance
   - Breaking changes

2. Address review feedback
3. Once approved, a maintainer will merge

## Getting Help

- [GitHub Discussions](https://github.com/OWASP-BLT/Fresh/discussions) for questions
- [GitHub Issues](https://github.com/OWASP-BLT/Fresh/issues) for bugs
- Email: support@example.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing! 🎉
