# SendGrid Email Setup Guide

This guide explains how to properly configure SendGrid for OWASP BLT API email functionality.

## Prerequisites

1. **SendGrid Account**: Sign up at https://sendgrid.com
2. **Email Address**: You need a verified email address or domain

## Setup Steps

### 1. Create SendGrid API Key

1. Log into SendGrid dashboard: https://app.sendgrid.com
2. Go to **Settings** → **API Keys**
3. Click **Create API Key**
4. Name: `BLT-API-Dev` (or any name you prefer)
5. Permissions: Select **Full Access** or **Mail Send** (restricted)
6. Click **Create & View**
7. **Copy the API key** (you won't see it again!)

### 2. Verify Sender Email/Domain

SendGrid requires sender verification before sending emails. Choose one option:

#### Option A: Single Sender Verification (Quick Setup - Recommended for Dev)

1. Go to **Settings** → **Sender Authentication**
2. Click **Verify a Single Sender**
3. Fill in your details:
   - **From Name**: OWASP BLT (or your name for testing)
   - **From Email**: your-email@example.com (use your real email)
   - **Reply To**: Same as From Email
   - **Company**: OWASP
   - **Address, City, State, Zip, Country**: Your location
4. Click **Save**
5. **Check your email** and click the verification link
6. Wait for verification confirmation

#### Option B: Domain Authentication (Production Setup)

1. Go to **Settings** → **Sender Authentication**
2. Click **Authenticate Your Domain**
3. Select your DNS host (e.g., Cloudflare, GoDaddy, etc.)
4. Enter your domain (e.g., `yourdomain.com`)
5. Follow the DNS record setup instructions
6. Add the provided DNS records to your domain:
   - CNAME records for DKIM
   - TXT record for SPF
7. Click **Verify** after adding records

### 3. Configure Environment Variables

#### Development (Local Testing)

Update `wrangler.toml`:

```toml
[vars]
BLT_API_BASE_URL = "http://localhost:8787"
BLT_WEBSITE_URL = "http://localhost:8787"
JWT_SECRET = "your_dev_jwt_secret_here"
SENDGRID_API_KEY = "SG.your-actual-api-key-here"
```

**Important**: Replace `SENDGRID_API_KEY` with your actual API key.

#### Production (Cloudflare Workers)

Use secrets for sensitive data:

```bash
# Set JWT secret
wrangler secret put JWT_SECRET
# Paste your JWT secret when prompted

# Set SendGrid API key
wrangler secret put SENDGRID_API_KEY
# Paste your SendGrid API key when prompted
```

### 4. Update Email Service Configuration

In `src/handlers/auth.py`, use your verified sender email:

```python
email_service = EmailService(
    api_key=env.SENDGRID_API_KEY,
    from_email="your-verified-email@example.com",  # ← Use verified email
    from_name="OWASP BLT"
)
```

## Testing Email Locally

### 1. Test with localhost

Since you can't receive emails to localhost, use your actual email for testing:

```python
# In auth.py for testing only
email_service = EmailService(
    api_key=env.SENDGRID_API_KEY,
    from_email="your-verified-email@gmail.com",  # Your verified email
    from_name="OWASP BLT Dev"
)
```

### 2. Test the Signup Flow

```bash
# Start development server
wrangler dev

# Test signup with curl
curl -X POST http://localhost:8787/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "your-test-email@gmail.com",
    "password": "securePassword123"
  }'
```

Check your email inbox for the verification email!

## Troubleshooting

### Error: "Maximum credits exceeded"

**Cause**: Sender email/domain not verified or account restrictions

**Solution**:
1. Complete Single Sender Verification (see Option A above)
2. Make sure you click the verification link in your email
3. Wait a few minutes for verification to process
4. Use the **exact same email** in your EmailService configuration

### Error: "POST method allowed only"

**Cause**: Fetch API request not properly formatted

**Solution**: Already fixed in the code - make sure you're using latest version

### Error: "The from email does not contain a valid address"

**Cause**: Using unverified sender email

**Solution**: 
- Use the exact email you verified in SendGrid
- Don't use `noreply@blt.owasp.org` unless you own and verified that domain

### Verification email not received

**Check**:
1. Spam/Junk folder
2. SendGrid Activity Feed: Settings → Activity Feed
3. Check if email was blocked or bounced
4. Verify sender email is correct

## Free Tier Limits

SendGrid Free Tier includes:
- **100 emails/day** forever
- Perfect for development and testing
- No credit card required

## Production Checklist

Before deploying to production:

- [ ] Domain Authentication completed
- [ ] API key stored as Cloudflare secret (not in wrangler.toml)
- [ ] JWT_SECRET stored as Cloudflare secret
- [ ] Sender email uses your authenticated domain
- [ ] Test email sending in production environment
- [ ] Monitor SendGrid Activity Feed for issues

## Additional Resources

- [SendGrid Documentation](https://docs.sendgrid.com/)
- [Sender Authentication Guide](https://docs.sendgrid.com/ui/account-and-settings/how-to-set-up-domain-authentication)
- [API Key Permissions](https://docs.sendgrid.com/ui/account-and-settings/api-keys)
- [Cloudflare Workers Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)

## Support

If you encounter issues:
1. Check SendGrid Activity Feed for delivery logs
2. Review error messages in Wrangler console
3. Verify all configuration steps above
4. Open an issue on GitHub with error details
