# BLT project logos: the wasp badge family

Every BLT project logo is the OWASP BLT wasp (white, on a `#dc2626` circle) with the project's own
symbol in a small round sub-badge at the bottom right, separated by a white ring. The shared
OWASP BLT top bar and the homepage keep the plain wasp (`public/_home/blt-logo.svg`).

- `symbols/<project>.svg`: the project's own symbol (its logo before this family). Edit one to change
  that project's sub-badge. BLT-Next has a new "next" symbol instead of the old red circle with an arrow.
- `targets.json`: other files in a project that show its logo on its site (header images, SVG favicons).
- `build.mjs`: writes `<project>/logo.svg`, `public/_home/logos/<project>.svg` and the targets.

```bash
node blt-home/scripts/wasp-badges/build.mjs          # regenerate everything
node blt-home/scripts/wasp-badges/build.mjs --check  # what npm test runs: fails if a file is stale
```

`<project>/logo.png` (512 px, used by READMEs) is rendered from `logo.svg` with any SVG renderer,
e.g. headless Chromium; keep it in step when a symbol changes.

Rasters stay only where a platform needs them (favicon.ico, app and extension icons, e-mail and
Slack images); the Flutter app and the browser extension use the plain wasp as their icon.
