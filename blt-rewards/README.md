# 🥓 BLT-Rewards (BACON)

**Blockchain Assisted Contribution Network**

Incentivize Open Source Contributions with Bitcoin & Solana Rewards

## 🚀 Overview

BACON is a cutting-edge blockchain-based token system designed to incentivize engagement and contributions within open-source ecosystems. By integrating with Bitcoin (via Runes protocol) and Solana blockchains, BACON introduces a transparent, secure, and gamified environment that rewards developers and contributors for their efforts.

## 📋 Project Structure

This is a Cloudflare Worker-based application with the following structure:

```
BLT-Rewards/
├── public/              # Static HTML pages and assets
│   ├── index.html       # Main landing page
│   ├── styles.css       # Styles
│   ├── script.js        # Client-side JavaScript
│   └── *.html           # Other static pages
├── src/                 # Python worker source code
│   └── index.py         # Main entry point
├── ord-server/          # Bitcoin Ordinals/Runes server
│   └── ...             # Ord server files
├── wrangler.toml        # Cloudflare Worker configuration
├── package.json         # Node.js dependencies
├── .env.example         # Environment variables template
└── README.md           # This file
```

## 🛠️ Development

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Cloudflare account
- Wrangler CLI

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

## 🔗 Features

- ✨ Multi-Chain Support (Bitcoin & Solana)
- 🔒 Secure & Transparent
- 🎮 Gamification
- 🤖 GitHub Actions Integration
- ⚡ Serverless Architecture (Cloudflare Workers)

## 📚 Documentation

Visit the [public documentation](public/index.html) to learn more about:
- Getting started with BACON
- Bitcoin integration (Runes protocol)
- Solana integration
- GitHub Actions setup
- API reference
- Security considerations

## 🔐 Security

For security concerns, please refer to [security.html](public/security.html) or contact the OWASP BLT team.

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🔗 Links

- [OWASP BLT](https://github.com/OWASP-BLT)
- [Documentation](public/index.html)
- [GitHub Repository](https://github.com/OWASP-BLT/BLT-Rewards)

---

Made with ❤️ by the OWASP BLT Team
