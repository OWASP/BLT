# BLT-Hackathon 🏆

A self-hosted GitHub Pages hackathon platform that lets you conduct a hackathon on your project with **charts**, **leaderboards**, and **prizes**!

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Pages](https://img.shields.io/badge/Deployed%20on-GitHub%20Pages-blue)](https://pages.github.com/)

## ✨ Features

- 📊 **Real-time Leaderboards** - Automatically track and rank contributors based on merged pull requests
- 📈 **Activity Charts** - Visualize pull request activity over time with beautiful charts
- 🏆 **Prize Management** - Showcase prizes and awards for top contributors
- 🤝 **Sponsor Display** - Highlight your hackathon sponsors
- 📱 **Responsive Design** - Works perfectly on desktop and mobile devices
- 🚀 **Zero Backend** - Runs entirely on GitHub Pages using GitHub API
- ⚡ **Easy Setup** - Just edit a config file and deploy!

## 🎯 Quick Start

### 1. Fork or Clone This Repository

```bash
git clone https://github.com/OWASP-BLT/BLT-Hackathon.git
cd BLT-Hackathon
```

### 2. Configure Your Hackathon

Edit `js/config.js` and customize the following:

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
    },
    prizes: [
        {
            position: 1,
            title: "First Place",
            description: "Amazing prize!",
            value: "500"
        }
        // Add more prizes...
    ]
};
```

### 3. Deploy to GitHub Pages

1. Push your changes to GitHub
2. Go to your repository **Settings** → **Pages**
3. Under "Source", select the branch you want to deploy (usually `main`)
4. Your hackathon dashboard will be live at: `https://your-username.github.io/BLT-Hackathon/`

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

**GitHub Token (Recommended):**
- Go to [GitHub Settings → Tokens](https://github.com/settings/tokens)
- Create a new token with `public_repo` scope
- Add it to the config to avoid API rate limits (60 requests/hour without token, 5000 with token)

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

To run multiple hackathons:

1. Create separate branches for each hackathon
2. Configure GitHub Pages to deploy from different branches
3. Each branch gets its own URL: `your-repo.github.io/branch-name/`

### Custom Domain

1. Add a `CNAME` file to your repository with your domain
2. Configure DNS settings with your domain provider
3. Enable custom domain in GitHub Pages settings

### Adding Analytics

Add Google Analytics or other tracking by inserting the code before the closing `</head>` tag in `index.html`.

## 🛠️ Development

### Local Testing

Simply open `index.html` in a web browser, or use a local server:

```bash
# Using Python 3
python -m http.server 8000

# Using Node.js
npx serve

# Visit http://localhost:8000
```

### File Structure

```
BLT-Hackathon/
├── index.html           # Main HTML file
├── js/
│   ├── config.js        # Hackathon configuration
│   ├── github-api.js    # GitHub API integration
│   └── main.js          # Dashboard logic
├── images/              # Optional: images and logos
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

Inspired by [OWASP BLT](https://github.com/OWASP-BLT/BLT) hackathon functionality.

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

- **Issues**: [GitHub Issues](https://github.com/OWASP-BLT/BLT-Hackathon/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OWASP-BLT/BLT-Hackathon/discussions)

---

Made with ❤️ by the OWASP BLT community
