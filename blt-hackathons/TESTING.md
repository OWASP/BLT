# Testing Your Hackathon Dashboard

Before going live, test your hackathon dashboard to ensure everything works correctly.

## Pre-Deployment Checklist

### ✅ Configuration
- [ ] Hackathon name and description are set
- [ ] Start and end dates are correct (ISO 8601 format)
- [ ] All repository names are correct (format: `owner/repo`)
- [ ] Prizes are configured (if applicable)
- [ ] Sponsors are configured (if applicable)
- [ ] GitHub token is added (recommended)

### ✅ Files
- [ ] `index.html` exists
- [ ] `js/config.js` exists and is properly configured
- [ ] `js/github-api.js` exists
- [ ] `js/main.js` exists
- [ ] Images are in `images/` folder (if using sponsor logos or banners)

### ✅ Testing

#### Local Testing

1. **Start a local server:**
   ```bash
   # Option 1: Python
   python -m http.server 8000
   
   # Option 2: Node.js
   npx serve
   
   # Option 3: PHP
   php -S localhost:8000
   ```

2. **Open in browser:** `http://localhost:8000`

3. **Check browser console:**
   - Press F12 (or Cmd+Option+I on Mac)
   - Look for errors in the Console tab
   - Verify API requests in the Network tab

#### Manual Test Cases

**Test 1: Page Loads**
- [ ] Page displays without errors
- [ ] Navigation bar shows hackathon name
- [ ] Banner section displays correctly
- [ ] Status badge shows correct status (Upcoming/Ongoing/Ended)

**Test 2: Statistics**
- [ ] Participant count displays
- [ ] Pull request count displays
- [ ] Merged PR count displays
- [ ] Repository count matches config

**Test 3: Chart**
- [ ] PR Activity chart renders
- [ ] Chart shows data (if hackathon has PRs)
- [ ] Hover tooltips work
- [ ] Legend displays correctly

**Test 4: Repositories**
- [ ] All repositories are listed
- [ ] GitHub links work
- [ ] Pull Requests links work
- [ ] Repository statistics show (if enabled)

**Test 5: Leaderboard**
- [ ] Leaderboard renders
- [ ] Participants show in correct order (by merged PR count)
- [ ] Avatar images load
- [ ] GitHub profile links work
- [ ] Top 3 have trophy icons
- [ ] PRs are listed (if showPRsInLeaderboard is true)

**Test 6: Prizes**
- [ ] All prizes display
- [ ] Prize icons show correctly
- [ ] Prize descriptions are readable

**Test 7: Sponsors**
- [ ] Sponsor section displays
- [ ] Sponsor logos load (if configured)
- [ ] Sponsor links work
- [ ] Sponsorship information displays

**Test 8: Mobile Responsive**
- [ ] Open in mobile view (DevTools → Toggle Device Toolbar)
- [ ] Layout adapts to small screens
- [ ] All sections are readable
- [ ] Navigation works

**Test 9: Different Browsers**
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari
- [ ] Mobile browsers

## Common Issues & Solutions

### Issue: "Failed to load hackathon data"

**Possible causes:**
1. Repository names incorrect
2. Repositories are private without token
3. API rate limit exceeded
4. Network error

**Solutions:**
- Check browser console for specific error
- Verify repository names (format: `owner/repo`)
- Add GitHub token to increase rate limit
- Wait 1 hour if rate limited

### Issue: Empty Leaderboard

**Possible causes:**
1. No PRs merged during hackathon period
2. Hackathon hasn't started
3. Date range is incorrect

**Solutions:**
- Verify dates are in ISO 8601 format
- Check that hackathon period includes PRs
- Wait for PRs to be merged if ongoing

### Issue: Chart Not Displaying

**Possible causes:**
1. Chart.js not loaded
2. JavaScript error
3. No data to display

**Solutions:**
- Check browser console for errors
- Verify Chart.js CDN is accessible
- Ensure dates are correctly formatted

### Issue: Images Not Loading

**Possible causes:**
1. Wrong file path
2. Files not committed to repo
3. Case sensitivity (GitHub is case-sensitive)

**Solutions:**
- Check image paths in config match actual files
- Ensure images are in `images/` folder
- Verify file names match exactly (case-sensitive)

### Issue: Dates Showing Incorrectly

**Possible causes:**
1. Wrong date format
2. Timezone confusion

**Solutions:**
- Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`
- Always use UTC (Z suffix)
- Use an online ISO 8601 converter if needed

## GitHub API Rate Limits

### Without Token
- **60 requests per hour**
- Shared across all unauthenticated requests from your IP

### With Token
- **5000 requests per hour**
- Per token

### Check Your Rate Limit
```javascript
// Add to browser console:
fetch('https://api.github.com/rate_limit', {
    headers: {
        'Authorization': 'token YOUR_TOKEN_HERE'
    }
}).then(r => r.json()).then(console.log);
```

## Performance Testing

### Expected Load Times
- Initial page load: < 2 seconds
- GitHub API requests: 1-3 seconds per repository
- Chart rendering: < 500ms

### Optimization Tips
1. Use a GitHub token to avoid rate limits
2. Limit number of repositories (recommend < 10)
3. Reduce `maxLeaderboardEntries` if slow
4. Cache is automatic (5 minutes)

## Security Checklist

- [ ] No sensitive data in config
- [ ] GitHub token not committed (if used in production)
- [ ] Using HTTPS for all external resources
- [ ] No mixed content warnings

## Deployment Verification

After deploying to GitHub Pages:

1. **Visit your site:** `https://your-username.github.io/repo-name/`

2. **Check GitHub Actions:**
   - Go to Actions tab
   - Verify deployment succeeded
   - Check for any errors

3. **Test from different devices:**
   - Desktop computer
   - Mobile phone
   - Tablet

4. **Share test link:**
   - Send to a friend or colleague
   - Verify they can access it
   - Ask for feedback

## Load Testing

For high-traffic hackathons, test with expected load:

1. **Use browser dev tools:**
   - Throttle network speed
   - Simulate slow 3G
   - Check if page still usable

2. **Check multiple simultaneous users:**
   - Open in multiple browsers/devices
   - Refresh simultaneously
   - Monitor for issues

## Final Checklist Before Launch

- [ ] All tests passing
- [ ] Configuration double-checked
- [ ] Images and assets uploaded
- [ ] GitHub Actions workflow working
- [ ] Site accessible at GitHub Pages URL
- [ ] Tested on multiple devices/browsers
- [ ] Backup plan ready (in case of issues)
- [ ] Contact information for support
- [ ] Announcement ready to share

## Monitoring During Hackathon

**Daily checks:**
- [ ] Site is accessible
- [ ] Leaderboard updating correctly
- [ ] No console errors
- [ ] GitHub API limits not exceeded

**Issue response:**
- Keep browser console open to catch errors
- Have GitHub token ready if rate limited
- Monitor GitHub Actions for deployment issues
- Respond quickly to participant questions

---

**Ready to launch? Let's go! 🚀**
