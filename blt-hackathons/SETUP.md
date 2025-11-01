# Quick Setup Guide

Follow these steps to get your hackathon dashboard up and running in minutes!

## Step 1: Get the Code

**Option A: Use the GitHub Template**
1. Click "Use this template" at the top of the repository
2. Create your new repository

**Option B: Fork the Repository**
1. Click "Fork" at the top right
2. Clone your fork to your local machine

**Option C: Clone Directly**
```bash
git clone https://github.com/OWASP-BLT/BLT-Hackathon.git my-hackathon
cd my-hackathon
```

## Step 2: Configure Your Hackathon

Open `js/config.js` and update:

### 🎯 Required Settings

```javascript
// 1. Name and description
name: "Your Hackathon Name Here"
description: "An exciting coding competition..."

// 2. Dates (use ISO 8601 format)
startTime: "2024-01-15T00:00:00Z"  // January 15, 2024, midnight UTC
endTime: "2024-01-31T23:59:59Z"    // January 31, 2024, 11:59 PM UTC

// 3. Repositories to track
github: {
    repositories: [
        "your-org/your-repo",
        "your-org/another-repo"
    ]
}
```

### ⚙️ Optional Settings

**GitHub Token (Recommended)**
```javascript
github: {
    token: "ghp_your_token_here",  // Increases rate limit from 60 to 5000/hour
    repositories: [...]
}
```

**Prizes**
```javascript
prizes: [
    {
        position: 1,
        title: "First Place - The Champion",
        description: "Amazing prize package including cash and swag!",
        value: "500"
    }
]
```

**Sponsors**
```javascript
sponsors: [
    {
        name: "Awesome Company",
        level: "gold",  // platinum, gold, silver, bronze, or partner
        logo: "images/company-logo.png",
        website: "https://company.com"
    }
]
```

## Step 3: Get a GitHub Token (Optional but Recommended)

Without a token, you're limited to 60 API requests per hour. With a token, you get 5000!

1. Go to [GitHub Settings → Tokens](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name like "Hackathon Dashboard"
4. Select scope: **public_repo** (for public repositories only)
5. Click "Generate token"
6. Copy the token and paste it in your config:
   ```javascript
   github: {
       token: "ghp_YourTokenHere123456789",
       repositories: [...]
   }
   ```

⚠️ **Important**: Never commit your token to a public repository! Consider using environment variables or GitHub Secrets for production.

## Step 4: Test Locally

Open `index.html` in your browser or run a local server:

```bash
# Python 3
python -m http.server 8000

# Node.js
npx serve

# Then visit: http://localhost:8000
```

Check that:
- ✅ Hackathon name and description appear correctly
- ✅ Dates display properly
- ✅ Repositories are listed
- ✅ Leaderboard loads (if hackathon has started)

## Step 5: Deploy to GitHub Pages

### Method 1: From Settings (Easiest)

1. Push your changes to GitHub:
   ```bash
   git add .
   git commit -m "Configure hackathon settings"
   git push origin main
   ```

2. Go to your repository on GitHub
3. Click **Settings** → **Pages**
4. Under "Source", select `main` branch
5. Click **Save**
6. Your site will be live at: `https://your-username.github.io/repository-name/`

### Method 2: Using GitHub Actions

Create `.github/workflows/pages.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/upload-pages-artifact@v2
        with:
          path: '.'
      - uses: actions/deploy-pages@v2
```

## Step 6: Share Your Hackathon!

Once deployed, share your hackathon dashboard:
- 📱 Social media
- 📧 Email newsletters  
- 💬 Community forums
- 📝 Blog posts

## Troubleshooting

### "Failed to load hackathon data"
- Check browser console for errors
- Verify repository names are correct (format: `owner/repo`)
- Ensure repositories are public (or token has access)

### Rate Limit Errors
- Add a GitHub token to your config
- Wait for the rate limit to reset (usually 1 hour)

### Leaderboard is Empty
- Check that the hackathon dates are correct
- Verify PRs were merged during the hackathon period
- Look at browser console for API errors

### Dates are Wrong
- Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`
- Times are in UTC (add timezone offset if needed)
- Example: "2024-01-15T00:00:00Z"

## Next Steps

- 🎨 Customize colors and styling in `index.html`
- 🖼️ Add sponsor logos to `images/` folder
- 📊 Monitor the dashboard during your hackathon
- 🏆 Announce winners based on the leaderboard

## Need Help?

- 📖 Read the full [README](README.md)
- 💬 Check [Discussions](https://github.com/OWASP-BLT/BLT-Hackathon/discussions)
- 🐛 Report issues on [GitHub Issues](https://github.com/OWASP-BLT/BLT-Hackathon/issues)

Happy hacking! 🚀
