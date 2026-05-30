# Contributing to BLT NetGuardian Client

Thank you for your interest in contributing to the BLT NetGuardian Client! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature or bugfix
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Flutter SDK 3.0.0 or later
- Dart SDK 3.0.0 or later
- Git

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/BLT-NetGuardian-Client.git
cd BLT-NetGuardian-Client
flutter pub get
```

## Code Style

This project follows the official Dart style guide and uses `flutter_lints` for linting.

### Run the linter

```bash
flutter analyze
```

### Format your code

```bash
dart format .
```

## Testing

### Run tests

```bash
flutter test
```

### Write tests

- Add unit tests for new models and services
- Add widget tests for new UI components
- Ensure test coverage for critical paths

## Project Structure

```
lib/
├── models/       # Data models
├── services/     # Business logic and API layer
├── providers/    # State management
├── screens/      # UI screens
├── widgets/      # Reusable UI components
└── main.dart     # App entry point
```

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the documentation with any new APIs or features
3. Add tests for your changes
4. Ensure all tests pass
5. Ensure code is properly formatted and linted
6. Submit your pull request with a clear description

## Commit Message Guidelines

- Use clear and descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Keep the first line under 72 characters
- Add detailed description if needed

Examples:
```
Add task deduplication feature
Fix API error handling in result manager
Update README with installation instructions
```

## Feature Requests and Bug Reports

Please use GitHub Issues to report bugs or request features.

### Bug Reports

Include:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Flutter/Dart version
- Platform (iOS, Android, Web, Desktop)

### Feature Requests

Include:
- Description of the feature
- Use case
- Proposed implementation (if any)

## Code of Conduct

This project follows the OWASP Code of Conduct. Please be respectful and professional in all interactions.

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue or contact the maintainers if you have any questions.

Thank you for contributing!