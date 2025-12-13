/**
 * Vulnerabilities page JavaScript for BLT-NetGuardian
 */

let allVulnerabilities = [];

document.addEventListener('DOMContentLoaded', function() {
    loadVulnerabilities();
});

async function loadVulnerabilities() {
    const vulnsLoading = document.getElementById('vulnsLoading');
    const vulnsTable = document.getElementById('vulnsTable');
    const vulnsEmpty = document.getElementById('vulnsEmpty');
    const tbody = document.getElementById('vulnsTableBody');
    
    vulnsLoading.style.display = 'block';
    vulnsTable.style.display = 'none';
    vulnsEmpty.style.display = 'none';
    
    try {
        const data = await apiRequest(CONFIG.ENDPOINTS.VULNERABILITIES);
        
        allVulnerabilities = data.vulnerabilities || [];
        
        vulnsLoading.style.display = 'none';
        
        if (allVulnerabilities.length === 0) {
            vulnsEmpty.style.display = 'block';
            updateSummary({ critical: 0, high: 0, medium: 0, low: 0, info: 0 });
            return;
        }
        
        displayVulnerabilities(allVulnerabilities);
        
    } catch (error) {
        vulnsLoading.style.display = 'none';
        vulnsTable.style.display = 'none';
        
        // Show demo data on error
        console.log('Using demo data due to error:', error.message);
        loadDemoData();
    }
}

function loadDemoData() {
    // Demo vulnerabilities for testing the UI
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
    
    displayVulnerabilities(allVulnerabilities);
}

function displayVulnerabilities(vulnerabilities) {
    const vulnsTable = document.getElementById('vulnsTable');
    const tbody = document.getElementById('vulnsTableBody');
    
    // Calculate summary
    const summary = {
        critical: vulnerabilities.filter(v => v.severity === 'critical').length,
        high: vulnerabilities.filter(v => v.severity === 'high').length,
        medium: vulnerabilities.filter(v => v.severity === 'medium').length,
        low: vulnerabilities.filter(v => v.severity === 'low').length,
        info: vulnerabilities.filter(v => v.severity === 'info').length
    };
    
    updateSummary(summary);
    
    // Display table
    vulnsTable.style.display = 'table';
    
    tbody.innerHTML = vulnerabilities.map(vuln => `
        <tr onclick="showVulnerabilityDetails(${JSON.stringify(vuln).replace(/"/g, '&quot;')})" 
            style="cursor: pointer;">
            <td>
                <span class="severity ${vuln.severity}">
                    ${vuln.severity.toUpperCase()}
                </span>
            </td>
            <td><strong>${vuln.title}</strong></td>
            <td>${vuln.type || 'N/A'}</td>
            <td><code>${vuln.affected_component}</code></td>
            <td>${vuln.cve_id || '-'}</td>
            <td>${vuln.cvss_score ? vuln.cvss_score.toFixed(1) : '-'}</td>
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

function filterBySeverity() {
    const severity = document.getElementById('severityFilter').value;
    
    if (!severity) {
        displayVulnerabilities(allVulnerabilities);
        return;
    }
    
    const filtered = allVulnerabilities.filter(v => v.severity === severity);
    displayVulnerabilities(filtered);
}

function showVulnerabilityDetails(vuln) {
    const details = [
        `Severity: ${vuln.severity.toUpperCase()}`,
        `Title: ${vuln.title}`,
        `Type: ${vuln.type || 'N/A'}`,
        `Affected Component: ${vuln.affected_component}`,
        vuln.cve_id ? `CVE: ${vuln.cve_id}` : '',
        vuln.cvss_score ? `CVSS Score: ${vuln.cvss_score}` : '',
        vuln.description ? `\nDescription: ${vuln.description}` : '',
        vuln.remediation ? `\nRemediation: ${vuln.remediation}` : '',
        `\nDiscovered: ${new Date(vuln.discovered_at).toLocaleString()}`
    ].filter(Boolean).join('\n');
    
    alert(details);
}

function refreshVulnerabilities() {
    loadVulnerabilities();
}

// Export functions
window.refreshVulnerabilities = refreshVulnerabilities;
window.filterBySeverity = filterBySeverity;
window.showVulnerabilityDetails = showVulnerabilityDetails;
