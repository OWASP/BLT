/**
 * Main Application Logic
 * Initializes and manages the hackathon dashboard
 */

class HackathonDashboard {
    constructor(config) {
        this.config = config;
        this.api = new GitHubAPI(config.github.token);
        this.chart = null;
        // Store resolved repositories (set during initialization)
        // Contains the merged list of explicit repositories and organization repositories
        this.repositories = null;
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        this.showLoading();
        try {
            // Update basic info
            this.updateBasicInfo();

            // Fetch and process GitHub data
            const startDate = new Date(this.config.startTime);
            const endDate = new Date(this.config.endTime);

            // Resolve repositories (including organization repos if specified)
            try {
                this.repositories = await this.api.resolveRepositories(this.config.github);
                
                // Check if we have any repositories to work with
                if (!this.repositories || this.repositories.length === 0) {
                    throw new Error('No repositories could be resolved. Please check your configuration.');
                }
                
                console.log(`✅ Successfully resolved ${this.repositories.length} repositories`);
            } catch (repoError) {
                console.error('Failed to resolve repositories:', repoError);
                this.showError(`Unable to load repository list: ${repoError.message}. Please check your organization name or add explicit repositories to the configuration.`);
                return;
            }

            // Fetch all PRs and issues in parallel
            const [prs, issues] = await Promise.all([
                this.api.getAllPullRequests(
                    this.repositories,
                    startDate,
                    endDate
                ),
                this.api.getAllIssues(
                    this.repositories,
                    startDate,
                    endDate
                )
            ]);

            // Fetch reviews using the already-fetched PR list (avoids duplicate API calls)
            const reviews = await this.api.getAllReviews(prs, startDate, endDate);

            // Process PR data
            const stats = this.api.processPRData(prs, startDate, endDate);

            // Process review data
            this.api.processReviewData(reviews, stats.participants);

            // Process issue data
            const issueStats = this.api.processIssueData(issues, stats.repoStats);
            stats.totalIssues = issueStats.totalIssues;
            stats.closedIssues = issueStats.closedIssues;

            // Update UI
            this.updateStats(stats);
            this.renderLeaderboard(stats.participants);
            this.renderReviewLeaderBoard(stats.participants);
            
            // Render chart (optional - gracefully handle missing Chart.js)
            try {
                this.renderChart(stats.dailyActivity, prs);
            } catch (chartError) {
                console.warn('Failed to render chart (Chart.js may not be loaded):', chartError);
                // Hide the chart section if Chart.js is not available
                const chartCanvas = document.getElementById('prActivityChart');
                if (chartCanvas && chartCanvas.parentElement) {
                    chartCanvas.parentElement.parentElement.style.display = 'none';
                }
            }
            
            this.renderRepositories(stats.repoStats);
            this.renderSponsors();
            this.hideLoading();
            this.updateApiInfo();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError('Failed to load hackathon data. Please check your configuration and try again.');
        }
    }

