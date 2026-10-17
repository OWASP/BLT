# Course Images

This directory contains header images for courses displayed on the BLT University website.

## Image Guidelines

### Dimensions
- **Recommended size**: 800x400 pixels (2:1 aspect ratio)
- **Minimum size**: 600x300 pixels
- **Maximum file size**: 500 KB (smaller is better for page load times)

### Format
- **SVG**: Preferred for graphics and illustrations (scalable, small file size)
- **PNG**: Good for screenshots or images with transparency
- **JPG**: Good for photographs

### Naming Convention
Use the course slug as the filename:
- `web-security-intro.svg`
- `advanced-pentesting.svg`
- `crypto-for-devs.svg`

### Content
- Keep designs simple and professional
- Use colors that complement the BLT University theme
- Include visual elements that represent the course topic
- Ensure text is readable on all devices
- Avoid copyrighted images or logos without permission

## Adding an Image to Your Course

1. Create or design your course image (800x400px recommended)
2. Save it in this directory: `assets/images/courses/your-course-slug.svg`
3. Add the `image` field to your course front matter:

```yaml
---
layout: course
title: Your Course Title
# ... other fields ...
image: /assets/images/courses/your-course-slug.svg
---
```

4. Commit and push your changes

## Examples

This directory contains example SVG images you can use as templates:
- **web-security.svg** - Shield and lock design for security courses
- **advanced-pentesting.svg** - Target/crosshair design for penetration testing
- **crypto-for-devs.svg** - Key and encryption design for cryptography

Feel free to customize these or create your own!

## Tools

Recommended tools for creating course images:
- **Vector Graphics**: Figma, Inkscape, Adobe Illustrator
- **Photo Editing**: GIMP, Photoshop, Canva
- **SVG Optimization**: SVGO, SVGOMG

## Questions?

See the [Contributing Guide](../../../CONTRIBUTING.md) or open an issue if you need help!
