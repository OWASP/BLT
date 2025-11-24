# Contributing to BLT-CVE

Thank you for your interest in contributing to the BLT-CVE decentralized CVE database! This document provides guidelines for contributing to the project.

## Code of Conduct

This project follows the OWASP Code of Conduct. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

If you find a bug:

1. Check if the issue already exists in [GitHub Issues](https://github.com/OWASP-BLT/BLT-CVE/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version)
   - Relevant logs or screenshots

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

1. Check existing issues and PRs
2. Create an issue describing:
   - The enhancement
   - Use case and benefits
   - Potential implementation approach
   - Any breaking changes

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/BLT-CVE.git
   cd BLT-CVE
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the coding style
   - Add tests for new functionality
   - Update documentation

4. **Test your changes**
   ```bash
   python test_system.py
   python demo.py
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Describe your changes

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

Example:

```python
def fetch_cve_data(cve_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch CVE data from the database.
    
    Args:
        cve_id: CVE identifier (e.g., CVE-2023-12345)
    
    Returns:
        CVE data dictionary or None if not found
    """
    # Implementation
    pass
```

### Testing

- Write tests for all new features
- Ensure all tests pass before submitting PR
- Aim for high code coverage
- Include both positive and negative test cases

```python
def test_new_feature(self):
    """Test description."""
    # Arrange
    input_data = {...}
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    self.assertEqual(result, expected_value)
```

### Documentation

Update documentation for:

- New features
- Changed behavior
- New API endpoints
- Configuration options

Files to update:
- `README.md` - Overview and quick start
- `ARCHITECTURE.md` - Technical details
- `QUICKSTART.md` - Usage examples
- API endpoint docstrings

### Commit Messages

Write clear commit messages:

```
feat: Add search functionality for CVEs

- Implement search by CVE ID
- Add regex pattern matching
- Update API documentation
```

Prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `perf:` - Performance improvement
- `chore:` - Maintenance

## Areas for Contribution

### High Priority

1. **Web Interface**
   - Create web UI for the API
   - CVE browsing interface
   - User reporting form

2. **Enhanced Search**
   - Full-text search
   - Filter by date, severity, vendor
   - Advanced query syntax

3. **Data Sources**
   - Add more CVE sources
   - Implement data reconciliation
   - Source priority/trust system

4. **Testing**
   - Increase test coverage
   - Integration tests
   - Performance tests

### Medium Priority

1. **Analytics**
   - CVE statistics dashboard
   - Trend analysis
   - Severity distribution

2. **Export/Import**
   - Export to CSV/JSON/XML
   - Import from other formats
   - Bulk operations

3. **Notifications**
   - Email alerts for new CVEs
   - Webhook support
   - RSS feed

4. **Documentation**
   - Video tutorials
   - API client examples
   - Architecture diagrams

### Future Ideas

1. **Distributed Nodes**
   - P2P network implementation
   - Node discovery
   - Consensus mechanism

2. **Smart Contracts**
   - CVE verification logic
   - Reputation system
   - Automated validation

3. **Mobile App**
   - iOS/Android clients
   - Push notifications
   - Offline support

4. **Integrations**
   - Slack/Discord bots
   - CI/CD plugins
   - Security scanner integration

## Getting Help

- **Questions**: Create a GitHub issue with "Question" label
- **Discussions**: Use GitHub Discussions
- **OWASP BLT**: Join the OWASP BLT community

## Recognition

Contributors will be:
- Listed in the README
- Mentioned in release notes
- Recognized in the OWASP BLT project

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## Development Setup

```bash
# Clone repository
git clone https://github.com/OWASP-BLT/BLT-CVE.git
cd BLT-CVE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_system.py

# Run demo
python demo.py

# Start server
python app.py
```

## Review Process

1. Automated tests run on all PRs
2. Code review by maintainers
3. Discussion of changes if needed
4. Approval and merge

Typical timeline: 3-7 days for review

## Questions?

Feel free to reach out:
- Create an issue
- Join OWASP BLT community
- Email maintainers

Thank you for contributing to BLT-CVE! 🎉
