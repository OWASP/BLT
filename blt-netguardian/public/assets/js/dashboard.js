/**
 * Dashboard JavaScript for BLT-NetGuardian
 */

let currentJobId = null;
let allJobs = [];

document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    currentJobId = urlParams.get('job_id');

    const jobsSearch = document.getElementById('jobsSearch');
    if (jobsSearch) {
        jobsSearch.addEventListener('input', applyJobFilters);
    }

    const jobsStatusFilter = document.getElementById('jobsStatusFilter');
    if (jobsStatusFilter) {
        jobsStatusFilter.addEventListener('change', applyJobFilters);
    }

    const jobsTableBody = document.getElementById('jobsTableBody');
    if (jobsTableBody) {
        jobsTableBody.addEventListener('click', handleJobsTableClick);
    }

    loadDashboard();
    setInterval(loadDashboard, 10000);
});

async function loadDashboard() {
    loadStatistics();

    if (currentJobId) {
        await loadCurrentJob(currentJobId);
    }

    loadRecentJobs();
}

function loadStatistics() {
    const stats = {
        totalJobs: parseInt(localStorage.getItem('totalJobs') || '0', 10),
        activeJobs: parseInt(localStorage.getItem('activeJobs') || '0', 10),
        totalVulnerabilities: parseInt(localStorage.getItem('totalVulnerabilities') || '0', 10),
        criticalVulns: parseInt(localStorage.getItem('criticalVulns') || '0', 10)
    };

    document.getElementById('totalJobs').textContent = stats.totalJobs;
    document.getElementById('activeJobs').textContent = stats.activeJobs;
    document.getElementById('totalVulnerabilities').textContent = stats.totalVulnerabilities;
    document.getElementById('criticalVulns').textContent = stats.criticalVulns;
}

async function loadCurrentJob(jobId) {
    const section = document.getElementById('currentJobSection');
    const statusDiv = document.getElementById('currentJobStatus');

    section.classList.remove('hidden');
    section.style.display = 'block';
    statusDiv.innerHTML = '<div class="loading"><div class="spinner" aria-hidden="true"></div><p>Loading job status...</p></div>';

    try {
        const data = await apiRequest(`${CONFIG.ENDPOINTS.JOB_STATUS}?job_id=${jobId}`);

        const progressPercent = data.progress || 0;
        const statusClass = data.status || 'queued';

        statusDiv.innerHTML = `
            <div class="rounded-lg border border-neutral-border bg-gray-50 p-4">
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <h4 class="text-base font-bold text-dark-base">Job ${escapeHtml(data.job_id || 'unknown')}</h4>
                    <span class="status ${escapeHtml(statusClass)}">${escapeHtml(String(data.status || 'queued'))}</span>
                </div>
                <p class="mt-2 text-sm text-gray-700">Progress: ${data.completed || 0}/${data.total || 0} tasks (${progressPercent}%)</p>
                <div class="mt-3 h-2.5 overflow-hidden rounded-full bg-gray-200" role="progressbar" aria-valuenow="${progressPercent}" aria-valuemin="0" aria-valuemax="100">
                    <div class="h-full rounded-full bg-red-600 transition-all" style="width: ${progressPercent}%;"></div>
                </div>
                <p class="mt-3 text-xs text-gray-500">Created: ${new Date(data.created_at).toLocaleString()}</p>
            </div>
        `;
    } catch (error) {
        statusDiv.innerHTML = `<div class="message error" style="display:block;">Failed to load job status: ${escapeHtml(error.message)}</div>`;
    }
}

function loadRecentJobs() {
    const jobsLoading = document.getElementById('jobsLoading');

    allJobs = JSON.parse(localStorage.getItem('recentJobs') || '[]');
    jobsLoading.style.display = 'none';

    applyJobFilters();
}

function applyJobFilters() {
    const query = (document.getElementById('jobsSearch')?.value || '').trim().toLowerCase();
    const statusFilter = (document.getElementById('jobsStatusFilter')?.value || '').trim().toLowerCase();

    const filteredJobs = allJobs.filter(job => {
        const jobId = String(job.job_id || '').toLowerCase();
        const target = String(job.target || '').toLowerCase();
        const status = String(job.status || '').toLowerCase();

        const matchesQuery = !query || jobId.includes(query) || target.includes(query);
        const matchesStatus = !statusFilter || status === statusFilter;

        return matchesQuery && matchesStatus;
    });

    renderJobs(filteredJobs);
}

function renderJobs(jobsData) {
    const jobsTable = document.getElementById('jobsTable');
    const jobsEmpty = document.getElementById('jobsEmpty');
    const tbody = document.getElementById('jobsTableBody');

    if (!jobsData.length) {
        jobsEmpty.style.display = 'block';
        jobsTable.style.display = 'none';
        tbody.innerHTML = '';
        return;
    }

    jobsEmpty.style.display = 'none';
    jobsTable.style.display = 'table';

    tbody.innerHTML = jobsData.map(job => {
        const safeId = escapeHtml(job.job_id || 'unknown');
        const shortId = safeId.length > 14 ? `${safeId.substring(0, 14)}...` : safeId;

        return `
            <tr>
                <td><code class="font-mono text-xs">${shortId}</code></td>
                <td>${escapeHtml(job.target || 'N/A')}</td>
                <td><span class="status ${escapeHtml(job.status || 'queued')}">${escapeHtml(String(job.status || 'queued'))}</span></td>
                <td>${escapeHtml(String(job.progress || 0))}%</td>
                <td>${new Date(job.created_at).toLocaleDateString()}</td>
                <td>
                    <button type="button" data-job-id="${escapeHtml(job.job_id || '')}" class="inline-flex items-center gap-1 rounded-md border border-brand px-3 py-1 text-xs font-semibold text-brand transition hover:bg-brand hover:text-white">
                        <i class="fa-solid fa-eye" aria-hidden="true"></i>
                        View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function viewJob(jobId) {
    window.location.href = `dashboard.html?job_id=${encodeURIComponent(jobId)}`;
}

function refreshDashboard() {
    loadDashboard();
}

function addRecentJob(jobData) {
    const recentJobs = JSON.parse(localStorage.getItem('recentJobs') || '[]');
    recentJobs.unshift(jobData);

    if (recentJobs.length > 20) {
        recentJobs.pop();
    }

    localStorage.setItem('recentJobs', JSON.stringify(recentJobs));

    const totalJobs = parseInt(localStorage.getItem('totalJobs') || '0', 10) + 1;
    const activeJobs = parseInt(localStorage.getItem('activeJobs') || '0', 10) + 1;

    localStorage.setItem('totalJobs', String(totalJobs));
    localStorage.setItem('activeJobs', String(activeJobs));

    loadDashboard();
}

function handleJobsTableClick(event) {
    const button = event.target.closest('button[data-job-id]');
    if (!button) {
        return;
    }

    viewJob(button.getAttribute('data-job-id') || '');
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

window.refreshDashboard = refreshDashboard;
window.viewJob = viewJob;
window.addRecentJob = addRecentJob;
