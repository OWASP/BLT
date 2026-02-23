# GitHub Pages - Deployment Guide

## 🎉 Static Site Ready

The OWASP BLT GSoC pages are now a pure static site hosted directly from the repository root.

## 📄 Pages

### 1. Main GSoC Landing Page (`index.html`)
- Hero section with GSoC logo
- Statistics cards
- Program benefits
- Application guidelines
- 7 OWASP projects showcase
- Mentor profiles and FAQ

### 2. PR Analytics Page (`pr-report.html`)
- Dashboard feature overview
- Project information
- Links to BLT application

## 🚀 Deployment

**Settings** → **Pages** → **Deploy from branch** → **/ (root)**

**URL**: `https://owasp-blt.github.io/BLT-GSOC/`

## 📁 Structure

```
BLT-GSOC/
├── index.html         # Main page
├── pr-report.html     # Analytics info
├── .nojekyll         # Bypass Jekyll
├── css/main.css      # Styles
├── images/gsoc.png   # Logo
└── js/               # Scripts
```

**Status**: ✅ Ready for deployment (root folder)
