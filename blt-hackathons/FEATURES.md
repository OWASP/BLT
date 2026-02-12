# Features Documentation

Complete guide to all features available in the BLT-Hackathon dashboard.

## 🏠 Dashboard Overview

The main dashboard (`index.html`) provides a comprehensive view of your hackathon with:
- Real-time statistics
- Visual charts
- Leaderboard rankings
- Repository information
- Prize details
- Sponsor showcase

## 📊 Core Features

### 1. Real-Time Statistics

**Quick Stats Panel**
- **Participants**: Unique contributors with merged PRs
- **Pull Requests**: Total PRs created during hackathon
- **Merged PRs**: Successfully merged contributions
- **Repositories**: Number of tracked repositories

**How it works:**
- Fetches data from GitHub API
- Filters by hackathon date range
- Excludes bot accounts automatically
- Updates when page is refreshed

### 2. Leaderboard

**Features:**
- Automatic ranking by merged PR count
- Shows top contributors
- Displays avatars and GitHub profiles
- Trophy icons for top 3 positions
- Expandable PR list for each contributor

**Configuration:**
```javascript
display: {
    maxLeaderboardEntries: 10,  // Number of entries to show
    showPRsInLeaderboard: true   // Show individual PRs
}
```

**Ranking Logic:**
1. Only counts merged PRs
2. PRs must be merged during hackathon period
3. Bot accounts are excluded
4. Ties are sorted by PR merge date

### 3. Activity Charts

**PR Activity Chart**
- Bar chart showing daily PR activity
- Two datasets: All PRs and Merged PRs
- Interactive tooltips
- Date range covers entire hackathon period

**Powered by Chart.js:**
- Responsive design
- Smooth animations
- Accessible color scheme
- Export capability (right-click)

### 4. Repository Tracking

**Repository Features:**
- List all tracked repositories
- Show PR statistics per repo
- Direct links to GitHub
- Quick access to pull requests
- **NEW: Organization-wide tracking**

**Repository Card Includes:**
- Repository name and owner
- Number of merged PRs
- Links to repository and PRs
- Repository description (if available)

**Configuration - Individual Repositories:**
```javascript
github: {
    repositories: [
        "owner/repo1",
        "owner/repo2"
    ]
}
```

**Configuration - Organization Tracking (NEW):**
```javascript
github: {
    organization: "OWASP-BLT",  // Track all repos in this organization
    repositories: []             // Optional: Add specific repos too
}
```

**How Organization Tracking Works:**
- Automatically fetches all repositories from the specified organization
- Updates dynamically as repos are added/removed from the organization
- Can be combined with explicit repository list
- Deduplicates repositories automatically
- Falls back to explicit repos if organization fetch fails

### 5. Prize Management

**Prize Display:**
- Visual hierarchy (1st, 2nd, 3rd, special)
- Custom titles and descriptions
- Optional monetary values
- Sponsor attribution

**Prize Types:**
- Position 1: Gold trophy icon
- Position 2: Silver trophy icon
- Position 3: Bronze trophy icon
- Position 4: Blue award icon (special prizes)

**Configuration Example:**
```javascript
prizes: [
    {
        position: 1,
        title: "First Place",
        description: "Amazing prize!",
        value: "500"  // Optional
    }
]
```

### 6. Sponsor Showcase

**Sponsor Levels:**
- Platinum: Highest tier
- Gold: Premium tier
- Silver: Standard tier
- Bronze: Basic tier
- Partner: In-kind sponsors

**Sponsor Features:**
- Logo display
- Website links
- Organized by tier
- Sponsorship information section

**Configuration:**
```javascript
sponsors: [
    {
        name: "Company Name",
        level: "gold",
        logo: "images/logo.png",
        website: "https://example.com"
    }
]
```

## 🔧 Technical Features

### 1. GitHub API Integration

**Features:**
- REST API v3 implementation
- Automatic pagination
- Smart caching (5-minute TTL)
- Rate limit handling
- Error recovery

**Rate Limits:**
- Without token: 60 requests/hour
- With token: 5,000 requests/hour

**API Calls:**
- Pull requests per repository
- Repository information
- User profiles (when needed)

### 2. Smart Caching

**Benefits:**
- Reduces API calls
- Faster page loads on refresh
- Prevents rate limit issues
- Improves performance

