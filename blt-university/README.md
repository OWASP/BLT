# 🎓 BLT University

> Open-Source Cybersecurity Education for Everyone

[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-blue?style=flat-square&logo=github)](https://owasp-blt.github.io/BLT-University/)
[![GitLab Pages](https://img.shields.io/badge/GitLab-Pages-orange?style=flat-square&logo=gitlab)](https://university.owaspblt.org/)
[![Cloudflare Pages](https://img.shields.io/badge/Cloudflare-Pages-f38020?style=flat-square&logo=cloudflare)](https://university.owaspblt.org/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

BLT University is a revolutionary **static online university** focused on cybersecurity education. We believe security knowledge should be free, collaborative, and community-driven.

## 🌟 What Makes Us Different

- **100% Free & Open Source**: All courses and materials are freely available
- **GitHub-Powered Learning**: Learn through pull requests, issues, and GitHub Actions
- **Industry Expert Instructors**: Courses taught by experienced security professionals
- **Hands-On Focus**: Practical labs, real-world projects, and interactive content
- **Community-Driven**: Built by the community, for the community
- **Multiple Content Types**: Videos, PDFs, labs, meetups, and more

## 📚 Browse Courses

Visit our [Course Catalog](https://owasp-blt.github.io/BLT-University/courses/) to explore available courses in:

- 🌐 Web Security
- 🔒 Network Security
- 🔐 Cryptography
- 🎯 Penetration Testing
- 💻 Secure Coding
- 🦠 Malware Analysis
- ☁️ Cloud Security
- 📱 Mobile Security
- 🚨 Incident Response
- 🛡️ Security Operations

## 🚀 Getting Started

### For Students

1. **Browse Courses**: Visit [BLT University](https://owasp-blt.github.io/BLT-University/) to explore our catalog
2. **Request a Course**: Don't see what you're looking for? [Request a course or topic](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-request.yml) you'd like to learn
3. **Create GitHub Account**: If you don't have one, [sign up for GitHub](https://github.com/signup)
4. **Enroll**: Submit an [enrollment request](https://github.com/OWASP-BLT/BLT-University/issues/new?template=enrollment.yml)
5. **Start Learning**: Access course materials and begin your journey!

### For Instructors

Want to teach at BLT University? We'd love to have you!

1. **Read the Guide**: Check out our [Contributing Guide](contributing.html)
2. **Submit Proposal**: Use our [course submission template](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-submission.yml)
3. **Create Course**: Develop your course using our templates
4. **Submit PR**: Submit a pull request with your course materials
5. **Go Live**: Once approved, your course joins our catalog!

## 🏗️ How It Works

### GitLab-Built Static Platform

All courses are built as static content in GitLab CI and published from the same `public/` artifact to GitLab Pages and Cloudflare Pages, making them:
- **Version Controlled**: Track changes and improvements over time
- **Collaborative**: Anyone can suggest improvements via pull requests
- **Transparent**: All course materials are open and visible
- **Fast & Reliable**: Served through static hosting on GitLab and Cloudflare

### Course Management

- **Course Files**: Stored in `_courses/` directory as Markdown with YAML front matter
- **Instructor Profiles**: Stored in `_instructors/` directory
- **Automatic Publishing**: GitLab CI builds the Jekyll site into `public/` on push
- **Easy Updates**: Instructors update courses via pull requests

### Enrollment System

- **GitHub Issues**: Students enroll by creating an issue
- **Automated Workflows**: GitHub Actions process enrollments automatically
- **Access Control**: Students added to course repositories upon approval
- **Certificate Generation**: Automated certificate creation on completion

### Content Types Supported

- 📹 **Videos**: YouTube embeds, hosted videos
- 📄 **PDFs**: Slides, guides, reference materials
- 💻 **Code**: GitHub repositories, interactive coding exercises
- 🔗 **External Resources**: Links to tools, documentation
- 📅 **Events**: Live meetups, virtual sessions
- ✏️ **Assignments**: GitHub-based homework and projects

## 🛠️ Technical Architecture

### Built With

- **Jekyll**: Static site generator
- **GitHub Pages**: Hosting platform
- **GitLab Pages**: CI build artifact and static hosting
- **Cloudflare Pages**: Public production hosting
- **GitHub Actions**: Automation and workflows
- **Markdown**: Content format
- **YAML**: Course metadata

### Project Structure

```
BLT-University/
├── _pages/                # Source pages rendered into public URLs
├── _courses/              # Course content files
├── _instructors/          # Instructor profiles
├── _layouts/              # Jekyll layouts
├── _includes/             # Reusable components
├── assets/
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript
├── .github/
│   ├── workflows/        # GitHub Actions
│   └── ISSUE_TEMPLATE/   # Issue templates
├── .gitlab-ci.yml        # GitLab build, GitLab Pages, and Cloudflare Pages deployment
├── wrangler.toml         # Cloudflare Pages output configuration
├── public/               # Generated pages committed by GitLab CI for Cloudflare
└── _config.yml           # Jekyll configuration
```

### GitLab and Cloudflare Deployment

GitLab CI builds the site once with:

```bash
bundle exec jekyll build -d public
```

The `pages` job publishes that artifact to GitLab Pages. The `commit_built_pages` job commits the generated `public/` files back to the default branch with `[skip ci]`, which lets Cloudflare Pages deploy automatically from the connected repository using the `public/` output directory configured in `wrangler.toml`.

If `CI_JOB_TOKEN` is not allowed to push to the repository, configure a masked GitLab CI/CD variable named `CI_PUSH_TOKEN` with a project access token that can write to the default branch.

### Local Development

To run the site locally:

```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT-University.git
cd BLT-University

# Install dependencies
bundle install

# Run Jekyll locally
bundle exec jekyll serve

# Visit http://localhost:4000/BLT-University/
```

## 📖 Documentation

- **[Course Creation Guide](contributing.html)**: How to create a course
- **[Student Handbook](#)**: Guide for students
- **[Instructor Handbook](#)**: Guide for instructors
- **[API Documentation](#)**: For developers building tools

## 🤝 Contributing

We welcome contributions from everyone! Here's how you can help:

- **🎓 Teach a Course**: Share your expertise
- **📝 Improve Content**: Fix typos, add examples, clarify concepts
- **🐛 Report Issues**: Found a problem? Let us know
- **💡 Request Courses**: Tell us what you want to learn using our [course request form](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-request.yml)
- **🌍 Translate**: Help make content accessible globally

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 🌐 Community

- **GitHub Discussions**: Ask questions, share knowledge
- **Issues**: Report bugs, request features
- **Pull Requests**: Contribute code and content
- **Social Media**: Follow us for updates

## 📜 License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

- ✅ **You Can**: View, use, modify, and distribute all content
- ✅ **You Must**: Share modifications under the same license
- ✅ **You Must**: Provide source code for network services
- ❌ **No Warranty**: Content provided as-is

See [LICENSE](LICENSE) for full details.

## 🙏 Acknowledgments

BLT University is part of the [OWASP BLT Project](https://github.com/OWASP-BLT), dedicated to building open-source security tools and education.

Special thanks to:
- All our instructors and contributors
- The OWASP community
- GitHub for providing amazing tools
- Our students who make this worthwhile

## 📊 Stats

- 📚 **Courses**: 6+ and growing
- 👨‍🏫 **Instructors**: 2+ expert instructors
- 🎯 **Categories**: 10 security specializations
- 🆓 **Cost**: Always FREE

## 🔗 Links

- **Website**: [https://owasp-blt.github.io/BLT-University/](https://owasp-blt.github.io/BLT-University/)
- **Cloudflare Pages**: [https://university.owaspblt.org/](https://university.owaspblt.org/)
- **GitHub Pages**: [https://owasp-blt.github.io/BLT-University/](https://owasp-blt.github.io/BLT-University/)
- **GitHub**: [https://github.com/OWASP-BLT/BLT-University](https://github.com/OWASP-BLT/BLT-University)
- **GitLab**: [https://gitlab.com/owasp-blt/blt-university](https://gitlab.com/owasp-blt/blt-university)
- **OWASP BLT**: [https://github.com/OWASP-BLT](https://github.com/OWASP-BLT)

## 💬 Support

Need help? Have questions?

- 📖 Check our [Documentation](https://owasp-blt.github.io/BLT-University/)
- 💬 Join [GitHub Discussions](https://github.com/OWASP-BLT/BLT-University/discussions)
- 🐛 Report [Issues](https://github.com/OWASP-BLT/BLT-University/issues)
- GitLab mirror: [Issues](https://gitlab.com/owasp-blt/blt-university/-/issues)

---

<div align="center">

**Made with ❤️ by the OWASP BLT Community**

[Website](https://owasp-blt.github.io/BLT-University/) • [GitLab](https://gitlab.com/owasp-blt/blt-university) • [Enroll](https://github.com/OWASP-BLT/BLT-University/issues/new?template=enrollment.yml) • [Request Course](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-request.yml) • [Teach](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-submission.yml) • [Contribute](CONTRIBUTING.md)

⭐ Star us on GitHub — it helps!

</div>
