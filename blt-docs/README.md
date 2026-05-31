# OWASP BLT Documentation

Official documentation for the OWASP Bug Logging Tool (BLT) project. This repository contains comprehensive documentation for users and developers.

## 🌐 Live Documentation

Visit the live documentation at: [https://docs.owaspblt.org/](https://docs.owaspblt.org/)

## 📚 Documentation Structure

The documentation is organized into the following sections:

- **Getting Started**: Setup guides and project information
- **Features**: Overview of BLT features and capabilities
- **User Guide**: Comprehensive guides for using BLT
  - Authentication and user management
  - Bug reporting and tracking
  - Leaderboards and statistics
  - Company management and bug hunts
  - Community features
  - Trademark search
- **Developer Guide**: Technical documentation for contributors
  - Contributing guidelines
  - Bot setup instructions
  - Development environment setup

## 🛠️ Local Development

### Prerequisites

- Python 3.x
- pip

### Setup

1. Clone this repository:
   ```bash
   git clone https://gitlab.com/owasp-blt/blt-docs.git
   cd blt-docs
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Serve the documentation locally:
   ```bash
   mkdocs serve
   ```

4. Open your browser and navigate to `http://127.0.0.1:8000/`

### Building

To build the static site:

```bash
mkdocs build
```

The built site will be in the `site/` directory.

## 🚀 Deployment

Documentation is built by GitLab CI and deployed to Cloudflare Workers when
changes are pushed to the default branch. The pipeline is defined in
`.gitlab-ci.yml`.

### Cloudflare Workers Setup

Create a Cloudflare API token with permission to edit Workers, then add these
variables in GitLab under **Settings** → **CI/CD** → **Variables**:

- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID for the deployment
- `CLOUDFLARE_API_TOKEN`: Cloudflare API token, stored as a masked and hidden variable

The generated MkDocs site is static, so `wrangler.toml` deploys the `site/`
directory directly with Workers Static Assets and connects the Worker to
`docs.owaspblt.org`. No Python Worker function is needed.

Before the first deployment, remove any existing CNAME record for
`docs.owaspblt.org` so Cloudflare can create the custom-domain DNS record and
certificate.

## 📝 Contributing

We welcome contributions to improve the documentation! To contribute:

1. Fork this repository
2. Create a new branch for your changes
3. Make your changes to the markdown files in the `docs/` directory
4. Test your changes locally with `mkdocs serve`
5. Submit a pull request

### Documentation Guidelines

- Use clear, concise language
- Include code examples where appropriate
- Add screenshots for UI-related documentation
- Follow the existing structure and formatting
- Test your changes locally before submitting

## 🔧 Technology Stack

- **Framework**: [MkDocs](https://www.mkdocs.org/)
- **Theme**: [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- **Hosting**: Cloudflare Workers Static Assets
- **CI/CD**: GitLab CI/CD

## 📖 Documentation Source

The documentation content is sourced from the main [OWASP-BLT/BLT](https://github.com/OWASP-BLT/BLT) repository:

- Technical docs from `docs/` directory
- User guides from `website/documents/` directory

## 📄 License

This documentation is part of the OWASP BLT project and follows the same licensing terms.

## 🔗 Related Links

- [OWASP BLT Main Repository](https://github.com/OWASP-BLT/BLT)
- [OWASP BLT Website](https://owaspblt.org)
- [OWASP Slack](https://owasp.org/slack/invite)

## 💬 Support

For questions or issues related to the documentation:

- Open an issue in this repository
- Join the OWASP Slack and visit the BLT channel
- Refer to the main BLT repository for project-related questions
