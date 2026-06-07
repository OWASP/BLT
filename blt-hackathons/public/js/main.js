/**
 * Main Application Logic
 * Initializes and manages the hackathon dashboard
 */

class HackathonDashboard {
    constructor(config) {
        this.config = config;
        this.provider = (config.provider || 'github').toLowerCase();
        this.providerConfig = this.provider === 'gitlab'
            ? (config.gitlab || {})
            : (config.github || {});
        // The class also contains the shared leaderboard sorting helpers.
        this.api = new GitHubAPI((config.github || {}).token);
        this.chart = null;
        // Store resolved repositories (set during initialization)
        // Contains the merged list of explicit repositories and organization repositories
        this.repositories = null;
        this.changeLabels = this.provider === 'gitlab'
            ? {
                singular: 'merge request',
                plural: 'merge requests',
                shortPlural: 'MRs',
                titlePlural: 'Merge requests',
                titleMerged: 'Merged MRs',
            }
            : {
                singular: 'pull request',
                plural: 'pull requests',
                shortPlural: 'PRs',
                titlePlural: 'Pull requests',
                titleMerged: 'Merged PRs',
            };
    }

    /**
     * Initialize the dashboard by loading pre-fetched stats from a JSON file.
     * All data is collected server-side by fetch_stats.py, so the page never
     * makes live source-control API calls.
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
                        `Data may not have been generated yet. Please wait for ` +
                        `the scheduled refresh or trigger it manually.`
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
                this.getConfiguredRepositories() ||
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
        this.updateProviderLabels();

        const eventName = this.config.name || 'Hackathon Dashboard';
        this.setText('hackathon-title', eventName);
        this.setText('nav-title', eventName);
        this.setText('hackathon-name', eventName);

        // Update banner image if provided
        const bannerSection = document.getElementById('banner-section');
        if (this.config.bannerImage) {
            const bannerUrl = this.safeUrl(this.config.bannerImage, '');
            if (bannerSection && bannerUrl) {
                bannerSection.style.backgroundImage = `url("${bannerUrl.replace(/"/g, '%22')}")`;
            }
        }

        // Update description
        this.setText(
            'hackathon-description',
            (this.config.description || 'Track progress, activity, repositories, and prizes for this hackathon.').trim()
        );

        // Update rules if provided
        const rulesSection = document.getElementById('rules-section');
        if (this.config.rules) {
            if (rulesSection) rulesSection.hidden = false;
            this.setText('hackathon-rules', this.config.rules.trim());
        } else {
            if (rulesSection) rulesSection.hidden = false;
            this.setText('hackathon-rules', 'No additional rules have been published for this event.');
        }

        // Update dates and status
        const startDate = new Date(this.config.startTime);
        const endDate = new Date(this.config.endTime);
        const now = new Date();

        const dateStr = `${this.formatDate(startDate)} - ${this.formatDate(endDate)}`;
        this.setText('hackathon-dates', dateStr);

        // Also update the standalone time-range bar at the top of the detail page
        const timeRangeDisplay = document.getElementById('time-range-display');
        if (timeRangeDisplay) {
            timeRangeDisplay.textContent = dateStr;
        }

        // Determine status
        let status, statusClass, timeRemaining;
        if (now < startDate) {
            status = 'Upcoming';
            statusClass = 'blt-status blt-status--upcoming';
            const daysUntil = Math.ceil((startDate - now) / (1000 * 60 * 60 * 24));
            timeRemaining = `Starts in ${daysUntil} day${daysUntil !== 1 ? 's' : ''}`;
        } else if (now > endDate) {
            status = 'Ended';
            statusClass = 'blt-status blt-status--ended';
            timeRemaining = 'This hackathon has ended';
        } else {
            status = 'Ongoing';
            statusClass = 'blt-status blt-status--ongoing';
            const remaining = endDate - now;
            const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
            const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            timeRemaining = `${days} day${days !== 1 ? 's' : ''}, ${hours} hour${hours !== 1 ? 's' : ''} remaining`;
        }

        const statusEl = document.getElementById('hackathon-status');
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.className = statusClass;
        }
        this.setText('time-remaining', timeRemaining);
        this.updateTimeline(startDate, endDate, status, timeRemaining);
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
        document.getElementById('participant-count').textContent = participantCount.toLocaleString();
        document.getElementById('pr-count').textContent = (stats.totalPRs || 0).toLocaleString();
        document.getElementById('merged-pr-count').textContent = (stats.mergedPRs || 0).toLocaleString();
        document.getElementById('issue-count').textContent = (stats.totalIssues || 0).toLocaleString();
        // Use resolved repositories count if available, otherwise fall back to config
        const repoCount = this.repositories ? this.repositories.length : this.getConfiguredRepositories().length;
        document.getElementById('repo-count').textContent = repoCount.toLocaleString();

        // Calculate days active: days elapsed from start up to today (capped at end date)
        const startDate = new Date(this.config.startTime);
        const endDate = new Date(this.config.endTime);
        const now = new Date();
        const effectiveEnd = now < endDate ? now : endDate;
        const daysActive = now < startDate
            ? 0
            : Math.floor((effectiveEnd - startDate) / (1000 * 60 * 60 * 24));
        document.getElementById('days-active-count').textContent = daysActive.toLocaleString();
    }

    updateProviderLabels() {
        this.setText('pr-stat-label', this.changeLabels.shortPlural);
        this.setText('merged-pr-stat-label', this.changeLabels.titleMerged);
        this.setText('chart-heading', `${this.changeLabels.titlePlural} activity`);
    }

    updateTimeline(startDate, endDate, status, timeRemaining) {
        const now = new Date();
        const totalMs = Math.max(endDate - startDate, 1);
        const elapsedMs = this.clamp(now - startDate, 0, totalMs);
        const percent = Math.round((elapsedMs / totalMs) * 100);
        const totalDays = Math.max(Math.ceil(totalMs / (1000 * 60 * 60 * 24)), 1);
        const elapsedDays = status === 'Upcoming'
            ? 0
            : Math.min(Math.floor(elapsedMs / (1000 * 60 * 60 * 24)), totalDays);

        const progressBar = document.getElementById('timeline-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            const progressShell = progressBar.closest('[role="progressbar"]');
            if (progressShell) {
                progressShell.setAttribute('aria-valuenow', String(percent));
            }
        }

        this.setText('timeline-progress-label', `${percent}% complete - ${timeRemaining}`);
        this.setText('timeline-start-date', this.formatCompactDate(startDate));
        this.setText('timeline-current-date', this.formatCompactDate(now));
        this.setText('timeline-end-date', this.formatCompactDate(endDate));
        this.setText('timeline-start-date-detail', this.formatDateTime(startDate));
        this.setText('timeline-end-date-detail', this.formatDateTime(endDate));
        this.setText(
            'timeline-current-status',
            `${status}. ${elapsedDays.toLocaleString()} of ${totalDays.toLocaleString()} scheduled day${totalDays !== 1 ? 's' : ''} elapsed.`
        );
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
        if (!container) return;
        container.setAttribute('aria-busy', 'false');

        if (leaderboard.length === 0) {
            container.innerHTML = this.renderEmptyState(
                'fa-code-pull-request',
                `No merged ${this.changeLabels.plural} yet. Be the first to contribute.`
            );
            return;
        }

        container.innerHTML = leaderboard.map((participant, index) => {
            const position = index + 1;
            let trophyIcon = '';

            if (position === 1) {
                trophyIcon = '<i class="fas fa-trophy trophy-gold"></i>';
            } else if (position === 2) {
                trophyIcon = '<i class="fas fa-trophy trophy-silver"></i>';
            } else if (position === 3) {
                trophyIcon = '<i class="fas fa-trophy trophy-bronze"></i>';
            }

            const username = participant.username || 'unknown';
            const safeUsername = this.escapeHtml(username);
            const participantUrl = this.safeUrl(participant.url, '#');
            const activityUrl = this.safeUrl(this.getContributorActivityUrl(participant), '#');
            const avatarHtml = this.renderAvatar(participant.avatar, username);
            const mergedCount = participant.mergedCount || 0;

            return `
                <div class="dashboard-leaderboard-item">
                    <div class="dashboard-rank">${position}</div>
                    ${avatarHtml}
                    <div class="dashboard-leaderboard-name">
                        <a href="${this.escapeAttribute(participantUrl)}" target="_blank" rel="noopener noreferrer">
                            ${safeUsername}
                        </a>
                        ${trophyIcon}
                        <p>${mergedCount.toLocaleString()} merged ${mergedCount === 1 ? this.changeLabels.singular : this.changeLabels.plural}</p>
                    </div>
                    <a href="${this.escapeAttribute(activityUrl)}"
                       target="_blank"
                       rel="noopener noreferrer"
                       class="dashboard-small-link"
                       title="View contributions by ${this.escapeAttribute(username)}">
                        <i class="fas fa-external-link-alt" aria-hidden="true"></i>
                        <span>View ${this.changeLabels.shortPlural}</span>
                    </a>
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
        if (!container) return;
        container.setAttribute('aria-busy', 'false');

        if (reviewLeaderboard.length === 0) {
            container.innerHTML = this.renderEmptyState(
                'fa-comments',
                'No reviews recorded yet. Review activity will appear here after the next data refresh.'
            );
            return;
        }

        container.innerHTML = reviewLeaderboard.map((participant, index) => {
            const position = index + 1;
            let trophyIcon = '';

            if (position === 1) {
                trophyIcon = '<i class="fas fa-trophy trophy-gold"></i>';
            } else if (position === 2) {
                trophyIcon = '<i class="fas fa-trophy trophy-silver"></i>';
            } else if (position === 3) {
                trophyIcon = '<i class="fas fa-trophy trophy-bronze"></i>';
            }

            const username = participant.username || 'unknown';
            const safeUsername = this.escapeHtml(username);
            const participantUrl = this.safeUrl(participant.url, '#');
            const reviewUrl = this.safeUrl(this.getReviewActivityUrl(participant), '#');
            const avatarHtml = this.renderAvatar(participant.avatar, username);
            const reviewCount = participant.reviewCount || 0;

            return `
                <div class="dashboard-leaderboard-item">
                    <div class="dashboard-rank">${position}</div>
                    ${avatarHtml}
                    <div class="dashboard-leaderboard-name">
                        <a href="${this.escapeAttribute(participantUrl)}" target="_blank" rel="noopener noreferrer">
                            ${safeUsername}
                        </a>
                        ${trophyIcon}
                        <p>${reviewCount.toLocaleString()} review${reviewCount !== 1 ? 's' : ''}</p>
                    </div>
                    <a href="${this.escapeAttribute(reviewUrl)}"
                       target="_blank"
                       rel="noopener noreferrer"
                       class="dashboard-small-link"
                       title="View all reviews by ${this.escapeAttribute(username)}">
                        <i class="fas fa-external-link-alt" aria-hidden="true"></i>
                        <span>View reviews</span>
                    </a>
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
        const chartCanvas = document.getElementById('prActivityChart');
        const emptyState = document.getElementById('chart-empty-state');

        if (!chartCanvas) return;

        const showChartEmptyState = (message) => {
            chartCanvas.hidden = true;
            if (emptyState) {
                emptyState.classList.remove('hidden');
                emptyState.innerHTML = `
                    <i class="fas fa-chart-simple" aria-hidden="true"></i>
                    <p>${this.escapeHtml(message)}</p>
                `;
            }
        };

        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js is not available. Skipping chart rendering.');
            showChartEmptyState('Chart.js is unavailable, so activity cannot be rendered.');
            return;
        }
        
        const dates = Object.keys(dailyActivity).sort();
        if (dates.length === 0) {
            showChartEmptyState(`No ${this.changeLabels.plural} were found in the generated activity data.`);
            return;
        }
        
        // Use the pre-computed per-day merged count directly
        const data = dates.map(date => (dailyMergedPRs[date] || 0));

        chartCanvas.hidden = false;
        if (emptyState) emptyState.classList.add('hidden');

        const ctx = chartCanvas.getContext('2d');
        if (this.chart) {
            this.chart.destroy();
        }

        const textColor = this.getCssVar('--blt-muted') || '#64748b';
        const gridColor = this.getCssVar('--blt-border') || 'rgba(0, 0, 0, 0.08)';
        const tooltipBg = document.documentElement.classList.contains('dark')
            ? 'rgba(15, 17, 23, 0.94)'
            : 'rgba(15, 23, 42, 0.92)';

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [{
                    label: this.changeLabels.titleMerged,
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
                        backgroundColor: tooltipBg,
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
                                return value === 1
                                    ? `1 ${this.changeLabels.singular}`
                                    : `${value} ${this.changeLabels.plural}`;
                            }.bind(this)
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
                            color: textColor,
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
                            color: gridColor,
                            drawBorder: false
                        },
                        ticks: {
                            color: textColor,
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
        if (!container) return;
        container.setAttribute('aria-busy', 'false');
        // Use resolved repositories if available, otherwise fall back to config
        const repositories = this.repositories || this.getConfiguredRepositories();
        
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

        if (repositories.length === 0) {
            container.innerHTML = this.renderEmptyState(
                'fa-code-branch',
                'No eligible repositories or projects are configured for this event.'
            );
            return;
        }
        
        const reposHtml = repositories.map(repoPath => {
            const stats = repoStats[repoPath] || { total: 0, merged: 0, issues: 0, closedIssues: 0 };
            const meta = repoMetaMap[repoPath] || {};
            const urls = this.getRepositoryUrls(repoPath, meta);
            const providerIcon = this.provider === 'gitlab' ? 'gitlab' : 'github';
            const repositoryUrl = this.safeUrl(urls.repository, '#');
            const changesUrl = this.safeUrl(urls.changes, '#');
            const issuesUrl = this.safeUrl(urls.issues, '#');
            const language = meta.language ? this.escapeHtml(meta.language) : '';
            const description = meta.description ? this.escapeHtml(meta.description) : '';
            return `
                <article class="dashboard-repo-item">
                    <div class="dashboard-repo-heading">
                        <div class="flex items-center gap-2">
                            <i class="fab fa-${providerIcon}" aria-hidden="true"></i>
                            <a href="${this.escapeAttribute(repositoryUrl)}" target="_blank" rel="noopener noreferrer">
                                ${this.escapeHtml(repoPath)}
                            </a>
                        </div>
                        ${meta.stargazers_count !== undefined ? `
                        <div class="dashboard-repo-meta">
                            <span title="Stars"><i class="fas fa-star" aria-hidden="true"></i>${Number(meta.stargazers_count || 0).toLocaleString()}</span>
                            <span title="Forks"><i class="fas fa-code-branch" aria-hidden="true"></i>${Number(meta.forks_count || 0).toLocaleString()}</span>
                            ${language ? `<span title="Language"><i class="fas fa-circle" aria-hidden="true"></i>${language}</span>` : ''}
                        </div>
                        ` : ''}
                    </div>
                    ${description ? `<p>${description}</p>` : ''}
                    ${this.config.display.showRepoStats ? `
                        <div class="dashboard-repo-stats">
                            <span>
                                <i class="fas fa-code-branch" aria-hidden="true"></i>
                                <strong>${Number(stats.total || 0).toLocaleString()}</strong> ${this.changeLabels.shortPlural}
                                (<strong>${Number(stats.merged || 0).toLocaleString()}</strong> merged)
                            </span>
                            <span>
                                <i class="fas fa-circle-dot" aria-hidden="true"></i>
                                <strong>${Number(stats.issues || 0).toLocaleString()}</strong> issues
                                (<strong>${Number(stats.closedIssues || 0).toLocaleString()}</strong> closed)
                            </span>
                        </div>
                    ` : ''}
                    <div class="dashboard-repo-actions">
                        <a href="${this.escapeAttribute(repositoryUrl)}" target="_blank" rel="noopener noreferrer" class="dashboard-small-link">
                            <i class="fab fa-${providerIcon}" aria-hidden="true"></i>
                            ${this.provider === 'gitlab' ? 'GitLab' : 'GitHub'}
                        </a>
                        <a href="${this.escapeAttribute(changesUrl)}" target="_blank" rel="noopener noreferrer" class="dashboard-small-link">
                            <i class="fas fa-code-branch" aria-hidden="true"></i>
                            ${this.provider === 'gitlab' ? 'Merge Requests' : 'Pull Requests'}
                        </a>
                        <a href="${this.escapeAttribute(issuesUrl)}" target="_blank" rel="noopener noreferrer" class="dashboard-small-link">
                            <i class="fas fa-circle-dot" aria-hidden="true"></i>
                            Issues
                        </a>
                    </div>
                </article>
            `;
        }).join('');

        container.innerHTML = reposHtml;
    }

    /**
     * Return configured repositories or projects before generated data loads.
     */
    getConfiguredRepositories() {
        return this.provider === 'gitlab'
            ? (this.providerConfig.projects || [])
            : (this.providerConfig.repositories || []);
    }

