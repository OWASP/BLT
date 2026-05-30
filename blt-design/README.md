# BLT-Design

Static BLT design system for light/dark mode, logos, colors, typography, and copy-paste component patterns.

## Preview

Serve the folder with any local static server, then open `index.html`. The guide is static HTML with Tailwind CDN, Font Awesome CDN, and local shared assets.

```bash
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/index.html`. Do not use `file://` directly, because the shared sidebar is loaded from a local HTML partial.

## Theme

- Shared CSS: `docs/assets/css/blt-design.css`
- Shared theme script: `docs/assets/js/theme.js`
- Dark mode uses the `dark` class on `<html>`.
- Theme preference is stored in `localStorage` under `blt-theme`.

## Component Coverage

The guide now covers the core BLT library:

- Shell: navbar, BLT sidebar, cards
- Controls: buttons, inputs, search, links, tabs
- Feedback: badges, alerts, modals, states
- Data and assets: tables, icons, repository logos

Every page should include the shared CSS and theme script, show a preview, and keep examples copy-paste friendly for BLT auth, cloud, reports, domains, contributors, and issue workflows.

## Design Direction

- Primary red: `#E10101`
- Hover red: `#B91C1C`
- Dark base: `#111827`
- Dark surface: `#1F2937`
- Dark borders: subdued slate, not white
- UI font: Manrope with system fallbacks

Keep new pages token-driven and copy-paste friendly.
