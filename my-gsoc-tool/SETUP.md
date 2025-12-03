# Setup Guide for GSoC Dashboard

A simple guide to set up your personalized GSoC dashboard to showcase your journey.

## Prerequisites

- A GitHub account
- Basic understanding of JSON

## Quick Setup

### Step 1: Fork Repository

1. Click **Fork** on this repository 
2. You'll have your copy at `https://github.com/YOUR-USERNAME/MY-GSOC-TOOL`

### Step 2: Enable GitHub Pages

1. Go to your repository **Settings** → **Pages**
2. Under **Source**, select **Deploy from a branch**
3. Choose **main** branch and **/ (root)** folder
4. Click **Save**

Your dashboard will be at: `https://YOUR-USERNAME.github.io/MY-GSOC-TOOL/`

### Step 3: Add Your Information

Edit `config.json` with your details:

```json
{
  "student": {
    "name": "Your Name",
    "email": "your.email@example.com",
    "bio": "Google Summer of Code contributor",
    "avatar": "https://github.com/YOUR-USERNAME.png",
    "github": "https://github.com/YOUR-USERNAME",
    "blog": "https://yourblog.dev",
    "linkedin": "https://linkedin.com/in/your-profile"
  }
}
```

## Adding Content

### Blog Posts (`data/blog-posts.json`)

```json
[
  {
    "title": "Week 1: Project Setup",
    "summary": "Set up development environment and met with mentors",
    "date": "2024-05-27",
    "_id": 1764524100639
  }
]
```

### Weekly Updates (`data/weekly-updates.json`)

```json
[
  {
    "title": "Week 1: Project Setup & Research",
    "summary": "Set up development environment, studied codebase, met with mentors",
    "date": "2024-05-27"
  }
]
```

### Mentor Information (`data/mentor.json`)

```json
{
  "mentor": {
    "avatar": "https://github.com/MENTOR-USERNAME.png",
    "name": "Mentor Name",
    "role": "Project Mentor",
    "email": "mentor@example.com"
  },
  "feedback": [
    {
      "from": "Mentor Name",
      "content": "Great work on the initial setup!",
      "date": "2024-05-25",
      "_id": 1764523378238.7498
    }
  ]
}
```

### Milestones (`data/milestones.json`)

```json
[
  {
    "title": "Project Proposal Accepted",
    "description": "Successfully got GSoC project proposal accepted",
    "date": "2024-05-01",
    "icon": "check-circle"
  }
]
```

**Available icons:** `check-circle`, `users`, `code-branch`, `star`, `trophy`, `award`, `flag`

### Community Participation (`data/community.json`)

```json
{
  "platformUrl": "https://your-org-chat.com",
  "channels": [
    {
      "name": "general",
      "_id": 1764525252158
    },
    {
      "name": "gsoc-2024",
      "_id": 1764526631085
    }
  ]
}
```

## Live Editing Mode

Add `?edit=true` to your URL to enable live editing:
`https://YOUR-USERNAME.github.io/MY-GSOC-TOOL/?edit=true`

### Setup Live Editing

1. **Get GitHub Token:**
   - Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
   - Generate new token with `repo` scope
   - Copy the token

2. **Configure Repository:**
   Edit `libs/constants.js`:
   ```javascript
   export const OWNER = "your-github-username";
   export const REPO = "MY-GSOC-TOOL";
   export const EMAIL = "your.email@example.com"
   export const BRANCH = "main"
   ```

3. **Start Editing:**
   - Visit your dashboard with `?edit=true`
   - Enter your GitHub token
   - Click Edit buttons on any section

## Troubleshooting

**Dashboard not showing?**
- Check GitHub Pages is enabled
- Wait 5-10 minutes for first deployment

**Edit mode not working?**
- Check your GitHub token has `repo` scope
- Verify `libs/constants.js` has correct username

**JSON errors?**
- Validate JSON at [jsonlint.com](https://jsonlint.com)
- Check for missing commas or quotes

## Tips

- Update content regularly
- Use the live editing mode for easy updates
- Add milestones to celebrate achievements
- Document mentor feedback
- Keep weekly updates consistent

Your dashboard is ready! Visit `https://YOUR-USERNAME.github.io/MY-GSOC-TOOL/` to see it live.
