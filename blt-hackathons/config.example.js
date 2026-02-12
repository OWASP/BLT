/**
 * Example Hackathon Configuration
 * 
 * This is a complete example showing all available options.
 * Copy values from here to js/config.js to customize your hackathon.
 */

const EXAMPLE_CONFIG = {
    // =====================
    // BASIC INFORMATION
    // =====================
    
    name: "Hacktoberfest 2024 - OWASP Edition",
    
    description: `
        Join us for an exciting month of open source contributions! 
        Whether you're a seasoned developer or just getting started, 
        this is your chance to contribute to security tools that make 
        the web safer for everyone. All skill levels welcome!
    `,
    
    rules: `
        1. Pull requests must be submitted between October 1-31, 2024
        2. Only merged pull requests count toward the leaderboard
        3. PRs must be made to the repositories listed below
        4. Quality over quantity - spam PRs will be disqualified
        5. Follow each project's contribution guidelines
        6. Be respectful and collaborative
        7. Have fun and learn something new!
    `,
    
    // =====================
    // TIMELINE
    // =====================
    // Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
    // Times are in UTC
    
    startTime: "2024-10-01T00:00:00Z",
    endTime: "2024-10-31T23:59:59Z",
    
    // =====================
    // GITHUB CONFIGURATION
    // =====================
    
    github: {
        // Personal access token (optional but highly recommended)
        // Get one at: https://github.com/settings/tokens
        // Required scopes: public_repo (for public repos)
        token: "", // Add your token here
        
        // Option 1: Track specific repositories
        // Format: "owner/repo-name"
        repositories: [
            "OWASP-BLT/BLT",
            "OWASP-BLT/BLT-Flutter",
            "OWASP-BLT/BLT-Bacon",
            "OWASP-BLT/BLT-Action",
            "OWASP-BLT/BLT-Extension",
            "OWASP-BLT/OWASP-BLT-Website-Monitor",
            "OWASP-BLT/BLT-on-Cloudflare",
            "OWASP-BLT/BLT-Tomato",
            "OWASP-BLT/BLT-Sammich",
            "OWASP-BLT/OWASP-BLT-Lyte",
            "OWASP-BLT/.github"
        ]
        
        // Option 2: Track ALL repositories in an organization
        // Uncomment the line below to track all repos in an organization:
        // organization: "OWASP-BLT"
        
        // Note: You can use both 'organization' and 'repositories' together.
        // The system will track all org repos PLUS any additional repos you list.
    },
    
    // =====================
    // PRIZES
    // =====================
    
    prizes: [
        {
            position: 1,
            title: "🥇 First Place - Grand Champion",
            description: "The top contributor wins $500 cash prize, exclusive swag pack, and a featured blog post about their contributions!",
            value: "500"
        },
        {
            position: 2,
            title: "🥈 Second Place - Runner Up",
            description: "Second place receives $300 cash prize and OWASP swag pack.",
            value: "300"
        },
        {
            position: 3,
            title: "🥉 Third Place - Bronze Star",
            description: "Third place winner gets $200 cash prize and swag.",
            value: "200"
        },
        {
            position: 4,
            title: "🌟 Best First-Time Contributor",
            description: "Special prize for someone making their first open source contribution! Includes $100 and a beginner's swag pack.",
            value: "100"
        },
        {
            position: 4,
            title: "🎯 Most Impactful PR",
            description: "For the pull request that makes the biggest impact. Judged by maintainers. Prize: $150 and recognition.",
            value: "150"
        },
        {
            position: 4,
            title: "📚 Best Documentation",
            description: "For outstanding documentation contributions. Prize: $100 and technical writing resources.",
            value: "100"
        }
    ],
    
    // =====================
    // SPONSORS
    // =====================
    
    sponsors: [
        // Platinum Sponsors ($10,000+)
        {
            name: "TechCorp Global",
            level: "platinum",
            logo: "images/sponsors/techcorp-logo.png",
            website: "https://techcorp.example.com"
        },
        
        // Gold Sponsors ($5,000+)
        {
            name: "SecureCloud Systems",
            level: "gold",
            logo: "images/sponsors/securecloud-logo.png",
            website: "https://securecloud.example.com"
        },
        {
            name: "DevTools Inc",
            level: "gold",
            logo: "images/sponsors/devtools-logo.png",
            website: "https://devtools.example.com"
        },
        
        // Silver Sponsors ($2,500+)
        {
            name: "OpenSource Foundation",
            level: "silver",
            logo: "images/sponsors/osf-logo.png",
            website: "https://osf.example.com"
        },
        
        // Bronze Sponsors ($1,000+)
        {
            name: "Local Tech Meetup",
            level: "bronze",
            logo: "images/sponsors/meetup-logo.png",
            website: "https://meetup.example.com"
        },
        
        // Partners (In-kind sponsors)
        {
            name: "GitHub",
            level: "partner",
            logo: "images/sponsors/github-logo.png",
            website: "https://github.com"
        }
    ],
    
    // Additional sponsor information
    sponsorNote: `
        Interested in sponsoring our hackathon? We offer various sponsorship 
        tiers with benefits including logo placement, social media mentions, 
        and direct engagement with participants. Contact us to learn more!
    `,
    sponsorLink: "mailto:sponsors@example.com",
    
    // =====================
    // DISPLAY OPTIONS
    // =====================
    
    display: {
        // Show repository statistics (PR counts per repo)
        showRepoStats: true,
        
        // Maximum number of entries to show on leaderboard
        maxLeaderboardEntries: 15,
        
        // Show individual PRs in leaderboard entries
        showPRsInLeaderboard: true
    }
};

