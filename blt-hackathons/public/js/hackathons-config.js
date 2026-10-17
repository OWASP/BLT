/**
 * Multiple Hackathons Configuration
 * 
 * This file contains configuration for multiple hackathons.
 * Each hackathon has a unique slug used in the URL.
 */

const OWASP_BLT_GITLAB_PROJECTS = [
    "owasp-blt/blt",
    "owasp-blt/blt-action",
    "owasp-blt/blt-api",
    "owasp-blt/blt-autopatch",
    "owasp-blt/blt-byte",
    "owasp-blt/blt-cve",
    "owasp-blt/blt-dash",
    "owasp-blt/blt-design",
    "owasp-blt/blt-design-contest",
    "owasp-blt/blt-docs",
    "owasp-blt/blt-enforcement",
    "owasp-blt/blt-extension",
    "owasp-blt/blt-flutter",
    "owasp-blt/blt-gitcaster",
    "owasp-blt/blt-gsoc",
    "owasp-blt/blt-hackathons",
    "owasp-blt/blt-hackerhouse",
    "owasp-blt/blt-ideas",
    "owasp-blt/blt-jobs",
    "owasp-blt/blt-ketchup",
    "owasp-blt/blt-leaf",
    "owasp-blt/blt-lettuce",
    "owasp-blt/blt-mayo",
    "owasp-blt/blt-mcp",
    "owasp-blt/blt-monitor",
    "owasp-blt/blt-netguardian",
    "owasp-blt/blt-netguardian-client",
    "owasp-blt/blt-newsletter",
    "owasp-blt/blt-next",
    "owasp-blt/blt-nexus",
    "owasp-blt/blt-ossh",
    "owasp-blt/blt-owasp-bumper",
    "owasp-blt/blt-owasp-metadata",
    "owasp-blt/blt-owasp-projects",
    "owasp-blt/blt-owasp-wich",
    "owasp-blt/blt-pages",
    "owasp-blt/blt-panini",
    "owasp-blt/blt-pool",
    "owasp-blt/blt-preflight",
    "owasp-blt/blt-profiles",
    "owasp-blt/blt-rewards",
    "owasp-blt/blt-safecloak",
    "owasp-blt/blt-sammich",
    "owasp-blt/blt-sizzle",
    "owasp-blt/blt-start",
    "owasp-blt/blt-timer-flutter",
    "owasp-blt/blt-timer-web",
    "owasp-blt/blt-toasty",
    "owasp-blt/blt-tomato",
    "owasp-blt/blt-university",
    "owasp-blt/blt-vanish",
    "owasp-blt/blt-vanish-flutter",
    "owasp-blt/blt-waypoint",
    "owasp-blt/blt-zero",
    "owasp-blt/coderabbit",
    "owasp-blt/dot_github",
    "owasp-blt/my-gsoc-tool",
];

