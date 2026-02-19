/**
 * Vulnerabilities page JavaScript for BLT-NetGuardian
 */

let allVulnerabilities = [];
let displayedVulnerabilities = [];

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('vulnSearch');
    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }

    const tableBody = document.getElementById('vulnsTableBody');
    if (tableBody) {
        tableBody.addEventListener('click', handleVulnerabilityRowClick);
    }

    loadVulnerabilities();
});

async function loadVulnerabilities() {
    const vulnsLoading = document.getElementById('vulnsLoading');
    const vulnsTable = document.getElementById('vulnsTable');
    const vulnsEmpty = document.getElementById('vulnsEmpty');

    vulnsLoading.style.display = 'block';
    vulnsTable.style.display = 'none';
    vulnsEmpty.style.display = 'none';

    try {
        const data = await apiRequest(CONFIG.ENDPOINTS.VULNERABILITIES);

        allVulnerabilities = data.vulnerabilities || [];
        vulnsLoading.style.display = 'none';

        if (!allVulnerabilities.length) {
            vulnsEmpty.textContent = 'No vulnerabilities found. Great job.';
            vulnsEmpty.style.display = 'block';
            updateSummary({ critical: 0, high: 0, medium: 0, low: 0, info: 0 });
            displayedVulnerabilities = [];
            return;
        }

        applyFilters();
    } catch (error) {
        vulnsLoading.style.display = 'none';
        vulnsTable.style.display = 'none';

        console.log('Using demo data due to error:', error.message);
        loadDemoData();
        applyFilters();
    }
}

function loadDemoData() {
    allVulnerabilities = [
        {
            severity: 'critical',
            title: 'SQL Injection in Login Form',
            type: 'sql_injection',
            affected_component: '/login.php',
            cve_id: 'CVE-2024-12345',
            cvss_score: 9.8,
            discovered_at: new Date().toISOString()
        },
        {
            severity: 'high',
            title: 'Cross-Site Scripting (XSS) Vulnerability',
            type: 'xss',
            affected_component: '/search',
            cve_id: null,
            cvss_score: 7.5,
            discovered_at: new Date().toISOString()
        },
        {
            severity: 'medium',
            title: 'Missing Security Headers',
            type: 'security_headers',
            affected_component: 'HTTP Response',
            cve_id: null,
            cvss_score: 5.0,
            discovered_at: new Date().toISOString()
        },
        {
            severity: 'low',
            title: 'Directory Listing Enabled',
            type: 'info_disclosure',
            affected_component: '/uploads/',
            cve_id: null,
            cvss_score: 3.0,
            discovered_at: new Date().toISOString()
        }
    ];
}

function displayVulnerabilities(vulnerabilities) {
    const vulnsTable = document.getElementById('vulnsTable');
    const vulnsEmpty = document.getElementById('vulnsEmpty');
    const tbody = document.getElementById('vulnsTableBody');

    displayedVulnerabilities = vulnerabilities;
    updateSummary(getSummary(vulnerabilities));

    if (!vulnerabilities.length) {
        vulnsTable.style.display = 'none';
        vulnsEmpty.textContent = 'No vulnerabilities match the current filters.';
        vulnsEmpty.style.display = 'block';
        tbody.innerHTML = '';
        return;
    }

    vulnsEmpty.style.display = 'none';
    vulnsTable.style.display = 'table';

    tbody.innerHTML = vulnerabilities.map((vuln, index) => `
        <tr class="cursor-pointer" data-vuln-index="${index}">
            <td>
                <span class="severity ${escapeHtml(vuln.severity || 'info')}">${escapeHtml(String(vuln.severity || 'info'))}</span>
            </td>
            <td><strong>${escapeHtml(vuln.title || 'Untitled issue')}</strong></td>
            <td>${escapeHtml(vuln.type || 'N/A')}</td>
            <td><code class="font-mono text-xs">${escapeHtml(vuln.affected_component || 'N/A')}</code></td>
            <td>${escapeHtml(vuln.cve_id || '-')}</td>
            <td>${vuln.cvss_score !== null && vuln.cvss_score !== undefined ? Number(vuln.cvss_score).toFixed(1) : '-'}</td>
            <td>${new Date(vuln.discovered_at).toLocaleDateString()}</td>
        </tr>
    `).join('');
}

function updateSummary(summary) {
    document.getElementById('criticalCount').textContent = summary.critical;
    document.getElementById('highCount').textContent = summary.high;
    document.getElementById('mediumCount').textContent = summary.medium;
    document.getElementById('lowCount').textContent = summary.low;
}

function getSummary(vulnerabilities) {
    return {
        critical: vulnerabilities.filter(v => v.severity === 'critical').length,
        high: vulnerabilities.filter(v => v.severity === 'high').length,
        medium: vulnerabilities.filter(v => v.severity === 'medium').length,
        low: vulnerabilities.filter(v => v.severity === 'low').length,
        info: vulnerabilities.filter(v => v.severity === 'info').length
    };
}

function applyFilters() {
    const severity = (document.getElementById('severityFilter')?.value || '').toLowerCase();
    const query = (document.getElementById('vulnSearch')?.value || '').trim().toLowerCase();

    const filtered = allVulnerabilities.filter(vuln => {
        const matchesSeverity = !severity || String(vuln.severity || '').toLowerCase() === severity;
        const searchText = [
            vuln.title,
            vuln.type,
            vuln.affected_component,
            vuln.cve_id,
            vuln.severity
        ].join(' ').toLowerCase();
        const matchesQuery = !query || searchText.includes(query);

        return matchesSeverity && matchesQuery;
    });

    displayVulnerabilities(filtered);
}

function filterBySeverity() {
    applyFilters();
}

function handleVulnerabilityRowClick(event) {
    const row = event.target.closest('tr[data-vuln-index]');
    if (!row) {
        return;
    }

    const index = Number.parseInt(row.getAttribute('data-vuln-index'), 10);
    if (Number.isNaN(index) || !displayedVulnerabilities[index]) {
        return;
    }

    showVulnerabilityDetails(displayedVulnerabilities[index]);
}

function showVulnerabilityDetails(vuln) {
    const details = [
        `Severity: ${String(vuln.severity || 'info').toUpperCase()}`,
        `Title: ${vuln.title || 'Untitled issue'}`,
        `Type: ${vuln.type || 'N/A'}`,
        `Affected Component: ${vuln.affected_component || 'N/A'}`,
        vuln.cve_id ? `CVE: ${vuln.cve_id}` : '',
        vuln.cvss_score !== null && vuln.cvss_score !== undefined ? `CVSS Score: ${vuln.cvss_score}` : '',
        vuln.description ? `\nDescription: ${vuln.description}` : '',
        vuln.remediation ? `\nRemediation: ${vuln.remediation}` : '',
        `\nDiscovered: ${new Date(vuln.discovered_at).toLocaleString()}`
    ].filter(Boolean).join('\n');

    alert(details);
}

function refreshVulnerabilities() {
    loadVulnerabilities();
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

window.refreshVulnerabilities = refreshVulnerabilities;
window.filterBySeverity = filterBySeverity;
window.showVulnerabilityDetails = showVulnerabilityDetails;
