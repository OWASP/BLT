# Contributing to BLT University

Thank you for your interest in contributing to BLT University! This document provides guidelines and instructions for contributing.

## 🌟 Ways to Contribute

### 1. Teach a Course

Share your cybersecurity expertise by creating a course!

**Steps:**
1. Submit a [course proposal](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-submission.yml)
2. Wait for approval and feedback from the curriculum team
3. Create your instructor profile in `_instructors/`
4. Develop your course content in `_courses/`
5. Submit a pull request with your materials
6. Work with reviewers to refine your course
7. Celebrate when your course goes live! 🎉

**Course Requirements:**
- Focus on cybersecurity or related topics
- Include clear learning objectives
- Provide multiple content types (videos, documents, labs)
- Follow the course template structure
- License content under AGPL-3.0

### 2. Improve Existing Content

Help make our courses better!

- Fix typos and grammatical errors
- Add examples and clarifications
- Update outdated information
- Improve code samples
- Enhance documentation

**Process:**
1. Fork the repository
2. Create a branch: `git checkout -b improve-course-name`
3. Make your changes
4. Commit: `git commit -m "Improve explanation of XSS in web-security course"`
5. Push: `git push origin improve-course-name`
6. Open a pull request

### 3. Report Issues

Found a problem? Let us know!

- Broken links
- Technical errors in course content
- Accessibility issues
- Website bugs

