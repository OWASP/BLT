# BLT-GSOC

This repository contains the Google Summer of Code (GSoC) pages for the OWASP BLT project, hosted as a static GitHub Pages site.

## 🌐 Live Site

**URL**: https://owasp-blt.github.io/BLT-GSOC/

## 📄 Pages

- **Home Page** (`index.html`) - Main GSoC landing page with:
  - Program overview and benefits
  - Statistics and project showcase
  - Application guidelines and timeline
  - Mentor information and FAQ

- **PR Analytics** (`pr-report.html`) - Information about the PR analytics dashboard

## 📁 Repository Structure

```
BLT-GSOC/
├── index.html          # Main GSoC page
├── pr-report.html      # PR analytics info page
├── .nojekyll          # Bypass Jekyll processing
├── css/
│   └── main.css       # Custom styles
├── images/
│   └── gsoc.png       # GSoC logo
├── js/
│   └── gsoc_pr_report.js  # Analytics scripts
├── README.md          # This file
├── CHANGELOG.md       # Version history
└── SUMMARY.md         # Project summary
```

## 🎨 Technology Stack

- **HTML5** - Semantic markup
- **Tailwind CSS** (CDN) - Utility-first styling framework
- **Font Awesome** (CDN) - Icon library
- **Custom CSS** - Additional styles and animations

### Features
- ✅ Fully responsive design (mobile, tablet, desktop)
- ✅ Dark mode support (automatic)
- ✅ Fast loading with CDN resources
- ✅ SEO optimized
- ✅ Accessible markup

## 📜 History

This repository includes all GSoC-related components from the BLT application:

## 📜 History

This repository originally contained Django templates, views, and management commands for GSoC functionality within the main OWASP BLT application. These have been converted to static HTML pages for hosting on GitHub Pages.

### Evolution
1. **Initial Migration** - GSoC pages extracted from main BLT repository
2. **Static Conversion** - Django templates converted to standalone HTML
3. **Root Migration** - Moved from `docs/` folder to root for simpler structure

All Django backend functionality has been removed in favor of a pure static site that can be easily hosted on GitHub Pages.

## 🚀 GitHub Pages Deployment

The site is configured to serve from the repository root. To enable GitHub Pages:

1. Go to repository **Settings** → **Pages**
2. Under "Source", select: **Deploy from a branch**
3. Branch: Select your branch (e.g., `main` or `copilot/move-gsoc-pages-to-repo`)
4. Folder: Select **/ (root)**
5. Click **Save**

The site will be published at: `https://owasp-blt.github.io/BLT-GSOC/`

## 🔧 Local Development

To test the pages locally:

```bash
# Using Python's built-in HTTP server
python3 -m http.server 8000

# Then open http://localhost:8000 in your browser
```

Or use any static file server like:
- `npx serve`
- VS Code Live Server extension
- `php -S localhost:8000`

## 📝 Content

### Main Page Features
- Hero section with GSoC logo and program overview
- Statistics cards (100+ countries, 7 years, 20+ projects)
- Student and mentor benefits
- Application timeline and process
- 7 OWASP project showcases:
  - BLT (Bug Logging Tool)
  - NEST
  - NETTACKER
  - JUICE-SHOP
  - DSOMM
  - PYGOAT
  - OpenCRE
- Mentor profiles
- Comprehensive FAQ section

### PR Analytics Page
- Feature overview
- Information about live dashboard (requires BLT backend)
- Links to main BLT application

## 🤝 Contributing

This is a static documentation site. To update content:
1. Edit the HTML files directly
2. Update CSS in `css/main.css` for styling changes
3. Test locally before committing
4. Submit a pull request

## 📄 License

This project is part of the OWASP BLT project and inherits its license.

## 🔗 Related Links

- **Main BLT Repository**: [OWASP-BLT/BLT](https://github.com/OWASP-BLT/BLT)
- **OWASP GSoC Info**: [owasp.org/www-community/initiatives/gsoc/](https://owasp.org/www-community/initiatives/gsoc/)
- **Google Summer of Code**: [summerofcode.withgoogle.com](https://summerofcode.withgoogle.com/)
