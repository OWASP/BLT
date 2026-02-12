# Quick Start Guide

Welcome to BLT University! This guide will help you get started whether you're a student or instructor.

## For Students

### 1. Browse Courses

Visit the [Course Catalog](https://owasp-blt.github.io/BLT-University/courses/) to explore available courses.

### 2. Prerequisites Check

Each course lists prerequisites. Make sure you meet them before enrolling.

### 3. Enroll

1. Go to the [Enrollment Page](https://owasp-blt.github.io/BLT-University/enroll/)
2. Click "Submit Enrollment Request"
3. Fill out the GitHub issue form
4. Wait for approval (2-3 business days)

### 4. Start Learning

Once approved:
- Access course materials on the course page
- Join course discussions
- Complete labs and assignments
- Submit work via GitHub

## For Instructors

### 1. Review Guidelines

Read the [Contributing Guide](CONTRIBUTING.md) to understand our requirements.

### 2. Submit Proposal

1. Use the [course submission template](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-submission.yml)
2. Provide detailed course information
3. Wait for curriculum team review

### 3. Create Content

Once approved:

```bash
# Fork the repository
git clone https://github.com/YOUR-USERNAME/BLT-University.git
cd BLT-University

# Create instructor profile
cat > _instructors/your-name.md << 'EOF'
---
layout: instructor
title: Your Name
expertise: Your Expertise
github: yourusername
---

Your bio here...
EOF

# Create course
cat > _courses/your-course.md << 'EOF'
---
layout: course
title: Your Course Title
category: Course Category
level: Beginner/Intermediate/Advanced
duration: X weeks
instructor: Your Name
description: Course description

syllabus:
  - title: Module 1
    description: Module description
    topics:
      - Topic 1
      - Topic 2
---

# Course Content

Your course content in Markdown...
EOF

# Test locally
bundle install
bundle exec jekyll serve

# Submit PR
git add .
git commit -m "Add new course: Your Course Title"
git push origin main
# Open pull request on GitHub
```

### 4. Maintain Course

- Update content as needed via PRs
- Respond to student questions in discussions
- Incorporate feedback

## Local Development

### Setup

```bash
# Clone repository
git clone https://github.com/OWASP-BLT/BLT-University.git
cd BLT-University

# Install Ruby dependencies
bundle install

# Run Jekyll locally
bundle exec jekyll serve

# Visit http://localhost:4000/BLT-University/
```

### Make Changes

```bash
# Create a branch
git checkout -b feature/your-change

# Make changes to files
# ...

# Test locally
bundle exec jekyll serve

# Commit and push
git add .
git commit -m "Description of changes"
git push origin feature/your-change

# Open pull request
```

## Course Structure

### Minimal Course File

```yaml
---
layout: course
title: Your Course Title
category: One of the defined categories
level: Beginner | Intermediate | Advanced
duration: X weeks
instructor: Instructor Name
description: Brief description
---

# Course Content

Your course content here using Markdown...
```

### Full Course File

```yaml
---
layout: course
title: Your Course Title
category: Security Category
level: Beginner | Intermediate | Advanced
duration: X weeks
instructor: Instructor Name
featured: true  # Show on homepage
prerequisites: List of prerequisites
description: Course description

resources:
  - title: Resource Name
    url: https://resource-url
    type: video | pdf | link
    
schedule:
  - date: Week 1
    topic: What's covered
    
syllabus:
  - title: Module Title
    description: Module description
    topics:
      - Topic 1
      - Topic 2
---

# Detailed Course Content

Write your full course content here...
```

## Content Guidelines

### Videos

```yaml
resources:
  - title: Introduction Video
    url: https://www.youtube.com/watch?v=VIDEO_ID
    type: video
```

### PDFs

```yaml
resources:
  - title: Course Slides
    url: /assets/courses/your-course/slides.pdf
    type: pdf
```

Place PDF files in: `assets/courses/your-course-name/`

### External Links

```yaml
resources:
  - title: External Resource
    url: https://example.com
    type: link
```

## Getting Help

- **Technical Issues**: [Open an issue](https://github.com/OWASP-BLT/BLT-University/issues)
- **Questions**: [Start a discussion](https://github.com/OWASP-BLT/BLT-University/discussions)
- **Course Content**: Contact the instructor via their profile
- **General**: Check the [README](README.md) and [Contributing Guide](CONTRIBUTING.md)

## Tips

### For Students

- Join early - courses fill up fast!
- Participate in discussions
- Complete assignments on time
- Ask questions when stuck
- Help other students when you can

### For Instructors

- Start simple - you can always add more later
- Use real-world examples
- Include hands-on labs
- Be responsive to student questions
- Keep content updated

## Resources

- **Website**: https://owasp-blt.github.io/BLT-University/
- **GitHub**: https://github.com/OWASP-BLT/BLT-University
- **Jekyll Docs**: https://jekyllrb.com/docs/
- **Markdown Guide**: https://www.markdownguide.org/

---

Ready to get started? Choose your path:

- **Students**: [Browse Courses](https://owasp-blt.github.io/BLT-University/courses/) → [Enroll](https://owasp-blt.github.io/BLT-University/enroll/)
- **Instructors**: [Read Contributing Guide](CONTRIBUTING.md) → [Submit Course](https://github.com/OWASP-BLT/BLT-University/issues/new?template=course-submission.yml)

Welcome to BLT University! 🎓
