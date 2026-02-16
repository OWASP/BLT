# BLT Newsletter

A newsletter signup and management system for the OWASP Bug Logging Tool (BLT) platform. This application allows users to subscribe to receive updates about BLT statistics, new features, security insights, and community highlights.

## Features

- 📧 **Newsletter Signup**: Clean, user-friendly signup form with BLT-Design styling
- 🎨 **BLT-Design Integration**: Consistent look and feel with the OWASP BLT design system
- 📬 **SendGrid Integration**: Automated email management and delivery
- ✉️ **Welcome Emails**: Automatic welcome emails sent to new subscribers
- 🔒 **Opt-in Subscription**: GDPR-compliant consent-based subscription
- 📊 **Platform Stats**: Display key BLT metrics on the landing page
- 📱 **Responsive Design**: Mobile-first, works on all device sizes

## Tech Stack

- **Backend**: Node.js with Express
- **Email Service**: SendGrid API
- **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
- **Design System**: OWASP BLT-Design

## Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- SendGrid account with API key

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/OWASP-BLT/BLT-Newsletter.git
   cd BLT-Newsletter
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your SendGrid credentials:
   ```
   SENDGRID_API_KEY=your_sendgrid_api_key_here
   SENDGRID_FROM_EMAIL=newsletter@blt.owasp.org
   SENDGRID_LIST_ID=your_sendgrid_list_id_here
   PORT=3000
   ```

## Getting SendGrid API Key

1. Create a free account at [SendGrid](https://sendgrid.com/)
2. Go to Settings > API Keys
3. Click "Create API Key"
4. Give it "Full Access" or at least "Mail Send" and "Marketing" permissions
5. Copy the API key to your `.env` file

## Running the Application

### Development Mode
```bash
npm start
```

The application will be available at `http://localhost:3000`

### Production Mode
```bash
NODE_ENV=production npm start
```

## API Endpoints

### POST `/api/subscribe`
Subscribe a user to the newsletter.

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully subscribed! Check your email for confirmation."
}
```

### GET `/api/health`
Check the health status of the application and SendGrid configuration.

**Response:**
```json
{
  "status": "ok",
  "sendgridConfigured": true
}
```

## SendGrid Setup

### Creating a Contact List

1. Log in to SendGrid
2. Go to Marketing > Contacts
3. Click "Create a List"
4. Name your list (e.g., "BLT Newsletter Subscribers")
5. Copy the List ID and add it to your `.env` file

### Sending Newsletters

To send newsletters to your list:

1. Go to SendGrid Marketing > Campaigns
2. Create a new campaign
3. Choose your contact list
4. Design your email using SendGrid's editor
5. Include BLT stats, updates, and community highlights
6. Schedule or send immediately

## Customization

### Updating Stats

Edit the stats section in `public/index.html`:
```html
<div class="mb-2 text-3xl font-bold text-red-600">5000+</div>
<div class="text-sm text-slate-600">Bugs Reported</div>
```

### Modifying Welcome Email

Edit the email template in `server.js` under the `/api/subscribe` endpoint.

### Styling Changes

The application uses Tailwind CSS with BLT-Design colors. To modify styles, edit the HTML classes in `public/index.html`.

## Security Considerations

- API keys are stored in environment variables
- Email validation is performed server-side
- HTTPS should be used in production
- Rate limiting should be added for production use
- CORS configuration may be needed depending on your setup

## Deployment

### Deploy to Heroku
```bash
heroku create blt-newsletter
heroku config:set SENDGRID_API_KEY=your_key_here
heroku config:set SENDGRID_FROM_EMAIL=newsletter@blt.owasp.org
git push heroku main
```

### Deploy to Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Add environment variables in Vercel dashboard

### Deploy to Docker
```bash
docker build -t blt-newsletter .
docker run -p 3000:3000 --env-file .env blt-newsletter
```

## Contributing

We welcome contributions! Please see the [OWASP BLT Contributing Guidelines](https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md).

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
