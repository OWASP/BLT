# BLT-Dash

A company cybersecurity dashboard that integrates with everything and gives a heads-up display single page of everything you need to see.

## Quick Deploy

Deploy this application to Cloudflare Workers with one click:

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/OWASP-BLT/BLT-Dash)

## Project Structure

```
BLT-Dash/
├── public/              # Static assets served by Cloudflare Workers
│   └── index.html      # Cybersecurity dashboard frontend (single-page app)
├── src/                 # Backend Python code
│   └── index.py        # Main entry point and routing
├── wrangler.toml        # Cloudflare Workers configuration
├── package.json         # npm scripts for deployment
└── README.md            # This file
```

## Features

- 🛡 **NIST Framework Scoring** — Live maturity scores for Identify, Protect, Detect, Respond, and Recover categories
- 🌍 **World Map** — Animated threat map with active pulse indicators for global incidents
- 📊 **Icon Grid Panels** — Administrative, Risk & Compliance, Engineering & Architect, Threat & Response
- 💼 **Business Function Alignment** — Finance, HR, Crypto, Sales, Fraud, Dev Ops, and more
- 🔧 **Critical Control / Tool Optimization** — Full tool inventory (WAF, SIEM, Firewalls, PAM, etc.)
- 🎓 **Skill Maturity** — Security team competency tracking
- ⚡ **Live Animations** — Pulsing alerts and random tile highlights simulate real-time activity
- 🌑 **Cyber Dark Theme** — High-contrast dark UI with green/cyan accents and scan-line overlay

## Tech Stack

- **Frontend**: Single HTML page with vanilla JavaScript and embedded CSS (no frameworks)
- **Backend**: Python on Cloudflare Workers
- **Styling**: Dark cyber theme with CSS grid layout, SVG world map, and hexagonal score indicators

## Setup

### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- Cloudflare account

### Installation

1. Clone the repository:

```bash
git clone https://github.com/OWASP-BLT/BLT-Dash.git
cd BLT-Dash
```

2. Install Wrangler (if not already installed):

```bash
npm install -g wrangler
```

3. Login to Cloudflare:

```bash
wrangler login
```

4. Run locally:

```bash
npm run dev
```

5. Deploy to production:

```bash
npm run deploy
```

