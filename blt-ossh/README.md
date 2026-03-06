# BLT-OSSH ≡ƒÄ⌐Γ£¿
**Open Source Sorting Hat** - AI-powered GitHub profile analyzer that recommends perfect open source projects

## Overview
OSSH (Open Source Sorting Hat) is a magical tool that analyzes your GitHub profile and recommends personalized open source projects, communities, learning resources, and discussion channels based on your skills, interests, and activity.

## Features

### ≡ƒöì GitHub Profile Analysis
- Fetches and analyzes your GitHub repositories, languages, and topics
- AI-powered matching of projects based on your tech stack
- Real-time GitHub API integration

### ≡ƒæÑ Community Platform
- **Create Developer Profiles** - Share your profile with the community
- **Browse Profiles** - Discover developers with similar interests
- **Smart Profile Creation** - After analyzing your GitHub, create a community profile with pre-filled data
- **Filter & Search** - Find developers by experience level, skills, or location

### ≡ƒÄ» Personalized Recommendations
- Open source projects matching your tech stack
- Developer communities and organizations
- Curated learning resources and articles
- Active discussion channels (Discord, Slack, Reddit, etc.)

### ≡ƒîÖ Modern UI/UX
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

BLT-OSSH (Open Source Sorting Hat) helps contributors discover open-source projects that match their skills and interests by analyzing GitHub profiles and repository metadata.

