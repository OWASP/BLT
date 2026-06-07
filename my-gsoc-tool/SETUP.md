# Setup Guide for Your GSoC Dashboard

Welcome to your GSoC Dashboard! This guide will walk you through setting up your personalized dashboard in just a few minutes.

## 📋 Prerequisites

- A GitHub account
- Participation in Google Summer of Code (or any open-source program)
- A web browser

## 🚀 Step-by-Step Setup

### 1. Fork This Repository

1. Click the **Fork** button at the top right of the [repository page](https://github.com/OWASP-BLT/MY-GSOC-TOOL)
2. Wait for GitHub to create your fork
3. You now have your own copy at `https://github.com/YOUR-USERNAME/MY-GSOC-TOOL`

### 2. Deploy on Cloudflare

Cloudflare will host your dashboard from the `public/` folder:

1. Create a Cloudflare Pages project from this repository
2. Leave the build command empty
3. Set the build output directory to `public`
4. Deploy the project

Cloudflare will provide a project URL after the first deploy.

### 3. Configure Your Personal Information

#### Edit `public/config.json`

This is the main configuration file for your dashboard. Click on `public/config.json` in your repository and then click the pencil icon to edit.

Replace the placeholder values with your information:

```json
{
  "student": {
    "name": "Jane Doe",
    "bio": "GSoC 2024 @ OWASP | Full-Stack Developer",
    "avatar": "https://github.com/janedoe.png",
    "github": "https://github.com/janedoe",
    "email": "jane.doe@example.com",
    "blog": "https://janedoe.dev",
    "linkedin": "https://linkedin.com/in/janedoe"
  },
  "project": {
    "title": "BLT - Bug Logging Tool Enhancement",
    "description": "Improving the bug reporting and management system with new features including advanced search, real-time notifications, and an improved UI.",
    "organization": "OWASP Foundation",
    "timeline": "May 2024 - August 2024",
    "repository": "https://github.com/OWASP-BLT/BLT"
  },
  "slack": {
    "workspaceUrl": "https://owasp.slack.com/join/shared_invite/zt-xyz",
    "channels": [
      "general",
      "gsoc-2024",
      "blt-project"
    ]
  },
  "mentor": {
    "name": "John Smith",
    "email": "john.smith@owasp.org",
    "avatar": "https://github.com/johnsmith.png",
    "role": "OWASP BLT Maintainer & GSoC Mentor",
    "github": "https://github.com/johnsmith"
  }
}
```

**Tips:**
- For `avatar`, use `https://github.com/YOUR-USERNAME.png` to automatically use your GitHub profile picture
- Leave any field empty (use `""`) if you don't want to display it
- The `repository` should point to the main project you're contributing to

#### Commit Your Changes

After editing, scroll down and click **Commit changes**.

### 4. Add Your Content

#### Blog Posts (`public/data/blog-posts.json`)

Add your GSoC blog posts:

```json
[
  {
    "title": "GSoC 2024: My Journey Begins",
    "excerpt": "Excited to share that I've been selected for GSoC 2024! Here's what I'll be working on.",
    "url": "https://janedoe.dev/gsoc-2024-begins",
    "date": "2024-05-01",
    "readTime": "5 min read"
  },
  {
    "title": "First Week: Understanding the Codebase",
    "excerpt": "My first week involved diving deep into the existing codebase and understanding the architecture.",
    "url": "https://janedoe.dev/week-1-codebase",
    "date": "2024-06-03",
    "readTime": "8 min read"
  }
]
```

#### Weekly Updates (`public/data/weekly-updates.json`)

Track your weekly progress:

```json
[
  {
    "title": "Week 1: Project Setup & Planning",
    "summary": "Set up development environment, reviewed project requirements with mentor, created initial project timeline and milestones.",
    "date": "2024-06-03"
  },
  {
    "title": "Week 2: Database Schema Design",
    "summary": "Designed the new database schema for enhanced search functionality. Reviewed with mentor and got approval.",
    "date": "2024-06-10"
  }
]
```

#### Mentor Feedback (`public/data/feedback.json`)

Document feedback from your mentor:

```json
[
  {
    "from": "John Smith",
    "content": "Excellent work on the initial setup! Your code organization is clean and follows the project's conventions. Looking forward to seeing the feature implementation.",
    "date": "2024-06-05"
  },
  {
    "from": "John Smith",
    "content": "Great job handling the code review feedback. Your approach to testing is thorough and will help maintain code quality.",
    "date": "2024-06-20"
  }
]
```

#### Milestones (`public/data/milestones.json`)

Celebrate your achievements:

```json
[
  {
    "title": "GSoC Proposal Accepted",
    "description": "My project proposal was accepted! Ready to start this amazing journey.",
    "date": "2024-05-01",
    "icon": "check-circle"
  },
  {
    "title": "First PR Merged",
    "description": "Successfully merged my first pull request implementing the search API endpoint.",
    "date": "2024-06-15",
    "icon": "code-branch"
  },
  {
    "title": "Mid-term Evaluation Passed",
    "description": "Passed the mid-term evaluation with positive feedback from my mentor!",
    "date": "2024-07-15",
    "icon": "star"
  }
]
```

**Available Icons:**
- `check-circle` - Checkmark
- `users` - People/team
- `code-branch` - Git branch
- `star` - Star
- `trophy` - Trophy
- `award` - Award medal
- `flag` - Flag
- `rocket` - Rocket
- `lightbulb` - Lightbulb

### 5. Automatic GitHub Contributions

The dashboard automatically fetches your GitHub activity! The workflow:

1. Runs daily at midnight UTC
2. Fetches your commits, pull requests, issues, and reviews
3. Updates `public/data/github-contributions.json`
4. Leaves the updated dashboard ready for Cloudflare to serve from `public/`

**Manual Update:**
1. Go to the **Actions** tab in your repository
2. Click **Update GSoC Dashboard**
3. Click **Run workflow** → **Run workflow**

### 6. View Your Dashboard

After setup, your dashboard will be live at the URL Cloudflare gives your Pages project. Give it a few minutes for the initial deployment to complete.

## 🎨 Customization Tips

### Change Colors

Edit `public/styles.css` and modify the CSS variables:

```css
:root {
    --primary-color: #4285f4;    /* Main brand color */
    --secondary-color: #34a853;   /* Secondary brand color */
    --accent-color: #fbbc04;      /* Accent/highlight color */
    --danger-color: #ea4335;      /* Error/danger color */
}
```

### Add Custom Sections

Edit `public/index.html` to add your own sections following the existing card pattern:

```html
<section class="card">
    <h2><i class="fas fa-your-icon"></i> Your Section Title</h2>
    <div id="your-content">
        <!-- Your content here -->
    </div>
</section>
```

### Modify Layout

The dashboard uses CSS Grid. Edit the grid in `public/styles.css`:

```css
.content-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
    gap: 30px;
}
```

## 📱 Sharing Your Dashboard

Once your dashboard is live, share it:

1. **In Your GSoC Proposal** - Link to your dashboard to showcase your preparation
2. **In Your Final Report** - Document your entire journey
3. **On Social Media** - Share your progress with the community
4. **In Your Resume** - Demonstrate your GSoC experience
5. **With Your Organization** - Keep everyone updated on your progress

## 🐛 Troubleshooting

### Dashboard Not Showing

**Problem:** The page shows a 404 error.

**Solution:**
1. Check that Cloudflare is serving the `public` output directory
2. Verify the source is set to "GitHub Actions"
3. Check the Actions tab to see if the workflow ran successfully

### GitHub Contributions Not Updating

**Problem:** The contributions section shows zeros or old data.

**Solution:**
1. Go to Actions tab and manually trigger the workflow
2. Check if the workflow has proper permissions
3. Verify your GitHub username in `public/config.json` is correct
4. Make sure your contributions are public (not in private repos)

### Invalid JSON Errors

**Problem:** Dashboard shows errors or doesn't load.

**Solution:**
1. Validate your JSON files at [jsonlint.com](https://jsonlint.com)
2. Common issues:
   - Missing commas between items
   - Extra comma after the last item
   - Unescaped quotes in strings
   - Missing closing brackets

### Styling Issues

**Problem:** The page looks broken or unstyled.

**Solution:**
1. Clear your browser cache (Ctrl+Shift+R or Cmd+Shift+R)
2. Check the browser console for errors (F12)
3. Verify all files are committed and pushed

## 💡 Best Practices

1. **Update Regularly:** Commit your progress weekly to keep the dashboard current
2. **Write Meaningful Updates:** Provide context in your weekly summaries
3. **Document Challenges:** Share not just successes, but also challenges you overcame
4. **Get Mentor Feedback:** Regularly ask for and document mentor feedback
5. **Blog Consistently:** Technical blogs help you reflect and help others learn
6. **Celebrate Wins:** Don't forget to add milestones, even small ones!

## 📞 Need Help?

- **Issues:** Open an issue in the [original repository](https://github.com/OWASP-BLT/MY-GSOC-TOOL/issues)
- **Discussions:** Join the discussions tab for questions
- **Documentation:** Check the main [README.md](README.md) for detailed documentation

## 🎉 You're All Set!

Congratulations! Your GSoC dashboard is now live. Keep it updated throughout your GSoC journey, and best of luck with your project! 🚀

---

**Remember:** This dashboard is yours to customize. Feel free to modify it to best represent your journey and style!
