# BLT-OSSH 🎩✨
**Open Source Sorting Hat** - AI-powered GitHub profile analyzer that recommends perfect open source projects

## Overview
OSSH (Open Source Sorting Hat) is a magical tool that analyzes your GitHub profile and recommends personalized open source projects, communities, learning resources, and discussion channels based on your skills, interests, and activity.

## Features
- 🔍 **Smart Profile Analysis** - Fetches and analyzes your GitHub repositories, languages, and topics
- 🎯 **Personalized Recommendations** - Matching of projects based on your tech stack
- 👥 **Community Connections** - Discover relevant developer communities
- 📚 **Learning Resources** - Curated articles and documentation
- 💬 **Discussion Channels** - Find active forums and chat platforms
- 🌙 **Dark Mode** - Beautiful UI with dark mode support
- ⚡ **Fast & Lightweight** - Pure static site hosted on GitHub Pages

## Tech Stack
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **APIs**: GitHub REST API v3 (called directly from the browser)
- **Deployment**: GitHub Pages via GitHub Actions

## Getting Started

### Prerequisites
- A modern web browser (no server-side dependencies)

### Local Development
Open `index.html` directly in your browser, or serve it with any static file server:

```bash
# Python built-in server
python -m http.server 8000
```

The application will be available at `http://localhost:8000`

### Deployment
Pushes to the `main` branch automatically deploy to GitHub Pages via the workflow at `.github/workflows/deploy.yml`.

To enable GitHub Pages for the repository:
1. Go to **Settings → Pages**
2. Set **Source** to **GitHub Actions**

## Project Structure
```
BLT-OSSH/
├── .github/
│   └── workflows/
│       └── deploy.yml      # GitHub Actions deployment workflow
├── static/
│   └── logo.png            # BLT logo
└── index.html              # Main frontend page (all-in-one)
```

## GitHub API

The site calls the GitHub REST API directly from the browser (no backend required):

- `GET https://api.github.com/users/{username}` — profile data
- `GET https://api.github.com/users/{username}/repos` — repository list

> **Note**: Unauthenticated requests are limited to 60 requests/hour per IP. This is sufficient for casual use.

## Usage
1. Visit the OSSH page
2. Enter your GitHub username
3. Click "Find My Projects"
4. View personalized recommendations
5. Explore projects, communities, and resources

## Features in Detail

### Smart Matching Algorithm
- Analyzes your repository languages
- Considers your starred repos and topics
- Matches you with trending and maintained projects

### Recommendation Categories
- **Projects**: Open source repositories matching your tech stack
- **Communities**: Developer communities and organizations
- **Articles**: Learning resources and documentation
- **Discussions**: Forums, Discord servers, and chat platforms

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is part of OWASP BLT and follows its licensing terms.

## Links
- [OWASP BLT](https://github.com/OWASP-BLT/BLT)
- [BLT Website](https://blt.owasp.org/)
- [Report Issues](https://github.com/OWASP-BLT/BLT-OSSH/issues)

## Acknowledgments
- OWASP Foundation
- BLT Community
- All contributors

---
Made with ❤️ by the OWASP BLT Community