Within the **BLT (Bug Logging Tool) ecosystem**, OSSH acts as a **discovery layer** that helps users find relevant repositories, communities, and learning resources. It complements the main [BLT platform](https://github.com/OWASP-BLT/BLT) by focusing on contributor onboarding and project matching rather than bug reporting.

### How It Works

1. **User submits a GitHub username** — The user enters their GitHub handle on the OSSH homepage.
2. **OSSH fetches and analyzes** — The frontend calls the GitHub API to retrieve user profile, repositories, languages, and topics.
3. **Matching logic runs client-side** — The `buildRecommendations()` function in `js/app.js` analyzes repository languages, contribution patterns, and metadata to identify relevant projects.
4. **Recommendations are displayed** — Results include recommended repositories, communities, articles, and discussion channels.

### Key Architectural Decisions

- **No backend** — All logic runs in the browser. GitHub API is called directly from the client.
- **Static deployment** — Hosted on GitHub Pages with no server-side dependencies.
- **GitHub Issues as database** — Community profiles are stored as GitHub Issues with the `profile` label, enabling moderation and editing without a database.

## How Profiles Work

### Simple & Direct
1. **Submit Profile**: Users create a GitHub Issue using the template
2. **Auto-Labeled**: Issue gets `profile` label automatically
3. **Live Display**: Community page fetches and displays issues in real-time
4. **Edit Anytime**: Users edit their issue to update their profile

### Why GitHub Issues?
- Γ£à **Simple**: No backend needed, just GitHub API
- Γ£à **User-Friendly**: Anyone can submit via familiar GitHub Issues
- Γ£à **Editable**: Users can update their profiles anytime
- Γ£à **Moderated**: Maintainers can review via issue management
- Γ£à **No Rate Limits**: Reasonable usage stays within GitHub's limits

## Getting Started

### Local Development

This section explains how contributors can run BLT-OSSH locally for development and testing.

### Prerequisites

- **Python 3.x** or **Node.js 18+** — For running a local static file server
- **Git** — For cloning the repository
- **Modern web browser** — Chrome, Firefox, Safari, or Edge

No environment variables or configuration files are required for basic local development. The app uses the public GitHub API without authentication.

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

### Configuration

- **No `.env` or config files** — The app is fully static and requires no environment variables
- **CORS** — GitHub API allows requests from any origin; no CORS configuration needed for local development

### Testing Workflow

1. Run the local server as above
2. Enter a GitHub username and click "Find My Projects"
3. Verify recommendations display correctly
4. Test the "Create My Community Profile" flow (redirects to GitHub Issues)
5. Open `community.html` and verify profile fetching works

### Deployment
Pushes to the `main` branch automatically deploy to GitHub Pages via the workflow at `.github/workflows/deploy.yml`.

To enable GitHub Pages for the repository:
1. Go to **Settings ΓåÆ Pages**
2. Set **Source** to **GitHub Actions**

## Project Structure
```
BLT-OSSH/
Γö£ΓöÇΓöÇ .github/
Γöé   Γö£ΓöÇΓöÇ workflows/
Γöé   Γöé   ΓööΓöÇΓöÇ deploy.yml           # GitHub Pages deployment
Γöé   ΓööΓöÇΓöÇ ISSUE_TEMPLATE/
Γöé       ΓööΓöÇΓöÇ user_profile.yml     # Community profile template
Γö£ΓöÇΓöÇ static/
Γöé   ΓööΓöÇΓöÇ logo.png                 # BLT logo
Γö£ΓöÇΓöÇ js/
Γöé   ΓööΓöÇΓöÇ app.js                   # Frontend logic & GitHub API calls
Γö£ΓöÇΓöÇ index.html                   # Main analysis page
Γö£ΓöÇΓöÇ community.html               # Community profiles page
ΓööΓöÇΓöÇ README.md                    # This file
```

## How It Works

### 1. GitHub Analysis Flow
1. User enters their GitHub username
2. Frontend fetches profile and repository data from GitHub API
3. System analyzes languages, topics, and contribution patterns
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
7. Profile appears on Community page immediately (fetched from GitHub Issues)

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
| `GET https://api.github.com/repos/{owner}/{repo}/issues?labels=profile&state=open` | Community profiles (stored as GitHub Issues) |

### Data Fetched

- **User profile** — Avatar, bio, public repos count, followers, following
- **Repositories** — Names, descriptions, languages, stars, fork status
- **Languages used** — Extracted from repository metadata and weighted by frequency
- **Community profiles** — Parsed from issue bodies on the Community page

### Rate Limits

- **Unauthenticated requests**: 60 requests/hour per IP address
- **Authenticated requests**: 5,000 requests/hour (if you add a token — not required for basic use)
- The app typically makes 2–3 requests per profile analysis, so casual use stays within limits
- If rate limited, the app displays: *"GitHub API rate limit exceeded. Please wait a few minutes and try again."*

### Authentication

- **No authentication required** for basic usage — the app works with unauthenticated API calls
- For higher rate limits or private repository access, you could add a GitHub token; this is not currently implemented in the static frontend

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

### For Contributors
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Adding new project recommendations
- Improving the matching algorithm
- Enhancing the UI/UX
- Adding new features

## Features in Detail

### Smart Matching Algorithm
- Analyzes your repository languages and frequency
- Considers your starred repos and topics
- Matches you with trending and well-maintained projects
- Weighs factors like activity, stars, and relevance

### Community Features
- **Profile Cards**: Rich cards with avatar, bio, skills, interests
- **Experience Badges**: Visual indicators (Beginner, Intermediate, Advanced, Expert)
- **Search & Filter**: Find developers by name, username, skills, or experience level
- **Real-time Stats**: Community statistics (member count, languages, countries)
- **Social Integration**: Connect via GitHub, website, Twitter, LinkedIn
- **GitHub-Powered**: Uses GitHub Issues as database for profiles

### Recommendation Categories
- **Projects**: Open source repositories matching your tech stack
- **Communities**: Developer communities and organizations
- **Articles**: Learning resources and documentation
- **Discussions**: Forums, Discord servers, and chat platforms

## Community Profile Template

Profiles are created as GitHub Issues using a structured template with these fields:

- **GitHub Username** (required) - Your GitHub handle
- **Display Name** (required) - How you want to be called
- **Bio** (required) - Brief description about yourself
- **Experience Level** (required) - Beginner, Intermediate, Advanced, or Expert
- **Areas of Interest** (checkboxes) - Web Dev, Mobile, AI/ML, Security, DevOps, etc.
- **Skills & Technologies** (required) - Comma-separated list (e.g., JavaScript, Python, React)
- **Looking For** (required) - Your goals (e.g., "Mentorship in AI", "Open source collaborations")
- **Location** (optional) - City, Country
- **Website/Portfolio** (optional) - Your personal website
- **Twitter** (optional) - Handle without @
- **LinkedIn** (optional) - LinkedIn username

### Pre-filled Profile Creation
After analyzing your GitHub profile, the system automatically pre-fills:
- Your GitHub username
- Display name from your GitHub profile
- Bio from GitHub (or primary language as fallback)
- Skills extracted from your most-used languages
- Looking for section with smart suggestions

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
Made with Γ¥ñ∩╕Å by the OWASP BLT Community
