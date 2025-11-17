# Contributing to OWASP-Wich

Thank you for your interest in contributing to OWASP-Wich! This document provides guidelines for contributing to this project.

## Code of Conduct

This project follows the [OWASP Code of Conduct](https://owasp.org/www-policy/operational/code-of-conduct). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/OWASP-BLT/OWASP-Wich/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version)

### Suggesting Enhancements

1. Check if the enhancement has been suggested
2. Create an issue describing:
   - The enhancement and its benefits
   - Possible implementation approach
   - Any alternatives considered

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Add or update tests as needed
5. Ensure tests pass
6. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
7. Push to the branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request

#### PR Guidelines

- Follow PEP 8 style guide for Python code
- Include docstrings for new functions and classes
- Update README.md if adding new features
- Add tests for new functionality
- Keep commits focused and atomic
- Write clear commit messages

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/OWASP-Wich.git
cd OWASP-Wich

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Test the CLI
python compliance_checker.py https://github.com/OWASP/owasp-mastg
```

### Adding New Compliance Checks

When adding new compliance checks:

1. Add the check to the appropriate category method in `compliance_checker.py`
2. Use the `_add_check()` method with:
   - Category name
   - Check name
   - Pass/fail boolean
   - Points value
   - Optional details
3. Update README.md with the new check
4. Add test cases

Example:
```python
def _check_new_category(self, repo) -> None:
    category = "New Category"
    
    # Your check logic
    has_feature = self._check_file_exists(repo, "FEATURE.md")
    self._add_check(category, "Feature file present", has_feature, 1, 
                   "Checks for FEATURE.md file")
```

## Testing

All contributions should include appropriate tests. Run tests with:

```bash
python -m pytest tests/ -v
```

## Documentation

- Keep README.md up to date
- Add docstrings to all public functions
- Update examples if changing CLI behavior

## Questions?

Feel free to:
- Open a discussion on GitHub
- Ask in OWASP Slack channels
- Contact the OWASP BLT team

Thank you for contributing! 🎉
