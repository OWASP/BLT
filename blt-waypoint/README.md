# OWASP BLT Organization Dashboard

A live interactive dashboard for exploring all OWASP-BLT repositories and their real-time statistics.

**Live Demo:** [github.owaspblt.org](http://github.owaspblt.org/)

---

## About OWASP BLT

**OWASP BLT (Bug Logging Tool)** is a community-driven OWASP Foundation project that develops open-source tools for structured vulnerability reporting, bug tracking, security automation, and contributor engagement. 

The BLT ecosystem includes:
- Core platform for bug discovery and reporting
- REST API for integration
- Mobile app (Flutter)
- Browser extension for Chrome
- Slack bot for team collaboration
- Various security and automation tools

All projects are developed transparently under OWASP governance with AGPL-3.0 licensing.

---

## ✨ Features

- **Real-Time Search** - Search repositories by name and description
- **Advanced Sorting** - Sort by stars, forks, issues, activity, and more
- **Smart Filtering** - Filter by programming language and topics
- **Dual Views** - Switch between table and card layouts
- **Dark Mode** - Full dark mode support
- **Responsive Design** - Works on all devices
- **Smart Preferences** - Remembers your settings

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                     GitHub API                       │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│            data.json (Generated Data)                │
└────────────────────────┬─────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐   ┌──────────┐   ┌────────────┐
    │index.html   │script.js │   │styles.css  │
    └─────────┘   └──────────┘   └────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
         ┌──────────────────────────────┐
         │   Interactive Dashboard      │
         │  (Table/Card Views, Search,  │
         │   Sort, Filter, Dark Mode)   │
         └──────────────────────────────┘
```

### Tech Stack
- **Frontend:** HTML5, CSS3, JavaScript
- **Styling:** Tailwind CSS
- **Data:** JSON-based repository metadata
- **Hosting:** GitHub Pages

### How It Works
1. Data is generated from GitHub API via automation
2. Repository statistics are compiled into `data.json`
3. JavaScript dynamically renders the dashboard
4. Users can search, sort, and filter in real-time

---

## 🚀 Quick Start

### Clone & Run Locally

```bash
git clone https://github.com/OWASP-BLT/owasp-blt.github.io.git
cd owasp-blt.github.io

# Start a local server
python -m http.server 8000
# Open http://localhost:8000
```

### Usage
- **Search:** Type in the search bar to find repositories
- **Sort:** Choose sorting option from dropdown
- **Filter:** Click language tags or use sidebar filters
- **Toggle View:** Switch between table and card layouts
- **Dark Mode:** Click the moon icon in header

---

## 🤝 Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Commit (`git commit -m "feat: add feature"`)
5. Push and create a Pull Request

---

## 💬 Community

- 🌐 **Website:** [owaspblt.org](https://owaspblt.org)
- 💬 **Slack:** [Join OWASP Slack](https://owasp.org/slack/invite)
- 📧 **Issues:** [GitHub Issues](https://github.com/OWASP-BLT/owasp-blt.github.io/issues)

---

## 📄 License

AGPL-3.0 - See [LICENSE](LICENSE) for details

<p align="center">Made with ❤️ by the OWASP BLT Community</p>

