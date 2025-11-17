# BACON GitHub Pages

This directory contains the GitHub Pages website for the BACON (Blockchain Assisted Contribution Network) project.

## 🌐 Live Site

Visit the site at: https://owasp-blt.github.io/BLT-Bacon

## 📚 Documentation

The site includes comprehensive documentation for integrating the BACON ecosystem:

- **Homepage** (`index.html`) - Overview and features
- **Getting Started** (`getting-started.html`) - Quick start guide
- **API Reference** (`api-reference.html`) - Complete SDK documentation
- **Bitcoin Integration** (`bitcoin-integration.html`) - Bitcoin/Runes protocol guide
- **Solana Integration** (`solana-integration.html`) - Solana/SPL token guide
- **GitHub Actions** (`github-actions.html`) - CI/CD automation guide
- **Security** (`security.html`) - Security best practices

## 🎨 Customization

### Styling

Edit `styles.css` to customize the appearance:

- CSS variables are defined in `:root` for easy theming
- Responsive design with mobile-first approach
- Smooth animations and transitions

### Content

All HTML files use semantic markup and can be edited directly. The site uses:

- Custom CSS (no framework dependencies)
- Vanilla JavaScript for interactivity
- Mobile-responsive design
- SEO-optimized markup

## 🚀 Local Development

To preview the site locally:

```bash
# Serve with Python
cd docs
python -m http.server 8000

# Or with Node.js
npx serve docs

# Then open http://localhost:8000
```

## 📦 Assets

- `styles.css` - Main stylesheet
- `script.js` - Interactive functionality
- `_config.yml` - Jekyll/GitHub Pages configuration

## 🔧 GitHub Pages Setup

This site is configured to deploy from the `docs` folder:

1. Go to repository Settings → Pages
2. Set Source to "Deploy from a branch"
3. Select branch: `main` (or your branch)
4. Select folder: `/docs`
5. Save

GitHub Pages will automatically build and deploy the site.

## 📝 Adding New Pages

1. Create a new HTML file in the `docs` folder
2. Copy the header and footer from an existing page
3. Add your content in the `<main>` section
4. Update navigation links in all pages
5. Add entry to sitemap if needed

## 🤝 Contributing

Contributions to improve the documentation are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## 📄 License

This documentation is part of the OWASP BLT Project and is licensed under the Apache License 2.0.
