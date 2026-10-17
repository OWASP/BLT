# End-to-end tests

The E2E suite verifies BLT University as a learner experiences it in a real browser. It exercises the built Jekyll site, not individual JavaScript functions, so the suite catches broken routes, missing assets, inaccessible controls, progress regressions, and navigation failures.

## Run the suite

Install the browser binaries once:

```bash
npx playwright install
```

Run against the existing site artifact:

```bash
npm run test:e2e
```

Build the Jekyll site first and run the same suite locally:

```bash
npm run test:e2e:local
```

Use Playwright UI mode while developing a test:

```bash
npm run test:e2e:ui
```

## Test layout

```text
tests/e2e/
├── helpers/               Test-only server and shared infrastructure
│   └── static-server.js
├── pages/                 Page objects and learner-facing actions
│   └── course-page.js
├── course-catalog.spec.js   Course list and search coverage
├── course-learning.spec.js  Complete course learning journey
└── fixtures.js              Shared runtime-error guard and page fixtures
```

`course-page.js` keeps stable locators and common actions in one place. Specs describe the learner outcome and use semantic roles for visible controls. `fixtures.js` fails a test when the page emits a console error, uncaught page error, or failed request.

## Adding a test

1. Start with a user-visible flow, such as opening a course, completing an activity, returning from a lab, or checking saved progress after a reload.
2. Add stable `data-*` hooks only when an accessible role or visible label cannot identify the element.
3. Put reusable page actions in `tests/e2e/pages/`; keep scenario assertions in the spec.
4. Keep tests independent. Each test receives a fresh browser context and must not depend on another test's local progress.
5. Run `npm test`, `npm run test:e2e:local`, and the relevant content validator before opening a merge request.

The configured projects cover desktop Chromium, Firefox, WebKit, and mobile Chromium. CI uploads the Playwright report and test artifacts when a job fails.
