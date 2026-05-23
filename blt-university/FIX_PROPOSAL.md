To add the OWASP@Foundation social media links to the BLT University footer, you can modify the footer HTML code as follows:

```html
<!-- Add social media links to the footer -->
<div class="social-media-links">
  <a href="https://owasp.org/slack/invite" target="_blank" rel="noopener noreferrer">
    <i class="fa fa-slack" aria-hidden="true"></i>
    Slack (OWASP Invite)
  </a>
  <a href="https://www.facebook.com/OWASPFoundation" target="_blank" rel="noopener noreferrer">
    <i class="fa fa-facebook" aria-hidden="true"></i>
    Facebook
  </a>
  <a href="https://twitter.com/OWASP" target="_blank" rel="noopener noreferrer">
    <i class="fa fa-twitter" aria-hidden="true"></i>
    Twitter
  </a>
  <a href="https://www.linkedin.com/company/owasp-foundation" target="_blank" rel="noopener noreferrer">
    <i class="fa fa-linkedin" aria-hidden="true"></i>
    LinkedIn
  </a>
  <a href="https://www.youtube.com/owasp" target="_blank" rel="noopener noreferrer">
    <i class="fa fa-youtube" aria-hidden="true"></i>
    YouTube
  </a>
  <a href="https://infosec.exchange/@owasp" target="_blank" rel="noopener noreferrer">
    <i class="fa fa-mastodon" aria-hidden="true"></i>
    Mastodon (Infosec)
  </a>
</div>
```

You will also need to add the Font Awesome library to your project to use the social media icons. You can do this by adding the following line to your HTML header:

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" />
```

Alternatively, you can use a CDN or install Font Awesome locally.

**Commit Message:**
`Add OWASP@Foundation social media links to BLT University footer`

**Changes:**

* Added social media links to the footer
* Included Font Awesome library for social media icons

**Files Changed:**

* `footer.html` (or equivalent file)
* `index.html` (or equivalent file) to include Font Awesome library

Please note that you may need to adjust the file names and paths based on your project's structure.