# BLT Jobs

A community-driven job board for the OWASP BLT ecosystem, built with GitHub Pages.

## Features

- **Post Job Opportunities**: Companies can post jobs via pull requests (Quick add from URL or manual file creation)
- **Feature Job Seeker Profiles**: Professionals can showcase their skills and availability
- **Automated Processing**: GitHub Actions automatically converts job URLs to markdown files and builds JSON data
- **Beautiful Design**: Built with BLT design guidelines using Tailwind CSS
- **Easy to Use**: Submit via pull requests, no complex forms needed

## How to Use

### For Employers - Post a Job

1. Go to the [Add a job](add.html) page
2. Choose **Quick add** (recommended) or **Manual add**:
   - **Quick add:** Open a [new pull request](https://github.com/OWASP-BLT/BLT-Jobs/compare) and paste the job listing URL in the PR description (or in a file named `job-url.txt`). Our bot will scrape the page and create a job file for you. Supported sites: Greenhouse, Lever, Workable, and other common ATS and career pages.
   - **Manual add:** Create a new file under `jobs/` with the filename format `company-slug-job-title-slug.md` (e.g. `acme-senior-engineer.md`). Use [the sample job](jobs/example-company-sample-job.md) as a template. Open a PR with your new file.
3. Your job will be automatically published to the [Jobs page](jobs.html) once the PR is merged.

Jobs are stored as `company-slug-job-title-slug.md` in the `jobs/` directory.

### For Job Seekers - Create Your Profile

1. Go to the [Add a job](add.html) page and scroll to the "Create a job seeker profile" section
2. Create a new file under `seekers/` named after you (e.g. `jane-doe.md`)
3. Use the frontmatter + body format from [`seekers/example-seeker.md`](seekers/example-seeker.md)
4. Open a pull request with your new file
5. Your profile will be automatically published to the [Seekers page](seekers.html) once merged

Profiles are stored as `name-slug.md` in the `seekers/` directory.

## File Structure

```
BLT-Jobs/
├── index.html          # Landing page (hero, How It Works, recent listings)
├── jobs.html           # Full job listings page
├── job.html            # Individual job detail page
├── seekers.html        # Job seeker profiles page
├── add.html            # Contribute page (add jobs or create profiles)
├── jobs/               # Job posting markdown files (company-slug-job-title-slug.md)
├── seekers/            # Job seeker markdown files (name-slug.md)
├── data/               # Generated JSON files (jobs.json, seekers.json)
├── assets/             # JavaScript and CSS assets
├── scripts/            # Build scripts and scrapers
├── .github/
│   ├── workflows/
│   │   ├── build-jobs.yml        # Auto-build JSON from markdown
│   │   └── quick-add-job.yml     # Auto-process job URLs from PRs
│   └── PULL_REQUEST_TEMPLATE/
│       ├── PULL_REQUEST_TEMPLATE.md  # Default PR template
│       └── quick_add.md              # Quick add PR template
└── README.md
```

## Design

This project follows the [BLT Design Guidelines](https://github.com/OWASP-BLT/BLT-Design), featuring:

- Tailwind CSS for styling
- Red accent colors (#e74c3c)
- Responsive, accessible design
- Font Awesome icons
- Dark mode support

## Contributing

Contributions are welcome! This is an OWASP BLT community project.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is part of the [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/).

## Links

- [Live Site](https://pritz395.github.io/BLT-Jobs/) (when GitHub Pages is enabled)
- [OWASP BLT](https://github.com/OWASP-BLT/BLT)
- [BLT Design System](https://github.com/OWASP-BLT/BLT-Design)

## Technical Details

### Data Model

Jobs and seeker profiles are stored as Markdown files with YAML frontmatter. A build script (`npm run build:jobs`) generates `data/jobs.json` and `data/seekers.json` from these files. The build runs automatically via GitHub Actions on push to `main`.

### Local Development

```bash
# Install dependencies
npm ci

# Build data files from markdown
npm run build:jobs

# Serve locally
python -m http.server 8000
```

Then open:
- `http://localhost:8000/index.html` – landing page
- `http://localhost:8000/jobs.html` – job list
- `http://localhost:8000/seekers.html` – seeker profiles
- `http://localhost:8000/job.html?id=<job-id>` – job detail

Note: `fetch("data/jobs.json")` requires running over HTTP/HTTPS; opening `index.html` directly from the filesystem (`file://`) will not work.
