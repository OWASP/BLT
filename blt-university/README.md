# BLT University

**Live Site:** [https://university.owaspblt.org/](https://university.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/BLT/tree/main/blt-university](https://git.owaspblt.org/BLT/BLT/tree/main/blt-university)

<p align="center"><img src="logo.png" alt="blt-university logo" width="160" height="160"></p>

[![Pipeline status](https://git.owaspblt.org/BLT/BLT/badges/main/pipeline.svg)](https://git.owaspblt.org/BLT/BLT/pipelines)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

BLT University is the open-source cybersecurity learning platform maintained by the OWASP BLT community. It combines short, structured courses with browser-based security labs, local learning progress, and current vulnerability intelligence in a statically generated site.

[Open BLT University](https://university.owaspblt.org/) · [Browse the source](https://git.owaspblt.org/BLT/BLT/tree/main/blt-university) · [Read the contribution guide](CONTRIBUTING.md)

## What is included

- Five focused learning paths, from cybersecurity foundations to advanced application, cloud, and cryptography topics.
- Thirteen hands-on labs covering common security weaknesses and defensive reasoning.
- Interactive course activities built around evidence review, DevTools inspection, security decisions, and ordered response steps.
- Browser-local progress, streaks, recommendations, and achievement badges. No account is required and learning state is not sent to a server.
- A Security Trends dashboard backed by a validated 90-day NVD and CISA KEV dataset.
- Schema validation, JavaScript tests, data-pipeline tests, and cross-browser learner-flow tests in GitLab CI.

## Learning model

Courses use a compact sequence:

1. Read a short explanation of the security concept.
2. Work through an activity or inspect realistic mock evidence.
3. Open the related practice labs when the topic has an existing lab.
4. Return to the course and continue from locally saved progress.
5. Move to the recommended next course.

All exercises run with static or simulated data. They do not target external systems or require provider credentials.

## Getting started

### For students

1. **Browse Courses**: Visit [BLT University](https://university.owaspblt.org/) to explore our catalog.
2. **Request a Course**: Don't see what you're looking for? [Request a course or topic](https://git.owaspblt.org/BLT/BLT/issues/new) you'd like to learn.
3. **Create a GitLab Account**: If you don't have one, [sign up for GitLab](https://gitlab.com/users/sign_up).
4. **Enroll**: Submit an [enrollment request](https://git.owaspblt.org/BLT/BLT/issues/new).
5. **Start Learning**: Open a course and work through its lessons and practice labs.

### For instructors

Want to teach at BLT University?

1. Read the [contributing guide](CONTRIBUTING.md).
2. Use the [course submission issue](https://git.owaspblt.org/BLT/BLT/issues/new).
3. Build the course with the existing content and layout conventions.
4. Open a merge request for review.

## Technology

- [Jekyll](https://jekyllrb.com/) generates the static site.
- Markdown and YAML front matter define courses, labs, instructors, and pages.
- Vanilla JavaScript powers labs, validation, local progress, recommendations, and dashboard interactions.
- Jest and jsdom cover functional JavaScript behavior.
- Playwright verifies the complete learner journey in desktop Chromium, Firefox, WebKit, and mobile Chromium.
- GitLab CI validates, builds, tests, and publishes the site.

## Repository structure

```text
.
├── _courses/                         Course lessons and activities
├── _labs/                            Hands-on lab content and tasks
├── _pages/                           Top-level site pages
├── _layouts/                         Jekyll page and learning layouts
├── _includes/                        Shared interface components
├── _data/                            Navigation and vulnerability datasets
├── assets/js/                        Site, course, lab, and dashboard behavior
├── docs/                             Lab-authoring documentation and template
├── schemas/                          Lab and vulnerability-data schemas
├── scripts/                          Content validation and data refresh tools
├── tests/e2e/                        Cross-browser learner-flow tests and guide
├── tests/vulnerability_intel/        Vulnerability pipeline tests
├── tests/                            Jest functional and content tests
├── .gitlab-ci.yml                    Validation, build, test, and deploy jobs
├── playwright.config.js              Cross-browser E2E configuration
└── _config.yml                       Jekyll and site configuration
```

The generated `public/` directory is a deployment artifact. Make source changes in the Jekyll content, layouts, data, or assets rather than editing generated files directly.

## Local development

### Requirements

- Ruby 3.2 and Bundler
- Node.js 20 and npm
- Python 3.11 for content and vulnerability-data validation

### Setup

```bash
git clone https://git.owaspblt.org/BLT/BLT.git
cd blt-university

bundle install
npm ci
bundle exec jekyll serve
```

Open `http://127.0.0.1:4001/`.

Jekyll watches source files and rebuilds while the server is running. Restart it after changing `_config.yml`.

## Tests and validation

Run the JavaScript functional and content tests:

```bash
npm test
```

Run the complete E2E learner journey locally:

```bash
npx playwright install
npm run test:e2e:local
```

This checks the learner journey in desktop Chromium, Firefox, WebKit, and mobile Chromium.

See [`tests/e2e/README.md`](tests/e2e/README.md) for the test architecture, page-object conventions, and authoring guidance.

Confirm that the production Jekyll build succeeds:

```bash
JEKYLL_ENV=production bundle exec jekyll build
```

Validate lab front matter and tasks:

```bash
python -m pip install jsonschema==4.25.1 python-frontmatter==1.1.0
python scripts/validate_labs.py
```

Validate the committed vulnerability dataset and its pipeline tests:

```bash
python -m pip install "jsonschema[format-nongpl]==4.25.1"
python -B scripts/vulnerability_intel/validate.py
python -B -m unittest discover -s tests/vulnerability_intel -p 'test_*.py' -v
```

## Authoring learning content

Course files live in `_courses/`. Each course defines its metadata and ordered lessons in YAML front matter, followed by a short course introduction. A lesson can include an example, observation, interactive challenge, or links to existing practice labs.

Labs live in `_labs/` and must satisfy [`schemas/lab.schema.json`](schemas/lab.schema.json). Start with the [lab-authoring guide](docs/lab-authoring-guide.md) and [lab template](docs/lab-template.md), then run the validator and tests before opening a merge request.

Keep new content concise, concrete, and safe:

- Use mock targets and synthetic evidence.
- Explain the trust boundary or defensive lesson behind an activity.
- Reuse existing lab components and validators when possible.
- Do not include live credentials, private data, or instructions that depend on attacking external systems.
- Test keyboard behavior, narrow layouts, refreshes, and saved progress.

## Local learning data

Learning state is stored in the browser using these localStorage keys:

- `blt-lab-progress` for completed lab tasks.
- `blt-course-progress` for course lessons, challenges, and completion.
- `blt-learning-progress` for activity history, streaks, and achievements.

Storage failures or malformed saved values are handled without blocking course and lab interactions. Clearing site data in the browser resets progress on that device.

## Security Trends and vulnerability intelligence

The [Security Trends dashboard](https://university.owaspblt.org/dashboard/) turns recent vulnerability disclosures into learning paths:

1. The NVD CVE API supplies published CVEs, CWE identifiers, CVSS metrics, and affected products.
2. The CISA Known Exploited Vulnerabilities catalog adds the known-exploitation signal.
3. `_data/cwe_owasp_lab_mapping.json` maps CWE identifiers to OWASP Top 10:2021 categories and BLT University labs.
4. Description matching is used only when no usable structured CWE is available; those records are labeled `description_fallback` with lower confidence.

The dashboard provides category, distribution, and trend views with text fallbacks when charts cannot load. Selecting a category filters the learning map and CVE explorer, then updates the recommended lab. The recommendation combines vulnerability frequency, incomplete local lab progress, and CISA KEV activity.

Refresh the committed 90-day dataset with:

```bash
python -B scripts/vulnerability_intel/update.py --days 90
python -B scripts/vulnerability_intel/validate.py
```

Set `NVD_API_KEY` to increase the NVD request rate when refreshing data. Review the generated changes before committing `_data/vulnerability_intel.json`.

## Continuous integration and deployment

The GitLab pipeline contains the following relevant jobs:

- `validate-labs` checks lab content when lab or schema files change.
- `validate-vulnerability-intel` validates the dataset and Python pipeline tests when related files change.
- `build_site` generates the production site in `public/`.
- `test_js` runs the Jest suite.
- `test_e2e` runs the Playwright learner journey against the build artifact.
- `pages` publishes `public/` from the default branch to GitLab Pages.
- `commit_built_pages` commits the generated `public/` output for the connected production deployment.

## Contributing

Contributions to content, accessibility, simulations, tests, data quality, and documentation are welcome. Before opening a merge request:

1. Create a focused branch.
2. Follow the existing content and code style.
3. Run the relevant validators, Jest suite, production build, and E2E test.
4. Describe the learner-facing change and how it was verified.
5. Avoid committing generated test output, local environment files, or credentials.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and review expectations.

## License

BLT University is licensed under the [GNU Affero General Public License v3.0](LICENSE). Contributions are accepted under the same license.

## Project links

- Website: [university.owaspblt.org](https://university.owaspblt.org/)
- GitLab: [owasp-blt/blt-university](https://git.owaspblt.org/BLT/BLT/tree/main/blt-university)
- OWASP BLT: [owaspblt.org](https://owaspblt.org/)
- OWASP project page: [Bug Logging Tool](https://owasp.org/www-project-bug-logging-tool/)
