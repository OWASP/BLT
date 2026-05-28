# 🎓 BLT University

> Open-Source Cybersecurity Education for Everyone

[![GitLab Pages](https://img.shields.io/badge/GitLab-Pages-blue?style=flat-square&logo=gitlab)](https://university.owaspblt.org/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

BLT University is a revolutionary **GitLab Pages-based online university** focused on cybersecurity education. We believe security knowledge should be free, collaborative, and community-driven.

## 🌟 What Makes Us Different

- **100% Free & Open Source**: All courses and materials are freely available
- **GitLab-Powered Learning**: Learn through pull requests, issues, and GitLab CI/CD
- **Industry Expert Instructors**: Courses taught by experienced security professionals
- **Hands-On Focus**: Practical labs, real-world projects, and interactive content
- **Community-Driven**: Built by the community, for the community
- **Multiple Content Types**: Videos, PDFs, labs, meetups, and more

## 📚 Browse Courses

Visit our [Course Catalog](https://university.owaspblt.org/courses/) to explore available courses in:

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

1. **Browse Courses**: Visit [BLT University](https://university.owaspblt.org/) to explore our catalog
2. **Request a Course**: Don't see what you're looking for? [Request a course or topic](https://gitlab.com/owasp-blt/blt-university/-/issues/new) you'd like to learn
3. **Create GitLab Account**: If you don't have one, [sign up for GitLab](https://gitlab.com/users/sign_up)
4. **Enroll**: Submit an [enrollment request](https://gitlab.com/owasp-blt/blt-university/-/issues/new)
5. **Start Learning**: Access course materials and begin your journey!

### For Instructors

Want to teach at BLT University? We'd love to have you!

1. **Read the Guide**: Check out our [Contributing Guide](contributing.html)
2. **Submit Proposal**: Use our [course submission template](https://gitlab.com/owasp-blt/blt-university/-/issues/new)
3. **Create Course**: Develop your course using our templates
4. **Submit PR**: Submit a pull request with your course materials
5. **Go Live**: Once approved, your course joins our catalog!

## 🏗️ How It Works

### GitLab Pages-Based Platform

All courses are hosted as static content on GitLab Pages, making them:
- **Version Controlled**: Track changes and improvements over time
- **Collaborative**: Anyone can suggest improvements via pull requests
- **Transparent**: All course materials are open and visible
- **Fast & Reliable**: Served through GitLab Pages infrastructure

### Course Management

- **Course Files**: Stored in `_courses/` directory as Markdown with YAML front matter
- **Instructor Profiles**: Stored in `_instructors/` directory
- **Automatic Publishing**: Jekyll builds the site automatically on push
- **Easy Updates**: Instructors update courses via pull requests

### Enrollment System

- **GitLab Issues**: Students enroll by creating an issue
- **Automated Workflows**: GitLab CI/CD processes enrollments automatically
- **Access Control**: Students added to course repositories upon approval
- **Certificate Generation**: Automated certificate creation on completion

### Content Types Supported

- 📹 **Videos**: YouTube embeds, hosted videos
- 📄 **PDFs**: Slides, guides, reference materials
- 💻 **Code**: GitLab repositories, interactive coding exercises
- 🔗 **External Resources**: Links to tools, documentation
- 📅 **Events**: Live meetups, virtual sessions
- ✏️ **Assignments**: GitLab-based homework and projects

## 🛠️ Technical Architecture

### Built With

- **Jekyll**: Static site generator
- **GitLab Pages**: Hosting platform
- **GitLab CI/CD**: Automation and workflows
- **Markdown**: Content format
- **YAML**: Course metadata

### Project Structure

```
BLT-University/
├── _courses/              # Course content files
├── _instructors/          # Instructor profiles
├── _layouts/              # Jekyll layouts
├── _includes/             # Reusable components
├── assets/
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript
├── .gitlab-ci.yml        # GitLab Pages deployment
├── _config.yml           # Jekyll configuration
└── *.html                # Static pages
```

### Local Development

To run the site locally:

```bash
# Clone the repository
git clone https://gitlab.com/owasp-blt/blt-university.git
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
- **💡 Request Courses**: Tell us what you want to learn using our [course request form](https://gitlab.com/owasp-blt/blt-university/-/issues/new)
- **🌍 Translate**: Help make content accessible globally

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 🌐 Community

- **GitLab Issues**: Ask questions, share knowledge
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

BLT University is part of the [OWASP BLT Project](https://gitlab.com/owasp-blt), dedicated to building open-source security tools and education.

Special thanks to:
- All our instructors and contributors
- The OWASP community
- GitLab for providing amazing tools
- Our students who make this worthwhile

## 📊 Stats

- 📚 **Courses**: 6+ and growing
- 👨‍🏫 **Instructors**: 2+ expert instructors
- 🎯 **Categories**: 10 security specializations
- 🆓 **Cost**: Always FREE

## 🔗 Links

- **Website**: [https://university.owaspblt.org/](https://university.owaspblt.org/)
- **GitLab**: [https://gitlab.com/owasp-blt/blt-university](https://gitlab.com/owasp-blt/blt-university)
- **OWASP BLT**: [https://gitlab.com/owasp-blt](https://gitlab.com/owasp-blt)

## 💬 Support

Need help? Have questions?

- 📖 Check our [Documentation](https://university.owaspblt.org/)
- 💬 Join [GitLab Issues](https://gitlab.com/owasp-blt/blt-university/-/issues)
- 🐛 Report [Issues](https://gitlab.com/owasp-blt/blt-university/-/issues)

---

<div align="center">

**Made with ❤️ by the OWASP BLT Community**

[Website](https://university.owaspblt.org/) • [Enroll](https://gitlab.com/owasp-blt/blt-university/-/issues/new) • [Request Course](https://gitlab.com/owasp-blt/blt-university/-/issues/new) • [Teach](https://gitlab.com/owasp-blt/blt-university/-/issues/new) • [Contribute](CONTRIBUTING.md)

⭐ Star us on GitLab — it helps!

</div>