    /**
     * Update basic hackathon information
     */
    updateBasicInfo() {
        // Update title
        document.getElementById('hackathon-title').textContent = this.config.name;
        document.getElementById('nav-title').textContent = this.config.name;
        document.getElementById('hackathon-name').textContent = this.config.name;

        // Update banner image if provided
        const bannerSection = document.getElementById('banner-section');
        if (this.config.bannerImage) {
            bannerSection.style.backgroundImage = `url('${this.config.bannerImage}')`;
            bannerSection.style.backgroundSize = 'cover';
            bannerSection.style.backgroundPosition = 'center';
        }

        // Update description
        document.getElementById('hackathon-description').innerHTML =
            `<p class="text-gray-700">${this.escapeHtml(this.config.description.trim())}</p>`;

        // Update rules if provided
        if (this.config.rules) {
            document.getElementById('rules-section').style.display = 'block';
            document.getElementById('hackathon-rules').innerHTML =
                `<p class="text-gray-700">${this.escapeHtml(this.config.rules.trim())}</p>`;
        }

        // Update dates and status
        const startDate = new Date(this.config.startTime);
        const endDate = new Date(this.config.endTime);
        const now = new Date();

        const dateFormat = { year: 'numeric', month: 'long', day: 'numeric' };
        const dateStr = `${startDate.toLocaleDateString('en-US', dateFormat)} - ${endDate.toLocaleDateString('en-US', dateFormat)}`;
        document.getElementById('hackathon-dates').textContent = dateStr;

        // Also update the standalone time-range bar at the top of the detail page
        const timeRangeDisplay = document.getElementById('time-range-display');
        if (timeRangeDisplay) {
            timeRangeDisplay.textContent = dateStr;
        }

        // Determine status
        let status, statusClass, timeRemaining;
        if (now < startDate) {
            status = 'Upcoming';
            statusClass = 'bg-blue-100 text-blue-800';
            const daysUntil = Math.ceil((startDate - now) / (1000 * 60 * 60 * 24));
            timeRemaining = `Starts in ${daysUntil} day${daysUntil !== 1 ? 's' : ''}`;
        } else if (now > endDate) {
            status = 'Ended';
            statusClass = 'bg-gray-100 text-gray-800';
            timeRemaining = 'This hackathon has ended';
        } else {
            status = 'Ongoing';
            statusClass = 'bg-green-100 text-green-800';
            const remaining = endDate - now;
            const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
            const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            timeRemaining = `${days} day${days !== 1 ? 's' : ''}, ${hours} hour${hours !== 1 ? 's' : ''} remaining`;
        }

        document.getElementById('hackathon-status').textContent = status;
        document.getElementById('hackathon-status').className = `px-3 py-1 rounded-full text-sm font-medium ${statusClass}`;
        document.getElementById('time-remaining').textContent = timeRemaining;
    }

    /**
     * Update statistics
     */
    updateStats(stats) {
        document.getElementById('participant-count').textContent = stats.participants.size;
        document.getElementById('pr-count').textContent = stats.totalPRs;
        document.getElementById('merged-pr-count').textContent = stats.mergedPRs;
        document.getElementById('issue-count').textContent = stats.totalIssues || 0;
        // Use resolved repositories count if available, otherwise fall back to config
        const repoCount = this.repositories ? this.repositories.length : (this.config.github.repositories || []).length;
        document.getElementById('repo-count').textContent = repoCount;
    }

