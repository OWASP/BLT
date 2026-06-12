# Quick Start Guide

Get started with BLT-Vanish in 5 minutes!

## What is BLT-Vanish?

BLT-Vanish is a privacy toolkit that helps you:
- 🔍 Find where your personal data is exposed online
- 📝 Generate opt-out/deletion requests
- 📊 Track your privacy progress
- 🔒 Keep your data encrypted on your device

**Your data never leaves your device** - it's encrypted and stored locally.

## Installation

### Option 1: Download Pre-Built App (Easiest)

1. Go to [Releases](https://github.com/OWASP-BLT/BLT-Vanish-Web/releases)
2. Download for your platform:
   - **Android**: `blt-vanish-android.apk`
   - **Windows**: `blt-vanish-windows-x64.zip`
   - **macOS**: `blt-vanish-macos-x64.zip`
   - **Linux**: `blt-vanish-linux-x64.tar.gz`
3. Install/extract and run

### Option 2: Build from Source

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-Vanish-Web.git
cd BLT-Vanish-Web/flutter_app

# Install dependencies
flutter pub get

# Run the app
flutter run
```

## First-Time Setup

### 1. Launch the App

Open BLT-Vanish on your device.

### 2. Create Your Profile

1. Navigate to the **Profile** tab
2. Enter your information:
   - First Name *
   - Last Name *
   - Email (optional)
   - Phone (optional)
3. Tap **Save Profile**

**Remember**: This data is encrypted and stays on your device only.

### 3. Browse Data Brokers

1. Go to the **Brokers** tab
2. Browse or search for data brokers
3. Tap a broker to see details

### 4. Create an Opt-Out Request

1. Select a broker
2. Tap **Create Opt-Out Request**
3. Review the generated request
4. Send it to the broker via:
   - Email
   - Online form
   - Phone
   - Mail

### 5. Track Your Progress

1. Go to the **Requests** tab
2. See all your opt-out requests
3. Update status as you get responses
4. Monitor your privacy progress

## Common Tasks

### Finding a Specific Broker

1. Go to **Brokers** tab
2. Use the search bar
3. Type the broker name
4. Tap to view details

### Updating Your Profile

1. Go to **Profile** tab
2. Tap the edit icon (pencil)
3. Make your changes
4. Tap **Save Profile**

### Backing Up Your Data

Coming soon: Export encrypted backup

### Checking Broker Status

1. Find a broker
2. Look for health status indicator
3. Green = operational
4. Red = potential issues

## Privacy Tips

### ✅ Do This
- ✅ Keep your profile information current
- ✅ Check broker responses regularly
- ✅ Update request statuses
- ✅ Use the app offline if needed

### ❌ Avoid This
- ❌ Don't share your device password
- ❌ Don't screenshot sensitive info
- ❌ Don't install from untrusted sources

## Understanding Request Status

| Status | Meaning |
|--------|---------|
| **Draft** | Request created but not sent |
| **Pending** | Preparing to send |
| **Submitted** | Sent to broker |
| **Acknowledged** | Broker confirmed receipt |
| **Completed** | Data removed |
| **Failed** | Request unsuccessful |
| **Requires Action** | You need to do something |

## Frequently Asked Questions

### Is my data really safe?

Yes! Your data is:
- Encrypted with AES-256
- Stored only on your device
- Never transmitted to our servers
- Protected by your device's security

### Do I need an internet connection?

Not always! The app works offline for:
- Viewing your data
- Creating requests
- Managing your profile

You need internet only for:
- Fetching broker lists
- Checking broker health

### How do opt-out requests work?

1. You create a request in the app
2. App generates the text using a template
3. You manually send it to the broker
4. You track the response in the app

**BLT-Vanish doesn't send requests for you** - you stay in control.

### Can I use this on multiple devices?

Yes! Export your encrypted data from one device and import it on another.
(Feature coming soon)

### What if I forget to update a request?

No problem! Your data stays safe. Update whenever you remember.

### How many brokers can I opt out of?

As many as you want! There's no limit.

### Is BLT-Vanish free?

Yes! BLT-Vanish is completely free and open-source.

## Getting Help

### Need Support?

- 📖 [Documentation](https://github.com/OWASP-BLT/BLT-Vanish-Web/tree/main/docs)
- 💬 [Discussions](https://github.com/OWASP-BLT/BLT-Vanish-Web/discussions)
- 🐛 [Report a Bug](https://github.com/OWASP-BLT/BLT-Vanish-Web/issues)

### Want to Contribute?

- See [CONTRIBUTING.md](../CONTRIBUTING.md)
- Help add brokers
- Improve documentation
- Report issues

## Next Steps

Now that you're set up:

1. **Add More Brokers**: Search for brokers relevant to you
2. **Create Requests**: Generate opt-out requests
3. **Track Progress**: Monitor responses from brokers
4. **Stay Private**: Check back monthly for new brokers

## Tips for Success

### Best Practices

1. **Be Patient**: Brokers may take 30-90 days to respond
2. **Keep Records**: Save confirmation emails
3. **Follow Up**: Re-check if no response after estimated time
4. **Update Regularly**: Check for new brokers quarterly
5. **Stay Organized**: Use notes to track details

### Common Mistakes to Avoid

- ❌ Not providing enough information
- ❌ Using outdated contact methods
- ❌ Forgetting to follow up
- ❌ Giving up after one attempt
- ❌ Not tracking confirmation numbers

## Privacy Laws to Know

BLT-Vanish helps you exercise rights under:

- **GDPR** (EU): Right to erasure
- **CCPA** (California): Right to deletion
- **PIPEDA** (Canada): Right to erasure
- **LGPD** (Brazil): Right to deletion

Check which laws apply to you!

## Advanced Features

### Coming Soon

- 📦 Encrypted backup/restore
- 🔄 Automated status updates
- 🌐 Browser extension
- 📧 Email integration
- 📱 Mobile notifications

Stay tuned for updates!

## Troubleshooting

### App won't start?
- Check your device meets requirements
- Reinstall the app
- Report the issue on GitHub

### Can't save profile?
- Ensure all required fields are filled
- Check for special characters
- Try restarting the app

### Brokers not loading?
- Check internet connection
- Try refreshing
- App works offline with cached data

### Request not appearing?
- Check the Requests tab
- Try creating it again
- Make sure profile is set up

## Learn More

- 📖 [Architecture](./architecture.md)
- 🔒 [Security Whitepaper](../SECURITY.md)
- 🤝 [Contributing](../CONTRIBUTING.md)
- 📊 [Broker Guide](./broker-guide.md)

---

**Welcome to BLT-Vanish! Take control of your privacy today.** 🔒✨
