# BLT Newsletter - Testing Guide

## Manual Testing Checklist

### Prerequisites
- Node.js installed
- SendGrid API key configured in `.env`

### Test Cases

#### 1. Server Health Check
```bash
curl http://localhost:3000/api/health
```
Expected response:
```json
{
  "status": "ok",
  "sendgridConfigured": true
}
```

#### 2. Newsletter Subscription - Valid Email
```bash
curl -X POST http://localhost:3000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User"}'
```
Expected response:
```json
{
  "success": true,
  "message": "Successfully subscribed! Check your email for confirmation."
}
```

#### 3. Newsletter Subscription - Invalid Email
```bash
curl -X POST http://localhost:3000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"invalid-email","name":"Test User"}'
```
Expected response:
```json
{
  "success": false,
  "message": "Please provide a valid email address."
}
```

#### 4. Newsletter Subscription - Missing Email
```bash
curl -X POST http://localhost:3000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User"}'
```
Expected response:
```json
{
  "success": false,
  "message": "Please provide a valid email address."
}
```

### UI Testing

1. **Open the newsletter page**
   - Navigate to `http://localhost:3000`
   - Verify the page loads with BLT branding
   - Check responsive design on mobile/tablet/desktop

2. **Test form validation**
   - Try submitting without checking consent checkbox
   - Try submitting with invalid email format
   - Try submitting with valid email

3. **Test form submission**
   - Fill in name (optional)
   - Enter valid email address
   - Check consent checkbox
   - Click "Subscribe to Newsletter"
   - Verify loading state appears
   - Verify success/error message displays

4. **Test email receipt**
   - Check inbox for welcome email
   - Verify email content and formatting
   - Check that contact was added to SendGrid list

### Visual Regression Testing

Compare the page appearance with BLT-Design guidelines:
- [ ] Uses BLT red color (#dc2626)
- [ ] Uses Inter font family
- [ ] Gradient background matches BLT style
- [ ] Components have proper border radius
- [ ] Shadows and hover states work correctly
- [ ] Icons display correctly

### Browser Compatibility

Test in the following browsers:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

### Accessibility Testing

- [ ] All form inputs have labels
- [ ] Focus states are visible
- [ ] Tab navigation works correctly
- [ ] Screen reader compatible
- [ ] Color contrast meets WCAG guidelines

## Automated Testing (Future Enhancement)

Consider adding:
- Unit tests for API endpoints (Jest, Mocha)
- Integration tests for SendGrid
- E2E tests for form submission (Playwright, Cypress)
- Visual regression tests (Percy, Chromatic)
