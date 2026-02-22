/**
 * Index Page Logic
 * Displays list of all hackathons
 */

class HackathonIndex {
    constructor(config) {
        this.config = config;
        this.currentFilter = 'all';
    }

    /**
     * Initialize the index page
     */
    init() {
        const global = this.config.global || {};
        
        // Update site title
        if (global.siteName) {
            document.getElementById('site-title').textContent = global.siteName;
            document.getElementById('hero-title').textContent = global.siteName;
            document.title = global.siteName;
        }

        if (global.siteDescription) {
            document.getElementById('hero-description').textContent = global.siteDescription;
        }

        // Render hackathons
        this.renderHackathons();
    }

    /**
     * Get status of a hackathon
     */
    getHackathonStatus(hackathon) {
        const now = new Date();
        const startDate = new Date(hackathon.startTime);
        const endDate = new Date(hackathon.endTime);

        if (now < startDate) {
            return {
                status: 'upcoming',
                label: 'Upcoming',
                class: 'bg-blue-100 text-blue-800'
            };
        } else if (now > endDate) {
            return {
                status: 'ended',
                label: 'Ended',
                class: 'bg-gray-100 text-gray-800'
            };
        } else {
            return {
                status: 'ongoing',
                label: 'Ongoing',
                class: 'bg-green-100 text-green-800'
            };
        }
    }

    /**
     * Format date range for display
     */
    formatDateRange(startTime, endTime) {
        const startDate = new Date(startTime);
        const endDate = new Date(endTime);
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        
        return `${startDate.toLocaleDateString('en-US', options)} - ${endDate.toLocaleDateString('en-US', options)}`;
    }

    /**
     * Get time remaining for upcoming or ongoing hackathons
     */
    getTimeRemaining(hackathon) {
        const now = new Date();
        const startDate = new Date(hackathon.startTime);
        const endDate = new Date(hackathon.endTime);

        if (now < startDate) {
            const daysUntil = Math.ceil((startDate - now) / (1000 * 60 * 60 * 24));
            return `Starts in ${daysUntil} day${daysUntil !== 1 ? 's' : ''}`;
        } else if (now <= endDate) {
            const remaining = endDate - now;
            const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
            const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            
            if (days > 0) {
                return `${days} day${days !== 1 ? 's' : ''} remaining`;
            } else if (hours > 0) {
                return `${hours} hour${hours !== 1 ? 's' : ''} remaining`;
            } else {
                return 'Ending soon';
            }
        } else {
            return 'Ended';
        }
    }