    getRepositoryUrls(repoPath, metadata = {}) {
        const baseUrl = metadata.html_url || (
            this.provider === 'gitlab'
                ? `${(this.providerConfig.url || 'https://gitlab.com').replace(/\/$/, '')}/${repoPath}`
                : `https://github.com/${repoPath}`
        );
        return {
            repository: baseUrl,
            changes: `${baseUrl}/${this.provider === 'gitlab' ? '-/merge_requests' : 'pulls'}`,
            issues: `${baseUrl}/${this.provider === 'gitlab' ? '-/issues' : 'issues'}`,
        };
    }

    getContributorActivityUrl(participant) {
        if (this.provider === 'gitlab') return participant.url;
        return `https://github.com/search?q=author%3A${encodeURIComponent(participant.username)}+org%3AOWASP-BLT+type%3Apr+is%3Amerged`;
    }

    getReviewActivityUrl(participant) {
        if (this.provider === 'gitlab') return participant.url;
        return `https://github.com/search?q=reviewed-by%3A${encodeURIComponent(participant.username)}+type%3Apr`;
    }

    /**
     * Render sponsors
     */
    renderSponsors() {
        const container = document.getElementById('sponsors-list');
        if (!container) return;

        const becomeASponsorBtn = `
            <div class="dashboard-sponsor-cta">
                <button onclick="openSponsorModal()" class="blt-button blt-button-primary px-4 py-2 text-sm">
                    <i class="fas fa-handshake" aria-hidden="true"></i>
                    Become a Sponsor
                </button>
            </div>
        `;

        const prizes = Array.isArray(this.config.prizes) ? this.config.prizes : [];
        const sponsors = Array.isArray(this.config.sponsors) ? this.config.sponsors : [];

        const prizesHtml = prizes.length > 0
            ? `
                <div class="dashboard-prize-list">
                    ${prizes.map(prize => `
                        <article class="dashboard-prize-item">
                            <strong>${this.escapeHtml(prize.title || `Prize ${prize.position || ''}`.trim())}</strong>
                            <p>
                                ${prize.value ? `<span>${this.escapeHtml(prize.value)}</span> - ` : ''}
                                ${this.escapeHtml(prize.description || 'Prize details will be announced by the organizers.')}
                            </p>
                        </article>
                    `).join('')}
                </div>
            `
            : this.renderEmptyState('fa-gift', 'No prizes have been announced for this event yet.');

        // Group sponsors by level
        const levels = ['platinum', 'gold', 'silver', 'bronze', 'partner'];
        const grouped = {};
        levels.forEach(level => { grouped[level] = []; });
        sponsors.forEach(sponsor => {
            if (grouped[sponsor.level]) {
                grouped[sponsor.level].push(sponsor);
            } else {
                grouped.partner.push(sponsor);
            }
        });

        const sponsorsHtml = levels.map(level => {
            const sponsorsForLevel = grouped[level];
            if (sponsorsForLevel.length === 0) return '';

            return `
                <div class="dashboard-sponsor-list">
                    ${sponsorsForLevel.map(sponsor => {
                        const sponsorUrl = this.safeUrl(sponsor.website, '#');
                        const logoUrl = this.safeUrl(sponsor.logo, '');
                        const sponsorName = sponsor.name || 'Sponsor';
                        return `
                            <a href="${this.escapeAttribute(sponsorUrl)}" target="_blank" rel="noopener noreferrer" class="dashboard-sponsor-item">
                                ${logoUrl ? `
                                    <img src="${this.escapeAttribute(logoUrl)}" alt="${this.escapeAttribute(sponsorName)}" class="h-12 object-contain mb-2">
                                ` : `
                                    <div class="dashboard-avatar-placeholder mb-2">
                                        <span>${this.escapeHtml(sponsorName.charAt(0).toUpperCase())}</span>
                                    </div>
                                `}
                                <strong>${this.escapeHtml(sponsorName)}</strong>
                                <p>${this.escapeHtml(level)} sponsor${sponsor.amount ? ` - ${this.escapeHtml(sponsor.amount)}` : ''}</p>
                            </a>
                        `;
                    }).join('')}
                </div>
            `;
        }).join('');

        const sponsorNoteHtml = this.config.sponsorNote
            ? `<p class="dashboard-progress-label">${this.escapeHtml(this.config.sponsorNote)}</p>`
            : '';

        container.innerHTML = `
            <section aria-label="Prizes">
                <h3 class="dashboard-section-subtitle">Prizes</h3>
                ${prizesHtml}
            </section>
            <section aria-label="Sponsors" class="mt-4">
                <h3 class="dashboard-section-subtitle">Sponsors</h3>
                ${sponsorsHtml || this.renderEmptyState('fa-handshake', 'No sponsors are listed yet.')}
            </section>
            ${sponsorNoteHtml}
            ${becomeASponsorBtn}
        `;
    }

