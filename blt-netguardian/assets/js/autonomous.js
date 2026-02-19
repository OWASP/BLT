/**
 * Autonomous scanning interface for BLT-NetGuardian
 */

let allDiscoveries = [];

document.addEventListener('DOMContentLoaded', function() {
    const suggestionForm = document.getElementById('suggestionForm');
    if (suggestionForm) {
        suggestionForm.addEventListener('submit', handleSuggestionSubmit);
    }

    setupDiscoverySearch();

    // Start live updates
    startLiveUpdates();

    // Load initial data
    loadScanningStatus();
    loadRecentDiscoveries();
});

async function handleSuggestionSubmit(e) {
    e.preventDefault();

    const messageDiv = document.getElementById('suggestionMessage');
    const submitButton = e.target.querySelector('button[type="submit"]');
    const suggestion = document.getElementById('suggestion').value;
    const priority = document.getElementById('priority').checked;

    messageDiv.style.display = 'none';
    submitButton.disabled = true;
    submitButton.textContent = 'Submitting...';

    try {
        const response = await apiRequest('/api/discovery/suggest', {
            method: 'POST',
            body: JSON.stringify({
                suggestion,
                priority,
                source: 'user_suggestion',
                timestamp: new Date().toISOString()
            })
        });

        if (!response.success) {
            throw new Error(response.message || 'Failed to submit suggestion');
        }

        showMessage(
            messageDiv,
            'success',
            `Thank you. "${suggestion}" was added to the discovery queue. ${priority ? 'Priority processing enabled.' : 'Standard processing enabled.'}`
        );

        document.getElementById('suggestionForm').reset();
        setTimeout(() => loadRecentDiscoveries(), 1000);
    } catch (error) {
        console.error('Suggestion submission error:', error);
        showMessage(
            messageDiv,
            'error',
            `Error: ${error.message}. The suggestion was stored locally and will be retried when backend access returns.`
        );

        queueLocalSuggestion(suggestion, priority);
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fa-solid fa-crosshairs" aria-hidden="true"></i> Suggest Target';
    }
}

async function loadScanningStatus() {
    try {
        const status = await apiRequest('/api/discovery/status');

        if (status.current_target) {
            document.getElementById('scanningTarget').innerHTML =
                `Currently scanning: <span class="highlight">${status.current_target}</span>`;
        }

        if (status.scanned_today !== undefined && status.scanned_today !== null) {
            document.getElementById('scannedCount').innerHTML =
                `Total scanned today: <span class="highlight">${status.scanned_today.toLocaleString()}</span> targets`;
        }

        if (status.vulnerabilities_found !== undefined && status.vulnerabilities_found !== null) {
            document.getElementById('foundVulns').innerHTML =
                `Vulnerabilities found: <span class="highlight critical">${status.vulnerabilities_found}</span>`;
        }

        if (status.stats) {
            updateStats(status.stats);
        }
    } catch (error) {
        console.log('Using demo data for scanning status');
        useDemoScanningStatus();
    }
}

async function loadRecentDiscoveries() {
    try {
        const response = await apiRequest('/api/discovery/recent?limit=10');

        if (response.discoveries && response.discoveries.length > 0) {
            allDiscoveries = response.discoveries;
            applyDiscoverySearch();
            return;
        }

        if (allDiscoveries.length === 0) {
            allDiscoveries = readDiscoveriesFromDom();
        }
        applyDiscoverySearch();
    } catch (error) {
        console.log('Using demo data for recent discoveries');
        if (allDiscoveries.length === 0) {
            allDiscoveries = readDiscoveriesFromDom();
        }
        applyDiscoverySearch();
    }
}

