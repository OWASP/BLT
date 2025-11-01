/**
 * GitHub API Integration
 * Handles all interactions with the GitHub API
 */

class GitHubAPI {
    constructor(token = null) {
        this.token = token;
        this.baseURL = 'https://api.github.com';
        this.cache = new Map();
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

                // Filter PRs by date range
                for (const pr of prs) {
                    const createdAt = new Date(pr.created_at);
                    const mergedAt = pr.merged_at ? new Date(pr.merged_at) : null;
                    
                    // Include if created or merged during hackathon
                    const relevantByCreation = createdAt >= startDate && createdAt <= endDate;
                    const relevantByMerge = mergedAt && mergedAt >= startDate && mergedAt <= endDate;
                    
                    if (relevantByCreation || relevantByMerge) {
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
            stats.totalPRs++;
            
            const isMerged = pr.merged_at !== null;
            if (isMerged) {
                stats.mergedPRs++;
            }

            // Track by user
            const username = pr.user.login;
            const isBot = username.includes('[bot]') || username.toLowerCase().includes('bot');
            
            if (!isBot) {
                if (!stats.participants.has(username)) {
                    stats.participants.set(username, {
                        username: username,
                        avatar: pr.user.avatar_url,
                        url: pr.user.html_url,
                        prs: [],
                        mergedCount: 0
                    });
                }

                const participant = stats.participants.get(username);
                participant.prs.push(pr);
                if (isMerged) {
                    participant.mergedCount++;
                }
            }

            // Track daily activity
            const createdDate = new Date(pr.created_at).toISOString().split('T')[0];
            if (stats.dailyActivity[createdDate]) {
                stats.dailyActivity[createdDate].total++;
                if (isMerged) {
                    stats.dailyActivity[createdDate].merged++;
                }
            }

            // Track repo statistics
            const repo = pr.repository;
            if (!stats.repoStats[repo]) {
                stats.repoStats[repo] = { total: 0, merged: 0 };
            }
            stats.repoStats[repo].total++;
            if (isMerged) {
                stats.repoStats[repo].merged++;
            }
        });

        return stats;
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
}
