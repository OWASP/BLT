# Contributing to GSoC Student Dashboard

Thank you for your interest in improving the GSoC Student Dashboard! This project aims to help GSoC students showcase their journey, and we welcome contributions from everyone.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug:

1. **Check existing issues** to see if it's already reported
2. **Open a new issue** with:
   - Clear title describing the problem
   - Steps to reproduce the bug
   - Expected vs. actual behavior
   - Screenshots (if applicable)
   - Browser/environment details

### Suggesting Features

We love new ideas! To suggest a feature:

1. **Check existing issues** to avoid duplicates
2. **Open an issue** with:
   - Clear description of the feature
   - Use case explaining why it's needed
   - Proposed implementation (optional)
   - Mockups or examples (if applicable)

### Code Contributions

#### Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/MY-GSOC-TOOL.git
   cd MY-GSOC-TOOL
   ```

3. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### Making Changes

1. **Keep changes focused**: One feature or fix per pull request
2. **Follow the existing code style**:
   - Use meaningful variable names
   - Add comments for complex logic
   - Keep functions small and focused
   - Maintain consistent indentation

3. **Test your changes**:
   - Test locally with a simple HTTP server
   - Check responsiveness on different screen sizes
   - Validate JSON files
   - Test in multiple browsers if possible

4. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Update SETUP.md for setup process changes
   - Add inline comments for complex code

#### Submitting Pull Requests

1. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add: brief description of your changes"
   ```

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**:
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template with:
     - Description of changes
     - Related issue number (if applicable)
     - Screenshots (for UI changes)
     - Testing done

4. **Respond to feedback**:
   - Be open to suggestions
   - Make requested changes promptly
   - Ask questions if anything is unclear

## 📋 Development Guidelines

### Code Style

#### HTML
- Use semantic HTML5 elements
- Maintain proper indentation (2 spaces)
- Add comments for major sections
- Use descriptive IDs and classes

#### CSS
- Follow the existing naming convention
- Use CSS variables for theme values
- Keep selectors specific but not overly complex
- Group related styles together
- Comment major sections

#### JavaScript
- Use modern ES6+ syntax
- Keep functions pure when possible
- Handle errors gracefully
- Add JSDoc comments for functions
- Use async/await for promises

### File Organization

```
MY-GSOC-TOOL/
├── .github/
│   └── workflows/       # GitHub Actions workflows
├── data/                # JSON data files
├── index.html          # Main HTML file
├── styles.css          # All styles
├── dashboard.js        # All JavaScript
├── config.json         # Configuration
└── docs/               # Documentation
```

### Commit Message Format

Use clear, descriptive commit messages:

```
Add: New feature description
Fix: Bug description
Update: What was updated
Refactor: What was refactored
Docs: Documentation changes
Style: Code style changes
```

## 🎯 Areas for Contribution

We especially welcome contributions in these areas:

### High Priority
- [ ] Improved error handling and user feedback
- [ ] Support for more platforms (GitLab, Bitbucket)
- [ ] Dark mode theme
- [ ] Print-friendly stylesheet
- [ ] Export to PDF functionality

### Medium Priority
- [ ] More data visualization (charts, graphs)
- [ ] Timeline visualization improvements
- [ ] Mobile app (PWA)
- [ ] Internationalization (i18n)
- [ ] Accessibility improvements

### Good First Issues
- [ ] Additional icon options
- [ ] Color theme presets
- [ ] Social media preview cards (Open Graph)
- [ ] More example configurations
- [ ] Tutorial videos or GIFs

## 🧪 Testing

Before submitting a PR, please test:

1. **Local Testing**:
   ```bash
   python3 -m http.server 8080
   # Visit http://localhost:8080
   ```

2. **JSON Validation**:
   - All JSON files should be valid
   - Use https://jsonlint.com for validation

3. **Cross-Browser Testing** (if possible):
   - Chrome/Edge
   - Firefox
   - Safari

4. **Responsive Testing**:
   - Desktop (1920x1080)
   - Tablet (768x1024)
   - Mobile (375x667)

## 📖 Documentation Standards

When adding or updating documentation:

1. **Be clear and concise**: Use simple language
2. **Include examples**: Show, don't just tell
3. **Add screenshots**: For UI-related docs
4. **Keep formatting consistent**: Follow existing style
5. **Update table of contents**: If adding major sections

## 🔒 Security

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email the maintainers directly
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## 🏗️ Architecture Overview

### Data Flow

```
config.json → dashboard.js → Renders to HTML
     ↓
data/*.json → dashboard.js → Updates sections
     ↓
GitHub API → GitHub Actions → data/github-contributions.json
```

### Key Components

1. **Configuration** (`config.json`): User's personal information
2. **Data Files** (`data/`): Dynamic content that changes over time
3. **Dashboard Logic** (`dashboard.js`): Loads and renders all data
4. **Styling** (`styles.css`): All visual presentation
5. **Automation** (`.github/workflows/`): Automatic updates

## 🎨 Design Guidelines

When making UI changes:

1. **Maintain consistency**: Follow the existing design language
2. **Consider accessibility**: Ensure good color contrast, screen reader support
3. **Think responsive**: Test on different screen sizes
4. **Keep it simple**: Avoid cluttering the interface
5. **Use existing components**: Extend rather than recreate

### Color Palette

```css
Primary:   #4285f4 (Blue)
Secondary: #34a853 (Green)
Accent:    #fbbc04 (Yellow)
Danger:    #ea4335 (Red)
```

## 📝 Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Code follows the project's style guidelines
- [ ] Changes have been tested locally
- [ ] Documentation is updated (if needed)
- [ ] Commit messages are clear and descriptive
- [ ] No unnecessary files are included
- [ ] JSON files are valid
- [ ] The dashboard still works after your changes
- [ ] You've added yourself to the contributors list (if first contribution)

## 🌟 Recognition

Contributors will be:
- Listed in the project's contributors section
- Mentioned in release notes
- Thanked in the README

## 📞 Questions?

- Open a discussion for general questions
- Open an issue for bug reports or feature requests
- Check existing documentation first

## 💚 Code of Conduct

This project follows a Code of Conduct. By participating, you agree to:

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

Thank you for helping make the GSoC Student Dashboard better! 🎉

---

**Happy Contributing!** 🚀
