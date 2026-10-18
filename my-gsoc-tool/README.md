# GSoC Student Dashboard 🎓

**Live Site:** [https://gsoc-tool.owaspblt.org/](https://gsoc-tool.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/MY-GSOC-TOOL](https://git.owaspblt.org/BLT/MY-GSOC-TOOL)

<p align="center"><img src="logo.png" alt="my-gsoc-tool logo" width="160" height="160"></p>

A comprehensive, automated dashboard for Google Summer of Code students to showcase their entire GSoC journey on one page. This dashboard automatically fetches your GitHub contributions, displays your blog posts, tracks mentor feedback, and highlights your milestones—all in a beautiful, responsive interface.

![GSoC Dashboard](https://img.shields.io/badge/GSoC-Dashboard-blue)
![License](https://img.shields.io/badge/License-AGPL--3.0-green)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Enabled-brightgreen)

## ✨ Features

- **📊 GitHub Contributions Tracking**: Automatically fetches and displays your commits, pull requests, issues, and code reviews using GitHub Actions
- **💬 Slack Integration**: Link to your organization's Slack workspace and showcase your community participation
- **📝 Blog Posts Integration**: Display your progress blog posts and technical write-ups
- **👨‍🏫 Mentor-Student Interactions**: Document feedback and interactions with your mentors
- **📅 Weekly Updates Timeline**: Track your weekly progress throughout the program
- **🏆 Milestones & Achievements**: Highlight your accomplishments and key milestones
- **🚀 One-Click Setup**: Simply fork this repository and update the config—GitHub Actions handles the rest!
- **📱 Responsive Design**: Beautiful UI that works on all devices
- **🔄 Auto-Updates**: Dashboard updates automatically via scheduled GitHub Actions

## 🚀 Quick Start (3 Steps!)

### Step 1: Fork This Repository

Click the "Fork" button at the top right of this page to create your own copy of this dashboard.

### Step 2: Deploy on Cloudflare

1. Create a Cloudflare Pages project from this repository
2. Set the build output directory to `public`
3. Leave the build command empty

### Step 3: Customize Your Dashboard

Edit `public/config.json` with your information:

```json
{
  "student": {
    "name": "Your Name",
    "bio": "Google Summer of Code Contributor",
    "avatar": "https://github.com/YOUR-USERNAME.png",
    "github": "https://github.com/YOUR-USERNAME",
    "email": "your.email@example.com",
    "blog": "https://yourblog.dev",
    "linkedin": "https://linkedin.com/in/YOUR-PROFILE"
  },
  "project": {
    "title": "Your GSoC Project Title",
    "description": "Brief description of your project",
    "organization": "Your Organization Name",
    "timeline": "May 2024 - August 2024",
    "repository": "https://github.com/ORG/REPO"
  },
  "slack": {
    "workspaceUrl": "https://your-org.slack.com/join/shared_invite/xxx",
    "channels": ["general", "gsoc-2024", "your-project-channel"]
  },
  "mentors": [
    {
      "name": "Mentor Name",
      "email": "mentor@example.com",
      "avatar": "https://github.com/MENTOR-USERNAME.png",
      "role": "Lead Mentor",
      "github": "https://github.com/MENTOR-USERNAME"
    },
    {
      "name": "Co-Mentor Name",
      "email": "co-mentor@example.com",
      "avatar": "https://github.com/CO-MENTOR-USERNAME.png",
      "role": "Co-Mentor",
      "github": "https://github.com/CO-MENTOR-USERNAME"
    }
  ]
}
```

That's it! Cloudflare will serve the dashboard from the `public/` folder.

## 📖 Detailed Usage

### Adding Blog Posts

Edit `public/data/blog-posts.json`:

```json
[
  {
    "title": "Your Blog Post Title",
    "excerpt": "A brief summary of your post",
    "url": "https://yourblog.dev/post-url",
    "date": "2024-06-01",
    "readTime": "5 min read"
  }
]
```

### Adding Weekly Updates

Edit `public/data/weekly-updates.json`:

```json
[
  {
    "title": "Week 1: Getting Started",
    "summary": "What you accomplished this week",
    "date": "2024-06-03"
  }
]
```

### Adding Mentor Feedback

Edit `public/data/feedback.json`:

```json
[
  {
    "from": "Mentor Name",
    "content": "Feedback from your mentor",
    "date": "2024-06-05"
  }
]
```

### Adding Milestones

Edit `public/data/milestones.json`:

```json
[
  {
    "title": "Milestone Title",
    "description": "What you achieved",
    "date": "2024-06-10",
    "icon": "trophy"
  }
]
```

Available icons: `check-circle`, `users`, `code-branch`, `star`, `trophy`, `award`, `flag`

## 🤖 GitHub Actions Automation

The dashboard includes a GitHub Actions workflow that:

1. **Automatically fetches your GitHub contributions** (commits, PRs, issues, reviews)
2. **Updates the data** daily at midnight UTC
3. **Keeps the static data ready for Cloudflare** automatically

The workflow runs:
- Daily at midnight UTC (scheduled)
- When you push changes to `public/config.json` or `public/data/` files
- Manually via the Actions tab

### Manual Trigger

To manually update your dashboard:
1. Go to the **Actions** tab in your repository
2. Select **Update GSoC Dashboard**
3. Click **Run workflow**

## 🎨 Customization

### Colors & Styling

Edit `public/styles.css` to customize the appearance. The CSS uses CSS variables for easy theme customization:

```css
:root {
    --primary-color: #4285f4;
    --secondary-color: #34a853;
    --accent-color: #fbbc04;
    /* ... more variables */
}
```

### Layout

Modify `public/index.html` to change the dashboard layout or add new sections.

### Data Processing

The `public/dashboard.js` file handles all data loading and rendering. Modify it to add custom data processing logic.

## 🔄 Data refresh (Worker and KV)

`wrangler.toml` deploys `worker/index.js` with the static dashboard in `public/`. Once a day
[blt-cron](../blt-cron) calls the Worker's `POST /__scheduled`, which fetches:

- the student's recent public GitHub events (user from `public/config.json`) into
  `/data/github-contributions.json`;
- the forks of `OWASP-BLT/MY-GSOC-TOOL` (or the `FORKS_REPO` variable) into `/data/forks.json`.

Both are stored in Workers KV (binding `DATA`, namespace `my-gsoc-tool-data`) and served at those
paths, falling back to the committed files in `public/data/` until the first refresh. Nothing is
committed. Worker secrets: `CRON_SECRET` (same as blt-cron) and `GH_API_TOKEN`. After changing
`student.github` in `config.json`, the dashboard shows the new user's activity after the next daily
run, or right away with:

```bash
curl -X POST https://gsoc-tool.owaspblt.org/__scheduled -H "X-BLT-Cron-Secret: $CRON_SECRET" -d '{}'
```

Tests: `npm test`.

## 📋 File Structure

```
MY-GSOC-TOOL/
├── worker/                       # Worker: daily data refresh into KV
├── public/                       # Cloudflare static site root
│   ├── data/
│   │   ├── github-contributions.json # GitHub data fallback (live copy in KV)
│   │   ├── forks.json                # Forks list fallback (live copy in KV)
│   │   ├── blog-posts.json           # Your blog posts
│   │   ├── feedback.json             # Mentor feedback
│   │   ├── weekly-updates.json       # Weekly progress
│   │   └── milestones.json           # Your achievements
│   ├── index.html                # Dashboard HTML
│   ├── styles.css                # Dashboard styles
│   ├── dashboard.js              # Dashboard logic
│   └── config.json               # Your personal config
├── wrangler.toml                 # Cloudflare Worker, assets and KV config
└── README.md                     # This file
```

## 🔧 Troubleshooting

### Dashboard not updating?

1. Check that Cloudflare is serving `public` as the output directory
2. GitHub data refreshes once a day (00:03 UTC); the response header `X-Data-Updated-At` of
   `/data/github-contributions.json` shows when it last ran
3. Make sure `public/config.json` has valid JSON syntax

### GitHub contributions not showing?

1. Ensure your `public/config.json` has the correct GitHub username
2. Check the Worker's logs in the Cloudflare dashboard and that its `GH_API_TOKEN` secret is set
3. Verify your repository activity is public

### Custom domain?

Configure the custom domain in Cloudflare and point DNS at the Cloudflare project.

## 🤝 Contributing

Contributions are welcome! If you have ideas for improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🌟 Acknowledgments

- Built for Google Summer of Code students
- Inspired by the need for a comprehensive GSoC portfolio tool
- Thanks to all GSoC mentors and organizations

## 💡 Tips for GSoC Students

1. **Update regularly**: Commit your weekly updates and blog posts consistently
2. **Document everything**: Use the feedback section to track mentor interactions
3. **Share your dashboard**: Include the link in your GSoC proposal and final report
4. **Showcase achievements**: Add all your milestones, no matter how small
5. **Write blog posts**: Technical writing helps you and others learn

## 📞 Support

If you encounter issues or have questions:
- Open an issue in this repository
- Check existing issues for solutions
- Reach out to the community

---

## 🍴 Project Forks

The forks of the template repository (GitHub `OWASP-BLT/MY-GSOC-TOOL`) are listed at
[`/data/forks.json`](https://gsoc-tool.owaspblt.org/data/forks.json), refreshed daily by the site's
Worker. This section used to be rewritten by a workflow that committed to the repository.

---

**Made with ❤️ for GSoC Students**

Start your GSoC journey with a professional dashboard! 🚀
