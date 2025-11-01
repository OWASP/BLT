/**
 * Main Application Logic
 * Initializes and manages the hackathon dashboard
 */

class HackathonDashboard {
    constructor(config) {
        this.config = config;
        this.api = new GitHubAPI(config.github.token);
        this.chart = null;
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
            
            // Fetch all PRs
            const prs = await this.api.getAllPullRequests(
                this.config.github.repositories,
                startDate,
                endDate
            );

            // Process PR data
            const stats = this.api.processPRData(prs, startDate, endDate);

            // Update UI
            this.updateStats(stats);
            this.renderLeaderboard(stats.participants);
            this.renderChart(stats.dailyActivity);
            this.renderRepositories(stats.repoStats);
            this.renderPrizes();
            this.renderSponsors();
            
            this.hideLoading();
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
        document.getElementById('repo-count').textContent = this.config.github.repositories.length;
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

            const prsHtml = this.config.display.showPRsInLeaderboard ? `
                <div class="mt-2 pl-11">
                    <div class="text-sm font-medium text-gray-700 mb-2">Contributions:</div>
                    <div class="space-y-2 max-h-48 overflow-y-auto">
                        ${participant.prs.filter(pr => pr.merged_at).slice(0, 5).map(pr => `
                            <a href="${pr.html_url}" target="_blank" rel="noopener noreferrer"
                               class="block p-2 bg-gray-50 hover:bg-gray-100 rounded border-l-4 border-red-600 transition">
                                <div class="font-medium text-sm truncate">${this.escapeHtml(pr.title)}</div>
                                <div class="flex items-center text-xs text-gray-500 mt-1">
                                    <span class="flex items-center">
                                        <i class="fas fa-code-branch mr-1"></i>
                                        ${pr.repository}
                                    </span>
                                    <span class="mx-2">•</span>
                                    <span>
                                        <i class="far fa-calendar-alt mr-1"></i>
                                        ${new Date(pr.merged_at).toLocaleDateString()}
                                    </span>
                                </div>
                            </a>
                        `).join('')}
                    </div>
                </div>
            ` : '';

            return `
                <div class="p-4 ${bgClass} rounded-lg border border-gray-200">
                    <div class="flex items-center mb-3">
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
                    </div>
                    ${prsHtml}
                </div>
            `;
        }).join('');
    }

    /**
     * Render the PR activity chart
     */
    renderChart(dailyActivity) {
        const dates = Object.keys(dailyActivity).sort();
        const totalCounts = dates.map(date => dailyActivity[date].total);
        const mergedCounts = dates.map(date => dailyActivity[date].merged);

        const ctx = document.getElementById('prActivityChart').getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'All Pull Requests',
                        data: totalCounts,
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Merged Pull Requests',
                        data: mergedCounts,
                        backgroundColor: 'rgba(239, 68, 68, 0.7)',
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Pull Requests'
                        },
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }

    /**
     * Render repositories list
     */
    renderRepositories(repoStats) {
        const container = document.getElementById('repositories-list');
        
        const reposHtml = this.config.github.repositories.map(repoPath => {
            const [owner, repo] = repoPath.split('/');
            const stats = repoStats[repoPath] || { total: 0, merged: 0 };
            
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
                        ${this.config.display.showRepoStats ? `
                            <span class="text-sm text-gray-500">
                                ${stats.merged} merged PR${stats.merged !== 1 ? 's' : ''}
                            </span>
                        ` : ''}
                    </div>
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
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = reposHtml || '<p class="text-gray-600">No repositories configured.</p>';
    }

    /**
     * Render prizes
     */
    renderPrizes() {
        const container = document.getElementById('prizes-list');
        
        if (!this.config.prizes || this.config.prizes.length === 0) {
            container.innerHTML = '<p class="text-gray-500 italic">No prizes have been announced yet.</p>';
            return;
        }

        container.innerHTML = this.config.prizes.map(prize => {
            let icon, iconColor;
            if (prize.position === 1) {
                icon = 'fa-trophy';
                iconColor = 'text-yellow-500';
            } else if (prize.position === 2) {
                icon = 'fa-trophy';
                iconColor = 'text-gray-400';
            } else if (prize.position === 3) {
                icon = 'fa-trophy';
                iconColor = 'text-orange-600';
            } else {
                icon = 'fa-award';
                iconColor = 'text-blue-500';
            }

            return `
                <div class="border-b pb-4 last:border-b-0 last:pb-0">
                    <div class="flex items-center mb-2">
                        <i class="fas ${icon} ${iconColor} mr-2 text-xl"></i>
                        <h3 class="text-xl font-semibold">${this.escapeHtml(prize.title)}</h3>
                    </div>
                    <p class="text-gray-600 mb-2">${this.escapeHtml(prize.description)}</p>
                    ${prize.value ? `<p class="font-medium text-red-600">$${prize.value}</p>` : ''}
                </div>
            `;
        }).join('');
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
    const dashboard = new HackathonDashboard(HACKATHON_CONFIG);
    dashboard.init();
});
