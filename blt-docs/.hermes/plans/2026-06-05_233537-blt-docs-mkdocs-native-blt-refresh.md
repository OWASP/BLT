# BLT-docs MkDocs-Native BLT Refresh Plan

## Goal

Refresh BLT-docs so it still feels like a normal MkDocs Material documentation site, but with a clear BLT identity.

We are skipping the custom landing-page direction. The homepage should remain documentation-first, not a marketing/product landing page. The primary work is now:

- BLT logo/brand update
- BLT primary and secondary colors
- header/footer polish
- typography polish
- small MkDocs-native homepage cleanup
- content quality and freshness across docs

## Current decision

The custom landing-page experiment is not the direction. It fought the inherited MkDocs layout and did not feel right inside Material for MkDocs.

New direction:

- Keep MkDocs Material layout and behavior.
- Use Material theme customization where possible.
- Add only light CSS overrides where needed.
- Make BLT-docs look like documentation, but BLT-branded documentation.
- Focus on content correctness and maintainability more than custom homepage UI.

## Current local state to handle

There may be experimental changes from the landing-page attempt:

- `docs/index.md`
- `mkdocs.yml`
- `docs/assets/stylesheets/blt-home.css`

Before implementation, either the user reverts them manually or we revert them safely. If Hermes handles the revert, first save a patch so the experiment is recoverable:

```bash
git status --short --branch
git diff > /tmp/blt-docs-landing-experiment.patch
```

Then restore the landing-page experiment files and proceed with the MkDocs-native refresh.

## Design principles

### Keep it MkDocs-native

Use Material for MkDocs defaults and extension points:

- `theme.palette`
- `theme.font`
- `theme.logo`
- `theme.favicon`
- `extra_css`
- `extra` social links
- Material card grids where useful
- admonitions and tabs where useful

Avoid building a custom frontend inside `docs/index.md`.

### BLT touch, not full redesign

The site should keep familiar docs behavior:

- top nav
- tabs
- left nav
- right table of contents
- search
- previous/next footer navigation
- readable markdown pages

The BLT touch should come from:

- logo
- red palette
- secondary/accent color
- typography
- header/footer surfaces
- link/button/card accents
- cleaner homepage content

## Visual direction

### Brand colors

Use BLT red as the main brand:

```text
Primary red: #E10101
Primary hover/deep red: #B91C1C
Soft red background: #FEEAEA or rgba(225, 1, 1, 0.08)
Dark base: #111827
Dark surface: #1F2937
Light background: #F8FAFC
Light surface: #FFFFFF
Border light: #E5E7EB
Border dark: #374151
Muted text: #64748B light / #9CA3AF dark
```

### Material palette mapping

MkDocs Material only supports named palette values directly, so use `primary: red` / `accent: red` or `deep orange` in `mkdocs.yml`, then use CSS variables for exact BLT shades.

Recommended:

```yaml
theme:
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: red
      accent: red
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: red
      accent: red
```

Then set exact colors with CSS overrides.

### Typography

Prefer Manrope if we can load it cleanly. Options:

1. Use Google Fonts through MkDocs Material:

```yaml
theme:
  font:
    text: Manrope
    code: Roboto Mono
```

2. If self-hosted fonts are already available or easy to add under `docs/assets/fonts/`, use `extra_css` with `@font-face`.

Initial recommendation: set `text: Manrope`, keep `code: Roboto Mono` or `JetBrains Mono` if available.

### Logo and favicon

Current config uses:

```yaml
favicon: assets/favicon.ico
```

Need check existing assets:

```text
docs/assets/logo.png
docs/assets/favicon.png
docs/assets/favicon.ico
```

Plan:

- Use BLT logo in header with `theme.logo: assets/logo.png` if logo is appropriate.
- Keep `theme.favicon: assets/favicon.ico` or update to `assets/favicon.png` if cleaner.
- Verify the logo displays in both light/dark header modes.

Potential config:

```yaml
theme:
  logo: assets/logo.png
  favicon: assets/favicon.ico
```

## Implementation plan

### Step 1: Revert landing-page experiment

If not already reverted by the user:

- Restore `docs/index.md` to a documentation-style page.
- Remove or stop referencing `docs/assets/stylesheets/blt-home.css`.
- Remove landing-page-only CSS from `mkdocs.yml`.

If the file should be preserved temporarily, rename it outside MkDocs references:

```text
docs/assets/stylesheets/blt-home.css.disabled
```

But preferred final state: no unused custom landing CSS.

### Step 2: Add MkDocs-native BLT theme CSS

Create:

```text
docs/assets/stylesheets/blt-theme.css
```

Keep CSS small and focused on Material classes:

- `.md-header`
- `.md-tabs`
- `.md-search__form`
- `.md-typeset a`
- `.md-typeset .md-button`
- `.md-typeset .grid.cards > ul > li`
- `.md-footer`
- `.md-footer-meta`
- `.md-typeset .admonition`
- `.md-typeset code`

Example direction:

```css
:root {
  --blt-primary: #e10101;
  --blt-primary-hover: #b91c1c;
  --blt-soft: #feeaea;
  --blt-dark: #111827;
  --blt-surface-dark: #1f2937;
}

.md-header,
.md-tabs {
  background-color: var(--blt-primary);
}

.md-header__button.md-logo img,
.md-header__button.md-logo svg {
  height: 2rem;
}

.md-typeset a {
  color: var(--blt-primary);
}

.md-typeset a:hover {
  color: var(--blt-primary-hover);
}

.md-footer,
.md-footer-meta {
  background-color: var(--blt-dark);
}
```

