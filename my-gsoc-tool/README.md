# GSoC Student Dashboard 🎓

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

### Step 2: Enable GitHub Pages

1. Go to your forked repository's **Settings** → **Pages**
2. Under "Source", select **GitHub Actions**
3. Save the changes

### Step 3: Customize Your Dashboard

Edit `config.json` with your information:

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
  "mentor": {
    "name": "Mentor Name",
    "email": "mentor@example.com",
    "avatar": "https://github.com/MENTOR-USERNAME.png",
    "role": "Project Mentor"
  }
}
```

That's it! Your dashboard will be live at `https://YOUR-USERNAME.github.io/MY-GSOC-TOOL/`

## 📖 Detailed Usage

### Adding Blog Posts

Edit `data/blog-posts.json`:

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

Edit `data/weekly-updates.json`:

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

Edit `data/feedback.json`:

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

Edit `data/milestones.json`:

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
3. **Deploys to GitHub Pages** automatically

The workflow runs:
- Daily at midnight UTC (scheduled)
- When you push changes to `config.json` or `data/` files
- Manually via the Actions tab

### Manual Trigger

To manually update your dashboard:
1. Go to the **Actions** tab in your repository
2. Select **Update GSoC Dashboard**
3. Click **Run workflow**

## 🎨 Customization

### Colors & Styling

Edit `styles.css` to customize the appearance. The CSS uses CSS variables for easy theme customization:

```css
:root {
    --primary-color: #4285f4;
    --secondary-color: #34a853;
    --accent-color: #fbbc04;
    /* ... more variables */
}
```

### Layout

Modify `index.html` to change the dashboard layout or add new sections.

### Data Processing

The `dashboard.js` file handles all data loading and rendering. Modify it to add custom data processing logic.

## 📋 File Structure

```
MY-GSOC-TOOL/
├── .github/
│   └── workflows/
│       └── update-dashboard.yml  # GitHub Actions workflow
├── data/
│   ├── github-contributions.json # Auto-generated GitHub data
│   ├── blog-posts.json          # Your blog posts
│   ├── feedback.json            # Mentor feedback
│   ├── weekly-updates.json      # Weekly progress
│   └── milestones.json          # Your achievements
├── index.html                    # Dashboard HTML
├── styles.css                    # Dashboard styles
├── dashboard.js                  # Dashboard logic
├── config.json                   # Your personal config
└── README.md                     # This file
```

## 🔧 Troubleshooting

### Dashboard not updating?

1. Check that GitHub Pages is enabled in Settings → Pages
2. Verify the GitHub Actions workflow ran successfully in the Actions tab
3. Make sure `config.json` has valid JSON syntax

### GitHub contributions not showing?

1. Ensure your `config.json` has the correct GitHub username
2. Check that the GitHub Actions workflow has the necessary permissions
3. Verify your repository activity is public

### Custom domain?

Add a `CNAME` file to the repository root with your domain name, and configure your DNS settings.

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

<!-- FORKS_START -->
## 🍴 Project Forks

The following users have forked this project:

- [Pritz395/MY-GSOC-TOOL](https://github.com/Pritz395/MY-GSOC-TOOL) - ⭐ 1 stars
- [mdkaifansari04/MY-GSOC-TOOL](https://github.com/mdkaifansari04/MY-GSOC-TOOL) - ⭐ 0 stars
- [ananya-09/MY-GSOC-TOOL](https://github.com/ananya-09/MY-GSOC-TOOL) - ⭐ 0 stars
- [arnavkirti/MY-GSOC-TOOL](https://github.com/arnavkirti/MY-GSOC-TOOL) - ⭐ 0 stars
- [Krishiv-Mahajan/MY-GSOC-TOOL](https://github.com/Krishiv-Mahajan/MY-GSOC-TOOL) - ⭐ 0 stars
- [sidd190/MY-GSOC-TOOL](https://github.com/sidd190/MY-GSOC-TOOL) - ⭐ 0 stars
- [DishaA06/MY-GSOC-TOOL](https://github.com/DishaA06/MY-GSOC-TOOL) - ⭐ 0 stars

_Last updated: 2026-01-12 00:24:04 UTC_
<!-- FORKS_END -->

---

**Made with ❤️ for GSoC Students**

Start your GSoC journey with a professional dashboard! 🚀
