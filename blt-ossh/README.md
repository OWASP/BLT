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

## How Profiles Work

### Simple & Direct
1. **Submit Profile**: Users create a GitHub Issue using the template
2. **Auto-Labeled**: Issue gets `profile` label automatically
3. **Live Display**: Community page fetches and displays issues in real-time
4. **Edit Anytime**: Users edit their issue to update their profile

### Why GitHub Issues?
- ✅ **Simple**: No backend needed, just GitHub API
- ✅ **User-Friendly**: Anyone can submit via familiar GitHub Issues
- ✅ **Editable**: Users can update their profiles anytime
- ✅ **Moderated**: Maintainers can review via issue management
- ✅ **No Rate Limits**: Reasonable usage stays within GitHub's limits

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
│   ├── workflows/
│   │   └── deploy.yml           # GitHub Pages deployment
│   └── ISSUE_TEMPLATE/
│       └── user_profile.yml     # Community profile template
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

## GitHub API

The site calls the GitHub REST API directly from the browser (no backend required):

- `GET https://api.github.com/users/{username}` — User profile data
- `GET https://api.github.com/users/{username}/repos` — User repository list
- `GET https://api.github.com/repos/{owner}/{repo}/issues?labels=profile&state=open` — Community profiles

> **Note**: Unauthenticated requests are limited to 60 requests/hour per IP. This is sufficient for casual use.

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
Made with ❤️ by the OWASP BLT Community