function displayDiscoveries(discoveries) {
    const container = document.getElementById('discoveriesList');
    if (!container) {
        return;
    }

    if (!discoveries.length) {
        container.innerHTML = `
            <div class="discovery-item">
                <div class="discovery-info">
                    <span class="discovery-type">Info</span>
                    <span class="discovery-target">No discoveries match the current search.</span>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = discoveries.map(discovery => {
        const vulnerabilities = discovery.vulnerabilities || [];
        const hasVulns = vulnerabilities.length > 0;
        const vulnClass = hasVulns ? 'vulnerability-found' : '';
        const statusText = getStatusText(discovery.status);

        return `
            <div class="discovery-item ${vulnClass}">
                <div class="discovery-info">
                    <span class="discovery-type">${escapeHtml(discovery.type || 'target')}</span>
                    <span class="discovery-target">${escapeHtml(discovery.target || 'unknown')}</span>
                    <span class="discovery-time">${formatTimeAgo(discovery.discovered_at)}</span>
                </div>
                <div class="discovery-status">
                    ${hasVulns ? vulnerabilities.map(v =>
                        `<span class="severity ${escapeHtml(v.severity || 'info')}">${escapeHtml(String(v.count || 0))} ${escapeHtml(v.severity || 'info')}</span>`
                    ).join('') : ''}
                    <span class="status ${escapeHtml(discovery.status || 'queued')}">${escapeHtml(statusText)}</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateStats(stats) {
    if (stats.domains_discovered !== undefined && stats.domains_discovered !== null) {
        document.getElementById('domainCount').textContent = stats.domains_discovered.toLocaleString();
    }
    if (stats.repos_found !== undefined && stats.repos_found !== null) {
        document.getElementById('repoCount').textContent = stats.repos_found.toLocaleString();
    }
    if (stats.active_scans !== undefined && stats.active_scans !== null) {
        document.getElementById('activeScans').textContent = stats.active_scans;
    }
    if (stats.contacts_made !== undefined && stats.contacts_made !== null) {
        document.getElementById('contactedCount').textContent = stats.contacts_made;
    }
}

function startLiveUpdates() {
    setInterval(loadScanningStatus, 10000);
    setInterval(loadRecentDiscoveries, 30000);
}

function useDemoScanningStatus() {
    const targetElement = document.getElementById('scanningTarget');
    if (!targetElement) {
        return;
    }

    const targets = [
        'example.com',
        'newstartup.io',
        'github.com/trending',
        'crypto-exchange.io',
        'open-api.dev'
    ];

    let currentIndex = 0;
    setInterval(() => {
        currentIndex = (currentIndex + 1) % targets.length;
        targetElement.innerHTML = `Currently scanning: <span class="highlight">${targets[currentIndex]}</span>`;
    }, 5000);
}

function queueLocalSuggestion(suggestion, priority) {
    const suggestions = JSON.parse(localStorage.getItem('pendingSuggestions') || '[]');
    suggestions.push({
        suggestion,
        priority,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem('pendingSuggestions', JSON.stringify(suggestions));
}

function formatTimeAgo(timestamp) {
    if (!timestamp) {
        return 'just now';
    }

    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (Number.isNaN(seconds) || seconds < 0) {
        return 'just now';
    }
    if (seconds < 60) return `${seconds} seconds ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    return `${Math.floor(seconds / 86400)} days ago`;
}

function getStatusText(status) {
    const statusMap = {
        queued: 'Queued for scan',
        running: 'Scanning...',
        completed: 'Scan complete',
        contacted: 'Contact attempted',
        failed: 'Scan failed'
    };
    return statusMap[status] || String(status || 'queued');
}

function showMessage(element, type, message) {
    element.className = `message ${type}`;
    element.textContent = message;
    element.style.display = 'block';
}

function viewDiscoveryQueue() {
    window.location.href = 'dashboard.html?view=discovery';
}

function viewContactLog() {
    window.location.href = 'dashboard.html?view=contacts';
}

function setupDiscoverySearch() {
    const discoverySearch = document.getElementById('discoverySearch');
    if (!discoverySearch) {
        return;
    }

    discoverySearch.addEventListener('input', applyDiscoverySearch);
}

function applyDiscoverySearch() {
    const discoverySearch = document.getElementById('discoverySearch');
    if (!discoverySearch) {
        return;
    }

    const query = discoverySearch.value.trim().toLowerCase();

    if (allDiscoveries.length > 0) {
        const filtered = allDiscoveries.filter(discovery => {
            const typeText = String(discovery.type || '').toLowerCase();
            const targetText = String(discovery.target || '').toLowerCase();
            return typeText.includes(query) || targetText.includes(query);
        });
        displayDiscoveries(filtered);
        return;
    }

    const items = Array.from(document.querySelectorAll('#discoveriesList .discovery-item'));
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(query) ? '' : 'none';
    });
}

function readDiscoveriesFromDom() {
    const items = Array.from(document.querySelectorAll('#discoveriesList .discovery-item'));
    return items.map(item => {
        const type = item.querySelector('.discovery-type')?.textContent?.trim() || 'target';
        const target = item.querySelector('.discovery-target')?.textContent?.trim() || 'unknown';
        const statusElement = item.querySelector('.status');
        const statusClass = Array.from(statusElement?.classList || []).find(cls => !['status'].includes(cls)) || 'queued';

        return {
            type,
            target,
            discovered_at: new Date().toISOString(),
            status: statusClass,
            vulnerabilities: []
        };
    });
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

window.viewDiscoveryQueue = viewDiscoveryQueue;
window.viewContactLog = viewContactLog;
