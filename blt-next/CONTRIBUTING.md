# Contributing to OWASP BLT-Next

Thank you for your interest in contributing to OWASP BLT! We welcome contributions from everyone. By participating in this project, you agree to abide by the [OWASP Code of Conduct](https://owasp.org/www-policy/operational/code-of-conduct).

## How Can I Contribute?

### Reporting Bugs
Before creating bug reports, please check the [existing issues](https://github.com/OWASP-BLT/BLT-Next/issues) to avoid duplicates. When creating a bug report, include:
- Clear title and description.
- Steps to reproduce the issue.
- Expected behavior vs actual behavior.
- Screenshots and environment details (browser, OS) if applicable.

### Suggesting Enhancements
Enhancement suggestions are tracked as GitHub issues. Provide a clear title, a detailed description of the functionality, and explain why it would be useful.

## Getting Started

### 1. Fork and Clone
Fork the [BLT-Next](https://github.com/OWASP-BLT/BLT-Next) repository and clone it locally:
```bash
git clone https://github.com/your-username/BLT-Next.git
cd BLT-Next
```

### 2. Local Setup (Recommended)
1. **Install Node.js** (v18 or later) and **Python**.
2. **Install Dependencies**: `npm install`
3. **Start Development Server**: `npm run dev`
   - This starts a unified server at `http://localhost:8787` serving both the frontend and the backend API.

## Development Workflow

1. Create a branch: `git checkout -b feature/my-feature`
2. Make changes and test locally.
3. Commit with clear messages: `git commit -m "feat: add user profile page"`
4. Push and open a Pull Request.

## Coding Guidelines

### Frontend (HTML/CSS/JS)
- Use **semantic HTML5** and ensure accessibility.
- Use **CSS variables** for theming and follow mobile-first principles.
- Use **ES6+** JavaScript, write modular code, and handle errors gracefully.

### Backend (Python Workers)
- Follow **PEP 8** style guide.
- Use **type hints** and write docstrings for functions.
- Keep functions small and focused on a single task.

## Project Structure

- `src/index.html`: Main landing page.
- `src/assets/`: CSS and JavaScript assets.
- `src/pages/`: Additional static HTML pages.
- `workers/`: Cloudflare Worker (Python) backend logic.
- `docs/`: Expanded documentation.

## License
By contributing, you agree that your contributions will be licensed under the GNU Affero General Public License v3.0.

---
Thank you for helping make the internet more secure! 🚀
