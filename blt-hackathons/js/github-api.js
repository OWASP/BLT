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
        const perPage = 100;
        const maxPages = 20;

        while (page <= maxPages) {
            const url = `${this.baseURL}/repos/${owner}/${repo}/issues?state=all&sort=updated&direction=desc&per_page=${perPage}&page=${page}`;

            try {
                const issues = await this.makeRequest(url);

                if (!issues || issues.length === 0) {
                    break;
                }

                // Filter issues by date range and exclude pull requests
                for (const issue of issues) {
                    // Skip pull requests (they have a pull_request property)
                    if (issue.pull_request) {
                        continue;
                    }

                    const createdAt = new Date(issue.created_at);
                    const closedAt = issue.closed_at ? new Date(issue.closed_at) : null;

                    // Include if created or closed during hackathon
                    const relevantByCreation = createdAt >= startDate && createdAt <= endDate;
                    const relevantByClosure = closedAt && closedAt >= startDate && closedAt <= endDate;

                    if (relevantByCreation || relevantByClosure) {
                        allIssues.push({
                            ...issue,
                            repository: `${owner}/${repo}`
                        });
                    }

                    // If issues are too old, stop fetching
                    if (createdAt < startDate && (!closedAt || closedAt < startDate)) {
                        page = maxPages + 1; // Break outer loop
                        break;
                    }
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
        const perPage = 100;
        const maxPages = 20; // Increased to allow more PRs to be fetched

        while (page <= maxPages) {
            const url = `${this.baseURL}/repos/${owner}/${repo}/pulls?state=all&sort=updated&direction=desc&per_page=${perPage}&page=${page}`;

            try {
                const prs = await this.makeRequest(url);

                if (!prs || prs.length === 0) {
                    break;
                }

                // Filter PRs by date range - only include PRs merged during hackathon
                for (const pr of prs) {
                    const createdAt = new Date(pr.created_at);
                    const mergedAt = pr.merged_at ? new Date(pr.merged_at) : null;

                    // Only include PRs that were merged during the hackathon timeframe
                    if (mergedAt && mergedAt >= startDate && mergedAt <= endDate) {
                        allPRs.push({
                            ...pr,
                            repository: `${owner}/${repo}`
                        });
                    }

                    // If PRs are too old, stop fetching
                    if (createdAt < startDate && (!mergedAt || mergedAt < startDate)) {
                        page = maxPages + 1; // Break outer loop
                        break;
                    }
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
     * Process PRs and generate statistics
     */
    processPRData(prs, startDate, endDate) {
        const stats = {
            totalPRs: 0,
            mergedPRs: 0,
            participants: new Map(),
            dailyActivity: {},
            repoStats: {}
        };

        // Initialize daily activity for date range
        const currentDate = new Date(startDate);
        while (currentDate <= endDate) {
            const dateStr = currentDate.toISOString().split('T')[0];
            stats.dailyActivity[dateStr] = { total: 0, merged: 0 };
            currentDate.setDate(currentDate.getDate() + 1);
        }

        // Process each PR
        prs.forEach(pr => {
            // Only count PRs that were merged during the hackathon timeframe
            const mergedAt = pr.merged_at ? new Date(pr.merged_at) : null;
            if (!mergedAt || mergedAt < startDate || mergedAt > endDate) {
                return; // Skip PRs not merged in timeframe
            }

            stats.totalPRs++;
            stats.mergedPRs++; // All PRs here are merged due to filtering above

            // Track by user - filter out bots and Copilot
            const username = pr.user.login;
            const isBot = username.includes('[bot]') || username.toLowerCase().includes('bot');
            const isCopilot = username.toLowerCase().includes('copilot') ||
                pr.title.toLowerCase().includes('pr merged by copilot') ||
                pr.title.toLowerCase().includes('copilot');

            if (!isBot && !isCopilot) {
                if (!stats.participants.has(username)) {
                    stats.participants.set(username, {
                        username: username,
                        avatar: pr.user.avatar_url,
                        url: pr.user.html_url,
                        prs: [],
                        mergedCount: 0,
                        reviews: [],
                        reviewCount: 0,
                        is_contributor: false
                    });
                }

                const participant = stats.participants.get(username);
                participant.prs.push(pr);
                participant.mergedCount++;
            }

            // Track daily activity based on merge date
            const mergedDate = new Date(pr.merged_at).toISOString().split('T')[0];
            if (stats.dailyActivity[mergedDate]) {
                stats.dailyActivity[mergedDate].total++;
                stats.dailyActivity[mergedDate].merged++; // All are merged
            }

            // Track repo statistics
            const repo = pr.repository;
            if (!stats.repoStats[repo]) {
                stats.repoStats[repo] = { total: 0, merged: 0, issues: 0, closedIssues: 0 };
            }
            stats.repoStats[repo].total++;
            stats.repoStats[repo].merged++; // All PRs here are merged
        });

        return stats;
    }

    /**
     * Process review data and integrate with participant stats
     */
    processReviewData(reviews, participants) {
        reviews.forEach(review => {
            const username = review.user.login;
            const isBot = username.includes('[bot]') || username.toLowerCase().includes('bot');
            const isCopilot = username.toLowerCase().includes('copilot');

            if (!isBot && !isCopilot && review.state !== 'DISMISSED') {
                if (!participants.has(username)) {
                    participants.set(username, {
                        username: username,
                        avatar: review.user.avatar_url,
                        url: review.user.html_url,
                        prs: [],
                        mergedCount: 0,
                        reviews: [],
                        reviewCount: 0,
                        is_contributor: true
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
     * Generate leaderboard from participants
     */
    generateLeaderboard(participants, limit = 10) {
        return Array.from(participants.values())
            .filter(p => p.mergedCount > 0) // Only show participants with merged PRs
            .sort((a, b) => b.mergedCount - a.mergedCount)
            .slice(0, limit);
    }

    /**
     * Generate review leaderboard from participants
     */
    generateReviewLeaderboard(participants, limit = 10) {
        return Array.from(participants.values())
            .filter(p => p.reviewCount > 0) // Only show participants with reviews
            .sort((a, b) => b.reviewCount - a.reviewCount)
            .slice(0, limit);
    }
}
