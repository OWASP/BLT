# BLT-OSSH 🎩✨
**Open Source Sorting Hat** - AI-powered GitHub profile analyzer that recommends perfect open source projects

## Overview
OSSH (Open Source Sorting Hat) is a magical tool that analyzes your GitHub profile and recommends personalized open source projects, communities, learning resources, and discussion channels based on your skills, interests, and activity.

## Features
- 🔍 **Smart Profile Analysis** - Fetches and analyzes your GitHub repositories, languages, and topics
- 🎯 **Personalized Recommendations** - AI-powered matching of projects based on your tech stack
- 👥 **Community Connections** - Discover relevant developer communities
- 📚 **Learning Resources** - Curated articles and documentation
- 💬 **Discussion Channels** - Find active forums and chat platforms
- 🌙 **Dark Mode** - Beautiful UI with dark mode support
- ⚡ **Fast & Lightweight** - Built on Cloudflare Workers

## Tech Stack
- **Backend**: Python (Cloudflare Workers)
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **APIs**: GitHub REST API v3
- **Deployment**: Cloudflare Workers

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python (v3.12+)
- Wrangler CLI

### Installation
```bash
# Install dependencies
npm install

# Install Python dependencies (if needed)
pip install -r requirements.txt
```

### Development
```bash
# Start development server
npm run dev
# or
wrangler dev
```

The application will be available at `http://localhost:8787`

### Deployment
```bash
# Deploy to Cloudflare Workers
npm run deploy
# or
wrangler deploy
```

## Project Structure
```
BLT-OSSH/
├── src/
│   ├── main.py              # Python worker with routing logic
│   └── pages/
│       └── index.htm        # Main frontend page
├── static/
│   └── logo.png            # BLT logo
├── wrangler.toml           # Cloudflare Workers configuration
├── package.json            # Node dependencies
└── pyproject.toml          # Python dependencies
```

## API Endpoints

### `GET /`
Serves the main HTML page

### `POST /api`
Analyzes GitHub profile and returns recommendations

**Request Body:**
```json
{
  "username": "octocat"
}
```

**Response:**
```json
{
  "status": "success",
  "username": "octocat",
  "data": {
    "github_stats": {
      "username": "octocat",
      "name": "The Octocat",
      "avatar_url": "...",
      "bio": "...",
      "public_repos": 8,
      "followers": 1000,
      "following": 100,
      "languages": ["JavaScript", "Python"],
      "topics": ["web", "api"]
    },
    "recommended_repos": [...],
    "recommended_communities": [...],
    "recommended_articles": [...],
    "recommended_discussion_channels": [...]
  }
}
```

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
