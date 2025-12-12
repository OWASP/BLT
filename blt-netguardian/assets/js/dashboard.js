/**
 * Dashboard JavaScript for BLT-NetGuardian
 */

let currentJobId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Get job ID from URL if present
    const urlParams = new URLSearchParams(window.location.search);
    currentJobId = urlParams.get('job_id');
    
    loadDashboard();
    
    // Auto-refresh every 10 seconds
    setInterval(loadDashboard, 10000);
});

async function loadDashboard() {
    // Load statistics (placeholder for now)
    loadStatistics();
    
    // Load current job if specified
    if (currentJobId) {
        await loadCurrentJob(currentJobId);
    }
    
    // Load recent jobs (from localStorage for demo)
    loadRecentJobs();
}

function loadStatistics() {
    // In production, these would come from the API
    // For now, using placeholder/demo data
    const stats = {
        totalJobs: parseInt(localStorage.getItem('totalJobs') || '0'),
        activeJobs: parseInt(localStorage.getItem('activeJobs') || '0'),
        totalVulnerabilities: parseInt(localStorage.getItem('totalVulnerabilities') || '0'),
        criticalVulns: parseInt(localStorage.getItem('criticalVulns') || '0')
    };
    
    document.getElementById('totalJobs').textContent = stats.totalJobs;
    document.getElementById('activeJobs').textContent = stats.activeJobs;
    document.getElementById('totalVulnerabilities').textContent = stats.totalVulnerabilities;
    document.getElementById('criticalVulns').textContent = stats.criticalVulns;
}

async function loadCurrentJob(jobId) {
    const section = document.getElementById('currentJobSection');
    const statusDiv = document.getElementById('currentJobStatus');
    
    section.style.display = 'block';
    statusDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading job status...</p></div>';
    
    try {
        const data = await apiRequest(`${CONFIG.ENDPOINTS.JOB_STATUS}?job_id=${jobId}`);
        
        const progressPercent = data.progress || 0;
        const statusClass = data.status || 'queued';
        
        statusDiv.innerHTML = `
            <div class="stat-card">
                <h3>Job: ${data.job_id}</h3>
                <p><span class="status ${statusClass}">${data.status.toUpperCase()}</span></p>
                <p>Progress: ${data.completed}/${data.total} tasks (${progressPercent}%)</p>
                <div style="background: #eee; border-radius: 8px; overflow: hidden; margin-top: 10px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                height: 20px; width: ${progressPercent}%; transition: width 0.3s;"></div>
                </div>
                <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                    Created: ${new Date(data.created_at).toLocaleString()}
                </p>
            </div>
        `;
        
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="message error">
                Failed to load job status: ${error.message}
            </div>
        `;
    }
}

function loadRecentJobs() {
    const jobsLoading = document.getElementById('jobsLoading');
    const jobsTable = document.getElementById('jobsTable');
    const jobsEmpty = document.getElementById('jobsEmpty');
    const tbody = document.getElementById('jobsTableBody');
    
    // Get jobs from localStorage (demo data)
    const jobsData = JSON.parse(localStorage.getItem('recentJobs') || '[]');
    
    jobsLoading.style.display = 'none';
    
    if (jobsData.length === 0) {
        jobsEmpty.style.display = 'block';
        jobsTable.style.display = 'none';
        return;
    }
    
    jobsEmpty.style.display = 'none';
    jobsTable.style.display = 'table';
    
    tbody.innerHTML = jobsData.map(job => `
        <tr>
            <td><code>${job.job_id.substring(0, 12)}...</code></td>
            <td>${job.target || 'N/A'}</td>
            <td><span class="status ${job.status}">${job.status.toUpperCase()}</span></td>
            <td>${job.progress || 0}%</td>
            <td>${new Date(job.created_at).toLocaleDateString()}</td>
            <td>
                <button onclick="viewJob('${job.job_id}')" style="padding: 4px 12px; font-size: 0.85em;">
                    View
                </button>
            </td>
        </tr>
    `).join('');
}

function viewJob(jobId) {
    window.location.href = `dashboard.html?job_id=${jobId}`;
}

function refreshDashboard() {
    loadDashboard();
}

// Add job to recent jobs (called when a new job is created)
function addRecentJob(jobData) {
    const recentJobs = JSON.parse(localStorage.getItem('recentJobs') || '[]');
    recentJobs.unshift(jobData);
    
    // Keep only last 20 jobs
    if (recentJobs.length > 20) {
        recentJobs.pop();
    }
    
    localStorage.setItem('recentJobs', JSON.stringify(recentJobs));
    
    // Update stats
    const totalJobs = parseInt(localStorage.getItem('totalJobs') || '0') + 1;
    const activeJobs = parseInt(localStorage.getItem('activeJobs') || '0') + 1;
    
    localStorage.setItem('totalJobs', totalJobs.toString());
    localStorage.setItem('activeJobs', activeJobs.toString());
}

// Export functions
window.refreshDashboard = refreshDashboard;
window.viewJob = viewJob;
window.addRecentJob = addRecentJob;