const HACKATHONS_CONFIG = {
    // List of all hackathons
    hackathons: [
        {
            // Unique identifier for URL (no spaces, lowercase recommended)
            slug: "blt-mentor-warmup",

            // Basic Information
            name: "BLT Mentor Warmup Hackathon",
            description: `BLT Mentor Warmup - A dedicated hackathon for OWASP BLT mentors to lead by example and contribute to the organization's projects. To register, please add yourself to the mentor pool and then do a PR to this repo with your GitHub username — you can then submit PRs to all of the repos in the org.`,
            organizer: "OWASP BLT",

            // Optional rules section
            rules: `
                1. All pull requests must be submitted during the hackathon period (Oct 31, 2025 - Mar 30, 2026)
                2. PRs must be merged to count towards the leaderboard
                3. All repositories in the BLT organization are eligible
                4. Be respectful and follow each project's contribution guidelines
                5. Have fun and lead by example!
            `,

            // Hackathon Timeline (ISO 8601 format)
            startTime: "2025-10-31T00:00:00Z",
            endTime: "2026-03-30T18:00:00Z",

            // GitHub Configuration
            github: {
                token: "",

                // Organization field - all repos in this org will be tracked
                organization: "OWASP-BLT",
                // Fallback repositories in case organization fetch fails
                repositories: [
                    "OWASP-BLT/BLT",
                    "OWASP-BLT/BLT-Extension",
                    "OWASP-BLT/BLT-Rewards",
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
                maxLeaderboardEntries: Infinity,
                showPRsInLeaderboard: true,
                showReviewsInLeaderboard: true
            },

            // Optional: path to a YAML file listing allowed participants.
            // When set, only the listed GitHub usernames are counted as
            // contributors (merged PRs leaderboard) AND reviewers
            // (review leaderboard).
            participantsFile: "hackathon-participants/blt-mentor-warmup.yml",

            // Banner image (optional)
            bannerImage: "images/How-do-hackathons-work-1024x576.png"
        },
        {
            // Unique identifier for URL (no spaces, lowercase recommended)
            slug: "gsoc-2026-warmup",
            
            // Basic Information
            name: "GSOC 2026 Warmup",
            description: `GSOC 2026 Warmup - Preparation event for Google Summer of Code contributors in the OWASP BLT organization.`,
            organizer: "OWASP BLT",
            
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
                    "OWASP-BLT/BLT-Rewards",
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
                maxLeaderboardEntries: Infinity,
                showPRsInLeaderboard: true,
                showReviewsInLeaderboard: true
            },
            
            // Banner image (optional)
            bannerImage: "images/How-do-hackathons-work-1024x576.png"
        },
        {
            // Unique identifier for URL (no spaces, lowercase recommended)
            slug: "gsoc-2027-warmup",

            // Basic Information
            name: "GSOC 2027 Warmup",
            description: `GSOC 2027 Warmup - Preparation event for Google Summer of Code contributors in the OWASP BLT GitLab group.`,
            organizer: "OWASP BLT",

            // Optional rules section
            rules: `
                1. All merge requests must be submitted during the hackathon period (Nov 01, 2026 - May 09, 2027)
                2. Merge requests must be merged to count towards the leaderboard
                3. All projects in the OWASP BLT GitLab group are eligible
                4. Be respectful and follow each project's contribution guidelines
                5. Have fun and learn something new!
            `,

            // Hackathon Timeline (ISO 8601 format)
            startTime: "2026-11-01T00:00:00Z",
            endTime: "2027-05-09T23:59:59Z",

            // GitLab Configuration
            provider: "gitlab",
            gitlab: {
                token: "",
                url: "https://gitlab.com",
                group: "owasp-blt",
                projects: OWASP_BLT_GITLAB_PROJECTS
            },

            // Prizes Configuration
            prizes: [],

            // Sponsors Configuration (optional)
            sponsors: [],

            // Display Options
            display: {
                showRepoStats: true,
                maxLeaderboardEntries: Infinity,
                showPRsInLeaderboard: true,
                showReviewsInLeaderboard: true
            }
        },
        {
            slug: "may-2025-hackathon",
            name: "May Hackathon $100 prize",
            description: `This hackathon will focus on only issues with the $5 bounty on them. The prize is $100 to the person with the most merged PRs within the time period.`,
            organizer: "OWASP BLT",
            rules: `
                1. All pull requests must be submitted during the hackathon period (May 11, 2025 - June 1, 2025)
                2. PRs must be merged to count towards the leaderboard
                3. Only issues with the $5 bounty label are eligible
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
                    "OWASP-BLT/BLT-Rewards",
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
                maxLeaderboardEntries: Infinity,
                showPRsInLeaderboard: true,
                showReviewsInLeaderboard: true
            },
            
            // Banner image (optional)
            bannerImage: "images/97137d26-6b7a-44cc-b43e-24229ba60061.png",

            // Number of contributors (optional)
            contributors: 12
        },
        {
            slug: "summer-2025-hackathon",
            name: "OWASP BLT Summer 2025 hackathon $200 prize",
            description: `This leaderboard is for new PRs from Feb 28 to May 8, the prize will be paid by DonnieBLT by BCH (preferred) or Github Sponsors`,
            organizer: "OWASP BLT",
            rules: `
                1. All pull requests must be submitted during the hackathon period (Feb 28, 2025 - May 08, 2025)
                2. PRs must be merged to count towards the leaderboard
                3. All repositories in the BLT organization are eligible
                4. Be respectful and follow each project's contribution guidelines
                5. Prize paid by DonnieBLT via BCH (preferred) or Github Sponsors
            `,
            startTime: "2025-02-28T00:00:00Z",
            endTime: "2025-05-08T23:59:59Z",
            github: {
                token: "",
                // Organization field - all repos in this org will be tracked
                organization: "OWASP-BLT",
                // Fallback repositories in case organization fetch fails
                repositories: [
                    "OWASP-BLT/BLT",
                    "OWASP-BLT/BLT-Extension",
                    "OWASP-BLT/BLT-Rewards",
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
                    value: "$200"
                }
            ],
            sponsors: [],
            display: {
                showRepoStats: true,
                maxLeaderboardEntries: Infinity,
                showPRsInLeaderboard: true,
                showReviewsInLeaderboard: true
            },
            
            // Banner image (optional)
            bannerImage: "images/b43f3d7d-5626-4678-bf0f-a149d8938f84 (1).webp",

            // Number of contributors (optional)
            contributors: 15
        }
    ],
    
    // Global settings
    global: {
        siteName: "BLT Hackathons",
        siteDescription: "Open source hackathon platform",
        organizationName: "OWASP BLT",
        organizationUrl: "https://gitlab.com/owasp-blt"
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