    /**
     * Render the leaderboard
     */
    renderLeaderboard(participants) {
        const leaderboard = this.api.generateLeaderboard(
            participants,
            this.config.display.maxLeaderboardEntries
        );

        const container = document.getElementById('leaderboard');

        if (leaderboard.length === 0) {
            container.innerHTML = '<p class="text-gray-500 italic">No contributions yet. Be the first to contribute!</p>';
            return;
        }

        container.innerHTML = leaderboard.map((participant, index) => {
            const position = index + 1;
            let trophyIcon = '';
            let bgClass = '';

            if (position === 1) {
                trophyIcon = '<i class="fas fa-trophy trophy-gold"></i>';
                bgClass = 'bg-yellow-50';
            } else if (position === 2) {
                trophyIcon = '<i class="fas fa-trophy trophy-silver"></i>';
                bgClass = 'bg-gray-50';
            } else if (position === 3) {
                trophyIcon = '<i class="fas fa-trophy trophy-bronze"></i>';
                bgClass = 'bg-orange-50';
            }

            return `
                <div class="p-4 ${bgClass} rounded-lg border border-gray-200">
                    <div class="flex items-center">
                        <div class="w-8 h-8 flex items-center justify-center mr-3 bg-gray-100 text-gray-600 rounded-full font-bold">
                            ${position}
                        </div>
                        <img src="${participant.avatar}" alt="${participant.username}"
                             class="w-8 h-8 rounded-full mr-3" width="32" height="32">
                        <div class="flex-grow">
                            <div class="font-medium flex items-center gap-2">
                                <a href="${participant.url}" target="_blank" class="hover:text-red-600">
                                    ${this.escapeHtml(participant.username)}
                                </a>
                                ${trophyIcon}
                            </div>
                            <div class="text-sm text-gray-500">
                                ${participant.mergedCount} merged PR${participant.mergedCount !== 1 ? 's' : ''}
                            </div>
                        </div>
                        <a href="https://github.com/search?q=author%3A${participant.username}+type%3Apr" 
                           target="_blank" 
                           rel="noopener noreferrer"
                           class="ml-2 px-2 sm:px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-xs sm:text-sm font-medium whitespace-nowrap"
                           title="View all PRs by ${this.escapeHtml(participant.username)}">
                            <i class="fas fa-external-link-alt mr-1"></i>
                            <span class="hidden sm:inline">View PRs</span>
                        </a>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderReviewLeaderBoard(participants) {
        const reviewLeaderboard = this.api.generateReviewLeaderboard(
            participants,
            this.config.display.maxLeaderboardEntries
        );

        const container = document.getElementById('review-leaderboard');

        if (reviewLeaderboard.length === 0) {
            container.innerHTML = '<p class="text-gray-500 italic">No reviews yet. Be the first to review!</p>';
            return;
        }

        container.innerHTML = reviewLeaderboard.map((participant, index) => {
            const position = index + 1;
            let trophyIcon = '';
            let bgClass = '';

            if (position === 1) {
                trophyIcon = '<i class="fas fa-trophy trophy-gold"></i>';
                bgClass = 'bg-yellow-50';
            } else if (position === 2) {
                trophyIcon = '<i class="fas fa-trophy trophy-silver"></i>';
                bgClass = 'bg-gray-50';
            } else if (position === 3) {
                trophyIcon = '<i class="fas fa-trophy trophy-bronze"></i>';
                bgClass = 'bg-orange-50';
            }

            return `
                <div class="p-4 ${bgClass} rounded-lg border border-gray-200">
                    <div class="flex items-center">
                        <div class="w-8 h-8 flex items-center justify-center mr-3 bg-gray-100 text-gray-600 rounded-full font-bold">
                            ${position}
                        </div>
                        <img src="${participant.avatar}" alt="${participant.username}"
                             class="w-8 h-8 rounded-full mr-3" width="32" height="32">
                        <div class="flex-grow">
                            <div class="font-medium flex items-center gap-2">
                                <a href="${participant.url}" target="_blank" class="hover:text-red-600">
                                    ${this.escapeHtml(participant.username)}
                                </a>
                                ${trophyIcon}
                            </div>
                            <div class="text-sm text-gray-500">
                                ${participant.reviewCount} review${participant.reviewCount !== 1 ? 's' : ''}
                            </div>
                        </div>
                        <a href="https://github.com/search?q=reviewed-by%3A${participant.username}+type%3Apr" 
                           target="_blank" 
                           rel="noopener noreferrer"
                           class="ml-2 px-2 sm:px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-xs sm:text-sm font-medium whitespace-nowrap"
                           title="View all reviews by ${this.escapeHtml(participant.username)}">
                            <i class="fas fa-external-link-alt mr-1"></i>
                            <span class="hidden sm:inline">View Reviews</span>
                        </a>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Render the PR activity chart - simplified to show total merged PRs per day across all repositories
     */
    renderChart(dailyActivity, prs) {
        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js is not available. Skipping chart rendering.');
            return;
        }
        
        const dates = Object.keys(dailyActivity).sort();
        
        // Calculate total merged PRs per day (combined across all repositories)
        // We use merged_at date to show when contributions were actually accepted
        const prCountsByDate = {};
        prs.forEach(pr => {
            if (!pr.merged_at) return; // Only count merged PRs
            const prDate = new Date(pr.merged_at).toISOString().split('T')[0];
            if (!prCountsByDate[prDate]) {
                prCountsByDate[prDate] = 0;
            }
            prCountsByDate[prDate]++;
        });
        
        // Create data array for the chart
        const data = dates.map(date => prCountsByDate[date] || 0);

        const ctx = document.getElementById('prActivityChart').getContext('2d');
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Pull Requests',
                    data: data,
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderColor: 'rgba(220, 38, 38, 1)',
                    borderWidth: 2,
                    borderRadius: 4,
                    barThickness: 'flex',
                    maxBarThickness: 40
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        cornerRadius: 8,
                        callbacks: {
                            title: function(context) {
                                const date = new Date(context[0].label);
                                return date.toLocaleDateString('en-US', { 
                                    month: 'short', 
                                    day: 'numeric',
                                    year: 'numeric'
                                });
                            },
                            label: function(context) {
                                const value = context.parsed.y;
                                return value === 1 ? '1 Pull Request' : `${value} Pull Requests`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            maxRotation: 45,
                            minRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 10,
                            callback: function(value, index) {
                                const date = new Date(this.getLabelForValue(value));
                                return date.toLocaleDateString('en-US', { 
                                    month: 'short', 
                                    day: 'numeric'
                                });
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            precision: 0,
                            font: {
                                size: 11
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    /**
     * Generate distinct colors for chart datasets
     */
    generateColors(count) {
        const colors = [
            'rgba(239, 68, 68, 0.8)',   // red
            'rgba(59, 130, 246, 0.8)',  // blue
            'rgba(34, 197, 94, 0.8)',   // green
            'rgba(249, 115, 22, 0.8)',  // orange
            'rgba(168, 85, 247, 0.8)',  // purple
            'rgba(236, 72, 153, 0.8)',  // pink
            'rgba(14, 165, 233, 0.8)',  // sky
            'rgba(132, 204, 22, 0.8)',  // lime
            'rgba(251, 146, 60, 0.8)',  // amber
            'rgba(192, 132, 252, 0.8)', // violet
            'rgba(244, 63, 94, 0.8)',   // rose
        ];
        // If we need more colors than predefined, generate random ones
        const MIN_COLOR_VALUE = 55;  // Minimum RGB value to avoid too dark colors
        const COLOR_RANGE = 200;     // Range of RGB values for reasonable brightness
        while (colors.length < count) {
            const r = Math.floor(Math.random() * COLOR_RANGE + MIN_COLOR_VALUE);
            const g = Math.floor(Math.random() * COLOR_RANGE + MIN_COLOR_VALUE);
            const b = Math.floor(Math.random() * COLOR_RANGE + MIN_COLOR_VALUE);
            colors.push(`rgba(${r}, ${g}, ${b}, 0.8)`);
        }
        return colors.slice(0, count);
    }

    /**
     * Render repositories list
     */
    renderRepositories(repoStats) {
        const container = document.getElementById('repositories-list');
        // Use resolved repositories if available, otherwise fall back to config
        const repositories = this.repositories || this.config.github.repositories || [];
        
        // Update the repositories count
        const titleElement = document.getElementById('repositories-title');
        if (titleElement) {
            titleElement.textContent = `(${repositories.length})`;
        }
        
        const reposHtml = repositories.map(repoPath => {
            const [owner, repo] = repoPath.split('/');
            const stats = repoStats[repoPath] || { total: 0, merged: 0, issues: 0, closedIssues: 0 };
            return `
                <div class="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center">
                            <i class="fab fa-github text-gray-600 mr-2"></i>
                            <a href="https://github.com/${repoPath}" target="_blank"
                               class="font-medium hover:text-red-600">
                                ${repoPath}
                            </a>
                        </div>
                    </div>
                    ${this.config.display.showRepoStats ? `
                        <div class="flex gap-4 text-sm text-gray-600 mb-2">
                            <span class="flex items-center">
                                <i class="fas fa-code-branch mr-1 text-blue-500"></i>
                                <strong>${stats.total}</strong> PRs (<strong>${stats.merged}</strong> merged)
                            </span>
                            <span class="flex items-center">
                                <i class="fas fa-circle-dot mr-1 text-green-500"></i>
                                <strong>${stats.issues || 0}</strong> Issues (<strong>${stats.closedIssues || 0}</strong> closed)
                            </span>
                        </div>
                    ` : ''}
                    <div class="flex gap-2">
                        <a href="https://github.com/${repoPath}" target="_blank"
                           class="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                            <i class="fab fa-github mr-1"></i>
                            GitHub
                        </a>
                        <a href="https://github.com/${repoPath}/pulls" target="_blank"
                           class="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                            <i class="fas fa-code-branch mr-1"></i>
                            Pull Requests
                        </a>
                        <a href="https://github.com/${repoPath}/issues" target="_blank"
                           class="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                            <i class="fas fa-circle-dot mr-1"></i>
                            Issues
                        </a>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = reposHtml || '<p class="text-gray-600">No repositories configured.</p>';
    }

    /**
     * Render sponsors
     */
    renderSponsors() {
        const container = document.getElementById('sponsors-list');
        if (!this.config.sponsors || this.config.sponsors.length === 0) {
            let html = '<p class="text-gray-500 italic">No sponsors yet.</p>';
            if (this.config.sponsorNote || this.config.sponsorLink) {
                html += '<div class="mt-6 pt-6 border-t border-gray-200">';
                if (this.config.sponsorNote) {
                    html += `
                        <div class="mb-4">
                            <h3 class="text-lg font-semibold mb-2 text-gray-800">Sponsorship Information</h3>
                            <p class="text-gray-600">${this.escapeHtml(this.config.sponsorNote)}</p>
                        </div>
                    `;
                }
                if (this.config.sponsorLink) {
                    html += `
                        <a href="${this.config.sponsorLink}" target="_blank"
                           class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700">
                            <i class="fas fa-handshake mr-2"></i>
                            Become a Sponsor
                        </a>
                    `;
                }
                html += '</div>';
            }
            container.innerHTML = html;
            return;
        }

        // Group sponsors by level
        const levels = ['platinum', 'gold', 'silver', 'bronze', 'partner'];
        const grouped = {};
        levels.forEach(level => { grouped[level] = []; });
        this.config.sponsors.forEach(sponsor => {
            if (grouped[sponsor.level]) {
                grouped[sponsor.level].push(sponsor);
            }
        });

        const html = levels.map(level => {
            const sponsors = grouped[level];
            if (sponsors.length === 0) return '';

            return `
                <div class="mb-6 last:mb-0">
                    <h3 class="text-lg font-semibold mb-3 capitalize">${level} Sponsors</h3>
                    <div class="grid grid-cols-2 gap-4">
                        ${sponsors.map(sponsor => `
                            <a href="${sponsor.website || '#'}" target="_blank"
                               class="flex flex-col items-center p-3 border rounded-lg hover:bg-gray-50 transition">
                                ${sponsor.logo ? `
                                    <img src="${sponsor.logo}" alt="${this.escapeHtml(sponsor.name)}"
                                         class="h-12 object-contain mb-2">
                                ` : `
                                    <div class="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                                        <span class="text-gray-500 font-bold">${sponsor.name.charAt(0)}</span>
                                    </div>
                                `}
                                <div class="text-center">
                                    <div class="text-sm font-medium">${this.escapeHtml(sponsor.name)}</div>
                                </div>
                            </a>
                        `).join('')}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html || '<p class="text-gray-500 italic">No sponsors yet.</p>';
    }

    /**
     * Update API info section in footer with token status and rate limit details
     */
    async updateApiInfo() {
        const infoEl = document.getElementById('github-api-info');
        if (!infoEl) return;

        const hasToken = typeof this.config.github.token === 'string' && this.config.github.token.length > 0;

        // Use rate limit already captured from prior API calls; fetch if not yet available
        let rl = this.api.rateLimit;
        if (rl.remaining === null) {
            rl = await this.api.fetchRateLimit();
        }

        const tokenHtml = hasToken
            ? '<span class="inline-flex items-center gap-1 text-green-600"><i class="fas fa-key"></i> GitHub Token: Active</span>'
            : '<span class="inline-flex items-center gap-1 text-yellow-600"><i class="fas fa-exclamation-triangle"></i> No GitHub Token (unauthenticated – 60 req/hr limit)</span>';

        let rateLimitHtml = '';
        if (rl.remaining !== null) {
            const resetDate = new Date(rl.reset * 1000);
            const resetTime = resetDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
            const pct = Math.round((rl.remaining / rl.limit) * 100);
            const barColor = pct > 50 ? 'bg-green-500' : pct > 20 ? 'bg-yellow-500' : 'bg-red-500';
            rateLimitHtml = `
                <span class="text-gray-400">|</span>
                <span>API calls: <strong>${rl.remaining}</strong> / ${rl.limit} remaining</span>
                <span class="inline-block w-16 h-2 rounded-full bg-gray-200 align-middle">
                    <span class="block h-2 rounded-full ${barColor}" style="width:${pct}%"></span>
                </span>
                <span class="text-gray-400">|</span>
                <span>Resets at <strong>${resetTime}</strong></span>`;
        }

        infoEl.innerHTML = `<div class="flex flex-wrap items-center justify-center gap-2 text-sm">${tokenHtml}${rateLimitHtml}</div>`;
    }

    /**
     * Show loading state
     */
    showLoading() {
        // Could add a loading overlay here
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        // Could remove loading overlay here
    }

    /**
     * Show error message
     */
    showError(message) {
        const banner = document.getElementById('banner-section');
        banner.innerHTML = `
            <div class="text-center text-white p-4">
                <i class="fas fa-exclamation-triangle text-4xl mb-4"></i>
                <h2 class="text-2xl font-bold mb-2">Error Loading Hackathon</h2>
                <p class="text-lg">${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    /**
     * Get CSS class for review state
     */
    getReviewStateClass(state) {
        switch (state?.toLowerCase()) {
            case 'approved':
                return 'bg-green-100 text-green-700';
            case 'changes_requested':
                return 'bg-red-100 text-red-700';
            case 'commented':
                return 'bg-blue-100 text-blue-700';
            default:
                return 'bg-gray-100 text-gray-700';
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Get slug from URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const slug = urlParams.get('slug');
    
    // Find hackathon by slug
    let hackathonConfig;
    if (slug && typeof getHackathonBySlug === 'function') {
        hackathonConfig = getHackathonBySlug(slug);
    }
    
    // If no slug or hackathon not found, try to use the first hackathon or fall back to legacy config
    if (!hackathonConfig) {
        // Check if legacy config exists (for backwards compatibility)
        if (typeof HACKATHON_CONFIG !== 'undefined') {
            hackathonConfig = HACKATHON_CONFIG;
        } else if (typeof HACKATHONS_CONFIG !== 'undefined' && HACKATHONS_CONFIG && HACKATHONS_CONFIG.hackathons && HACKATHONS_CONFIG.hackathons.length > 0) {
            // Use first hackathon as default
            hackathonConfig = HACKATHONS_CONFIG.hackathons[0];
            console.warn('No slug provided, using first available hackathon');
        } else {
            // Show error if no configuration available
            const banner = document.getElementById('banner-section');
            if (banner) {
                banner.innerHTML = `
                    <div class="text-center text-white p-4">
                        <i class="fas fa-exclamation-triangle text-4xl mb-4"></i>
                        <h2 class="text-2xl font-bold mb-2">Hackathon Not Found</h2>
                        <p class="text-lg mb-4">The requested hackathon could not be found.</p>
                        <a href="index.html" class="inline-block px-6 py-3 bg-white text-red-600 rounded-lg font-medium hover:bg-gray-100">
                            View All Hackathons
                        </a>
                    </div>
                `;
            }
            return;
        }
    }
    
    const dashboard = new HackathonDashboard(hackathonConfig);
    dashboard.init();
});