// =====================
// DATE FORMAT EXAMPLES
// =====================

/*
Common date/time examples in ISO 8601 format:

January 1, 2024 at midnight UTC:
"2024-01-01T00:00:00Z"

February 14, 2024 at 9:00 AM EST (14:00 UTC):
"2024-02-14T14:00:00Z"

December 31, 2024 at 11:59 PM PST (7:59 AM next day UTC):
"2025-01-01T07:59:00Z"

Note: Always use UTC (Z suffix) for consistency across timezones!
*/

// =====================
// REPOSITORY FORMAT
// =====================

/*
Repository format is always: "owner/repo-name"

Examples:
- "facebook/react"
- "microsoft/vscode"  
- "OWASP-BLT/BLT"
- "your-organization/your-project"

Make sure repositories are:
1. Public (or your token has access)
2. Active (has pull requests)
3. Correctly spelled

ORGANIZATION TRACKING:
Instead of listing individual repositories, you can track all repositories
in a GitHub organization by using the 'organization' field:

github: {
    token: "",
    organization: "OWASP-BLT"  // Track all repos in this org
}

This is particularly useful for organizations with many repositories
or when repositories are added/removed frequently.
*/

// =====================
// TOKEN SETUP GUIDE
// =====================

/*
To get a GitHub token:

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it something like "Hackathon Dashboard"
4. Set expiration (recommend: No expiration for long-term hackathons)
5. Select scopes:
   - ✅ public_repo (for public repositories)
   - ✅ repo (if tracking private repositories)
6. Click "Generate token"
7. Copy the token (you won't see it again!)
8. Paste it in the config:
   
   github: {
       token: "ghp_your_token_here_abc123xyz789",
       repositories: [...]
   }

⚠️ SECURITY WARNING:
Never commit tokens to public repositories!
For production, use environment variables or GitHub Secrets.
*/

// =====================
// CUSTOMIZATION TIPS
// =====================

/*
1. COLORS: 
   - Edit index.html and replace "red-600" with your brand color
   - Available colors: blue, green, purple, pink, indigo, yellow, etc.

2. BANNER:
   - Add a banner image in the images/ folder
   - Reference it in index.html's banner section

3. FONTS:
   - Add Google Fonts or custom fonts in index.html <head>

4. ADDITIONAL PAGES:
   - Create separate HTML pages for rules, FAQs, etc.
   - Link to them from index.html

5. ANALYTICS:
   - Add Google Analytics or similar tracking code
   - Insert before </head> in index.html

6. SOCIAL SHARING:
   - Add Open Graph meta tags to index.html for better sharing
*/
