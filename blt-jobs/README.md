# BLT Jobs

A community-driven job board for the OWASP BLT ecosystem, built with GitHub Pages.

## 🌟 Features

- **Post Job Opportunities**: Companies can post jobs via GitHub issues
- **Feature Job Seeker Profiles**: Professionals can showcase their skills and availability
- **Automated Processing**: GitHub Actions automatically converts submissions to markdown files
- **Beautiful Design**: Built with BLT design guidelines using Tailwind CSS
- **Easy to Use**: Submit via GitHub issues, no complex forms needed

## 🚀 How to Use

### For Employers - Post a Job

1. Go to [Issues](https://github.com/OWASP-BLT/BLT-Jobs/issues/new?template=job-posting.md)
2. Select "Job Posting" template
3. Fill out the job details
4. Submit the issue
5. Your job will be automatically published to the [Jobs page](https://owasp-blt.github.io/BLT-Jobs/jobs.html)

Jobs are stored as `domain.com-job-title.md` in the `jobs/` directory.

### For Job Seekers - Create Your Profile

1. Go to [Issues](https://github.com/OWASP-BLT/BLT-Jobs/issues/new?template=job-seeker.md)
2. Select "Job Seeker Profile" template
3. Fill out your profile information
4. Submit the issue
5. Your profile will be automatically published to the [Seekers page](https://owasp-blt.github.io/BLT-Jobs/seekers.html)

Profiles are stored as `seekers/name.md` in the `seekers/` directory.

## 📁 File Structure

```
BLT-Jobs/
├── index.html          # Home page
├── jobs.html           # Job listings page
├── seekers.html        # Job seeker profiles page
├── jobs/               # Job posting markdown files (domain.com-job-title.md)
├── seekers/            # Job seeker markdown files (name.md)
├── .github/
│   ├── workflows/
│   │   ├── process-submissions.yml  # Auto-process issues
│   │   └── pages.yml                # Deploy to GitHub Pages
│   └── ISSUE_TEMPLATE/
│       ├── job-posting.md           # Job posting template
│       └── job-seeker.md            # Job seeker template
└── README.md
```

## 🎨 Design

This project follows the [BLT Design Guidelines](https://github.com/OWASP-BLT/BLT-Design), featuring:
- Tailwind CSS for styling
- Inter font family
- Red accent colors (#dc2626)
- Responsive, accessible design
- Font Awesome icons

## 🤝 Contributing

Contributions are welcome! This is an OWASP BLT community project.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is part of the [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/).

## 🔗 Links

- [Live Site](https://owasp-blt.github.io/BLT-Jobs/)
- [OWASP BLT](https://github.com/OWASP-BLT/BLT)
- [BLT Design System](https://github.com/OWASP-BLT/BLT-Design)