# BLT-OSSH 🎩✨
**Open Source Sorting Hat** - AI-powered GitHub profile analyzer that recommends perfect open source projects

## Overview
OSSH (Open Source Sorting Hat) is a magical tool that analyzes your GitHub profile and recommends personalized open source projects, communities, learning resources, and discussion channels based on your skills, interests, and activity.

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
- Open source projects matching your tech stack
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

BLT-OSSH (Open Source Sorting Hat) is a **magical recommendation engine with special powers** that helps contributors discover open-source projects that match their skills and interests by analyzing GitHub profiles and repository metadata.

Within the **BLT (Bug Logging Tool) ecosystem**, OSSH acts as a **discovery layer** that helps users find relevant repositories, communities, and learning resources. It goes beyond project matching to suggest information such as blogs and educational pathways integrating with **BLT University**. Like the Sorting Hat, OSSH is designed to eventually sort contributors into four houses:

| House | Focus |
|-------|-------|
| **Buggleton** | Bug hunting & security |
| **Cybermoose** | Infrastructure & DevOps |
| **Bufferbit** | Web & application development |
| **Darkram** | Low-level & systems programming |

It complements the main [BLT platform](https://github.com/OWASP-BLT/BLT) by focusing on contributor onboarding rather than bug reporting.

### Key Architectural Decisions

- **No backend** — All logic runs in the browser. GitHub API is called directly from the client.
- **Static deployment** — Hosted on GitHub Pages with no server-side dependencies.
- **GitHub Issues as a database** — Community profiles are stored as GitHub Issues with the `profile` label, enabling moderation and editing without a database.

### Smart Hatching Algorithm

- Analyzes your repository languages and frequency
- Considers your starred repos and topics
- Matches you with trending and well-maintained projects
- Weights factors like activity, stars, and relevance

### Community Features

- **Profile Cards**: Rich cards with avatar, bio, skills, interests
- **Experience Badges**: Visual indicators (Beginner, Intermediate, Advanced, Expert)
- **Search & Filters**: Find developers by name, username, skills, or experience level
- **Real-time Stats**: Community statistics (member count, languages, countries)
- **Social Integrations**: Connect via Github, website, Twitter, LinkedIn
- **Github-Powered**: Uses Github Issues as a database for profiles

### Recommendation Categories

- **Projects**: Open source repositories matching your tech stack
- **Communities**: Developer communities and organizations
- **Articles**: Learning resources and documentation

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
- ✅ **Within limits**: Normal usage stays within GitHub's rate limits

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
7. Profile appears on Community page immediately (after workflow syncs `data/profiles.json`)

### 3. Profile Discovery
- Community page fetches all open issues with `profile` label
- Parses issue body to extract profile information
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
| `GET https://api.github.com/users/{username}/events/public?per_page=100` | Recent public events used to calculate the contributor activity score |
| `GET https://api.github.com/repos/{owner}/{repo}/issues?labels=profile&state=open` | Community profiles (used by workflow) |
| `data/profiles.json` | Community profiles (static file; workflow populates it from GitHub Issues) |

### Data Fetched

- **User profile** — Avatar, bio, public repos count, followers, following
- **Repositories** — Names, descriptions, languages, stars, fork status
- **Languages used** — Extracted from repository metadata and weighted by frequency
- **Public events** — Recent PushEvent, PullRequestEvent, and IssuesEvent counts used for activity scoring (see `js/app.js`, `activity_score`, `activity_breakdown`)
- **Community profiles** — Parsed from issue bodies on the Community page (or from `data/profiles.json`)

### Rate Limits

- **Unauthenticated requests**: 60 requests/hour per IP address
- **Authenticated requests**: 5,000 requests/hour (if you add a token — not required for basic use)
- The app typically makes 2–4 requests per profile analysis (profile, repos, optionally events), so casual use stays within limits
- If rate limited, the app displays: *"GitHub API rate limit exceeded. Please wait a few minutes and try again."*

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Part of OWASP BLT; follows its licensing terms.

## Links
- [OWASP BLT](https://github.com/OWASP-BLT/BLT)
- [BLT Website](https://blt.owasp.org/)
- [Report Issues](https://github.com/OWASP-BLT/BLT-OSSH/issues)
- [Create Your Profile](https://github.com/OWASP-BLT/BLT-OSSH/issues/new?template=user_profile.yml)
- [Browse Community](./community.html)

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
