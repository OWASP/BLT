# 🍞 Panini - Banned Apps Visualization

**Live Site:** [https://panini.owaspblt.org/](https://panini.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT-Panini](https://git.owaspblt.org/BLT/BLT-Panini)

**Panini** is a static web application that visualizes apps banned by different countries around the world. It provides both a list view and an interactive map view to explore censorship data.

This project was extracted from the [OWASP BLT](https://git.owaspblt.org/BLT/BLT-Core) project to serve as a standalone visualization.

## ✨ Features

- **🌍 Interactive Map View**: Visualize banned apps directly on a global map. Countries with bans are highlighted, and clicking them reveals details.
- **📋 List View**: A clean, responsive list of all banned apps, sortable and filterable.
- **🔍 Smart Search**: Search by country or app name.
  - In **Map View**, searching for a country automatically zooms to and highlights it!
- **lighting Dark Mode**: Fully supported dark mode for comfortable viewing at night.
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices.

### Live Demo - https://panini.owaspblt.org/

## 🛠️ Technologies

- **HTML5**
- **Tailwind CSS** (via CDN)
- **Leaflet.js** (for maps)
- **Vanilla JavaScript** (no heavy frameworks)

## 📂 Data

The data is stored in `public/banned_apps.json` in a structured format, making it easy to update or expand.

`public/slack_apps.json` lists Slack apps with curated security notes. New apps from the Slack App
Directory are merged in weekly (see below); curated fields are edited in the committed file.

## Deployment

`wrangler.toml` deploys a Worker (`worker/index.js`) with `public/` as its static assets. Deploy it
with `scripts/deploy.sh blt-panini` from the monorepo root (or `npx wrangler deploy` here); test with
`scripts/ci/test.sh blt-panini`.

## Weekly Slack apps refresh (Workers KV)

`.forkmesh/blt-panini--update_slack_apps.yml` runs every Sunday at 00:00 UTC on git.owaspblt.org.
It runs `scripts/refresh-kv.sh`, which starts from the `slack_apps.json` in the Worker's KV
namespace with the committed entries laid over it (so curation in git wins and apps found earlier
are kept), runs `scripts/update_slack_apps.py` and writes the result back to KV when it changed.
Nothing is committed and nothing is redeployed. The Worker serves `/slack_apps.json` from KV and
falls back to the committed file while KV has none; `banned_apps.json` is a plain static file. The
workflow needs the Actions secrets `CLOUDFLARE_API_TOKEN` (Workers KV Storage: Edit) and
`CLOUDFLARE_ACCOUNT_ID`.

## 🤝 Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## 📄 License

This project is open source. See the [LICENSE](LICENSE) file for details.
