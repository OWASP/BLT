/**
 * Index Page Logic
 * Displays the all-events contribution hub.
 */

class HackathonIndex {
    constructor(config) {
        this.config = config || {};
        this.currentFilter = 'all';
        this.hackathonStats = {};
        this.loadedSummaries = 0;
        this.loadedAt = null;
    }

    /**
     * Initialize the index page.
     */
    async init() {
        this.loadedAt = new Date();
        const global = this.config.global || {};
        const siteTitle = document.getElementById('site-title');

        if (global.siteName && siteTitle) {
            siteTitle.textContent = String(global.siteName);
            document.title = `${String(global.siteName)} - OWASP BLT Contribution Events`;
        }

        await this.loadAllStats();
        this.renderPlatformStats();
        this.renderFeaturedEvent();
        this.renderHackathons();
    }

    /**
     * Return configured hackathons as a defensive copy.
     */
    getHackathons() {
        return Array.isArray(this.config.hackathons) ? [...this.config.hackathons] : [];
    }

    /**
     * Load pre-fetched stats for all hackathons.
     */
    async loadAllStats() {
        const fetches = this.getHackathons().map(async hackathon => {
            const slug = String(hackathon.slug || '').trim();
            if (!slug) return;

            try {
                const response = await fetch(`hackathon-data/${encodeURIComponent(slug)}-summary.json`);
                if (!response.ok) {
                    this.hackathonStats[slug] = this.buildStats(hackathon, null, false);
                    return;
                }

                const summary = await response.json();
                this.hackathonStats[slug] = this.buildStats(hackathon, summary, true);
                this.loadedSummaries += 1;
            } catch (error) {
                console.warn(`Failed to load stats for ${slug}:`, error);
                this.hackathonStats[slug] = this.buildStats(hackathon, null, false);
            }
        });

        await Promise.all(fetches);
    }

    /**
     * Normalize summary values into safe display stats.
     */
    buildStats(hackathon, summary, summaryAvailable) {
        const safeSummary = summary && typeof summary === 'object' ? summary : {};
        const topContributors = Array.isArray(safeSummary.topContributors)
            ? safeSummary.topContributors.slice(0, 4).map(rawContributor => {
                const contributor = rawContributor && typeof rawContributor === 'object' ? rawContributor : {};
                return {
                    username: String(contributor.username || 'Contributor'),
                    avatar: this.safeUrl(contributor.avatar, ''),
                    url: this.safeUrl(contributor.url, '#'),
                    mergedCount: this.toSafeInteger(contributor.mergedCount),
                };
            })
            : [];

        return {
            participantCount: this.toSafeInteger(safeSummary.participantCount),
            totalPRs: this.toSafeInteger(safeSummary.totalPRs),
            mergedPRs: this.toSafeInteger(safeSummary.mergedPRs),
            totalIssues: this.toSafeInteger(safeSummary.totalIssues),
            repositories: this.toSafeInteger(safeSummary.repositories),
            topContributors,
            daysActive: this.calculateDaysActive(hackathon),
            summaryAvailable,
        };
    }

    /**
     * Calculate elapsed active days from config dates.
     */
    calculateDaysActive(hackathon) {
        const startDate = new Date(hackathon.startTime);
        const endDate = new Date(hackathon.endTime);

        if (!this.isValidDate(startDate) || !this.isValidDate(endDate)) {
            return 0;
        }

        const now = new Date();
        const effectiveEnd = now < endDate ? now : endDate;

        if (now < startDate) {
            return 0;
        }

        return Math.max(0, Math.floor((effectiveEnd - startDate) / (1000 * 60 * 60 * 24)));
    }

    /**
     * Get status of a hackathon.
     */
    getHackathonStatus(hackathon) {
        const now = new Date();
        const startDate = new Date(hackathon.startTime);
        const endDate = new Date(hackathon.endTime);

        if (!this.isValidDate(startDate) || !this.isValidDate(endDate)) {
            return {
                status: 'upcoming',
                label: 'Schedule pending',
                class: 'blt-status blt-status--upcoming',
            };
        }

        if (now < startDate) {
            return {
                status: 'upcoming',
                label: 'Upcoming',
                class: 'blt-status blt-status--upcoming',
            };
        }

        if (now > endDate) {
            return {
                status: 'ended',
                label: 'Ended',
                class: 'blt-status blt-status--ended',
            };
        }

        return {
            status: 'ongoing',
            label: 'Ongoing',
            class: 'blt-status blt-status--ongoing',
        };
    }

