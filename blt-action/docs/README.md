# BLT-Action GitHub Pages

This directory contains the GitHub Pages website for the OWASP BLT-Action project.

## 🌐 Live Site

Visit: [https://owasp-blt.github.io/BLT-Action/](https://owasp-blt.github.io/BLT-Action/)

## 📋 Design Specifications

This site follows the **BLT Official Style Guide** with the following specifications:

### Tech Stack
- **Pure HTML** - No frameworks, clean and performant
- **Tailwind CSS** (CDN) - Utility-first CSS framework
- **Font Awesome** (CDN) - Icon library for visual elements

### Brand Tokens
- **Primary Color**: `#E10101` (BLT red)
- **Primary Hover**: `#b91c1c` (red-700)
- **Active Background**: `#feeae9` (light red for active nav items)
- **Neutral Border**: `#E5E5E5`
- **Dark Base**: `#111827`
- **Dark Surface**: `#1F2937`

### Component Standards
- **Buttons**: Primary (filled) and outline variants
- **Inputs**: Gray-400 border, rounded-md, focus:border-red-600 with ring
- **Links**: Red-600 text with underline on hover
- **Icons**: Semantic usage with aria-hidden for decorative icons
- **Sidebar/Nav**: Active items use #feeae9 background with #E10101 text

### Features Documented
1. **Assignment Management** - Self-assign with natural language commands
2. **Automated Workflow** - 24-hour stale issue unassignment
3. **Kudos System** - Contributor recognition with OWASP BLT API integration
4. **Tip System** - GitHub Sponsors financial support
5. **GIF Integration** - Giphy-powered engagement
6. **Smart Protection** - Multi-assignment prevention and PR validation

## 🚀 Deployment

The site is automatically deployed via GitHub Actions when changes are pushed to the `main` branch:
- Workflow file: `.github/workflows/deploy-pages.yml`
- Trigger: Push to `main` branch with changes in `docs/**`
- Manual trigger: Available via workflow_dispatch

## 📱 Responsive Design

The site is fully responsive with:
- Mobile-first approach
- Hamburger menu for mobile devices
- Responsive grid layouts for feature cards
- Optimized typography for all screen sizes

## ♿ Accessibility

- Semantic HTML structure
- ARIA labels where appropriate
- `aria-hidden="true"` for decorative icons
- Proper heading hierarchy
- Keyboard navigation support
- Focus states on interactive elements

## 🌙 Dark Mode

Full dark mode support using Tailwind's dark mode classes:
- Automatic detection via system preferences
- BLT brand colors adapted for dark theme
- Proper contrast ratios maintained

## 📝 Content Structure

- **Hero Section** - Overview and CTA buttons
- **Features** - 6 key features with icons and descriptions
- **Installation** - Prerequisites, configuration table, and workflow YAML
- **Usage** - All commands documented with examples
- **API Integrations** - GitHub, Giphy, and OWASP BLT APIs
- **How It Works** - Workflow triggers and execution flow
- **Contributing** - Step-by-step contribution guide
- **Footer** - Links, resources, and attribution

## 🔧 Local Development

To test the site locally:

```bash
cd docs
python3 -m http.server 8080
# Visit http://localhost:8080 in your browser
```

## 📚 References

- [BLT Design System](https://owasp-blt.github.io/BLT-Design/)
- [Figma Design Files](https://www.figma.com/file/s0xuxeU6O2guoWEfA9OElZ/Design)
- [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## ✨ Code Quality

- **Clean & Modern** - No AI-generated boilerplate
- **Semantic HTML** - Proper use of HTML5 elements
- **Copy-Paste Friendly** - All code examples are ready to use
- **Well-Commented** - JavaScript functions documented
- **Performance** - Minimal dependencies, CDN-hosted assets

## 🎨 Design Principles

1. **Clarity** - Clear information hierarchy
2. **Consistency** - Uniform styling throughout
3. **Accessibility** - WCAG compliant
4. **Performance** - Fast loading times
5. **Maintainability** - Easy to update and extend
