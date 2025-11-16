# Contributing to SelfErase

Thank you for your interest in contributing to SelfErase! We're building a privacy-first toolkit that helps people take control of their personal data online.

## 🎯 Project Mission

SelfErase is committed to:
- **Privacy First**: No user data ever leaves their device
- **Security First**: Industry-standard encryption and security practices
- **Transparency**: Open-source and verifiable
- **User Control**: Users own and control all their data

## 🤝 Ways to Contribute

### 1. Add Data Brokers

Help expand our database of data brokers and people search sites.

**Requirements**:
- Broker must have a documented opt-out process
- Contact information must be current and verified
- Opt-out procedure must be legal and legitimate

**Process**:
1. Create a new broker JSON file in `data/brokers/`
2. Fill out all required fields (see schema)
3. Test the opt-out process yourself
4. Submit a pull request

See [docs/broker-guide.md](./docs/broker-guide.md) for detailed instructions.

### 2. Improve Opt-Out Templates

Create or improve templates for deletion/opt-out requests.

**Templates should**:
- Be clear and professional
- Reference relevant privacy laws (GDPR, CCPA, etc.)
- Include all required information fields
- Be tested with actual brokers

**Location**: `data/templates/`

### 3. Enhance the Flutter App

Work on the local application.

**Areas to contribute**:
- UI/UX improvements
- New features
- Bug fixes
- Performance optimization
- Platform-specific enhancements
- Accessibility improvements

**Location**: `flutter_app/`

### 4. Improve Cloudflare Workers

Enhance the edge automation layer.

**Areas to contribute**:
- Better broker health checks
- API improvements
- Performance optimization
- Error handling
- Rate limiting

**Location**: `cloudflare_workers/`

### 5. Security Improvements

Help make SelfErase more secure.

**Areas to contribute**:
- Security audits
- Encryption improvements
- Code reviews
- Vulnerability testing
- Documentation

See [SECURITY.md](./SECURITY.md) for our security model.

### 6. Documentation

Improve documentation and guides.

**Areas to contribute**:
- User guides
- Developer documentation
- API documentation
- Architecture diagrams
- Video tutorials
- Translations

**Location**: `docs/`

### 7. Testing

Add or improve tests.

**Testing areas**:
- Unit tests
- Widget tests
- Integration tests
- Security tests
- Platform-specific tests

## 🚀 Getting Started

### Prerequisites

- Git
- Flutter 3.x or later
- Dart 3.x or later
- (For Workers) Node.js 18+ and npm
- (Optional) Code editor with Dart/Flutter support

### Setup Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/SelfErase.git
cd SelfErase

# Set up Flutter app
cd flutter_app
flutter pub get
flutter pub run build_runner build

# Run tests
flutter test

# Set up Cloudflare Workers (optional)
cd ../cloudflare_workers
npm install
npm test
```

### Running the App

```bash
cd flutter_app

# Check available devices
flutter devices

# Run on specific device
flutter run -d <device_id>

# Run in debug mode
flutter run --debug

# Run in release mode (for performance testing)
flutter run --release
```

## 📝 Contribution Process

### 1. Fork & Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/SelfErase.git
cd SelfErase

# Add upstream remote
git remote add upstream https://github.com/OWASP-BLT/SelfErase.git
```

### 2. Create a Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

**Branch naming conventions**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `security/` - Security improvements
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 3. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add comments where necessary
- Update documentation as needed
- Add tests for new functionality

### 4. Test Your Changes

```bash
# Flutter app tests
cd flutter_app
flutter analyze
flutter test
flutter test --coverage

# Cloudflare Workers tests
cd cloudflare_workers
npm run lint
npm test

# Manual testing
flutter run
# Test your changes thoroughly
```

### 5. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add support for new broker XYZ"
```

**Commit message format**:
```
<type>: <short description>

<optional longer description>

<optional footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build process or auxiliary tool changes
- `security`: Security improvements