    /**
     * Sort hackathons: ongoing first, then upcoming, then ended.
     */
    getSortedHackathons(hackathons = this.getHackathons()) {
        const statusOrder = { ongoing: 0, upcoming: 1, ended: 2 };

        return [...hackathons].sort((a, b) => {
            const statusA = this.getHackathonStatus(a);
            const statusB = this.getHackathonStatus(b);
            const orderA = statusOrder[statusA.status] ?? 3;
            const orderB = statusOrder[statusB.status] ?? 3;

            if (orderA !== orderB) {
                return orderA - orderB;
            }

            if (statusA.status === 'ended') {
                return new Date(b.endTime) - new Date(a.endTime);
            }

            return new Date(a.startTime) - new Date(b.startTime);
        });
    }

    /**
     * Pick the most relevant active/upcoming event, falling back to recent ended events.
     */
    getFeaturedHackathon() {
        const sorted = this.getSortedHackathons();
        return sorted.find(hackathon => {
            const status = this.getHackathonStatus(hackathon).status;
            return status === 'ongoing' || status === 'upcoming';
        }) || sorted[0] || null;
    }

    /**
     * Format date range for display.
     */
    formatDateRange(startTime, endTime) {
        const startDate = new Date(startTime);
        const endDate = new Date(endTime);
        const options = { year: 'numeric', month: 'short', day: 'numeric' };

        if (!this.isValidDate(startDate) || !this.isValidDate(endDate)) {
            return 'Dates to be announced';
        }

        return `${startDate.toLocaleDateString('en-US', options)} - ${endDate.toLocaleDateString('en-US', options)}`;
    }

    /**
     * Get time remaining for upcoming or ongoing hackathons.
     */
    getTimeRemaining(hackathon) {
        const now = new Date();
        const startDate = new Date(hackathon.startTime);
        const endDate = new Date(hackathon.endTime);

        if (!this.isValidDate(startDate) || !this.isValidDate(endDate)) {
            return 'Schedule pending';
        }

        if (now < startDate) {
            const daysUntil = Math.ceil((startDate - now) / (1000 * 60 * 60 * 24));
            return `Starts in ${daysUntil} day${daysUntil !== 1 ? 's' : ''}`;
        }

        if (now <= endDate) {
            const remaining = endDate - now;
            const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
            const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

            if (days > 0) {
                return `${days} day${days !== 1 ? 's' : ''} remaining`;
            }

            if (hours > 0) {
                return `${hours} hour${hours !== 1 ? 's' : ''} remaining`;
            }

            return 'Ending soon';
        }

        return 'Ended';
    }

    /**
     * Render the platform stats band from loaded summaries.
     */
    renderPlatformStats() {
        const container = document.getElementById('platform-stats-grid');
        if (!container) return;

        const stats = this.aggregatePlatformStats();
        const cards = [
            { label: 'Events tracked', value: stats.events },
            { label: 'Pull requests', value: stats.totalPRs },
            { label: 'Merged PRs', value: stats.mergedPRs },
            { label: 'Participants', value: stats.participants },
            { label: 'Repositories', value: stats.repositories },
        ];

        container.innerHTML = cards.map(card => `
            <div class="blt-stat-card">
                <span>${this.formatNumber(card.value)}</span>
                <p>${this.escapeHtml(card.label)}</p>
            </div>
        `).join('');

        this.updateSnapshotStat('events', stats.events);
        this.updateSnapshotStat('participants', stats.participants);
        this.updateSnapshotStat('prs', stats.totalPRs);
    }

    /**
     * Aggregate platform stats.
     */
    aggregatePlatformStats() {
        const hackathons = this.getHackathons();
        const statsList = hackathons
            .map(hackathon => this.hackathonStats[hackathon.slug])
            .filter(Boolean);
        const repositoryFallback = new Set();

        hackathons.forEach(hackathon => {
            const repositories = hackathon.github && Array.isArray(hackathon.github.repositories)
                ? hackathon.github.repositories
                : [];
            repositories.forEach(repository => repositoryFallback.add(String(repository)));
        });

        const totals = statsList.reduce((accumulator, stats) => ({
            participants: accumulator.participants + stats.participantCount,
            totalPRs: accumulator.totalPRs + stats.totalPRs,
            mergedPRs: accumulator.mergedPRs + stats.mergedPRs,
            totalIssues: accumulator.totalIssues + stats.totalIssues,
            repositories: Math.max(accumulator.repositories, stats.repositories),
        }), {
            participants: 0,
            totalPRs: 0,
            mergedPRs: 0,
            totalIssues: 0,
            repositories: 0,
        });

        return {
            ...totals,
            events: hackathons.length,
            activeOrUpcoming: hackathons.filter(hackathon => {
                const status = this.getHackathonStatus(hackathon).status;
                return status === 'ongoing' || status === 'upcoming';
            }).length,
            summaryCount: this.loadedSummaries,
            repositories: totals.repositories || repositoryFallback.size,
        };
    }

