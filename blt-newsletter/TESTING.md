# BLT Newsletter - Testing Guide

## Testing the Static Site

### Prerequisites
- Modern web browser
- Internet connection (for CDN resources)

### Test Cases

#### 1. Page Load
- Open `index.html` in a browser or visit the GitHub Pages URL
- Verify BLT branding appears correctly
- Check that all styles load properly
- Verify responsive design on different screen sizes

#### 2. Form Validation - Valid Email
1. Fill in name (optional)
2. Enter valid email: `test@example.com`
3. Check consent checkbox
4. Click "Subscribe to Newsletter"
5. Verify success message appears

Expected: Green success message

#### 3. Form Validation - Invalid Email
1. Enter invalid email: `invalid-email`
2. Check consent checkbox
3. Click "Subscribe"

Expected: Red error message about invalid email

#### 4. Form Validation - Missing Consent
1. Enter valid email
2. Don't check consent checkbox
3. Try to submit

Expected: Browser validation prevents submission

#### 5. GitHub Issue Creation
1. Submit valid subscription
2. Go to repository Issues
3. Filter by label: `newsletter-subscription`
4. Verify new issue was created with subscriber info

Expected: Issue created with email and name

## Testing GitHub Actions

### Prerequisites
- Repository with Actions enabled
- SendGrid API key configured in secrets
- At least one subscriber (open issue with label)

### Test Newsletter Workflow

#### 1. Manual Workflow Trigger
1. Go to Actions > Send Newsletter
2. Click "Run workflow"
3. Enter subject: "Test Newsletter"
4. Enter content file: `newsletters/latest.md`
5. Click "Run workflow"
6. Wait for completion

Expected: Workflow completes successfully

#### 2. Check Workflow Logs
1. Open the workflow run
2. Expand "Get subscribers from issues"
3. Verify subscriber count is correct
4. Expand "Send newsletter via SendGrid"
5. Check for successful sends

Expected: All subscribers receive email

#### 3. Verify Email Receipt
1. Check inbox for test subscriber
2. Verify email has correct subject
3. Verify content matches newsletter file
4. Verify BLT branding in email

Expected: Well-formatted email received

### Test Subscriber Management

#### 1. Add Subscriber via Form
- Submit form with test email
- Check Issues for new entry

#### 2. Remove Subscriber
- Close a subscription issue
- Run newsletter workflow
- Verify closed issue subscriber doesn't receive email

#### 3. Export Subscribers
- Run workflow
- Check logs for subscriber list
- Verify all open issues are included

## Visual Regression Testing

Compare with BLT-Design guidelines:
- [ ] Uses BLT red color (#dc2626)
- [ ] Uses Inter font family
- [ ] Gradient background matches BLT style
- [ ] Components have proper border radius
- [ ] Shadows and hover states work correctly
- [ ] Icons display correctly

## Browser Compatibility

Test in the following browsers:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

## Mobile Testing

Test on different devices:
- [ ] iPhone (Safari)
- [ ] Android (Chrome)
- [ ] Tablet (iPad/Android)

## Accessibility Testing

- [ ] All form inputs have labels
- [ ] Focus states are visible
- [ ] Tab navigation works correctly
- [ ] Screen reader compatible (test with VoiceOver/NVDA)
- [ ] Color contrast meets WCAG guidelines
- [ ] Alt text for all images

## Performance Testing

- [ ] Page loads in under 3 seconds
- [ ] No console errors
- [ ] CDN resources load properly
- [ ] Form submission is responsive

## Security Testing

- [ ] Email validation prevents injection
- [ ] No sensitive data in client code
- [ ] HTTPS enabled (in production)
- [ ] No XSS vulnerabilities

## GitHub Pages Deployment

### 1. Verify Deployment
- Push to main branch
- Wait for Actions to complete
- Visit GitHub Pages URL
- Verify site is live

### 2. Check DNS/SSL
- Verify HTTPS is enabled
- Check custom domain (if configured)
- Test SSL certificate validity

## Troubleshooting

### Form Not Submitting
- Check browser console for errors
- Verify GitHub API is accessible
- Check repository name in JavaScript

### Newsletter Not Sending
- Verify SendGrid secrets are set
- Check workflow logs for errors
- Verify subscriber issues exist
- Check SendGrid dashboard

### Page Not Loading
- Check GitHub Pages is enabled
- Verify source branch is correct
- Check for deployment errors in Actions

## Automated Testing (Future)

Consider adding:
- E2E tests with Playwright/Cypress
- Unit tests for JavaScript functions
- Visual regression tests
- API integration tests
- Load testing for high subscriber counts