Do not over-style page internals initially.

### Step 3: Wire CSS in MkDocs

Update `mkdocs.yml`:

```yaml
extra_css:
  - assets/stylesheets/blt-theme.css
```

If `extra_css` already exists from the landing experiment, point it to the new theme file only.

### Step 4: Update logo and font config

Update `mkdocs.yml`:

```yaml
theme:
  logo: assets/logo.png
  favicon: assets/favicon.ico
  font:
    text: Manrope
    code: Roboto Mono
```

If Manrope load fails or visually feels wrong, fallback to Roboto or Inter.

### Step 5: Restore homepage to docs-first content

The homepage should be simple. Suggested structure:

```markdown
# OWASP BLT Documentation

Welcome to the documentation hub for OWASP BLT, the Bug Logging Tool ecosystem.
Use these docs to understand BLT, contribute to the right repository, and keep project documentation up to date.

<div class="grid cards" markdown>

-   :material-rocket-launch-outline: __Get started__

    Set up BLT locally and understand the main workflow.

    [Setup guide](getting-started/setup.md)

-   :material-source-branch: __Contribute__

    Find contribution instructions and project conventions.

    [Contributing guide](developer-guide/contributing.md)

-   :material-folder-search-outline: __Explore projects__

    Browse BLT repositories and choose where to work.

    [All projects](getting-started/projects.md)

-   :material-api: __Build with BLT APIs__

    Read BLT-API docs and ecosystem integration notes.

    [BLT-API](repositories/blt-api.md)

</div>

## What you can find here

- User guides for using BLT
- Developer guides for contributing
- Repository documentation for BLT ecosystem projects
- Deployment and maintenance notes for the docs site
```

Important:

- No broken shield badge wall.
- No star-history embed.
- No big custom HTML hero.
- No historical claims that are not verified.

### Step 6: Header polish checklist

- Header background is BLT red.
- Tabs are BLT red or slightly deeper red.
- Search box remains readable.
- Logo is visible and not distorted.
- Header links have accessible contrast.
- Dark mode toggle remains visible.

### Step 7: Footer polish checklist

- Footer uses dark BLT surface.
- Footer links are readable.
- Social icons still work.
- Previous/next navigation remains visible.

### Step 8: Content modernization agenda

This is the main long-term agenda for BLT-docs after visual polish.

Need create or update content around:

1. Current BLT overview
   - What BLT is now
   - What is historical vs current
   - Where active development lives

2. Contributor routing
   - Docs contributors
   - API contributors
   - Design contributors
   - Product-module contributors
   - Maintainers

3. Repository map
   - BLT-docs
   - BLT-API
   - BLT-Design
   - BLT-Jobs
   - Hackathons
   - Newsletter
   - CLI/MCP and future modules
   - GitHub/GitLab migration status where confirmed

4. BLT-API docs as one project page
   - Not the homepage focus
   - Keep API details in `repositories/blt-api.md`

5. Docs maintenance
   - How to run MkDocs
   - How to add pages
   - How to update screenshots/assets
   - How to check links/content quality
   - How Cloudflare deployment works

6. Agentic contribution guidance
   - README remains human-first
   - Dense agent context belongs in `AGENTS.md`, `llm.txt`, issue bodies, or docs pages
   - Require tests/build/screenshot evidence for agent-made changes

## Files likely to change in first implementation slice

```text
mkdocs.yml
docs/index.md
docs/assets/stylesheets/blt-theme.css
```

Possibly remove:

```text
docs/assets/stylesheets/blt-home.css
```

## Verification

Run:

```bash
uvx --with-requirements requirements.txt mkdocs build --strict
```

Preview:

```bash
uvx --with-requirements requirements.txt mkdocs serve -a 127.0.0.1:8001
```

Check:

- Home page renders normally.
- Header is BLT-branded.
- Footer is BLT-branded.
- Logo appears correctly.
- Search opens and is readable.
- Dark mode is readable.
- Homepage local links return 200.
- Browser console has no errors.

## Suggested GitLab issue updates

Since #3 currently says landing page, update or comment on #3 with the changed direction:

New direction comment:

```text
Direction update: we are skipping the custom landing-page approach because it fights the inherited MkDocs layout. The homepage should stay MkDocs-native and documentation-first. This task should now focus on a clean docs homepage plus BLT header/footer/color/font/logo polish.
```

Issue #2 remains useful as the broader visual-system refresh, but first implementation can be a small #3 slice.

## Recommended commit shape

If implementation is small:

```text
feat(docs): apply BLT branding to MkDocs theme
```

If homepage and theme are separated:

```text
style(docs): add BLT theme colors to MkDocs
```

```text
docs(home): simplify homepage for documentation hub
```

## Risks

- MkDocs Material class names can change, so keep overrides minimal.
- Header/search contrast needs manual visual QA.
- Logo may not fit header dimensions without small CSS adjustment.
- Manrope may change page feel; test before keeping.

## Final recommendation

Do this as a small, reviewable style/content PR:

1. Revert custom landing-page experiment.
2. Add `blt-theme.css` with minimal MkDocs-native overrides.
3. Set logo/font/palette in `mkdocs.yml`.
4. Restore homepage to a clean docs hub using Material card grid.
5. Verify strict build and visual QA.

This gives BLT-docs a BLT touch without fighting MkDocs.
