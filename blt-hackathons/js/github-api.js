/**
 * GitHub API Integration
 * Handles all interactions with the GitHub API
 */

class GitHubAPI {
    constructor(token = null) {
        this.token = token;
        this.baseURL = 'https://api.github.com';
        this.cache = new Map();

        // Validate token format if provided
        if (this.token && !this.isValidToken(this.token)) {
            console.warn('GitHub token format may be invalid. Personal access tokens should start with "ghp_"');
        }
    }

    /**
     * Validate GitHub token format
     */
    isValidToken(token) {
        // Basic validation: tokens should start with 'ghp_' for personal access tokens
        // or 'github_pat_' for fine-grained tokens
        return token.startsWith('ghp_') || token.startsWith('github_pat_') || token.startsWith('gho_');
    }

    /**
     * Make a request to GitHub API
     */
    async makeRequest(url, useCache = true) {
        // Check cache first
        if (useCache && this.cache.has(url)) {
            const cached = this.cache.get(url);
            const age = Date.now() - cached.timestamp;
            // Cache for 5 minutes
            if (age < 5 * 60 * 1000) {
                return cached.data;
            }
        }

        const headers = {
            'Accept': 'application/vnd.github.v3+json'
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, { headers });

            if (!response.ok) {
                if (response.status === 403) {
                    console.warn('GitHub API rate limit may have been exceeded');
                }
                throw new Error(`GitHub API error: ${response.status}`);
            }

            const data = await response.json();

            // Cache the result
            this.cache.set(url, {
                data: data,
                timestamp: Date.now()
            });

            return data;
        } catch (error) {
            console.error('Error fetching from GitHub:', error);
            throw error;
        }
    }

    /**
     * Fetch all issues for a repository
     */
    async fetchIssues(owner, repo, startDate, endDate) {
        const allIssues = [];
        let page = 1;
        const perPage = 100; // GitHub max is 100
        const maxPages = 20;

        while (page <= maxPages) {
            // Sort by CREATED (not updated) to get chronological order
            const url = `${this.baseURL}/repos/${owner}/${repo}/issues?state=all&sort=created&direction=desc&per_page=${perPage}&page=${page}`;

            try {
                const issues = await this.makeRequest(url);
                if (!issues || issues.length === 0) {
                    console.log("No more issues to fetch");
                    break;
                }

                let foundOldIssue = false;
                for (const issue of issues) {
                    // Skip pull requests (GitHub API returns PRs as issues)
                    if (issue.pull_request) {
                        continue;
                    }

                    const createdAt = new Date(issue.created_at);
                    const closedAt = issue.closed_at ? new Date(issue.closed_at) : null;

                    // Check if issue is relevant by creation OR close date
                    const relevantByCreation = createdAt >= startDate && createdAt <= endDate;
                    const relevantByClosure = closedAt && closedAt >= startDate && closedAt <= endDate;

                    if (relevantByCreation || relevantByClosure) {
                        allIssues.push({
                            ...issue,
                            repository: `${owner}/${repo}`
                        });
                    }

                    // Early exit: If issue was created before startDate, we've gone too far back
                    // (since we're sorting by created date descending)
                    if (createdAt < startDate) {
                        foundOldIssue = true;
                        break;
                    }
                }

                if (foundOldIssue) {
                    break; // Exit while loop
                }

                page++;
            } catch (error) {
                console.error(`Error fetching issues for ${owner}/${repo}:`, error);
                break;
            }
        }
        return allIssues;
    }

    /**
     * Fetch all pull requests for a repository
     */
    async fetchPullRequests(owner, repo, startDate, endDate) {
        const allPRs = [];
        let page = 1;
        const perPage = 100; // max is 100 item per page
        const maxPages = 20;
        startDate = new Date(startDate);
        endDate = new Date(endDate);

        while (page <= maxPages) {
            // Sort by CREATED (not updated) to get chronological order
            const url = `${this.baseURL}/repos/${owner}/${repo}/pulls?state=all&sort=created&direction=desc&per_page=${perPage}&page=${page}`;

            try {
                const prs = await this.makeRequest(url);

                if (!prs || prs.length === 0) {
                    console.log("No more PRs to fetch");
                    break;
                }

                let foundOldPR = false;

                for (const pr of prs) {
                    const createdAt = new Date(pr.created_at);
                    const mergedAt = pr.merged_at ? new Date(pr.merged_at) : null;

                    // Check if PR is relevant by creation OR merge date
                    const relevantByCreation = createdAt >= startDate && createdAt <= endDate;
                    const relevantByMerge = mergedAt && mergedAt >= startDate && mergedAt <= endDate;

                    if (relevantByCreation || relevantByMerge) {
                        allPRs.push({
                            ...pr,
                            repository: `${owner}/${repo}`
                        });
                    }

                    // Early exit: If PR was created before startDate, we've gone too far back
                    // (since we're sorting by created date descending)
                    if (createdAt < startDate) {
                        console.log(`Found PR created before ${startDate.toISOString()}, stopping pagination`);
                        foundOldPR = true;
                        break;
                    }
                }

                if (foundOldPR) {
                    break; // Exit while loop
                }

                page++;
            } catch (error) {
                console.error(`Error fetching PRs for ${owner}/${repo}:`, error);
                break;
            }
        }
        return allPRs;
    }

    /**
     * Fetch repository information
     */
    async fetchRepository(owner, repo) {
        const url = `${this.baseURL}/repos/${owner}/${repo}`;
        return await this.makeRequest(url);
    }

    /**
     * Fetch user information
     */
    async fetchUser(username) {
        const url = `${this.baseURL}/users/${username}`;
        return await this.makeRequest(url);
    }

    /**
     * Fetch reviews for a specific pull request
     */
    async fetchReviews(owner, repo, prNumber) {
        const url = `${this.baseURL}/repos/${owner}/${repo}/pulls/${prNumber}/reviews`;
        try {
            return await this.makeRequest(url);
        } catch (error) {
            console.error(`Error fetching reviews for ${owner}/${repo}#${prNumber}:`, error);
            return [];
        }
    }

    /**
     * Fetch all reviews for multiple repositories within timeframe
     */
    async getAllReviews(repositories, startDate, endDate) {
        const allReviews = [];

        for (const repoPath of repositories) {
            const [owner, repo] = repoPath.split('/');

            const prs = await this.fetchPullRequests(owner, repo, startDate, endDate);

            for (const pr of prs) {
                const reviews = await this.fetchReviews(owner, repo, pr.number);

                for (const review of reviews) {
                    const submittedAt = new Date(review.submitted_at);

                    if (submittedAt >= startDate && submittedAt <= endDate) {
                        allReviews.push({
                            ...review,
                            repository: `${owner}/${repo}`,
                            pull_request_title: pr.title,
                            pull_request_url: pr.html_url
                        });
                    }
                }
            }
        }

        return allReviews;
    }

    /**
     * Get all issues for multiple repositories
     */
    async getAllIssues(repositories, startDate, endDate) {
        const promises = repositories.map(repoPath => {
            const [owner, repo] = repoPath.split('/');
            return this.fetchIssues(owner, repo, startDate, endDate);
        });

        const results = await Promise.allSettled(promises);

        // Combine all successful results
        const allIssues = [];
        results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
                allIssues.push(...result.value);
            } else {
                console.error(`Failed to fetch issues for ${repositories[index]}:`, result.reason);
            }
        });

        return allIssues;
    }

    /**
     * Get all pull requests for multiple repositories
     */
    async getAllPullRequests(repositories, startDate, endDate) {
        const promises = repositories.map(repoPath => {
            const [owner, repo] = repoPath.split('/');
            return this.fetchPullRequests(owner, repo, startDate, endDate);
        });

        const results = await Promise.allSettled(promises);

        console.log("results", results);

        // Combine all successful results
        const allPRs = [];
        results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
                allPRs.push(...result.value);
            } else {
                console.error(`Failed to fetch PRs for ${repositories[index]}:`, result.reason);
            }
        });

        return allPRs;
    }

    /**
     * Get repository information for multiple repositories
     */
    async getAllRepositories(repositories) {
        const promises = repositories.map(repoPath => {
            const [owner, repo] = repoPath.split('/');
            return this.fetchRepository(owner, repo);
        });

        const results = await Promise.allSettled(promises);

        return results
            .filter(r => r.status === 'fulfilled')
            .map(r => r.value);
    }

    /**
     * Process issues and generate statistics
     * 
     * Note: This method modifies the repoStats parameter by adding issue counts
     * to existing repository statistics. This is intentional to combine PR and
     * issue data in a single stats object.
     * 
     * @param {Array} issues - Array of GitHub issues
     * @param {Object} repoStats - Repository statistics object (will be modified)
     * @returns {Object} Summary with totalIssues and closedIssues counts
     */
    processIssueData(issues, repoStats) {
        issues.forEach(issue => {
            const repo = issue.repository;
            if (!repoStats[repo]) {
                repoStats[repo] = { total: 0, merged: 0, issues: 0, closedIssues: 0 };
            }
            repoStats[repo].issues++;
            if (issue.state === 'closed') {
                repoStats[repo].closedIssues++;
            }
        });

        return {
            totalIssues: issues.length,
            closedIssues: issues.filter(i => i.state === 'closed').length
        };
    }

    /**
     * Process PRs and generate statistics - matching Python implementation logic
     */
    processPRData(prs, startDate, endDate) {
        const stats = {
            totalPRs: prs.length,
            mergedPRs: 0,
            participants: new Map(),
            dailyActivity: {},
            repoStats: {}
        };
        startDate = new Date(startDate);
        endDate = new Date(endDate);

        // Group PRs by user
        const leaderboard = {};

        // Process each PR
        prs.forEach(pr => {
            const isMerged = pr.merged_at !== null;
            if (isMerged) {
                stats.mergedPRs++;
            }

            // Track by user - filter out bots and Copilot
            const username = pr.user.login;
            const isBot = username.includes('[bot]') || username.toLowerCase().includes('bot');
            const isCopilot = username.toLowerCase().includes('copilot') ||
                pr.title.toLowerCase().includes('pr merged by copilot') ||
                pr.title.toLowerCase().includes('copilot');

            if (!isBot && !isCopilot) {
                // Group by GitHub username
                const contributorId = `contributor_${username}`;

                if (leaderboard[contributorId]) {
                    leaderboard[contributorId].count += 1; // Count ALL PRs
                    leaderboard[contributorId].prs.push(pr);
                    if (isMerged) {
                        leaderboard[contributorId].mergedCount += 1;
                    }
                } else {
                    leaderboard[contributorId] = {
                        user: {
                            username: username,
                            email: "",
                            id: contributorId,
                        },
                        count: 1, // Count ALL PRs
                        prs: [pr],
                        is_contributor: true,
                        avatar: pr.user.avatar_url,
                        url: pr.user.html_url,
                        reviews: [],
                        reviewCount: 0,
                        mergedCount: isMerged ? 1 : 0
                    };
                }
            }

            // Track daily activity
            const createdDate = new Date(pr.created_at).toISOString().split('T')[0];
            const relevantByCreation = new Date(pr.created_at) >= startDate && new Date(pr.created_at) <= endDate;
            if (stats.dailyActivity[createdDate] && relevantByCreation) {
                stats.dailyActivity[createdDate].total++;
            }

            if (isMerged) {
                const mergedDate = new Date(pr.merged_at).toISOString().split('T')[0];
                if (stats.dailyActivity[mergedDate]) {
                    stats.dailyActivity[mergedDate].merged++;
                }
            }

            // Track repo statistics
            const repo = pr.repository;
            if (!stats.repoStats[repo]) {
                stats.repoStats[repo] = { total: 0, merged: 0, issues: 0, closedIssues: 0 };
            }
            stats.repoStats[repo].total++;
            if (isMerged) {
                stats.repoStats[repo].merged++;
            }
        });

        // Convert leaderboard object to Map for consistency with existing code
        Object.values(leaderboard).forEach(participant => {
            // Don't overwrite mergedCount - keep it separate from total count
            stats.participants.set(participant.user.username, participant);
        });

        return stats;
    }

    /**
     * Process review data and integrate with participant stats - matching Python logic
     */
    processReviewData(reviews, participants) {
        reviews.forEach(review => {
            const username = review.user.login;
            const isBot = username.includes('[bot]') || username.toLowerCase().includes('bot');
            const isCopilot = username.toLowerCase().includes('copilot');

            if (!isBot && !isCopilot && review.state !== 'DISMISSED') {
                // Use same contributor ID format as PR processing
                if (!participants.has(username)) {
                    participants.set(username, {
                        user: {
                            username: username,
                            email: "",
                            id: `contributor_${username}`,
                        },
                        count: 0,
                        prs: [],
                        is_contributor: true,
                        avatar: review.user.avatar_url,
                        url: review.user.html_url,
                        reviews: [],
                        reviewCount: 0,
                        mergedCount: 0
                    });
                }

                const participant = participants.get(username);
                participant.reviews.push({
                    ...review,
                    html_url: review.pull_request_url || review.html_url
                });
                participant.reviewCount++;
            }
        });
    }

    /**
     * Generate leaderboard from participants - matching Python return structure
     */
    generateLeaderboard(participants, limit = 10) {
        return Array.from(participants.values())
            .filter(p => p.mergedCount > 0) // Only show participants with merged PRs
            .sort((a, b) => b.mergedCount - a.mergedCount)
            .slice(0, limit)
            .map(p => ({
                user: p.user || {
                    username: p.username,
                    email: "",
                    id: p.user?.id || `contributor_${p.username}`
                },
                count: p.mergedCount,
                prs: p.prs,
                is_contributor: p.is_contributor,
                // Keep original structure for rendering
                username: p.user?.username || p.username,
                avatar: p.avatar,
                url: p.url,
                mergedCount: p.mergedCount
            }));
    }

    /**
     * Generate review leaderboard from participants - matching Python return structure
     */
    generateReviewLeaderboard(participants, limit = 10) {
        return Array.from(participants.values())
            .filter(p => p.reviewCount > 0) // Only show participants with reviews
            .sort((a, b) => b.reviewCount - a.reviewCount)
            .slice(0, limit)
            .map(p => ({
                user: p.user || {
                    username: p.username,
                    email: "",
                    id: p.user?.id || `contributor_${p.username}`
                },
                count: p.reviewCount,
                reviews: p.reviews,
                is_contributor: p.is_contributor,
                // Keep original structure for rendering
                username: p.user?.username || p.username,
                avatar: p.avatar,
                url: p.url,
                reviewCount: p.reviewCount
            }));
    }
}