**How it works:**
- In-memory cache using Map()
- 5-minute cache duration
- Automatic cache invalidation
- Per-URL caching

### 3. Data Processing

**PR Filtering:**
- Date range filtering
- Status filtering (merged/open)
- Bot account exclusion
- Duplicate removal

**Statistics Calculation:**
- Unique participant counting
- Daily activity aggregation
- Per-repository totals
- Leaderboard generation

### 4. Responsive Design

**Breakpoints:**
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

**Optimizations:**
- Flexible grid layouts
- Stacked cards on mobile
- Readable fonts at all sizes
- Touch-friendly buttons

### 5. Performance

**Optimizations:**
- Lazy loading of images
- Efficient DOM updates
- Minimal JavaScript bundle
- CDN-hosted libraries

**Load Times:**
- Initial page: < 2 seconds
- API requests: 1-3 seconds
- Chart rendering: < 500ms

## 🎨 Customization Features

### 1. Branding

**Customizable Elements:**
- Hackathon name and title
- Description and rules
- Color scheme
- Banner image
- Logos and icons

**How to Customize:**
1. Edit `js/config.js` for text content
2. Edit `index.html` for structural changes
3. Add custom CSS in `<style>` section
4. Replace gradient with banner image

### 2. Date & Time

**Features:**
- Automatic status detection (Upcoming/Ongoing/Ended)
- Countdown timer
- Timezone support (UTC recommended)
- Flexible date ranges

**Status Logic:**
- **Upcoming**: Current time < start time
- **Ongoing**: Start time ≤ current time ≤ end time
- **Ended**: Current time > end time

### 3. Display Options

**Configurable Settings:**
```javascript
display: {
    showRepoStats: true,           // Show PR counts per repo
    maxLeaderboardEntries: 10,     // Leaderboard size
    showPRsInLeaderboard: true     // Expand PR details
}
```

## 🔒 Security Features

### 1. XSS Prevention

**Protection Methods:**
- HTML escaping on all user-generated content
- Sanitized URLs
- Safe innerHTML usage
- DOM-based rendering

### 2. API Security

**Best Practices:**
- Token stored in config (not in URL)
- HTTPS-only API calls
- No token exposure in DOM
- Rate limit compliance

### 3. Content Security

**Measures:**
- External resource integrity checks
- CDN-hosted libraries
- No inline scripts (except initial load)
- CORS compliance

## 📱 Mobile Features

**Mobile-Optimized:**
- Responsive navigation
- Touch-friendly buttons
- Readable text sizes
- Optimized charts
- Fast loading

**Progressive Enhancement:**
- Works without JavaScript (basic content)
- Graceful degradation
- Accessible to all devices

## ♿ Accessibility Features

**WCAG 2.1 Compliance:**
- Semantic HTML5 elements
- ARIA labels where needed
- Keyboard navigation support
- Color contrast compliance
- Screen reader friendly

**Navigation:**
- Logical tab order
- Skip links (can be added)
- Focus indicators
- Clear link text

## 🚀 Deployment Features

### 1. GitHub Pages Support

**Features:**
- One-click deployment
- Automatic builds
- Custom domain support
- HTTPS by default

**Workflow:**
- Push to main branch
- Automatic deployment via Actions
- Live in minutes

### 2. Zero Configuration

**Out-of-the-Box:**
- No build step required
- No dependencies to install
- Static file hosting
- CDN-delivered assets

### 3. Version Control

**Git-Friendly:**
- All configuration in git
- Easy rollback
- Branch-based staging
- Collaborative editing

## 📈 Analytics Integration

**Supported Analytics:**
- Google Analytics (add script)
- Plausible Analytics
- Simple Analytics
- Custom tracking

**How to Add:**
Insert tracking code in `index.html` before `</head>`:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## 🔄 Future Features (Planned)

- [ ] Live updates with WebSocket
- [ ] PR approval workflows
- [ ] Multi-language support
- [ ] Export leaderboard as CSV
- [ ] Email notifications
- [ ] Social media integration
- [ ] Advanced filtering options
- [ ] Custom scoring algorithms
- [ ] Team competitions
- [ ] Badge generation

## 💡 Feature Requests

Have an idea for a new feature? 
- Open an issue on GitHub
- Tag it with `enhancement`
- Describe the use case
- Provide examples if possible

---

**Questions about features?** Check the [FAQ](README.md#faq) or open a discussion!
