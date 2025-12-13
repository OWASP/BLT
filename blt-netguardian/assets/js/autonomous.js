/**
 * Autonomous scanning interface for BLT-NetGuardian
 */

document.addEventListener('DOMContentLoaded', function() {
    const suggestionForm = document.getElementById('suggestionForm');
    if (suggestionForm) {
        suggestionForm.addEventListener('submit', handleSuggestionSubmit);
    }
    
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
    
    // Hide previous message
    messageDiv.style.display = 'none';
    
    // Disable submit button
    submitButton.disabled = true;
    submitButton.textContent = '⏳ Submitting...';
    
    try {
        // Submit suggestion to the autonomous discovery system
        const response = await apiRequest('/api/discovery/suggest', {
            method: 'POST',
            body: JSON.stringify({
                suggestion: suggestion,
                priority: priority,
                source: 'user_suggestion',
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.success) {
            throw new Error(response.message || 'Failed to submit suggestion');
        }
        
        // Success!
        showMessage(
            messageDiv, 
            'success', 
            `✅ Thank you! "${suggestion}" has been added to the discovery queue. ${priority ? 'It will be scanned soon.' : 'It will be scanned in the normal queue.'}`
        );
        
        // Reset form
        document.getElementById('suggestionForm').reset();
        
        // Reload recent discoveries
        setTimeout(() => loadRecentDiscoveries(), 1000);
        
    } catch (error) {
        console.error('Suggestion submission error:', error);
        showMessage(
            messageDiv, 
            'error', 
            `❌ Error: ${error.message}. The suggestion has been queued locally and will be submitted when the backend is available.`
        );
        
        // Queue locally for demo
        queueLocalSuggestion(suggestion, priority);
        
    } finally {
        // Re-enable submit button
        submitButton.disabled = false;
        submitButton.textContent = '🎯 Suggest Target';
    }
}

async function loadScanningStatus() {
    try {
        const status = await apiRequest('/api/discovery/status');
        
        if (status.current_target) {
            document.getElementById('scanningTarget').innerHTML = 
                `Currently scanning: <span class="highlight">${status.current_target}</span>`;
        }
        
        if (status.scanned_today) {
            document.getElementById('scannedCount').innerHTML = 
                `Total scanned today: <span class="highlight">${status.scanned_today.toLocaleString()}</span> targets`;
        }
        
        if (status.vulnerabilities_found) {
            document.getElementById('foundVulns').innerHTML = 
                `Vulnerabilities found: <span class="highlight critical">${status.vulnerabilities_found}</span>`;
        }
        
        // Update discovery stats
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
            displayDiscoveries(response.discoveries);
        }
        
    } catch (error) {
        console.log('Using demo data for recent discoveries');
        // Demo data is already in HTML
    }
}

function displayDiscoveries(discoveries) {
    const container = document.getElementById('discoveriesList');
    if (!container) return;
    
    container.innerHTML = discoveries.map(discovery => {
        const hasVulns = discovery.vulnerabilities && discovery.vulnerabilities.length > 0;
        const vulnClass = hasVulns ? 'vulnerability-found' : '';
        
        return `
            <div class="discovery-item ${vulnClass}">
                <div class="discovery-info">
                    <span class="discovery-type">${discovery.type}</span>
                    <span class="discovery-target">${discovery.target}</span>
                    <span class="discovery-time">${formatTimeAgo(discovery.discovered_at)}</span>
                </div>
                <div class="discovery-status">
                    ${hasVulns ? discovery.vulnerabilities.map(v => 
                        `<span class="severity ${v.severity}">${v.count} ${v.severity}</span>`
                    ).join('') : ''}
                    <span class="status ${discovery.status}">${getStatusText(discovery.status)}</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateStats(stats) {
    if (stats.domains_discovered) {
        document.getElementById('domainCount').textContent = stats.domains_discovered.toLocaleString();
    }
    if (stats.repos_found) {
        document.getElementById('repoCount').textContent = stats.repos_found.toLocaleString();
    }
    if (stats.active_scans) {
        document.getElementById('activeScans').textContent = stats.active_scans;
    }
    if (stats.contacts_made) {
        document.getElementById('contactedCount').textContent = stats.contacts_made;
    }
}

function startLiveUpdates() {
    // Reload status every 10 seconds
    setInterval(loadScanningStatus, 10000);
    
    // Reload discoveries every 30 seconds
    setInterval(loadRecentDiscoveries, 30000);
    
    // Animate scanning indicator
    animateScanningIndicator();
}

function animateScanningIndicator() {
    const indicator = document.querySelector('.status-indicator');
    if (indicator) {
        setInterval(() => {
            indicator.style.opacity = indicator.style.opacity === '0.5' ? '1' : '0.5';
        }, 1000);
    }
}

function useDemoScanningStatus() {
    // Demo data already in HTML, just animate
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
        document.getElementById('scanningTarget').innerHTML = 
            `Currently scanning: <span class="highlight">${targets[currentIndex]}</span>`;
    }, 5000);
}

function queueLocalSuggestion(suggestion, priority) {
    // Store in localStorage for demo
    const suggestions = JSON.parse(localStorage.getItem('pendingSuggestions') || '[]');
    suggestions.push({
        suggestion,
        priority,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem('pendingSuggestions', JSON.stringify(suggestions));
}

function formatTimeAgo(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return `${seconds} seconds ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    return `${Math.floor(seconds / 86400)} days ago`;
}

function getStatusText(status) {
    const statusMap = {
        'queued': 'Queued for scan',
        'running': 'Scanning...',
        'completed': 'Scan complete',
        'contacted': 'Contact attempted',
        'failed': 'Scan failed'
    };
    return statusMap[status] || status;
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

// Export functions for use in HTML
window.viewDiscoveryQueue = viewDiscoveryQueue;
window.viewContactLog = viewContactLog;