    /**
     * Render all hackathons
     */
    renderHackathons(filter = 'all') {
        this.currentFilter = filter;
        const container = document.getElementById('hackathons-grid');
        const noHackathonsMsg = document.getElementById('no-hackathons');
        
        let hackathons = this.config.hackathons;
        
        // Filter hackathons
        if (filter !== 'all') {
            hackathons = hackathons.filter(h => {
                const status = this.getHackathonStatus(h);
                return status.status === filter;
            });
        }

        if (hackathons.length === 0) {
            container.classList.add('hidden');
            noHackathonsMsg.classList.remove('hidden');
            return;
        }

        container.classList.remove('hidden');
        noHackathonsMsg.classList.add('hidden');

        // Sort hackathons: ongoing first, then upcoming, then ended
        hackathons.sort((a, b) => {
            const statusA = this.getHackathonStatus(a);
            const statusB = this.getHackathonStatus(b);
            
            const statusOrder = { ongoing: 0, upcoming: 1, ended: 2 };
            const orderA = statusOrder[statusA.status];
            const orderB = statusOrder[statusB.status];
            
            if (orderA !== orderB) {
                return orderA - orderB;
            }
            
            // If same status, sort by date (most recent first for ended, earliest first for others)
            if (statusA.status === 'ended') {
                return new Date(b.endTime) - new Date(a.endTime);
            } else {
                return new Date(a.startTime) - new Date(b.startTime);
            }
        });

        container.innerHTML = hackathons.map(hackathon => {
            const status = this.getHackathonStatus(hackathon);
            const dateRange = this.formatDateRange(hackathon.startTime, hackathon.endTime);
            const timeRemaining = this.getTimeRemaining(hackathon);
            // Count repositories - show appropriate message for organization-based tracking
            const explicitRepoCount = hackathon.github.repositories?.length || 0;
            const hasOrganization = !!hackathon.github.organization;
            const repoCount = hasOrganization ? `All repos in ${hackathon.github.organization}` : explicitRepoCount;
            const descriptionTrimmed = hackathon.description.trim();
            const descriptionPreview = descriptionTrimmed.substring(0, 150);
            const needsEllipsis = descriptionTrimmed.length > 150;

            return `
                <div class="hackathon-card bg-white rounded-lg shadow-lg overflow-hidden" data-status="${status.status}">
                    ${hackathon.bannerImage ? `
                    <div class="h-48 bg-cover bg-center relative" style="background-image: url('${hackathon.bannerImage}');">
                        <div class="absolute top-4 right-4">
                            <span class="px-3 py-1 rounded-full text-sm font-medium ${status.class}">
                                ${status.label}
                            </span>
                        </div>
                    </div>
                    ` : `
                    <div class="bg-gradient-to-r from-red-600 to-red-800 p-6 text-white">
                        <div class="flex justify-between items-start mb-2">
                            <h3 class="text-xl font-bold flex-grow">${this.escapeHtml(hackathon.name)}</h3>
                            <span class="px-3 py-1 rounded-full text-sm font-medium ${status.class}">
                                ${status.label}
                            </span>
                        </div>
                        <p class="text-sm opacity-90">
                            <i class="far fa-calendar mr-1"></i>
                            ${dateRange}
                        </p>
                        <p class="text-sm mt-1 opacity-90">
                            <i class="far fa-clock mr-1"></i>
                            ${timeRemaining}
                        </p>
                    </div>
                    `}
                    
                    <div class="p-6">
                        ${hackathon.bannerImage ? `
                        <h3 class="text-xl font-bold mb-2 text-gray-900">${this.escapeHtml(hackathon.name)}</h3>
                        ` : ''}
                        ${hackathon.organizer ? `
                        <div class="flex items-center text-sm text-gray-500 mb-2">
                            <i class="fas fa-users mr-2"></i>
                            <span>Organized by ${this.escapeHtml(hackathon.organizer)}</span>
                        </div>
                        ` : ''}
                        ${hackathon.bannerImage ? `
                        <div class="flex items-center text-sm text-gray-600 mb-2">
                            <i class="far fa-calendar mr-2"></i>
                            <span>${dateRange}</span>
                        </div>
                        <div class="flex items-center text-sm text-gray-600 mb-4">
                            <i class="far fa-clock mr-2"></i>
                            <span>${timeRemaining}</span>
                        </div>
                        ` : ''}
                        <p class="text-gray-700 mb-4 line-clamp-3">
                            ${this.escapeHtml(descriptionPreview)}${needsEllipsis ? '...' : ''}
                        </p>
                        
                        <div class="flex items-center text-sm text-gray-600 mb-2">
                            <i class="fas fa-code-branch mr-2"></i>
                            <span>${typeof repoCount === 'string' ? repoCount : `${repoCount} repositor${repoCount !== 1 ? 'ies' : 'y'}`}</span>
                        </div>
                        
                        ${hackathon.contributors !== undefined ? `
                        <div class="flex items-center text-sm text-gray-600 mb-4">
                            <i class="fas fa-user-friends mr-2"></i>
                            <span>${hackathon.contributors} contributor${hackathon.contributors !== 1 ? 's' : ''}</span>
                        </div>
                        ` : '<div class="mb-4"></div>'}
                        
                        <a href="hackathon.html?slug=${encodeURIComponent(hackathon.slug)}" 
                           class="block w-full text-center px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition">
                            View Details
                            <i class="fas fa-arrow-right ml-2"></i>
                        </a>
                    </div>
                </div>
            `;
        }).join('');
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

/**
 * Filter hackathons by status
 */
function filterHackathons(status) {
    // Update button styles
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.dataset.filter === status) {
            btn.className = 'filter-btn px-4 py-2 rounded-lg bg-red-600 text-white font-medium';
        } else {
            btn.className = 'filter-btn px-4 py-2 rounded-lg bg-gray-200 text-gray-700 font-medium hover:bg-gray-300';
        }
    });

    // Re-render with filter
    window.hackathonIndex.renderHackathons(status);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.hackathonIndex = new HackathonIndex(HACKATHONS_CONFIG);
    window.hackathonIndex.init();
});
