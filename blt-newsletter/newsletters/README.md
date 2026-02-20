# Newsletter Templates

This directory contains newsletter content in markdown format.

## Creating a Newsletter

1. **Create a new markdown file** in this directory
   ```bash
   cp latest.md february-2026.md
   ```

2. **Edit the content** with your updates:
   - Platform statistics
   - New features
   - Security insights
   - Community highlights
   - Upcoming events

3. **Send via GitHub Actions**:
   - Go to Actions > Send Newsletter
   - Enter subject line
   - Enter file path (e.g., `newsletters/february-2026.md`)
   - Run workflow

## Template Structure

```markdown
# BLT Newsletter - [Month Year]

## 📊 Platform Statistics
- Key metrics...

## 🚀 New Features
- Feature updates...

## 🔒 Security Insights
- Security tips...

## ⭐ Community Highlights
- Community news...

## 📅 Upcoming Events
- Event listings...

## 🔗 Quick Links
- Important links...
```

## Best Practices

- **Be Concise**: Keep it readable and scannable
- **Use Emojis**: Makes content more engaging
- **Include Links**: Link to relevant resources
- **Show Data**: Include real stats and numbers
- **Highlight People**: Recognize contributors
- **Call to Action**: Encourage engagement

## Styling

The markdown is automatically converted to HTML with BLT branding:
- Red color scheme (#dc2626)
- Inter font
- Responsive layout
- BLT header and footer

No HTML needed - just write markdown!
