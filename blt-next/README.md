# BLT-Next: Modern Static Frontend Architecture

> **A fresh, modern design by removing non-core components to create a clear, enjoyable user experience focused on core value**

## 🚀 Overview (Edited by Vandana)

BLT-Next is the next-generation architecture for OWASP BLT (Bug Logging Tool), migrating from a Django monolith to a lightweight, high performance static frontend with dynamic features powered by Cloudflare Python Workers.

## ✨ Key Features

- **⚡ Sub-200ms Global Response Times**: Optimized static assets served via Cloudflare
- **🎯 Progressive Enhancement**: Core functionality enhanced with HTMX and Tailwind CSS
- **📦 Modular Architecture**: Clean separation of concerns with reusable Python handlers
- **🔒 Secure by Default**: Cloudflare Workers handle authentication and D1 peristence
- **🌍 Global Edge Runtime**: Python Workers running everywhere on Cloudflare's network
- **💪 Maintainable**: Zero-build frontend using Tailwind CDN and Vanilla JS

## 🏗️ Architecture

### Frontend (Cloudflare Assets)
- **Static Assets**: HTML, CSS, JavaScript served via Cloudflare Workers Assets
- **CSS Framework**: Tailwind CSS (via CDN) for modern, responsive design
- **Interactions**: HTMX for seamless dynamic updates without page reloads

### Backend (Cloudflare Python Workers)
- **API Endpoints**: Python workers handle dynamic features and database interactions
- **Database**: Cloudflare D1 (SQL) for low-latency edge storage
- **Performance**: Edge computing for sub-200ms responses

## 📁 Project Structure

```
BLT-Next/
├── src/                        # Static Assets (Frontend Root)
│   ├── index.html              # Main landing page
│   ├── assets/
│   │   ├── js/
│   │   │   └── main.js        # Main application logic
│   └── pages/                 # Static pages
├── workers/                    # Cloudflare Workers (Backend)
│   └── main.py                # Unified API worker
├── docs/                      # Documentation
├── package.json               # Scripts for dev and database
├── wrangler.toml              # Infrastructure as code
└── schema.sql                 # Unified D1 database schema
```

## 🚦 Getting Started

### Quick Start

1.  **Clone the repository**
    ```bash
    git clone https://github.com/OWASP-BLT/BLT-Next.git
    cd BLT-Next
    ```

2.  **Install dependencies**
    ```bash
    npm install
    ```

3.  **Initialize local database**
    ```bash
    npm run db:init
    ```

4.  **Start development server**
    ```bash
    npm run dev
    ```
    This serves both the frontend and the backend API at `http://localhost:8787` using `wrangler`.

For more details on setting up Cloudflare Workers or custom configurations, please see our [Contributing Guide](CONTRIBUTING.md).

4. **Update API endpoint** in `src/assets/js/main.js`:
   ```javascript
   const CONFIG = {
       API_BASE_URL: 'https://your-worker.workers.dev',
   };
   ```

## 🎨 Features Implementation

### Core Features

- ✅ **Bug Reporting**: Intuitive form with HTMX for seamless submission
- ✅ **Leaderboard**: Dynamic ranking system loaded via API
- ✅ **Authentication**: Secure login/signup with JWT tokens
- ✅ **User Profiles**: User dashboard and activity tracking
- ✅ **Projects**: Company/project management
- ✅ **Rewards**: Gamification with points and badges

### Progressive Enhancement

1. **Base Layer**: Core HTML works without JavaScript
2. **Enhanced Layer**: HTMX adds dynamic interactions
3. **Rich Layer**: Vanilla JS provides advanced features

## 🔧 Configuration

### GitHub Pages

Enable GitHub Pages in repository settings:
1. Go to Settings > Pages
2. Source: Deploy from a branch
3. Branch: main / (root)
4. Save

### Environment Variables (Cloudflare)

Set these in Cloudflare Workers dashboard:
```bash
DATABASE_URL=your_database_url
JWT_SECRET=your_jwt_secret
ALLOWED_ORIGINS=https://owasp-blt.github.io
```

## 📊 Performance

- **First Contentful Paint**: < 1s
- **Time to Interactive**: < 2s
- **Total Bundle Size**: < 100KB (uncompressed)
- **API Response Time**: < 200ms (global average)

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- **HTML**: Semantic, accessible markup
- **CSS**: BEM methodology, CSS variables
- **JavaScript**: ES6+, modular, documented
- **Python**: PEP 8 compliant

## 📝 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing Guide](CONTRIBUTING.md)

## 🔒 Security

- All dynamic features handled by secure Cloudflare Workers
- CORS properly configured
- Input validation on both client and server
- JWT-based authentication
- No sensitive data in frontend code

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OWASP Community
- All contributors to the original BLT project
- GitHub for Pages hosting
- Cloudflare for Workers platform

## 📧 Contact

- **Project**: [OWASP BLT](https://owasp.org/www-project-bug-logging-tool/)
- **GitHub**: [OWASP-BLT](https://github.com/OWASP-BLT)
- **Issues**: [GitHub Issues](https://github.com/OWASP-BLT/BLT-Next/issues)

---

Made with ❤️ by the OWASP BLT community

note: this is a temperory change in the code to show the pull request.
