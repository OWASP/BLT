# BLT-Vanish Web App

This directory contains the GitHub Pages site for BLT-Vanish, which includes:

1. **Documentation**: Setup guides, architecture overview, and security information
2. **Web App**: A browser-based version of BLT-Vanish that allows users to:
   - Create and manage privacy profiles locally
   - Upload and download encrypted privacy files
   - View data broker information and opt-out instructions
   - All processing happens in the browser - no data is sent to servers

## Files

- `index.html` - Main site with documentation and web app
- `styles.css` - Styling for the site
- `app.js` - JavaScript for privacy profile management and encryption
- `_config.yml` - Jekyll configuration for GitHub Pages

## Features

### Privacy-First Design

All user data stays in the browser:
- Profile data is stored only in memory (not even localStorage)
- Encryption/decryption uses Web Crypto API (AES-256-GCM)
- No analytics, tracking, or telemetry
- No data sent to external servers

### Profile Management

- Create new privacy profiles
- Upload existing profiles (encrypted or plain JSON)
- Edit personal information
- Download encrypted profiles for backup

### Data Broker Information

- View list of data brokers
- See what data types each broker collects
- Get step-by-step opt-out instructions
- Access direct links to opt-out pages

## Deployment

This site is automatically deployed to GitHub Pages from the `docs/` directory.

## Local Development

To test locally:

```bash
# Serve the site with Python
cd docs
python3 -m http.server 8000

# Or use any other static file server
```

Then visit http://localhost:8000 in your browser.

## Security

The web app uses:
- **AES-256-GCM** for encryption
- **PBKDF2** with 100,000 iterations for key derivation
- **Web Crypto API** (native browser implementation)
- **No external dependencies** for crypto operations

All operations are performed client-side. Your data never leaves your device.
