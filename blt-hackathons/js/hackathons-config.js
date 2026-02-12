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
            slug: "blt-2024",
            
            // Basic Information
            name: "BLT Hackathon 2024",
            description: `
                Welcome to the BLT Hackathon 2024! This is an exciting opportunity to contribute to open source projects
                and collaborate with other developers. Join us in making great software!
            `,
            
            // Optional rules section
            rules: `
                1. All pull requests must be submitted during the hackathon period
                2. PRs must be merged to count towards the leaderboard
                3. Only pull requests to the listed repositories will count
                4. Be respectful and follow each project's contribution guidelines
                5. Have fun and learn something new!
            `,
            
            // Hackathon Timeline (ISO 8601 format)
            startTime: "2025-11-01T00:00:00Z",
            endTime: "2026-05-31T23:59:59Z",
            
            // GitHub Configuration
            github: {
                // Your GitHub personal access token (optional, but recommended to avoid rate limits)
                token: "",
                
                // List of repositories to track (format: "owner/repo")
                repositories: [
                    "OWASP-BLT/BLT",
                    "OWASP-BLT/BLT-Flutter",
                    "OWASP-BLT/BLT-Bacon",
                    "OWASP-BLT/BLT-Action",
                    "OWASP-BLT/BLT-Extension"
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
            }
        },
        {
            slug: "gsoc-warmup",
            name: "GSoC Warmup",
            description: `
                Welcome to the GSoC Warmup hackathon! This is a preparation event for Google Summer of Code,
                designed to help contributors get familiar with the BLT organization and its projects.
                All repositories in the BLT organization count towards this hackathon!
            `,
            rules: `
                1. All pull requests must be submitted during the hackathon period (Nov 01, 2025 - May 09, 2026)
                2. PRs must be merged to count towards the leaderboard
                3. All repositories in the BLT organization are eligible
                4. Be respectful and follow each project's contribution guidelines
                5. Have fun and learn something new!
            `,
            startTime: "2025-11-01T00:00:00Z",
            endTime: "2026-05-09T23:59:59Z",
            github: {
                token: "",
                // Organization field - all repos in this org will be tracked
                organization: "OWASP-BLT",
                // Can still specify additional repositories if needed
                repositories: []
            },
            prizes: [],
            sponsors: [],
            display: {
                showRepoStats: true,
                maxLeaderboardEntries: 10,
                showPRsInLeaderboard: true
            }
        },
        {
            slug: "example-hackathon",
            name: "Example Hackathon",
            description: "This is an example hackathon to demonstrate the multi-hackathon feature.",
            rules: "1. Have fun!\n2. Be respectful\n3. Learn something new",
            startTime: "2026-01-01T00:00:00Z",
            endTime: "2026-01-31T23:59:59Z",
            github: {
                token: "",
                repositories: [
                    "OWASP-BLT/BLT"
                ]
            },
            prizes: [],
            sponsors: [],
            display: {
                showRepoStats: true,
                maxLeaderboardEntries: 10,
                showPRsInLeaderboard: true
            }
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
