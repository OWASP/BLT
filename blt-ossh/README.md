# BLT-OSSH 🎩✨

**Open-Source Sorting Hat** — AI-powered GitHub profile analyzer that recommends perfect open-source projects for contributors.

[![OWASP BLT](https://img.shields.io/badge/OWASP-BLT-blue)](https://github.com/OWASP-BLT/BLT) [![GitHub Pages](https://img.shields.io/badge/Live-Demo-green)](https://owasp-blt.github.io/BLT-OSSH/)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture-overview)
- [Getting Started](#getting-started)
- [How It Works](#how-it-works)
- [Usage](#usage)
- [Contributing](#contributing)

## Overview
OSSH (Open-Source Sorting Hat) is a tool that analyzes your GitHub profile and recommends personalized open-source projects, communities, learning resources, and discussion channels based on your skills, interests, and activity.

## Features

### 🔍 GitHub Profile Analysis
- Fetches and analyzes your GitHub repositories, languages, and topics
- AI-powered matching of projects based on your tech stack
- Real-time GitHub API integration

### 👥 Community Platform
- **Create Developer Profiles** - Share your profile with the community
- **Browse Profiles** - Discover developers with similar interests
- **Smart Profile Creation** - After analyzing your GitHub, create a community profile with pre-filled data
- **Filter & Search** - Find developers by experience level, skills, or location

### 🎯 Personalized Recommendations
- Open-source projects matching your tech stack
- Developer communities and organizations
- Curated learning resources and articles
- Active discussion channels (Discord, Slack, Reddit, etc.)

### 🌙 Modern UI/UX
- Beautiful dark mode support
- Responsive design for all devices
- Smooth animations and transitions
- Accessible and intuitive interface

## Tech Stack
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Data Storage**: GitHub Issues (with `profile` label)
- **APIs**: GitHub REST API v3 (fetched directly from browser)
- **Deployment**: GitHub Pages

## Architecture Overview

BLT-OSSH (Open-Source Sorting Hat) is a recommendation engine that helps contributors discover open-source projects that match their skills and interests by analyzing GitHub profiles and repository metadata. It goes beyond project matching to suggest information such as blogs, educational pathways, and integration with **BLT University** (educational resources for contributors).

Within the **BLT (Bug Logging Tool) ecosystem**, BLT-OSSH acts as a **discovery layer** that helps users find relevant repositories, communities, and learning resources. It goes beyond project matching to suggest information such as blogs, educational pathways, and integration with **BLT University** (educational resources for contributors). Like the Sorting Hat, BLT-OSSH is designed to eventually sort contributors into four houses:

| House | Focus |
|-------|-------|
| **Buggleton** | Bug hunting & security |
| **Cybermoose** | Infrastructure & DevOps |
| **Bufferbit** | Web & application development |
| **Darkram** | Low-level & systems programming |

It complements the main [BLT platform](https://github.com/OWASP-BLT/BLT) by focusing on contributor onboarding rather than bug reporting.

### Key Architectural Decisions

- **No runtime backend** — The web app runs entirely in the browser and calls the GitHub API directly; automation jobs (GitHub Actions) only pre-generate community profile data.
- **Static deployment** — Hosted on GitHub Pages with no server-side dependencies.
- **GitHub Issues as a database** — Community profiles are stored as GitHub Issues with the `profile` label, enabling moderation and editing without a database.

### Smart Matching Algorithm

- Extracts language frequencies from the user's repositories
- Returns the user's non-fork repos sorted by stargazers count
- Implementation: `buildRecommendations()` in `js/app.js`

### Community Features

- **Profile Cards**: Rich cards with avatar, bio, skills, interests
- **Experience Badges**: Visual indicators (Beginner, Intermediate, Advanced, Expert)
- **Search & Filter**: Find developers by name, username, skills, or experience level
- **Real-time Stats**: Community statistics (member count, languages, countries)
- **Social Integration**: Connect via GitHub, website, Twitter, LinkedIn
- **GitHub-Powered**: Uses GitHub Issues as data source for profiles and projects

### Recommendation Categories

- **Projects**: Open-source repositories matching your skills and interests
- **Communities**: Developer communities and organizations
- **Articles**: Learning resources and documentation
- **Discussions**: Forums, Discord servers, and chat platforms

## How Profiles Work

### Simple & Direct
1. **Submit Profile**: Users create a GitHub Issue using the template
2. **Auto-Labeled**: Issue gets `profile` label automatically
3. **Live Display**: Workflow generates `data/profiles.json` from issues; Community page displays profiles
4. **Edit Anytime**: Users edit their issue to update their profile

### Why GitHub Issues?
- ✅ **Simple**: No backend needed, just GitHub API
- ✅ **User-Friendly**: Anyone can submit via familiar GitHub Issues
- ✅ **Editable**: Users can update their profiles anytime
- ✅ **Moderated**: Maintainers can review via issue management
- ✅ **Rate-limit friendly**: Normal usage stays within GitHub's rate limits

## Getting Started

### Local Development

**Prerequisites:** Python 3.x or Node.js 18+, Git, and a modern browser. No environment variables required.

### Setup

**1. Clone the repository**
```bash
git clone https://github.com/OWASP-BLT/BLT-OSSH.git
cd BLT-OSSH
```

**2. Serve the application locally**

Option A — Using Python (recommended):
```bash
python -m http.server 8000
```

Option B — Using npm:
```bash
npm run dev
```
(This runs `python -m http.server 8000` under the hood)

**3. Open in browser**

Visit `http://localhost:8000` to load the main analysis page. Visit `http://localhost:8000/community.html` for the Community profiles page.

### Testing Workflow

1. Run the local server as above
2. Enter a GitHub username and click "Find My Projects"
3. Verify recommendations display correctly
4. Test the "Create My Community Profile" flow (redirects to GitHub Issues)
5. Open `community.html` and verify profile fetching works

### Deployment

Pushes to `main` deploy via `.github/workflows/deploy.yml`. Enable in **Settings → Pages** with source **GitHub Actions**.

## Project Structure

```text
BLT-OSSH/
├── .github/
│   ├── workflows/
│   │   ├── deploy.yml           # GitHub Pages deployment
│   │   └── update-profiles.yml  # Generates data/profiles.json from GitHub Issues
│   └── ISSUE_TEMPLATE/
│       └── user_profile.yml     # Community profile template
├── data/
│   └── profiles.json            # Community profiles (generated by workflow)
├── static/
│   └── logo.png                 # BLT logo
├── js/
│   └── app.js                   # Frontend logic & GitHub API calls
├── index.html                   # Main analysis page
├── community.html               # Community profiles page
└── README.md                    # This file
```

## How It Works

### 1. GitHub Analysis Flow
1. User enters their GitHub username
2. Frontend fetches profile and repository data from GitHub API
3. System analyzes languages, topics, and repository metadata
4. Generates personalized recommendations
5. Results displayed with stats, projects, communities, and resources

### 2. Community Profile Creation Flow
1. User analyzes their GitHub profile
2. Clicks "Create My Community Profile" button
3. System pre-fills profile data:
   - GitHub username
   - Display name from GitHub
   - Bio (or primary language as fallback)
   - Skills extracted from repository languages
4. User redirected to GitHub Issues with template pre-filled
5. User adds additional info (interests, looking for, location, social links)
6. Submit issue to create profile
7. Profile appears on Community page after the workflow syncs `data/profiles.json` (runs on profile creation/edits, or every 6 hours)

### 3. Profile Discovery
- `update-profiles.yml` fetches all open issues with the `profile` label
- The workflow parses issue bodies and generates `data/profiles.json`
- Community page loads profiles from `data/profiles.json`
- Displays profiles with rich cards showing:
  - Experience level badge
  - Skills and interests
  - "Looking For" section
  - Social links and contact info
- Real-time search and filtering

## API Usage

The system interacts with the **GitHub REST API** to retrieve user and repository data. All API calls are made directly from the browser (no backend required).

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET https://api.github.com/users/{username}` | User profile data (name, bio, avatar, follower counts) |
| `GET https://api.github.com/users/{username}/repos?sort=updated&per_page=100` | User repository list with languages and topics |
| `GET https://api.github.com/repos/{owner}/{repo}/issues?labels=profile&state=open` | Community profiles (used by workflow to generate `data/profiles.json`) |
| `data/profiles.json` | Community profiles (static file; Community page loads this) |

### Data Fetched

- **User profile** — Avatar, bio, public repos count, followers, following
- **Repositories** — Names, descriptions, languages, stars, fork status
- **Languages used** — Extracted from repository metadata and weighted by frequency
- **Community profiles** — Loaded from `data/profiles.json` (workflow populates it from GitHub Issues)

### Rate Limits

- **Unauthenticated requests**: 60 requests/hour per IP address
- **Authenticated requests**: 5,000 requests/hour (if you add a token — not required for basic use)
- The app makes exactly 2 requests per profile analysis (profile and repos), so casual use stays within limits
- If rate limited, the app displays: *"GitHub API rate limit exceeded. Please wait a few minutes and try again."*

## Community Profile Template

Profiles are created as GitHub Issues using a structured template with these fields:

- **GitHub Username** (required) - Your GitHub handle
- **Display Name** (required) - How you want to be known
- **Bio** (required) - Brief description about yourself
- **Experience Level** (required) - Beginner, Intermediate, Advanced, or Expert
- **Areas of Interest** (checkboxes) - Web Dev, Mobile Dev, AI/ML, Cybersecurity, DevOps, etc.
- **Skills & Technologies** (required) - Comma-separated list (e.g., Python, JavaScript, React)
- **Looking For** (required) - Your goals (e.g., collaboration, mentorship)
- **Location** (optional) - Your geographical location
- **Website/Portfolio** (optional) - Your personal website or portfolio link
- **Twitter** (optional) - Handle without @
- **LinkedIn** (optional) - LinkedIn profile URL (e.g., https://linkedin.com/in/yourprofile)

### Pre-filled Profile Creation

After analyzing your GitHub profile, the system automatically pre-fills:
- Your GitHub username
- Display name from your GitHub profile
- Bio from GitHub (or primary language as fallback)
- Skills extracted from your most-used languages
- Looking for section with smart suggestions

## Usage

### For Users

1. **Analyze Your Profile**
   - Visit OSSH homepage
   - Enter your GitHub username
   - Click "Find My Projects"
   - Explore personalized recommendations

2. **Join the Community**
   - After analysis, click "Create My Community Profile"
   - Review pre-filled data (username, bio, skills)
   - Add additional information (interests, looking for, social links)
   - Submit to create your profile

3. **Discover Developers**
   - Visit the Community page
   - Browse developer profiles
   - Filter by experience level
   - Search by name, skills, or location
   - Connect via GitHub, website, or social media

## Features in Detail

- See [Smart Matching Algorithm](#smart-matching-algorithm)
- See [Community Features](#community-features)
- See [Recommendation Categories](#recommendation-categories)

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding project recommendations, improving the matching algorithm, enhancing the UI/UX, and more.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Part of OWASP BLT; follows its licensing terms.

## Links
- [OWASP BLT](https://github.com/OWASP-BLT/BLT)
- [BLT Website](https://blt.owasp.org/)
- [Report Issues](https://github.com/OWASP-BLT/BLT-OSSH/issues)
- [Create Your Profile](https://github.com/OWASP-BLT/BLT-OSSH/issues/new?template=user_profile.yml)
- [Browse Community](https://owasp-blt.github.io/BLT-OSSH/community.html)

## Roadmap

- [ ] AI-powered project recommendations using ML
- [ ] Profile verification badges
- [ ] Direct messaging between community members
- [ ] Project collaboration matching
- [ ] Mentorship program integration
- [ ] Event calendar for community meetups
- [ ] Skill endorsements
- [ ] Advanced search with tags

## Acknowledgments

- OWASP Foundation
- BLT Community
- All contributors

---
Made with ❤️ by the OWASP BLT Community
