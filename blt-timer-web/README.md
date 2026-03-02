# Fresh Time Tracker

> Privacy-focused time tracking system for developers with GitHub integration and local LLM analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-orange)](https://workers.cloudflare.com/)
[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)

## Overview

Fresh is a comprehensive time tracking system designed specifically for developers who want to monitor their productivity without compromising privacy. It tracks your work across multiple sources while ensuring all sensitive data processing happens locally on your machine.

The back-end runs as a **Cloudflare Python Worker** – no Node.js required.

## ✨ Features

### 🔒 Privacy First
- **Local LLM Processing**: All screenshot analysis happens on your machine
- **No 3rd Party Upload**: Screenshots and sensitive data never leave your device  
- **Encrypted Storage**: All data stored in Cloudflare D1
- **User Control**: You decide what to track and when

### 📊 Comprehensive Tracking
- **GitHub Integration**: Auto-track commits, PRs, issues, and reviews
- **Activity Monitoring**: Track keyboard and mouse activity (privacy-focused)
- **Agent Prompts**: Monitor AI assistant usage (Copilot, ChatGPT, etc.)
- **Screenshot Analysis**: Optional local analysis for productivity insights

### ⚡ Modern Architecture
- **Cloudflare Python Workers**: Global edge deployment for low latency
- **D1 Database**: Persistent, relational SQL data storage
- **Pure Python**: No Node.js or npm required

## 🚀 Quick Start

### Prerequisites
```
python >= 3.11   (only needed for local examples / tests)
wrangler >= 3    (npm install -g wrangler  OR  npx wrangler)
```

### Deploy

```bash
# Login to Cloudflare
npx wrangler login

# Create D1 database (copy the database_id into wrangler.toml)
npx wrangler d1 create time_tracker

# Apply the database schema
npx wrangler d1 migrations apply DB

# Deploy the Python Worker
npx wrangler deploy
```

### Local development

```bash
npx wrangler dev
```

### Basic Usage (Python client)

```python
import urllib.request, json

API_URL = "http://localhost:8787"
USER_ID = "your-user-id"

# Start a session
req = urllib.request.Request(
    f"{API_URL}/api/sessions/start",
    data=json.dumps({"projectId": "my-project"}).encode(),
    headers={"Content-Type": "application/json", "X-User-ID": USER_ID},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())
session_id = data["session"]["id"]
print("Session started:", session_id)
```

## 📚 Documentation

- [Complete Documentation](docs/README.md)
- [API Reference](docs/README.md#api-endpoints)
- [Privacy & Security](docs/README.md#privacy-guarantees)
- [GitHub Integration](examples/github_integration.py)
- [CLI Tool](examples/cli_tracker.py)

## 🏗️ Architecture

```
┌─────────────────┐
│  Client-Side    │  ← User's Machine (Browser/CLI/Python script)
│  Tracker        │     - Activity monitoring
└────────┬────────┘     - Local LLM analysis
         │
         │ HTTPS
         │
┌────────▼────────┐
│  Cloudflare     │  ← Edge Network (Python Worker)
│  Python Worker  │     - API endpoints
│                 │     - Session management
└────────┬────────┘
         │
┌────────▼────────┐
│  D1 Database    │  ← Cloudflare D1 (SQL)
│  (SQL)          │     - sessions table
│                 │     - activities table
└─────────────────┘
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
BLT-Timer-Web/
├── src/
│   └── worker.py         # Cloudflare Python Worker (main entry point)
├── client/               # (browser dashboard)
├── examples/             # Python example scripts
│   ├── cli_tracker.py
│   └── github_integration.py
├── docs/                 # Documentation
├── public/               # Static HTML dashboard
└── wrangler.toml         # Cloudflare Worker configuration
```

### Available Commands

```bash
# Development server
npx wrangler dev

# Deploy to Cloudflare
npx wrangler deploy

# Type-check / lint Python
python -m py_compile src/worker.py
```

## 📦 Deployment

### Deploy to Cloudflare Workers

```bash
# Login to Cloudflare
npx wrangler login

# Create D1 database (copy the database_id into wrangler.toml)
npx wrangler d1 create time_tracker

# Apply the database schema
npx wrangler d1 migrations apply DB

# Deploy
npx wrangler deploy
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
- Inspired by privacy-focused productivity tools

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/OWASP-BLT/BLT-Timer-Web/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OWASP-BLT/BLT-Timer-Web/discussions)

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