### 6. Push & Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name
```

Then:
1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Fill out the PR template
4. Submit for review

## ✅ Code Quality Standards

### Code Style

**Dart/Flutter**:
- Follow [Effective Dart](https://dart.dev/guides/language/effective-dart)
- Run `dart format` before committing
- Use `flutter analyze` to catch issues
- Maximum line length: 80 characters (flexible for readability)

**TypeScript (Workers)**:
- Use ESLint configuration
- Follow TypeScript best practices
- Use Prettier for formatting
- Add JSDoc comments for public APIs

### Security Requirements

**All contributions must**:
- Not introduce security vulnerabilities
- Not transmit PII to external servers
- Maintain encryption for sensitive data
- Follow OWASP guidelines
- Pass security linting

**Before submitting**:
- Review [SECURITY.md](./SECURITY.md)
- Consider threat implications
- Test with security in mind
- Document security considerations

### Testing Requirements

**All code changes should include**:
- Unit tests for new functions
- Widget tests for UI changes
- Integration tests for workflows
- Test coverage > 80% for new code

**Test naming**:
```dart
test('should encrypt data with AES-256', () {
  // Test implementation
});
```

### Documentation Requirements

**All contributions should**:
- Update relevant documentation
- Add inline comments for complex logic
- Update API documentation if applicable
- Include examples for new features

## 🔍 Pull Request Guidelines

### PR Template

When creating a PR, include:

1. **Description**: What does this PR do?
2. **Motivation**: Why is this change needed?
3. **Testing**: How was it tested?
4. **Screenshots**: For UI changes
5. **Breaking Changes**: List any breaking changes
6. **Checklist**: Complete the checklist

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] No new warnings
- [ ] No security vulnerabilities introduced

### Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: Maintainers review your code
3. **Feedback**: Address any requested changes
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainer merges your PR

**Review timeline**: We aim to review PRs within 7 days.

## 🐛 Bug Reports

### Before Reporting

- Check if the bug is already reported
- Verify it's reproducible
- Test with the latest version
- Check documentation

### Bug Report Template

**Title**: Brief description of the issue

**Description**:
- What happened?
- What did you expect to happen?
- Steps to reproduce
- Screenshots/videos (if applicable)

**Environment**:
- OS and version
- Flutter version
- Device/emulator
- App version

**Additional Context**:
- Error messages
- Log output
- Related issues

## 💡 Feature Requests

### Before Requesting

- Check if it's already requested
- Review project roadmap
- Consider if it aligns with project goals
- Think about implementation

### Feature Request Template

**Title**: Brief description of feature

**Problem**: What problem does this solve?

**Proposed Solution**: How should it work?

**Alternatives**: What other approaches did you consider?

**Additional Context**: Screenshots, mockups, examples

## 🚫 What We Don't Accept

### Security-Breaking Changes

- PII transmission to external servers
- Weakened encryption
- Backdoors or compromised security
- Closed-source dependencies with privacy concerns

### Scope Creep

- Features that don't align with privacy mission
- Bloated dependencies
- Unnecessary third-party services
- Telemetry or tracking

### Poor Quality

- Untested code
- Code without documentation
- Code that breaks existing functionality
- Code that doesn't follow style guidelines

## 📄 Licensing

By contributing to SelfErase, you agree that your contributions will be licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

See [LICENSE](./LICENSE) for full license text.

### Contributor License Agreement

By submitting a pull request, you certify that:

1. You have the right to submit the work
2. You grant OWASP-BLT project the right to distribute your work under AGPL-3.0
3. You understand your contribution is public and recorded
4. You have not included any copyrighted material you don't have rights to

## 🌟 Recognition

### Contributors

All contributors are recognized in:
- GitHub contributors page
- Release notes (for significant contributions)
- Documentation credits

### Hall of Fame

Outstanding contributors may be featured in:
- Project README
- Website (when available)
- Conference presentations

## 💬 Communication

### Where to Ask Questions

- **General Questions**: [GitHub Discussions](https://github.com/OWASP-BLT/SelfErase/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/OWASP-BLT/SelfErase/issues)
- **Security Issues**: [Security Advisory](https://github.com/OWASP-BLT/SelfErase/security/advisories)
- **Pull Requests**: Comment on the PR

### Code of Conduct

Be respectful, inclusive, and professional:
- ✅ Respect diverse viewpoints
- ✅ Accept constructive criticism
- ✅ Focus on what's best for the project
- ✅ Show empathy to other community members
- ❌ Harassment or discriminatory language
- ❌ Personal attacks or trolling
- ❌ Spam or off-topic discussions

## 📚 Additional Resources

- [Architecture Documentation](./docs/architecture.md)
- [Broker Addition Guide](./docs/broker-guide.md)
- [API Reference](./docs/api.md)
- [Security Whitepaper](./SECURITY.md)
- [Flutter Documentation](https://flutter.dev/docs)
- [Dart Style Guide](https://dart.dev/guides/language/effective-dart)

## 🎉 Thank You!

Every contribution, no matter how small, helps make the internet a more private place.

**Together, we're giving people control over their personal data.**

---

*Questions? Open a [Discussion](https://github.com/OWASP-BLT/SelfErase/discussions) and we'll help you get started!*
