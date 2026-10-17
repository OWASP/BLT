# Images Directory

Place your hackathon banner images, sponsor logos, and other graphics in this directory.

## Current Hackathon Banners

The following banner images are referenced in the hackathon configuration but need to be added:

- `gsoc-2026-warmup-banner.png` - Banner for GSOC 2026 Warmup hackathon
- `may-2025-hackathon-banner.png` - Banner for May Hackathon $100 prize

You can obtain these images from https://owaspblt.org/hackathons/ or create custom banners for each hackathon.

## Recommended Sizes

- **Banner Image**: 1200x400px (3:1 ratio)
- **Sponsor Logos**: 200x200px (square, transparent background recommended)

## Example Usage

```javascript
// In hackathons-config.js
{
    slug: "my-hackathon",
    name: "My Hackathon",
    // ... other config
    bannerImage: "images/my-hackathon-banner.png"
}
```

The banner will be displayed:
- On the hackathon dashboard page as a background image
- On the index page in the hackathon card

## Note

If banner images are not available, the system will fall back to a gradient background.
