/**
 * Hackathon Configuration
 * 
 * Edit this file to customize your hackathon settings
 */

const HACKATHON_CONFIG = {
    // Basic Information
    name: "My Awesome Hackathon",
    description: `
        Welcome to our hackathon! This is an exciting opportunity to contribute to open source projects,
        collaborate with other developers, and win amazing prizes. Join us in making great software!
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
    startTime: "2025-01-01T00:00:00Z",
    endTime: "2025-01-31T23:59:59Z",
    
    // GitHub Configuration
    github: {
        // Your GitHub personal access token (optional, but recommended to avoid rate limits)
        // Create one at: https://github.com/settings/tokens
        // Only needs 'public_repo' scope for public repositories
        token: "", // Leave empty if you don't want to use a token
        
        // List of repositories to track
        // Format: "owner/repo"
        repositories: [
            "OWASP-BLT/BLT",
            "OWASP-BLT/BLT-Flutter",
            "OWASP-BLT/BLT-Action"
        ]
    },
    
    // Prizes Configuration
    prizes: [
        {
            position: 1,
            title: "First Place",
            description: "Amazing prize for the top contributor!",
            value: "500" // Optional: prize value in USD
        },
        {
            position: 2,
            title: "Second Place",
            description: "Great prize for the runner-up!",
            value: "300"
        },
        {
            position: 3,
            title: "Third Place",
            description: "Excellent prize for third place!",
            value: "200"
        },
        {
            position: 4,
            title: "Best First-Time Contributor",
            description: "Special prize for newcomers to open source!",
            value: "100"
        }
    ],
    
    // Sponsors Configuration (optional)
    sponsors: [
        // Example sponsor entry (uncomment and fill in):
        // {
        //     name: "Company Name",
        //     level: "gold", // platinum, gold, silver, bronze, partner
        //     logo: "images/sponsor-logo.png", // Path to logo image
        //     website: "https://example.com"
        // }
    ],
    
    // Additional sponsor information
    sponsorNote: "Interested in sponsoring? Contact us for more information!",
    sponsorLink: "mailto:sponsor@example.com",
    
    // Display Options
    display: {
        // Show repository statistics
        showRepoStats: true,
        
        // Maximum number of leaderboard entries to display
        maxLeaderboardEntries: 10,
        
        // Show participant pull requests in leaderboard
        showPRsInLeaderboard: true
    }
};
