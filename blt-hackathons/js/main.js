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
     * Initialize the dashboard by loading pre-fetched stats from a JSON file.
     * All data is collected server-side (via fetch_stats.py running hourly) so
     * the page never makes live GitHub API calls.
     */
    async init() {
        this.showLoading();
        try {
            // Update basic info from the JS config (name, dates, rules, etc.)
            this.updateBasicInfo();

            const slug = this.config.slug;

            // Load pre-fetched stats produced by fetch_stats.py
            let statsData;
            try {
                const response = await fetch(`hackathon-data/${slug}.json`);
                if (!response.ok) {
                    throw new Error(
                        `Stats file not available (HTTP ${response.status}). ` +
                        `Data may not have been generated yet – please wait for ` +
                        `the hourly refresh or trigger it manually.`
                    );
                }
                statsData = await response.json();
            } catch (fetchError) {
                console.error('Failed to load pre-fetched stats:', fetchError);
                this.showError(`Unable to load hackathon stats: ${fetchError.message}`);
                return;
            }

            // Use repositories from pre-fetched data (may include org repos)
            this.repositories =
                statsData.repositories ||
                this.config.github.repositories ||
                [];

            const stats = statsData.stats || {};

            // Reconstruct a participants Map from the pre-fetched leaderboard arrays
            // so that existing render helpers (generateLeaderboard, etc.) work unchanged.
            const participants = new Map();
            const allParticipants = [
                ...(stats.leaderboard || []),
                ...(stats.reviewLeaderboard || []),
            ];
            const seen = new Set();
            allParticipants.forEach(p => {
                if (!seen.has(p.username)) {
                    seen.add(p.username);
                    participants.set(p.username, {
                        user: {
                            username: p.username,
                            email: '',
                            id: `contributor_${p.username}`,
                        },
                        count: p.mergedCount || 0,
                        prs: [],
                        is_contributor: true,
                        avatar: p.avatar,
                        url: p.url,
                        mergedCount: p.mergedCount || 0,
                        reviewCount: p.reviewCount || 0,
                        reviews: p.reviews || [],
                    });
                }
            });

            // Update UI
            this.updateStats({
                participants,
                participantCount: stats.participantCount,
                totalPRs: stats.totalPRs || 0,
                mergedPRs: stats.mergedPRs || 0,
                totalIssues: stats.totalIssues || 0,
                closedIssues: stats.closedIssues || 0,
            });
            this.renderLeaderboard(participants);
            this.renderReviewLeaderBoard(participants);

            // Render chart using pre-computed daily merged PR counts
            try {
                this.renderChart(
                    stats.dailyActivity || {},
                    stats.dailyMergedPRs || {}
                );
            } catch (chartError) {
                console.warn('Failed to render chart (Chart.js may not be loaded):', chartError);
                const chartCanvas = document.getElementById('prActivityChart');
                if (chartCanvas && chartCanvas.parentElement) {
                    chartCanvas.parentElement.parentElement.style.display = 'none';
                }
            }

            this.renderRepositories(stats.repoStats || {}, stats.repoData || []);
            this.renderSponsors();
            this.hideLoading();
            this.loadedAt = statsData.lastUpdated
                ? new Date(statsData.lastUpdated)
                : new Date();
            this.updateApiInfo();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError('Failed to load hackathon data. Please try again later.');
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
        // Use explicit participantCount from pre-fetched data when available,
        // otherwise fall back to the size of the participants Map.
        const participantCount =
            stats.participantCount !== undefined
                ? stats.participantCount
                : stats.participants.size;
        document.getElementById('participant-count').textContent = participantCount;
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
     * Render the PR activity chart using pre-computed daily merged PR counts.
     * @param {Object} dailyActivity   - Map of date string -> {total, merged} (used for date range)
     * @param {Object} dailyMergedPRs  - Map of date string -> merged PR count (pre-computed)
     */
    renderChart(dailyActivity, dailyMergedPRs) {
        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js is not available. Skipping chart rendering.');
            return;
        }
        
        const dates = Object.keys(dailyActivity).sort();
        
        // Use the pre-computed per-day merged count directly
        const data = dates.map(date => (dailyMergedPRs[date] || 0));

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
    renderRepositories(repoStats, repoData = []) {
        const container = document.getElementById('repositories-list');
        // Use resolved repositories if available, otherwise fall back to config
        const repositories = this.repositories || this.config.github.repositories || [];
        
        // Build a lookup map from full_name -> repo metadata
        const repoMetaMap = {};
        repoData.forEach(repo => {
            if (repo && repo.full_name) {
                repoMetaMap[repo.full_name] = repo;
            }
        });

        // Update the repositories count
        const titleElement = document.getElementById('repositories-title');
        if (titleElement) {
            titleElement.textContent = `(${repositories.length})`;
        }
        
        const reposHtml = repositories.map(repoPath => {
            const stats = repoStats[repoPath] || { total: 0, merged: 0, issues: 0, closedIssues: 0 };
            const meta = repoMetaMap[repoPath] || {};
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
                        ${meta.stargazers_count !== undefined ? `
                        <div class="flex items-center text-sm text-gray-500 gap-3">
                            <span title="Stars"><i class="fas fa-star text-yellow-400 mr-1"></i>${meta.stargazers_count}</span>
                            <span title="Forks"><i class="fas fa-code-branch text-blue-400 mr-1"></i>${meta.forks_count}</span>
                            ${meta.language ? `<span title="Language"><i class="fas fa-circle mr-1 text-gray-400"></i>${this.escapeHtml(meta.language)}</span>` : ''}
                        </div>
                        ` : ''}
                    </div>
                    ${meta.description ? `<p class="text-sm text-gray-600 mb-2">${this.escapeHtml(meta.description)}</p>` : ''}
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
     * Update API info section in footer.
     * Since stats are pre-fetched server-side, we only show when data was last
     * refreshed – no live GitHub API calls are made from the frontend.
     */
    async updateApiInfo() {
        const infoEl = document.getElementById('github-api-info');
        if (!infoEl) return;

        const lastUpdatedHtml = this.loadedAt
            ? `<span class="inline-flex items-center gap-1 text-green-600"><i class="fas fa-sync-alt"></i> Stats auto-refreshed hourly</span>` +
              `<span class="text-gray-400">|</span>` +
              `<span>Last updated: <span id="last-updated-time" title="${this.loadedAt.toLocaleString()}">${this.timeAgo(this.loadedAt)}</span></span>`
            : '';

        infoEl.innerHTML = `<div class="flex flex-wrap items-center justify-center gap-2 text-sm">${lastUpdatedHtml}</div>`;
        this.startLastUpdatedRefresh();
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
     * Start periodic refresh of the "last updated" relative time in the footer
     */
    startLastUpdatedRefresh() {
        const infoEl = document.getElementById('github-api-info');
        if (!infoEl || !this.loadedAt) return;
        if (this._lastUpdatedInterval) clearInterval(this._lastUpdatedInterval);
        this._lastUpdatedInterval = setInterval(() => {
            const timeEl = infoEl.querySelector('#last-updated-time');
            if (timeEl) timeEl.textContent = this.timeAgo(this.loadedAt);
        }, 60000);
    }

    /**
     * Return a human-readable relative time string (e.g. "just now", "3 minutes ago")
     */
    timeAgo(date) {
        const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
        if (seconds < 60) return 'just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
        const days = Math.floor(hours / 24);
        return `${days} day${days !== 1 ? 's' : ''} ago`;
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
