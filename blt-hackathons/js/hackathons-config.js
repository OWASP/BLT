/**
 * Multiple Hackathons Configuration
 * 
 * This file contains configuration for multiple hackathons.
 * Each hackathon has a unique slug used in the URL.
 */

const HACKATHONS_CONFIG = {
    // List of all hackathons
    hackathons: [
        {
            // Unique identifier for URL (no spaces, lowercase recommended)
            slug: "gsoc-2026-warmup",
            
            // Basic Information
            name: "GSOC 2026 Warmup",
            description: `
                Welcome to the GSoC 2026 Warmup hackathon! This is a preparation event for Google Summer of Code,
                designed to help contributors get familiar with the BLT organization and its projects.
                All repositories in the BLT organization count towards this hackathon!
            `,
            
            // Optional rules section
            rules: `
                1. All pull requests must be submitted during the hackathon period (Nov 01, 2025 - May 09, 2026)
                2. PRs must be merged to count towards the leaderboard
                3. All repositories in the BLT organization are eligible
                4. Be respectful and follow each project's contribution guidelines
                5. Have fun and learn something new!
            `,
            
            // Hackathon Timeline (ISO 8601 format)
            startTime: "2025-11-01T00:00:00Z",
            endTime: "2026-05-09T23:59:59Z",
            
            // GitHub Configuration
            github: {
                // Your GitHub personal access token (optional, but recommended to avoid rate limits)
                token: "",
                
                // Organization field - all repos in this org will be tracked
                organization: "OWASP-BLT",
                // Fallback repositories in case organization fetch fails
                repositories: [
                    "OWASP-BLT/BLT",
                    "OWASP-BLT/BLT-Extension",
                    "OWASP-BLT/BLT-Bacon",
                    "OWASP-BLT/BLT-Action",
                    "OWASP-BLT/BLT-Flutter",
                    "OWASP-BLT/BLT-Lettuce",
                    "OWASP-BLT/BLT-Raven"
                ]
            },
            
            // Prizes Configuration
            prizes: [],
            
            // Sponsors Configuration (optional)
            sponsors: [],
            
            // Display Options
            display: {
                showRepoStats: true,
                maxLeaderboardEntries: 10,
                showPRsInLeaderboard: true
            },
            
            // Banner image (optional)
            bannerImage: "images/gsoc-2026-warmup-banner.png"
        },
        {
            slug: "may-2025-hackathon",
            name: "May Hackathon $100 prize",
            description: `
                Welcome to the May 2025 Hackathon! This is an exciting opportunity to contribute to OWASP BLT
                and win prizes. The top contributor with the most merged pull requests will receive a $100 prize!
            `,
            rules: `
                1. All pull requests must be submitted during the hackathon period (May 11, 2025 - June 1, 2025)
                2. PRs must be merged to count towards the leaderboard
                3. All repositories in the BLT organization are eligible
                4. Be respectful and follow each project's contribution guidelines
                5. Have fun and learn something new!
            `,
            startTime: "2025-05-11T00:00:00Z",
            endTime: "2025-06-01T23:59:59Z",
            github: {
                token: "",
                // Organization field - all repos in this org will be tracked
                organization: "OWASP-BLT",
                // Fallback repositories in case organization fetch fails
                repositories: [
                    "OWASP-BLT/BLT",
                    "OWASP-BLT/BLT-Extension",
                    "OWASP-BLT/BLT-Bacon",
                    "OWASP-BLT/BLT-Action",
                    "OWASP-BLT/BLT-Flutter",
                    "OWASP-BLT/BLT-Lettuce",
                    "OWASP-BLT/BLT-Raven"
                ]
            },
            prizes: [
                {
                    position: 1,
                    title: "First Place",
                    description: "Most merged pull requests",
                    value: "$100"
                }
            ],
            sponsors: [],
            display: {
                showRepoStats: true,
                maxLeaderboardEntries: 10,
                showPRsInLeaderboard: true
            },
            
            // Banner image (optional)
            bannerImage: "images/may-2025-hackathon-banner.png"
        }
    ],
    
    // Global settings
    global: {
        siteName: "BLT Hackathons",
        siteDescription: "Open source hackathon platform",
        organizationName: "OWASP BLT",
        organizationUrl: "https://github.com/OWASP-BLT"
    }
};

/**
 * Helper function to get hackathon by slug
 */
function getHackathonBySlug(slug) {
    return HACKATHONS_CONFIG.hackathons.find(h => h.slug === slug);
}

/**
 * Helper function to get all hackathons
 */
function getAllHackathons() {
    return HACKATHONS_CONFIG.hackathons;
}