    /**
     * Update hero snapshot stat if the element exists.
     */
    updateSnapshotStat(name, value) {
        const element = document.querySelector(`[data-platform-stat="${name}"]`);
        if (element) {
            element.textContent = this.formatNumber(value);
        }
    }

    /**
     * Render the featured active/upcoming event panel.
     */
    renderFeaturedEvent() {
        const container = document.getElementById('featured-event-content');
        if (!container) return;

        const hackathon = this.getFeaturedHackathon();
        if (!hackathon) {
            container.innerHTML = `
                <div class="p-6 text-center text-gray-600">
                    <i class="fas fa-calendar-times text-4xl text-gray-300" aria-hidden="true"></i>
                    <p class="mt-3">No contribution events are configured yet.</p>
                </div>
            `;
            return;
        }

        const status = this.getHackathonStatus(hackathon);
        const stats = this.getStatsFor(hackathon);
        const dateRange = this.formatDateRange(hackathon.startTime, hackathon.endTime);
        const timeRemaining = this.getTimeRemaining(hackathon);
        const description = this.getDescriptionPreview(hackathon.description, 260);
        const detailUrl = `hackathon.html?slug=${encodeURIComponent(hackathon.slug)}`;

        container.innerHTML = `
            <div class="blt-featured-layout">
                ${this.renderEventMedia(hackathon, status, true)}
                <div class="blt-featured-copy">
                    <div>
                        <span class="${status.class}">${this.escapeHtml(status.label)}</span>
                        <h3 class="mt-4 text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">${this.escapeHtml(hackathon.name)}</h3>
                        <p class="mt-3 text-base leading-7 text-gray-600">${this.escapeHtml(description)}</p>
                    </div>
                    <div>
                        <div class="mb-4 grid gap-3 text-sm text-gray-600 sm:grid-cols-2">
                            <div><i class="far fa-calendar mr-2 text-red-600" aria-hidden="true"></i>${this.escapeHtml(dateRange)}</div>
                            <div><i class="far fa-clock mr-2 text-red-600" aria-hidden="true"></i>${this.escapeHtml(timeRemaining)}</div>
                            ${hackathon.organizer ? `<div class="sm:col-span-2"><i class="fas fa-users mr-2 text-red-600" aria-hidden="true"></i>Organized by ${this.escapeHtml(hackathon.organizer)}</div>` : ''}
                        </div>
                        ${this.renderStatsGrid(stats, true)}
                        ${this.renderSummaryNote(stats)}
                        <a href="${this.escapeHtml(detailUrl)}" class="blt-button blt-button-primary mt-5 px-5 py-3">
                            View event dashboard
                            <i class="fas fa-arrow-right" aria-hidden="true"></i>
                        </a>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render all hackathons.
     */
    renderHackathons(filter = 'all') {
        const allowedFilters = new Set(['all', 'ongoing', 'upcoming', 'ended']);
        this.currentFilter = allowedFilters.has(filter) ? filter : 'all';

        const container = document.getElementById('hackathons-grid');
        const noHackathonsMsg = document.getElementById('no-hackathons');
        if (!container || !noHackathonsMsg) return;

        let hackathons = this.getSortedHackathons();

        if (this.currentFilter !== 'all') {
            hackathons = hackathons.filter(hackathon => {
                const status = this.getHackathonStatus(hackathon);
                return status.status === this.currentFilter;
            });
        }

        if (hackathons.length === 0) {
            container.classList.add('hidden');
            noHackathonsMsg.classList.remove('hidden');
            return;
        }

        container.classList.remove('hidden');
        noHackathonsMsg.classList.add('hidden');

        container.innerHTML = hackathons.map(hackathon => this.renderHackathonCard(hackathon)).join('');
    }

    /**
     * Render a single event card.
     */
    renderHackathonCard(hackathon) {
        const status = this.getHackathonStatus(hackathon);
        const dateRange = this.formatDateRange(hackathon.startTime, hackathon.endTime);
        const timeRemaining = this.getTimeRemaining(hackathon);
        const description = this.getDescriptionPreview(hackathon.description, 170);
        const stats = this.getStatsFor(hackathon);
        const detailUrl = `hackathon.html?slug=${encodeURIComponent(hackathon.slug)}`;

        return `
            <article class="hackathon-card" data-status="${this.escapeHtml(status.status)}">
                ${this.renderEventMedia(hackathon, status, false)}
                <div class="blt-event-body">
                    <div>
                        <h3 class="text-xl font-bold leading-tight text-gray-900">${this.escapeHtml(hackathon.name)}</h3>
                        <div class="mt-3 grid gap-2 text-sm text-gray-600">
                            ${hackathon.organizer ? `<div><i class="fas fa-users mr-2 text-red-600" aria-hidden="true"></i>${this.escapeHtml(hackathon.organizer)}</div>` : ''}
                            <div><i class="far fa-calendar mr-2 text-red-600" aria-hidden="true"></i>${this.escapeHtml(dateRange)}</div>
                            <div><i class="far fa-clock mr-2 text-red-600" aria-hidden="true"></i>${this.escapeHtml(timeRemaining)}</div>
                        </div>
                        <p class="blt-line-clamp mt-4 text-sm leading-6 text-gray-600">${this.escapeHtml(description)}</p>
                    </div>

                    <div>
                        ${this.renderStatsGrid(stats, false)}
                        ${this.renderSummaryNote(stats)}
                    </div>

                    ${this.renderTopContributors(stats)}

                    <a href="${this.escapeHtml(detailUrl)}"
                       class="blt-button blt-button-primary mt-auto px-4 py-2.5 text-sm">
                        View details
                        <i class="fas fa-arrow-right" aria-hidden="true"></i>
                    </a>
                </div>
            </article>
        `;
    }

    /**
     * Render event media with a status badge.
     */
    renderEventMedia(hackathon, status, featured) {
        const imageUrl = this.safeUrl(hackathon.bannerImage, '');
        const name = String(hackathon.name || 'Contribution event');
        const mediaClass = featured ? 'blt-featured-media' : 'blt-event-media';

        if (imageUrl) {
            return `
                <div class="${mediaClass}">
                    <img src="${this.escapeHtml(imageUrl)}" alt="${this.escapeHtml(name)} banner" loading="lazy">
                    ${featured ? '' : `<span class="${status.class}">${this.escapeHtml(status.label)}</span>`}
                </div>
            `;
        }

        return `
            <div class="${mediaClass} flex items-center justify-center text-white">
                <div class="text-center">
                    <i class="fas fa-code-branch text-4xl" aria-hidden="true"></i>
                    <p class="mt-3 text-sm font-bold uppercase tracking-widest">Contribution event</p>
                </div>
                ${featured ? '' : `<span class="${status.class}">${this.escapeHtml(status.label)}</span>`}
            </div>
        `;
    }

    /**
     * Render compact stats for an event.
     */
    renderStatsGrid(stats, featured) {
        const cells = featured
            ? [
                ['Participants', stats.participantCount],
                ['Pull requests', stats.totalPRs],
                ['Merged PRs', stats.mergedPRs],
            ]
            : [
                ['Participants', stats.participantCount],
                ['Merged PRs', stats.mergedPRs],
                ['Days active', stats.daysActive],
            ];

        return `
            <div class="blt-event-stat-grid">
                ${cells.map(([label, value]) => `
                    <div class="blt-event-stat">
                        <strong>${this.formatNumber(value)}</strong>
                        <span>${this.escapeHtml(label)}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Render a short missing-summary note.
     */
    renderSummaryNote(stats) {
        if (stats.summaryAvailable) {
            return '';
        }

        return '<p class="mt-3 text-xs font-medium text-gray-500">Generated summary data is not available yet.</p>';
    }

    /**
     * Render top contributor avatars when summary data includes them.
     */
    renderTopContributors(stats) {
        if (!stats.topContributors.length) {
            return '';
        }

        return `
            <div class="blt-top-contributors">
                <span class="text-xs font-bold uppercase tracking-wide text-gray-500">Top contributors</span>
                <div class="flex -space-x-2">
                    ${stats.topContributors.map(contributor => {
                        const username = String(contributor.username || 'Contributor');
                        const fallbackAvatar = `https://github.com/identicons/${encodeURIComponent(username)}.png`;
                        const avatar = contributor.avatar || fallbackAvatar;
                        const url = contributor.url || '#';
                        const title = `${username} - ${this.formatNumber(contributor.mergedCount)} merged PR${contributor.mergedCount !== 1 ? 's' : ''}`;

                        return `
                            <a href="${this.escapeHtml(url)}" target="_blank" rel="noopener noreferrer" title="${this.escapeHtml(title)}">
                                <img src="${this.escapeHtml(avatar)}"
                                     alt="${this.escapeHtml(username)}"
                                     class="blt-top-contributor-avatar"
                                     loading="lazy"
                                     onerror="this.onerror=null;this.src='https://github.com/identicons/anonymous.png';">
                            </a>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Get normalized stats for a hackathon.
     */
    getStatsFor(hackathon) {
        const slug = String(hackathon.slug || '').trim();
        return this.hackathonStats[slug] || this.buildStats(hackathon, null, false);
    }

    /**
     * Update info section in footer with static summary status.
     */
    updateApiInfo() {
        const infoEl = document.getElementById('github-api-info');
        if (!infoEl) return;

        const stats = this.aggregatePlatformStats();
        const summaryLabel = `${this.formatNumber(stats.summaryCount)} generated summar${stats.summaryCount === 1 ? 'y' : 'ies'} loaded`;
        const eventLabel = `${this.formatNumber(stats.activeOrUpcoming)} active or upcoming event${stats.activeOrUpcoming === 1 ? '' : 's'}`;
        const lastUpdatedHtml = this.loadedAt
            ? `<span class="text-gray-400">|</span><span>Updated <span id="last-updated-time" title="${this.escapeHtml(this.loadedAt.toLocaleString())}">${this.timeAgo(this.loadedAt)}</span></span>`
            : '';

        infoEl.innerHTML = `
            <div class="flex flex-wrap items-center justify-center gap-2">
                <span>${this.escapeHtml(summaryLabel)}</span>
                <span class="text-gray-400">|</span>
                <span>${this.escapeHtml(eventLabel)}</span>
                ${lastUpdatedHtml}
            </div>
        `;
        this.startLastUpdatedRefresh();
    }

    /**
     * Start periodic refresh of the "last updated" relative time in the footer.
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
     * Return a human-readable relative time string.
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
     * Return a short text preview without cutting mid-word when possible.
     */
    getDescriptionPreview(description, maxLength) {
        const text = String(description || '').replace(/\s+/g, ' ').trim();
        if (text.length <= maxLength) {
            return text;
        }

        const truncated = text.slice(0, maxLength).trim();
        const lastSpace = truncated.lastIndexOf(' ');
        const preview = lastSpace > 80 ? truncated.slice(0, lastSpace) : truncated;
        return `${preview}...`;
    }

    /**
     * Convert API/config numeric values into safe non-negative integers.
     */
    toSafeInteger(value) {
        const number = Number(value);
        if (!Number.isFinite(number) || number < 0) {
            return 0;
        }

        return Math.floor(number);
    }

    /**
     * Format numbers consistently.
     */
    formatNumber(value) {
        return this.toSafeInteger(value).toLocaleString();
    }

    /**
     * Validate date objects.
     */
    isValidDate(date) {
        return date instanceof Date && Number.isFinite(date.getTime());
    }

    /**
     * Escape HTML to prevent XSS.
     */
    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, character => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        })[character]);
    }

    /**
     * Allow only browser-safe URL protocols and relative URLs.
     */
    safeUrl(value, fallback = '#') {
        const raw = String(value || '').trim();
        if (!raw || /[\u0000-\u001F\u007F<>"']/u.test(raw)) {
            return fallback;
        }

        if (/^(javascript|data|vbscript):/i.test(raw)) {
            return fallback;
        }

        try {
            const base = typeof window !== 'undefined' ? window.location.href : 'https://example.invalid/';
            const parsed = new URL(raw, base);
            if (['http:', 'https:', 'file:'].includes(parsed.protocol)) {
                return raw;
            }
        } catch (error) {
            return fallback;
        }

        return fallback;
    }
}

/**
 * Filter hackathons by status.
 */
function filterHackathons(status) {
    const allowedFilters = new Set(['all', 'ongoing', 'upcoming', 'ended']);
    const nextStatus = allowedFilters.has(status) ? status : 'all';

    document.querySelectorAll('.filter-btn').forEach(button => {
        const isActive = button.dataset.filter === nextStatus;
        button.classList.toggle('is-active', isActive);
        button.setAttribute('aria-pressed', String(isActive));
    });

    if (window.hackathonIndex) {
        window.hackathonIndex.renderHackathons(nextStatus);
    }
}

// Initialize when DOM is loaded.
document.addEventListener('DOMContentLoaded', async () => {
    window.hackathonIndex = new HackathonIndex(HACKATHONS_CONFIG);
    await window.hackathonIndex.init();
    window.hackathonIndex.updateApiInfo();
});
