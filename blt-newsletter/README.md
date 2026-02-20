# BLT Newsletter

A newsletter signup and management system for the OWASP Bug Logging Tool (BLT) platform, built as a static GitHub Pages site with GitHub Actions for automated newsletter delivery.

## Features

- 📧 **Newsletter Signup**: Clean, user-friendly signup form with BLT-Design styling
- 🎨 **BLT-Design Integration**: Consistent look and feel with the OWASP BLT design system
- 🤖 **GitHub Actions**: Automated newsletter sending via GitHub Actions workflow
- 📬 **SendGrid Integration**: Reliable email delivery through SendGrid
- ✉️ **Welcome Emails**: Automatic welcome emails sent to new subscribers
- 🔒 **Opt-in Subscription**: GDPR-compliant consent-based subscription
- 📊 **Platform Stats**: Display key BLT metrics on the landing page
- 📱 **Responsive Design**: Mobile-first, works on all device sizes
- 🚀 **GitHub Pages**: Static site hosted on GitHub Pages (no server required)

## Architecture

### Static Site (GitHub Pages)
The newsletter signup page is a static HTML site hosted on GitHub Pages. When users subscribe:
1. The form submits to GitHub Issues API
2. A new issue is created with label `newsletter-subscription`
3. The issue contains the subscriber's email and name

### Newsletter Distribution (GitHub Actions)
Newsletters are sent via a manual GitHub Actions workflow:
1. The workflow reads all open issues with `newsletter-subscription` label
2. Extracts subscriber emails from issue bodies
3. Sends the newsletter using SendGrid API
4. Supports markdown newsletter templates

## Tech Stack

- **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
- **Hosting**: GitHub Pages (static site)
- **Automation**: GitHub Actions
- **Email Service**: SendGrid API
- **Design System**: OWASP BLT-Design

## Setup

### 1. Enable GitHub Pages

1. Go to repository **Settings** > **Pages**
2. Set **Source** to "GitHub Actions"
3. The site will be deployed automatically on push to main

### 2. Configure GitHub Secrets

Add the following secrets in **Settings** > **Secrets and variables** > **Actions**:

- `SENDGRID_API_KEY`: Your SendGrid API key
- `SENDGRID_FROM_EMAIL`: Verified sender email (e.g., `newsletter@blt.owasp.org`)

### 3. Enable Issues

Make sure GitHub Issues are enabled for your repository in **Settings** > **General**.

### 4. Create Newsletter Subscription Label

Create a label called `newsletter-subscription` in your repository:
1. Go to **Issues** > **Labels**
2. Click **New label**
3. Name: `newsletter-subscription`
4. Color: Choose any color
5. Click **Create label**

## Usage

### Receiving Subscriptions

When someone subscribes via the website:
1. A new issue is automatically created
2. The issue has the `newsletter-subscription` label
3. Issue title: "Newsletter Subscription: user@example.com"
4. Issue body contains subscriber name and email

### Sending Newsletters

1. **Create your newsletter content**:
   - Add a markdown file to the `newsletters/` directory
   - Use `newsletters/latest.md` as a template

2. **Run the workflow**:
   - Go to **Actions** > **Send Newsletter**
   - Click **Run workflow**
   - Enter the email subject line
   - Enter the newsletter content file path (e.g., `newsletters/february-2026.md`)
   - Click **Run workflow**

3. **Monitor the results**:
   - Check the workflow logs for delivery status
   - View summary in the workflow run

## Getting SendGrid API Key

1. Create a free account at [SendGrid](https://sendgrid.com/)
2. Go to **Settings** > **API Keys**
3. Click **Create API Key**
4. Give it "Mail Send" permissions
5. Copy the API key to GitHub secrets

## Newsletter Content

Newsletter files are markdown documents in the `newsletters/` directory. Example structure:

```markdown
# BLT Newsletter - Month Year

## Platform Statistics
- Stats here...

## New Features
- Feature 1
- Feature 2

## Community Highlights
- Highlight 1
```

The markdown is automatically converted to HTML and wrapped in a BLT-branded email template.

## Local Development

To test the site locally:

```bash
# Serve the site locally (requires Python)
python3 -m http.server 8000

# Or use Node.js
npx http-server
```

Visit `http://localhost:8000` to see the site.

## Managing Subscribers

### View All Subscribers
Go to **Issues** and filter by label `newsletter-subscription`.

### Remove a Subscriber
Close the subscriber's issue to remove them from the mailing list.

### Export Subscribers
Use the GitHub API or run the "Get subscribers" step from the Actions workflow manually.

## Customization

### Update Newsletter Template
Edit `.github/scripts/send-newsletter.js` to modify the email template HTML.

### Change Signup Form
Edit `index.html` to modify the signup form appearance or behavior.

### Modify Stats
Update the stats section in `index.html`:
```html
<div class="mb-2 text-3xl font-bold text-red-600">5000+</div>
<div class="text-sm text-slate-600">Bugs Reported</div>
```

## Workflows

### Deploy to GitHub Pages
- **Trigger**: Push to main branch or manual dispatch
- **File**: `.github/workflows/deploy-pages.yml`
- **Purpose**: Deploys the static site to GitHub Pages

### Send Newsletter
- **Trigger**: Manual dispatch only
- **File**: `.github/workflows/send-newsletter.yml`
- **Purpose**: Sends newsletter to all subscribers

## Security Considerations

- API keys are stored as GitHub secrets
- Email validation is performed client-side
- GitHub API rate limits apply (5000 requests/hour for authenticated)
- Subscribers are stored as public GitHub issues (emails are visible)
- For private subscriber management, consider using GitHub Discussions or a private repository

## Alternative: Private Subscriber Storage

If you want to keep subscriber emails private:
1. Create a private repository for subscriber data
2. Modify the form to use GitHub API with a personal access token
3. Store subscribers in repository files instead of issues

## Troubleshooting

### Form submissions not creating issues
- Check if Issues are enabled in repository settings
- Verify the repository name in the JavaScript matches your repo
- Check browser console for errors

### Newsletter not sending
- Verify SendGrid API key is set correctly in secrets
- Check SendGrid sender email is verified
- Review workflow logs for detailed error messages

### Subscribers not appearing
- Ensure issues have the `newsletter-subscription` label
- Check that issues are in "open" state

## Contributing

We welcome contributions! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [OWASP BLT](https://github.com/OWASP-BLT/BLT) - Main bug logging platform
- [BLT-Design](https://github.com/OWASP-BLT/BLT-Design) - Design system and components

## Support

- [OWASP BLT Documentation](https://owasp-blt.github.io/documentation/)
- [GitHub Issues](https://github.com/OWASP-BLT/BLT-Newsletter/issues)
- [OWASP BLT Discord](https://discord.gg/owasp-blt)

## Acknowledgments

Built with ❤️ by the OWASP BLT community
