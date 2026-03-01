# 🥓 BLT-Rewards (BACON)

**Blockchain Assisted Contribution Network**

Incentivize Open Source Contributions with Bitcoin & Solana Rewards

## 🚀 Overview

BACON is a cutting-edge blockchain-based token system designed to incentivize engagement and contributions within open-source ecosystems. By integrating with Bitcoin (via Runes protocol) and Solana blockchains, BACON introduces a transparent, secure, and gamified environment that rewards developers and contributors for their efforts.

## 📋 Project Structure

This is a Cloudflare Worker-based application with the following structure:

```
BLT-Rewards/
├── .env.example         # Environment variables template
├── LICENSE              # License file
├── package.json         # Node.js dependencies
├── README.md            # This file
├── setup_bacon_node.sh  # Setup script for BACON node
├── wrangler.toml        # Cloudflare Worker configuration
├── public/              # Static HTML pages and assets
│   ├── static/          # Static assets
│   │   └── images/      # Image files
│   │       └── logo.png # BACON logo
│   ├── _config.yml      # Jekyll configuration
│   ├── README.md        # Public documentation readme
│   ├── index.html       # Main landing page
│   ├── getting-started.html      # Getting started guide
│   ├── api-reference.html        # API documentation
│   ├── bitcoin-integration.html  # Bitcoin integration guide
│   ├── solana-integration.html   # Solana integration guide
│   ├── github-actions.html       # GitHub Actions guide
│   ├── security.html             # Security documentation
│   ├── styles.css       # Tailwind CSS styles
│   └── script.js        # Client-side JavaScript
├── src/                 # Python worker source code
│   └── index.py         # Main Cloudflare Worker entry point
└── ord-server/          # Bitcoin Ordinals/Runes server
    ├── .env.example     # Ord server environment variables
    ├── example-split.yaml        # Example split configuration
    ├── ord-api.py                # Ord API server
    ├── ord-flask.service         # Flask service configuration
    └── requirements.txt          # Python dependencies
```

## 🛠️ Development

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Cloudflare account
- Wrangler CLI

### Architecture Notes

This project uses **Cloudflare Workers with Python runtime** for dynamic API endpoints and **Cloudflare's built-in asset serving** for static files:

- **Static Assets**: All files in `public/` are automatically served by Cloudflare's asset handling (configured in `wrangler.toml`)
- **Python Worker**: Handles API routes and redirects - does NOT use file I/O operations
- **No File Reading**: Cloudflare Workers runtime doesn't support traditional file operations like `open()`. Static files are served directly by Cloudflare.

### Setup

1. Clone the repository:
```bash
git clone https://github.com/OWASP-BLT/BLT-Rewards.git
cd BLT-Rewards
```

2. Install dependencies:
```bash
npm install
```

3. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start development server:
```bash
npm run dev
```

### Available Scripts

- `npm run dev` - Start development server
- `npm run deploy` - Deploy to production
- `npm run deploy:dev` - Deploy to development environment

## 🌐 Deployment

Deploy to Cloudflare Workers:

```bash
npm run deploy
```

For development environment:
```bash
npm run deploy:dev
```

## ✨ Features

- ✨ Multi-Chain Support (Bitcoin & Solana)
- 🔒 Secure & Transparent
- 🎮 Gamification
- 🤖 GitHub Actions Integration
- ⚡ Serverless Architecture (Cloudflare Workers)

## 📚 Documentation

The documentation is available as static HTML pages in the `public/` directory:

- [**Getting Started**](public/getting-started.html) - Installation and setup guide
- [**Bitcoin Integration**](public/bitcoin-integration.html) - Bitcoin & Runes protocol integration
- [**Solana Integration**](public/solana-integration.html) - Solana blockchain integration
- [**GitHub Actions**](public/github-actions.html) - CI/CD automation setup
- [**API Reference**](public/api-reference.html) - Complete API documentation
- [**Security**](public/security.html) - Security best practices and considerations

Visit the [main documentation site](public/index.html) for a complete overview.

## 🔐 Security

For security concerns and best practices, please refer to our [Security Documentation](public/security.html) or contact the OWASP BLT team.

**Important:** Never commit private keys or sensitive credentials to the repository. Use environment variables and GitHub Secrets for sensitive data.

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🔗 Links

- [OWASP BLT Project](https://github.com/OWASP-BLT)
- [BLT Main Repository](https://github.com/OWASP-BLT/BLT)
- [Documentation Site](public/index.html)
- [GitHub Repository](https://github.com/OWASP-BLT/BLT-Rewards)

---

Made with ❤️ by the OWASP BLT Team
