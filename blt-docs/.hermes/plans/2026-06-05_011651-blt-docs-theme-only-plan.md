# BLT-docs Theme-Only Redesign Plan

## Goal

Change direction for BLT-docs issue #3: do not ship a custom landing page inside MkDocs. Instead, keep the default MkDocs documentation homepage structure and focus on a clean BLT-branded theme pass, mainly header, footer, palette, links, and small visual polish.

## Current context

- Current branch should remain unchanged; do not switch branches for this plan.
- Local branch currently has experimental landing-page changes:
  - `docs/index.md`
  - `mkdocs.yml`
  - `docs/assets/stylesheets/blt-home.css`
- User reviewed the landing-page direction and decided it does not fit MkDocs well.
- New direction: keep MkDocs feeling like documentation, not a product landing page.
- Target GitLab work item remains #3 for homepage/design direction, but implementation should be reduced to MkDocs-native polish.

## Proposed approach

Use MkDocs Material as intended:

1. Restore or simplify `docs/index.md` so it is docs-first, not custom product-page HTML.
2. Keep a small custom stylesheet, but scope it to MkDocs theme polish rather than custom landing-page components.
3. Update header/footer colors and surface polish to match BLT red and dark-mode tokens.
4. Remove heavy custom hero/dashboard/card layout unless a minimal docs intro block is still useful.
5. Verify build and visual appearance in both light/dark modes.

## What to keep

- MkDocs Material navigation and search.
- Existing docs sections: Getting Started, Features, User Guide, Developer Guide, Repositories.
- BLT red as the primary brand color.
- A short homepage introduction if desired.
- Stable links to setup, contributing, projects, BLT-API, BLT-Jobs.

## What to remove/revert from the landing-page experiment

- Custom hero/dashboard layout in `docs/index.md`.
- Large landing-page card sections.
- Dashboard/terminal mockup.
- Heavy scoped `.blt-home` component CSS.
- Any homepage design that fights MkDocs content width/sidebar layout.

## Step-by-step plan

### Step 1: Preserve current work safely

Do not change branches. Before changing files, inspect status and optionally save a patch of the current landing experiment:

```bash
git status --short --branch
git diff > /tmp/blt-docs-landing-page-experiment.patch
```

This keeps the experiment recoverable without committing it.

### Step 2: Restore docs-first homepage

Replace `docs/index.md` with a simple MkDocs-native homepage:

- H1: `OWASP BLT Documentation`
- One concise paragraph explaining the docs hub.
- Four small sections/cards using plain Markdown or Material admonitions:
  - Start using BLT
  - Contribute to BLT
  - Explore repositories
  - Build with BLT APIs
- Remove external badge wall and star-history embed.
- Keep all links local where possible.

Likely homepage outline:

```markdown
# OWASP BLT Documentation

Welcome to the documentation hub for OWASP BLT...

<div class="grid cards" markdown>

-   :material-rocket-launch-outline: __Get started__
    ...
    [Setup guide](getting-started/setup.md)

-   :material-source-branch: __Contribute__
    ...
    [Contributing guide](developer-guide/contributing.md)

-   :material-folder-search-outline: __Explore projects__
    ...
    [All projects](getting-started/projects.md)

-   :material-api: __Build with BLT__
    ...
    [BLT-API](repositories/blt-api.md)

</div>
```

### Step 3: Replace landing CSS with theme CSS

Rename or rewrite `docs/assets/stylesheets/blt-home.css` into something like:

```text
docs/assets/stylesheets/blt-theme.css
```

Then update `mkdocs.yml`:

```yaml
extra_css:
  - assets/stylesheets/blt-theme.css
```

The stylesheet should target MkDocs-native classes, for example:

- `.md-header`
- `.md-tabs`
- `.md-footer`
- `.md-typeset a`
- `.md-typeset .grid.cards > ul > li`
- `.md-typeset .admonition`
- dark-mode variables under `[data-md-color-scheme="slate"]`

### Step 4: Header color direction

Use a clean BLT red header:

- Header background: `#E10101`
- Header hover/active: `#B91C1C`
- Header text: white
- Search box: slightly darker translucent red or white with enough contrast
- Active nav indicator: white or red-soft depending Material constraints

Avoid making the header overly gradient-heavy.

### Step 5: Footer color direction

Use a dark footer that works in both themes:

- Footer background: `#111827`
- Footer surface: `#1F2937`
- Footer links hover: `#EF4444`
- Footer text: muted gray but readable

### Step 6: Homepage polish using MkDocs-native components

Use Material card grid rather than custom HTML landing components:

```markdown
<div class="grid cards" markdown>
...
</div>
```

Optional small intro callout:

```markdown
!!! tip "Looking for where to contribute?"
    Start with the project map, then open the repository guide for your target BLT module.
```

### Step 7: Verification

Run:

```bash
uvx --with-requirements requirements.txt mkdocs build --strict
```

Then preview:

```bash
uvx --with-requirements requirements.txt mkdocs serve -a 127.0.0.1:8001
```

Visual QA checklist:

- Header uses BLT red and has good contrast.
- Footer feels branded and readable.
- Homepage reads like docs, not marketing/product page.
- Cards/admonitions render correctly in MkDocs.
- Search still works.
- Dark mode is readable.
- No console errors.
- Links on homepage resolve.

## Files likely to change

- `docs/index.md`
- `mkdocs.yml`
- `docs/assets/stylesheets/blt-theme.css`
- Possibly remove `docs/assets/stylesheets/blt-home.css` if not reused.

## Risks / tradeoffs

- Minimal theming may feel less dramatic than the landing-page experiment, but it will fit MkDocs better.
- Styling MkDocs internal classes can be sensitive to Material theme updates, so keep overrides small.
- A full design-system refresh belongs in issue #2; issue #3 should now stay homepage/doc-entry focused.

## Recommended final shape

For this branch, the cleanest final MR should be:

1. Restore docs-first homepage with no fragile external badges.
2. Add compact MkDocs Material card-grid entry points.
3. Add BLT header/footer palette overrides.
4. Verify strict build.

Commit message suggestion:

```text
feat(docs): refresh MkDocs homepage and BLT theme colors
```
