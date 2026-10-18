# BLT-Hackathon 🏆

**Live Site:** [https://hackathons.owaspblt.org/](https://hackathons.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Hackathons](https://git.owaspblt.org/BLT/BLT-Hackathons)

<p align="center"><img src="logo.png" alt="blt-hackathons logo" width="160" height="160"></p>

A static hackathon platform for the BLT projects on git.owaspblt.org (and GitHub or GitLab projects) with **charts**, **leaderboards**, and **prizes**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Pages](https://img.shields.io/badge/Deployed%20on-GitHub%20Pages-blue)](https://pages.github.com/)

## ✨ Features

- 🎯 **Multiple Hackathons** - Host multiple hackathons with individual pages and a unified index
- 📊 **Real-time Leaderboards** - Automatically track and rank contributors based on merged pull requests
- 📈 **Activity Charts** - Visualize pull request activity over time with beautiful charts
- 🏆 **Prize Management** - Showcase prizes and awards for top contributors
- 🤝 **Sponsor Display** - Highlight your hackathon sponsors
- 📱 **Responsive Design** - Works perfectly on desktop and mobile devices
- 🚀 **Almost No Backend** - Static files plus a tiny Worker that serves statistics from Workers KV
- ⚡ **Easy Setup** - Just edit a config file and deploy!

## 🎯 Quick Start

### Option 1: Single Hackathon (Legacy Mode)

For a single hackathon, edit `public/js/config.js`:

```javascript
const HACKATHON_CONFIG = {
    name: "Your Hackathon Name",
    description: "Your hackathon description...",
    startTime: "2024-01-01T00:00:00Z",
    endTime: "2024-01-31T23:59:59Z",
    github: {
        token: "", // Optional: Add a GitHub token to avoid rate limits
        repositories: [
            "owner/repo1",
            "owner/repo2"
        ]
    }
};
```

Then open `public/hackathon.html` directly.

### Option 2: Multiple Hackathons (Recommended)

For multiple hackathons, edit `public/js/hackathons-config.js`:

```javascript
const HACKATHONS_CONFIG = {
    hackathons: [
        {
            slug: "hackathon-2024",  // Unique identifier for URL
            name: "Hackathon 2024",
            description: "Description...",
            startTime: "2024-01-01T00:00:00Z",
            endTime: "2024-01-31T23:59:59Z",
            github: {
                token: "",
                repositories: ["owner/repo1"]
            }
        },
        // Add more hackathons...
    ]
};
```

Your main page (`index.html`) will show all hackathons, and each hackathon will have its own page at `hackathon.html?slug=hackathon-2024`.

### Deploy to GitHub Pages

1. Push your changes to GitHub
2. Go to your repository **Settings** → **Pages**
3. Under "Source", select the branch you want to deploy (usually `main`)
4. Your hackathon platform will be live at: `https://your-username.github.io/BLT-Hackathons/`

### Deploy to Cloudflare

In this repository the site is the `blt-hackathons` Cloudflare Worker (`wrangler.toml`), deployed by
`scripts/deploy.sh blt-hackathons`. It serves `public/` as static assets. A small Worker
(`worker/index.js`) answers `/stats.json` and `/hackathon-data/*.json` from Workers KV (binding
`DATA`, namespace `blt-hackathons-data`), and falls back to the files committed under `public/` when
KV has no copy yet.

### Statistics updates

The workflow `.forkmesh/blt-hackathons--update-stats.yml` runs every 6 hours, on pushes under
`blt-hackathons/`, and by hand. It runs `scripts/refresh-kv.sh`:

1. downloads the live data of every hackathon that has not ended, because KV holds the latest copy
   and `fetch_stats.py` merges GitHub reviews incrementally;
2. reads the refresh state from KV (`state/fetch-state.json`, not served by the Worker) with
   `scripts/worker-data/kv-get.sh`;
3. runs `fetch_stats.py`, which skips ended hackathons and stops after `FETCH_BUDGET_SECONDS`
   (900 in the workflow, against a 30-minute job timeout);
4. writes the files it changed, and the state when it changed, to KV through the Cloudflare API
   (`scripts/worker-data/kv-put.sh`).

Nothing is committed and the site is not redeployed.

**git.owaspblt.org hackathons** (`provider: "forkmesh"`) are cheap and resumable. ForkMesh keeps pull
requests on the `forkmesh/pulls` ledger branch and issues under `.forkmesh/issues/` in the
repository, and its public API serves them (`GET https://git.owaspblt.org/api/repo/owasp-blt/BLT/`
`tree`, `blobs` and `compare`, no token). `forkmesh_source.py` keeps every pull and issue folder's git
oid in the state and re-reads only the folders that changed: a refresh with no news is 3 requests.
One sync serves every hackathon on the same repository. When the budget runs out mid-sync, what was
read is saved and the next run continues; the hackathon keeps its previous file until a sync
completes. The monorepo has one folder per project, so items are attributed to projects:

1. a pull request counts for every project folder its diff touches (`changes.patch`,
   `commits.mbox`, or the compare of a branch-backed pull); `.forkmesh/<folder>--*.yml`
   workflows count for `<folder>`; files outside project folders count for none;
2. a pull request with no readable diff counts for the folder named by a `blt-leaf:` or
   `[blt-leaf]` title prefix;
3. an issue counts for the folders named by its labels (`blt-leaf` or `project:blt-leaf`), else
   for its title prefix.

A pull or issue that matches none of a hackathon's `paths` does not count for it. `paths: ["*"]`
counts everything, with one card per folder that has activity. Review files (`review`, `comment`,
`line-comment`, `thread-comment`) count as reviews; self-reviews do not.

GitHub hackathons still fetch every pull request of each repository and are not resumable: one
that runs out of budget keeps its previous file. GitLab support remains for third-party groups;
the BLT GitLab group is closed.

Secrets (Actions): `CLOUDFLARE_API_TOKEN` (Workers KV Storage: Edit) and `CLOUDFLARE_ACCOUNT_ID`;
optional `GH_API_TOKEN` (GitHub hackathons), `GITLAB_TOKEN` (third-party GitLab hackathons),
`SLACK_TOKEN_OWASP` and `SLACK_TOKEN_BLT` (Slack activity, below).

The JSON files under `public/hackathon-data/` are only the fallback. A hackathon's final data stays
in KV after it ends; copy it into git by hand if you want a snapshot there.

Tests: `python3 -m unittest discover -s test -p 'test_*.py'` (the ForkMesh source, the budget and
Slack, with a fake API) and `node --test 'test/*.test.mjs'` (the Worker and `refresh-kv.sh` with
stubbed fetch and curl).

### Slack activity

A hackathon with `trackSlack: true` shows how many messages each participant posted in the OWASP and
BLT Slack workspaces during the event (a "Slack messages" card with a total, and a Slack count next
to each contributor). `slackUsersFile` maps participants to Slack, because nothing else links a
git.owaspblt.org account to a Slack account:

```yaml
# hackathon-participants/<slug>-slack.yml; keys are git.owaspblt.org usernames
slack:
  alice: alice.dev                    # the same handle in both workspaces
  bob: {owasp: bob.smith, blt: bob}   # different handles
  carol: {owasp: U012ABCDEF}          # a Slack member id; only the OWASP workspace
```

Participants add themselves with a pull request to that file. The counts use Slack's
`search.messages` (`from:` plus the event's dates, as the GSoC progress tracker did) with the
user tokens `SLACK_TOKEN_OWASP` and `SLACK_TOKEN_BLT` (scope `search:read`). Slack allows about
20 searches a minute, so calls are 3.2 s apart, at most 40 per run (`SLACK_MAX_CALLS`), and each
participant is re-checked after 20 hours (`SLACK_REFRESH_HOURS`), oldest first. A workspace without
a token shows "—"; with no token at all the card is hidden. Slack errors never fail the run.

## 📖 Configuration Guide

### Basic Information

```javascript
name: "My Awesome Hackathon"
description: "Join us for an exciting coding competition!"
startTime: "2024-01-01T00:00:00Z"  // ISO 8601 format
endTime: "2024-01-31T23:59:59Z"    // ISO 8601 format
```

### GitHub Configuration

```javascript
github: {
    token: "",  // Optional but recommended
    repositories: [
        "facebook/react",
        "microsoft/vscode"
    ]
}
```

**New: Organization Support**

You can now track all repositories in a GitHub organization instead of listing them individually:

```javascript
github: {
    token: "",
    organization: "OWASP-BLT",  // Track all repos in this organization
    repositories: []  // Can still add specific repos if needed
}
```

When an `organization` field is specified, the system will automatically fetch all repositories from that organization and track them for the hackathon. You can combine this with explicit repositories if needed.

**GitHub Token (Recommended):**
- Go to [GitHub Settings → Tokens](https://github.com/settings/tokens)
- Create a new token with `public_repo` scope
- Add it to the config to avoid API rate limits (60 requests/hour without token, 5000 with token)

### git.owaspblt.org (ForkMesh) Configuration

BLT hackathons read the BLT monorepo on git.owaspblt.org, one folder per project:

```javascript
{
    slug: "summer-2027",
    name: "Summer 2027",
    startTime: "2027-06-01T00:00:00Z",
    endTime: "2027-06-30T23:59:59Z",
    provider: "forkmesh",
    forkmesh: {
        url: "https://git.owaspblt.org",       // API at <url>/api/repo/<owner>/<repo>/...
        owner: "owasp-blt",
        repo: "BLT",
        webUrl: "https://git.owaspblt.org/BLT", // pull and issue links
        paths: ["blt-leaf", "blt-jobs"]          // project folders, or ["*"] for all
    }
}
```

`OWASP_BLT_PROJECT_FOLDERS` in `public/js/hackathons-config.js` lists every project folder (a test
keeps it equal to `scripts/routing/projects.tsv`). No token is needed.

### GitLab Configuration

New hackathons can track GitLab projects and groups. Set `provider: "gitlab"` and use a `gitlab` block:

```javascript
{
    slug: "summer-2026",
    name: "Summer 2026",
    startTime: "2026-06-01T00:00:00Z",
    endTime: "2026-06-30T23:59:59Z",
    provider: "gitlab",
    gitlab: {
        url: "https://gitlab.com",
        group: "example-group",
        projects: ["example-group/example-project"]
    }
}
```

`group` includes projects from nested subgroups. `projects` can also contain paths such as `group/subgroup/project`. Public projects work without a token; private projects require an Actions secret named `GITLAB_TOKEN`. This is for third-party GitLab groups: gitlab.com/owasp-blt is closed.

GitLab merge-request notes are counted as review activity. Existing GitHub hackathons and their generated JSON files remain unchanged.

### Prizes Configuration

```javascript
prizes: [
    {
        position: 1,          // 1, 2, 3, or 4 (special prize)
        title: "First Place",
        description: "Cash prize and swag!",
        value: "500"         // Optional: display monetary value
    }
]
```

### Sponsors Configuration

```javascript
sponsors: [
    {
        name: "Company Name",
        level: "gold",  // platinum, gold, silver, bronze, or partner
        logo: "images/sponsor-logo.png",
        website: "https://example.com"
    }
]
```

### Display Options

```javascript
display: {
    showRepoStats: true,
    maxLeaderboardEntries: 10,
    showPRsInLeaderboard: true
}
```

## 🎨 Customization

### Adding a Banner Image

Replace the gradient banner with a custom image by modifying `index.html`:

```html
<div class="relative rounded-lg overflow-hidden mb-8 h-64" 
     style="background-image: url('images/banner.jpg'); background-size: cover;">
```

### Changing Colors

The dashboard uses Tailwind CSS. Main brand colors can be changed by replacing `red-600` and `red-700` classes with your preferred color:

- `red-600` → `blue-600`, `green-600`, `purple-600`, etc.
- `red-700` → `blue-700`, `green-700`, `purple-700`, etc.

### Performance Optimization

The dashboard uses Tailwind CSS via CDN for simplicity. For production, you can optimize by:

1. Installing Tailwind CLI: `npm install -D tailwindcss`
2. Creating a `tailwind.config.js` file
3. Building a custom CSS file with only used classes
4. Replacing the CDN link with your custom CSS

This can reduce the CSS from ~3MB to ~10KB.

### Adding Sponsor Logos

1. Create an `images` folder in your repository
2. Add sponsor logo files
3. Reference them in the config: `logo: "images/sponsor-logo.png"`

## 🔧 How It Works

1. **GitHub API Integration**: The dashboard fetches pull request data from specified repositories using the GitHub REST API
2. **Client-Side Processing**: All data processing happens in the browser - no backend needed!
3. **Real-Time Updates**: Data is cached for 5 minutes to balance freshness with API rate limits
4. **Leaderboard Logic**: Ranks contributors by the number of merged pull requests during the hackathon period

## 📊 What Gets Tracked?

- ✅ Pull requests created during the hackathon period
- ✅ Pull requests merged during the hackathon period
- ✅ Unique contributors (excludes bots)
- ✅ Daily PR activity
- ✅ Per-repository statistics

## 🚀 Advanced Usage

### Multiple Hackathons

The platform now supports hosting multiple hackathons on a single deployment:

1. **Configure multiple hackathons** in `public/js/hackathons-config.js`
2. **Each hackathon gets a unique slug** used in the URL (e.g., `hackathon.html?slug=blt-2024`)
3. **Main index page** at `/` lists all hackathons with filtering by status (ongoing, upcoming, ended)
4. **Individual hackathon pages** accessible via slug show full dashboard with stats and leaderboard

**Example configuration:**
```javascript
const HACKATHONS_CONFIG = {
    hackathons: [
        {
            slug: "winter-2024",
            name: "Winter Hackathon 2024",
            // ... other config
        },
        {
            slug: "spring-2024",
            name: "Spring Hackathon 2024",
            // ... other config
        }
    ]
};
```

### Custom Domain

1. Add a `CNAME` file to your repository with your domain
2. Configure DNS settings with your domain provider
3. Enable custom domain in GitHub Pages settings

### Adding Analytics

Add Google Analytics or other tracking by inserting the code before the closing `</head>` tag in both `index.html` and `hackathon.html`.

## 🛠️ Development

### Local Testing

Serve the deployable `public/` directory locally:

```bash
# Using Python 3
python -m http.server 8000 --directory public

# Using Node.js
npx serve public

# Visit http://localhost:8000
```

### File Structure

```
BLT-Hackathons/
├── public/                     # Cloudflare Pages and GitHub Pages output
│   ├── index.html              # Main page listing all hackathons
│   ├── hackathon.html          # Individual hackathon dashboard
│   ├── js/
│   │   ├── config.js           # Single hackathon configuration (legacy)
│   │   ├── hackathons-config.js # Multiple hackathons configuration
│   │   ├── index.js            # Index page logic
│   │   ├── github-api.js       # GitHub API integration
│   │   └── main.js             # Dashboard logic
│   ├── images/                 # Optional: images and logos
│   └── hackathon-data/         # Statistics fallback (live data is in Workers KV)
├── worker/index.js             # Serves the statistics from KV
├── scripts/refresh-kv.sh       # Refresh into KV (every 6 hours)
├── fetch_stats.py              # Statistics fetcher (git.owaspblt.org, GitHub, GitLab)
├── forkmesh_source.py          # git.owaspblt.org pulls/issues, incremental and resumable
├── slack_activity.py           # Slack message counts (trackSlack)
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Inspired by [OWASP BLT](https://git.owaspblt.org/BLT/BLT-Core) hackathon functionality.

## 💡 Tips & Best Practices

1. **Set Up GitHub Token**: Avoid rate limits by using a personal access token
2. **Test Before Launch**: Run a test hackathon with a short duration to verify everything works
3. **Communicate Rules Clearly**: Use the rules section to set expectations
4. **Promote Your Hackathon**: Share your hackathon dashboard link on social media
5. **Monitor Activity**: Check the dashboard regularly during the hackathon
6. **Plan Prize Distribution**: Have a clear plan for contacting winners

## ❓ FAQ

**Q: How often does the leaderboard update?**  
A: Data is cached for 5 minutes. Refresh the page to get the latest updates.

**Q: Can I track private repositories?**  
A: Yes, but you'll need a GitHub token with appropriate permissions.

**Q: What counts as a valid contribution?**  
A: Only merged pull requests created or merged during the hackathon period are counted.

**Q: Are bot accounts excluded?**  
A: Yes, accounts with "bot" in the name are automatically filtered out.

**Q: Can I customize the design?**  
A: Absolutely! The HTML and CSS are fully customizable.

## 📞 Support

- **Issues**: [GitHub Issues](https://git.owaspblt.org/BLT/issues)
- **Discussions**: [GitHub Discussions](https://git.owaspblt.org/BLT/discussions)

---

Made with ❤️ by the OWASP BLT community
