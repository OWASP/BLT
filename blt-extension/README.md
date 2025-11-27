# BLT Extension for Chrome

BLT is a Chrome extension that enables users to take screenshots or capture specific sections of webpages and quickly add them to the BLT website. This tool is perfect for users who need to save, annotate, or share parts of a webpage easily.

## Installation Instructions

### Quick Install (One-Line Command)

Run this command in your terminal to automatically download and install the BLT extension:

```bash
bash <(curl -sL https://raw.githubusercontent.com/OWASP-BLT/BLT-Extension/main/install.sh)
```

This script will:
- Download the latest BLT extension
- Detect your OS (Linux, macOS, or Windows)
- Find all Chrome/Chromium browser profiles
- Let you choose which profile to install to
- Guide you through the final setup steps

**Supported Browsers:** Google Chrome, Chromium, Brave, Microsoft Edge

### Manual Installation for Google Chrome

1. **Download the Extension**: Download the latest version of BLT from the [Releases](https://github.com/OWASP-BLT/BLT-Extension/releases) page on GitHub.

2. **Unzip the File**: After downloading, unzip the file to a directory on your computer.

3. **Load the Extension in Chrome**:
    - Open Google Chrome.
    - Navigate to `chrome://extensions/`.
    - Enable "Developer mode" by toggling the switch in the top right corner.
    - Click on "Load unpacked".
    - Browse to and select the unzipped BLT extension directory.

### Usage

Once installed, using BLT is straightforward:
- Navigate to the webpage you want to capture.
- Activate the BLT extension by clicking on the extension icon.
- Select the area of the webpage you want to capture or take a full-page screenshot.
- The captured content will be automatically uploaded to the BLT website, where you can further annotate, save, or share it.

### Support

Encounter any issues or have questions? Please file an issue on our GitHub [Issues](../issues) page.

## For Developers

### Creating a New Release

This repository uses GitHub Actions to automatically create releases that are ready to be installed in Chromium-based browsers.

To create a new release:

1. **Update the version** in `manifest.json` to the new version number (e.g., `1.5`)
2. **Commit and push** your changes to the main branch
3. **Create and push a tag** with the version number:
   ```bash
   git tag v1.5
   git push origin v1.5
   ```
4. The GitHub Action will automatically:
   - Package the extension files into a zip
   - Create a GitHub release with the zip file attached
   - Generate release notes

The release zip file will be available on the [Releases](https://github.com/OWASP-BLT/BLT-Extension/releases) page and can be downloaded and installed directly in Chromium.


https://www.github.com/OWASP/BLT  
https://www.github.com/OWASP/BLT-Flutter  
https://www.github.com/OWASP/BLT-Extension  
https://www.github.com/OWASP/BLT-Bacon  
https://www.github.com/OWASP/BLT-Action  


https://owasp.org/www-project-bug-logging-tool/