Use our [issue tracker](https://github.com/OWASP-BLT/BLT-University/issues) with clear descriptions and steps to reproduce.

### 4. Suggest Improvements

Have ideas? We'd love to hear them!

- New course topics
- Platform features
- User experience improvements
- Community initiatives

Open an issue or start a discussion.

## 📝 Course Creation Guide

### Instructor Profile

Create `_instructors/your-name.md`:

```yaml
---
layout: instructor
title: Your Name
expertise: Your Specialization
avatar: /assets/images/instructors/yourname.jpg
github: yourusername
linkedin: yourprofile
twitter: yourhandle
website: https://yoursite.com
---

Your biography goes here. Include:
- Professional background (2-3 paragraphs)
- Expertise areas
- Teaching philosophy
- Notable achievements
- Publications and certifications

Use Markdown for formatting.
```

### Course Structure

Create `_courses/your-course-slug.md`:

```yaml
---
layout: course
title: Your Course Title
category: One of the predefined categories
level: Beginner | Intermediate | Advanced
duration: X weeks
instructor: Your Name (must match instructor profile)
featured: false (set to true for homepage feature)
image: /assets/images/courses/your-course-image.svg (optional)
prerequisites: List prerequisites here
description: 1-2 sentence course description

resources:
  - title: Resource Name
    url: https://link-to-resource
    type: video | pdf | link
  - title: Another Resource
    url: /assets/courses/your-course/file.pdf
    type: pdf

schedule:
  - date: Week 1
    topic: Topic covered this week
  - date: Week 2
    topic: Another topic

syllabus:
  - title: Module 1 Title
    description: Module description
    topics:
      - Subtopic 1
      - Subtopic 2
  - title: Module 2 Title
    description: Another module
    topics:
      - Subtopic A
      - Subtopic B
---

## Course Content Starts Here

Use Markdown to write your course content:

### Section 1

Content here...

### Section 2

More content...

## Hands-On Labs

Describe labs...

## Assessments

Describe assessments...
```

### Content Guidelines

**Writing Style:**
- Clear and concise
- Beginner-friendly explanations
- Use examples and analogies
- Include code snippets with syntax highlighting
- Add diagrams and visuals where helpful

**Security Content:**
- Always emphasize ethical use
- Include legal considerations
- Provide safe lab environments
- Warning about dangerous techniques
- Explain defensive measures

**Accessibility:**
- Use descriptive alt text for images
- Provide transcripts for videos
- Use semantic HTML
- Test with screen readers
- Ensure color contrast

### Course Materials

**Organize materials in:**
```
assets/
└── courses/
    └── your-course-slug/
        ├── slides/
        ├── labs/
        ├── videos/ (links only)
        └── resources/
```

**Supported Formats:**
- **Videos**: YouTube, Vimeo links (preferred) or self-hosted
- **Documents**: PDF, Markdown
- **Code**: GitHub repositories
- **Labs**: Docker containers, VMs (provide setup instructions)

## 🔧 Development Setup

### Prerequisites

- Ruby 3.0+
- Bundler
- Git

### Local Setup

```bash
# Clone repository
git clone https://github.com/OWASP-BLT/BLT-University.git
cd BLT-University

# Install dependencies
bundle install

# Run locally
bundle exec jekyll serve --livereload

# Visit http://localhost:4000/BLT-University/
```

### Making Changes

```bash
# Create a branch
git checkout -b feature/your-feature

# Make changes and test locally
bundle exec jekyll serve

# Commit changes
git add .
git commit -m "Description of changes"

# Push to your fork
git push origin feature/your-feature

# Open pull request on GitHub
```

## ✅ Pull Request Guidelines

### Before Submitting

- [ ] Test changes locally
- [ ] Run Jekyll build without errors: `bundle exec jekyll build`
- [ ] Check for broken links
- [ ] Verify responsive design
- [ ] Spell-check content
- [ ] Follow existing code style
- [ ] Update documentation if needed

### PR Description

Provide:
- Clear description of changes
- Motivation and context
- Related issues (use "Fixes #123")
- Screenshots for UI changes
- Testing performed

### Review Process

1. **Automated Checks**: GitHub Actions will run tests
2. **Peer Review**: Community members review your PR
3. **Revisions**: Address feedback and make changes
4. **Approval**: Maintainers approve and merge
5. **Deployment**: Changes go live automatically

## 🎨 Style Guide

### Markdown

```markdown
# H1 - Course Title
## H2 - Major Section
### H3 - Subsection

**Bold** for emphasis
*Italic* for terms

- Bullet lists
1. Numbered lists

[Link text](URL)

`inline code`

```python
# Code block
print("Hello, Security!")
```

> Blockquote for important notes
```

### Code Examples

- Include comments
- Use syntax highlighting
- Provide context
- Show best practices
- Explain security implications

### Images

- Place in `assets/images/`
- Use descriptive filenames
- Optimize file size
- Add alt text
- Credit sources

**Course Images:**
- Add a header image to your course by including an `image` field in the course front matter
- Place course images in `assets/images/courses/`
- Recommended image dimensions: 800x400px
- Supported formats: SVG (preferred for graphics), PNG, JPG
- The image will appear on both the course listing page and the course detail page
- Example: `image: /assets/images/courses/web-security.svg`

## 🔒 Security Guidelines

### Content Security

- **Never** include real credentials or API keys
- Use sanitized examples and dummy data
- Warn about dangerous operations
- Provide safe testing environments
- Explain legal and ethical boundaries

### Vulnerability Disclosure

If you find security issues:
1. **Do NOT** open a public issue
2. Email security@bltuniversity.org
3. Provide details and POC
4. Wait for response before disclosure

## 📋 Code of Conduct

### Our Standards

- **Be respectful**: Treat everyone with respect
- **Be inclusive**: Welcome all backgrounds and skill levels
- **Be collaborative**: Work together constructively
- **Be professional**: Maintain professionalism
- **Be ethical**: Use knowledge responsibly

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or inflammatory comments
- Sharing others' private information
- Encouraging unethical hacking
- Disruptive behavior

### Enforcement

Violations will result in:
1. Warning
2. Temporary ban
3. Permanent ban (severe cases)

Report issues to conduct@bltuniversity.org

## 📜 Licensing

By contributing, you agree:

- Your contributions will be licensed under AGPL-3.0
- You have rights to contribute the content
- Your contributions are original or properly attributed
- You understand the license implications

## 🎓 Instructor Benefits

As a BLT University instructor, you get:

- **Recognition**: Profile on our website
- **Portfolio**: Showcase your teaching
- **Community**: Connect with security professionals
- **Impact**: Help thousands learn security
- **Growth**: Improve your teaching skills

## 📞 Getting Help

Need assistance?

- **Questions**: [GitHub Discussions](https://github.com/OWASP-BLT/BLT-University/discussions)
- **Bugs**: [Issue Tracker](https://github.com/OWASP-BLT/BLT-University/issues)
- **Chat**: Join our community chat
- **Email**: contribute@bltuniversity.org

## 🙏 Thank You!

Every contribution, no matter how small, helps make cybersecurity education accessible to everyone. Thank you for being part of our community!

---

**Ready to contribute?** Pick an issue, submit a course proposal, or improve existing content. We can't wait to see what you create!