    /**
     * Update API info section in footer.
     * Since stats are pre-fetched server-side, we only show when data was last
     * refreshed. No live source-control API calls are made from the frontend.
     */
    async updateApiInfo() {
        const infoEl = document.getElementById('github-api-info');
        if (!infoEl) return;

        const lastUpdatedHtml = this.loadedAt
            ? `<span><i class="fas fa-sync-alt" aria-hidden="true"></i> Stats auto-refreshed ${this.provider === 'gitlab' ? 'daily' : 'hourly'}</span>` +
              `<span aria-hidden="true">|</span>` +
              `<span>Last updated: <span id="last-updated-time" title="${this.escapeAttribute(this.loadedAt.toLocaleString())}">${this.timeAgo(this.loadedAt)}</span></span>`
            : '';

        infoEl.innerHTML = `<div class="dashboard-freshness-row">${lastUpdatedHtml}</div>`;
        this.startLastUpdatedRefresh();
    }

    /**
     * Show loading state
     */
    showLoading() {
        ['leaderboard', 'review-leaderboard', 'repositories-list'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.setAttribute('aria-busy', 'true');
        });
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        ['leaderboard', 'review-leaderboard', 'repositories-list'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.setAttribute('aria-busy', 'false');
        });
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorEl = document.getElementById('dashboard-error');
        if (errorEl) {
            errorEl.classList.remove('hidden');
            errorEl.innerHTML = `
                <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
                <span>${this.escapeHtml(message)}</span>
            `;
        }

        const dataFreshness = document.getElementById('github-api-info');
        if (dataFreshness) {
            dataFreshness.innerHTML = `<div class="dashboard-freshness-row"><span>${this.escapeHtml(message)}</span></div>`;
        }

        const emptyMessage = 'Generated stats could not be loaded. Try again after the next scheduled data refresh.';
        const leaderboard = document.getElementById('leaderboard');
        if (leaderboard) leaderboard.innerHTML = this.renderEmptyState('fa-triangle-exclamation', emptyMessage);
        const reviewLeaderboard = document.getElementById('review-leaderboard');
        if (reviewLeaderboard) reviewLeaderboard.innerHTML = this.renderEmptyState('fa-triangle-exclamation', emptyMessage);
        const repositories = document.getElementById('repositories-list');
        if (repositories) repositories.innerHTML = this.renderEmptyState('fa-triangle-exclamation', emptyMessage);
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

    setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }

    formatDate(date) {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) return 'Date unavailable';
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    }

    formatCompactDate(date) {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '--';
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
        });
    }

    formatDateTime(date) {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) return 'Date unavailable';
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        });
    }

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    renderEmptyState(icon, message) {
        return `
            <div class="dashboard-empty-state">
                <i class="fas ${this.escapeAttribute(icon)}" aria-hidden="true"></i>
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    renderAvatar(url, username) {
        const avatarUrl = this.safeUrl(url, '');
        const label = username || 'participant';
        if (!avatarUrl) {
            return `<div class="dashboard-avatar-placeholder" aria-hidden="true">${this.escapeHtml(label.charAt(0).toUpperCase() || '?')}</div>`;
        }

        return `
            <img src="${this.escapeAttribute(avatarUrl)}"
                 alt="${this.escapeAttribute(label)} avatar"
                 width="36"
                 height="36"
                 loading="lazy">
        `;
    }

    safeUrl(value, fallback = '#') {
        if (!value || typeof value !== 'string') return fallback;

        try {
            const parsed = new URL(value, window.location.href);
            if (['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
                return parsed.href;
            }
        } catch (error) {
            return fallback;
        }

        return fallback;
    }

    getCssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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

    escapeAttribute(text) {
        return this.escapeHtml(String(text)).replace(/`/g, '&#96;');
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
