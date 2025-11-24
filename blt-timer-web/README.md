# Fresh Time Tracker

> Privacy-focused time tracking system for developers with GitHub integration and local LLM analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-orange)](https://workers.cloudflare.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue)](https://www.typescriptlang.org/)

## Overview

Fresh is a comprehensive time tracking system designed specifically for developers who want to monitor their productivity without compromising privacy. It tracks your work across multiple sources while ensuring all sensitive data processing happens locally on your machine.

## ✨ Features

### 🔒 Privacy First
- **Local LLM Processing**: All screenshot analysis happens on your machine
- **No 3rd Party Upload**: Screenshots and sensitive data never leave your device  
- **Encrypted Storage**: All data encrypted in Cloudflare KV
- **User Control**: You decide what to track and when

### 📊 Comprehensive Tracking
- **GitHub Integration**: Auto-track commits, PRs, issues, and reviews
- **Activity Monitoring**: Track keyboard and mouse activity (privacy-focused)
- **Agent Prompts**: Monitor AI assistant usage (Copilot, ChatGPT, etc.)
- **Screenshot Analysis**: Optional local analysis for productivity insights

### ⚡ Modern Architecture
- **Cloudflare Workers**: Global edge deployment for low latency
- **Durable Objects**: Real-time session management with WebSocket support
- **KV Storage**: Persistent, distributed data storage
- **TypeScript**: Type-safe codebase

## 🚀 Quick Start

### Prerequisites
```bash
node >= 18.0.0
npm >= 9.0.0
```

### Installation

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/Fresh.git
cd Fresh

# Install dependencies
npm install

# Start development server
npm run dev
```

### Flutter Desktop App (Linux)

A native Flutter desktop application is available for real-time activity tracking on Linux:

```bash
cd flutter_tracker
./run.sh
```

See [flutter_tracker/SETUP.md](flutter_tracker/SETUP.md) for detailed setup instructions.

**Features:**
- Real-time keyboard and mouse activity tracking
- Live scrolling charts updated every second
- Daily activity summaries
- Compact window design
- Privacy-focused (no keystroke/position logging)

### Basic Usage

```typescript
import TimeTrackerClient from './client/tracker-client';

const tracker = new TimeTrackerClient({
  apiUrl: 'http://localhost:8787',
  userId: 'your-user-id',
  projectId: 'your-project-id',
  enableKeyboard: true,
  enableMouse: true,
});

// Start tracking
await tracker.startSession();

// Your work happens here...

// End tracking
await tracker.endSession();
```

## 📚 Documentation

- [Complete Documentation](docs/README.md)
- [API Reference](docs/README.md#api-endpoints)
- [Privacy & Security](docs/README.md#privacy-guarantees)
- [Client Usage](docs/README.md#client-usage)
- [GitHub Integration](examples/github-integration.ts)
- [CLI Tool](examples/cli-tracker.ts)

## 🏗️ Architecture

```
┌─────────────────┐
│  Client-Side    │  ← User's Machine (Browser/CLI)
│  Tracker        │     - Activity monitoring
└────────┬────────┘     - Local LLM analysis
         │
         │ HTTPS/WebSocket
         │
┌────────▼────────┐
│  Cloudflare     │  ← Edge Network
│  Worker         │     - API endpoints
│  + Durable      │     - Session management
│    Objects      │     - Real-time updates
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│  KV   │ │ Durable │
│ Store │ │ Objects │
└───────┘ └─────────┘
```

## 🔐 Privacy Guarantees

### What We Track ✅
- Activity patterns (counts only, no content)
- GitHub events (public metadata)
- Agent prompt metadata (lengths, names)
- High-level activity classification

### What We DON'T Track ❌
- Actual keystrokes or text content
- Screenshot images (only local analysis results)
- Specific code content
- Personal identifiable information

### Screenshot Analysis
When enabled (requires explicit consent):
1. Screenshot captured on your device
2. Analyzed locally with your own LLM
3. Screenshot immediately deleted
4. Only generic classification sent to server (e.g., "coding", "debugging")

## 🛠️ Development

### Project Structure
```
Fresh/
├── src/
│   ├── api/              # API routes
│   ├── modules/          # Core tracking modules
│   ├── types/            # TypeScript types
│   ├── durable-objects/  # Durable Objects
│   └── utils/            # Utilities
├── client/               # Client-side tracker
├── examples/             # Example implementations
├── docs/                 # Documentation
└── tests/                # Tests
```

### Available Scripts

```bash
# Development
npm run dev              # Start dev server
npm run type-check       # Type checking

# Deployment
npm run deploy           # Deploy to Cloudflare

# Testing
npm test                 # Run tests
```

## 📦 Deployment

### Deploy to Cloudflare Workers

```bash
# Login to Cloudflare
npx wrangler login

# Create KV namespaces
npx wrangler kv:namespace create TIME_TRACKING_DATA
npx wrangler kv:namespace create ACTIVITY_DATA

# Update wrangler.toml with KV namespace IDs

# Deploy
npm run deploy
```

## 🔧 Configuration

### Environment Variables

Create `.dev.vars` for local development:

```env
GITHUB_CLIENT_ID=your-github-app-client-id
GITHUB_CLIENT_SECRET=your-github-app-secret
ENCRYPTION_KEY=your-secure-encryption-key
LOCAL_LLM_ENDPOINT=http://localhost:11434
```

### Local LLM Setup

For screenshot analysis:

```bash
# Option 1: Ollama
curl https://ollama.ai/install.sh | sh
ollama pull llava
ollama serve

# Option 2: LocalAI (Docker)
docker run -p 8080:8080 quay.io/go-skynet/local-ai:latest
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Cloudflare Workers](https://workers.cloudflare.com/)
- Powered by [Hono](https://hono.dev/)
- Inspired by privacy-focused productivity tools

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/OWASP-BLT/Fresh/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OWASP-BLT/Fresh/discussions)
- **Email**: support@example.com

## 🗺️ Roadmap

- [ ] Mobile app support (iOS/Android)
- [ ] VS Code extension
- [ ] Browser extension (Chrome/Firefox)
- [ ] Jira/Linear integration
- [ ] Team dashboards
- [ ] Advanced analytics
- [ ] Export functionality (CSV/JSON)
- [ ] Custom reporting

---

Made with ❤️ by the OWASP-BLT community