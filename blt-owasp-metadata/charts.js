const MATRIX_URL = "data/metadata_matrix.json";

// Chart instances
let charts = {
    fieldFrequency: null,
    completeness: null,
    topFields: null,
    bottomFields: null
};

// Data
let matrixData = [];
let filteredData = [];
let fieldStats = {};
let archiveFilter = 'active'; // 'all', 'active', 'archived'

// Helper function to check if a repository is archived
function isArchived(row) {
    const archived = row.archived;
    if (archived === true || archived === 'true' || archived === '✔') return true;
    return false;
}

// Get filtered data based on archive filter
function getFilteredData() {
    if (archiveFilter === 'all') return matrixData;
    if (archiveFilter === 'active') return matrixData.filter(row => !isArchived(row));
    if (archiveFilter === 'archived') return matrixData.filter(row => isArchived(row));
    return matrixData;
}

// Initialize
async function loadData() {
    try {
        showLoadingStates();
        
        const res = await fetch(MATRIX_URL);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const rawData = await res.json();
        matrixData = processData(rawData);
        filteredData = getFilteredData();
        
        calculateFieldStats();
        renderAllCharts();
        updateStats();
        updateLastUpdated();
        
        hideLoadingStates();
        
    } catch (err) {
        console.error('Failed to load data:', err);
        showError('Failed to load metadata data. Please ensure data/metadata_matrix.json exists.');
    }
}

function processData(rawData) {
    return rawData.map(row => {
        const processed = {};
        Object.entries(row).forEach(([key, value]) => {
            // Normalize field names
            const cleanKey = key.trim().toLowerCase();
            // Convert string booleans and handle empty values
            if (value === 'true' || value === 'yes' || value === '1' || value === '✔') {
                processed[cleanKey] = true;
            } else if (value === 'false' || value === 'no' || value === '0' || value === '✘') {
                processed[cleanKey] = false;
            } else if (value && value.toString().trim() !== '') {
                processed[cleanKey] = value.toString().trim();
            } else {
                processed[cleanKey] = null;
            }
        });
        return processed;
    });
}

function calculateFieldStats() {
    fieldStats = {};
    const allFields = new Set();
    
    // Collect all unique fields (excluding archived)
    filteredData.forEach(row => {
        Object.keys(row).forEach(field => {
            if (field !== 'repo' && field !== 'archived') {
                allFields.add(field);
            }
        });
    });
    
    // Calculate statistics for each field based on filtered data
    allFields.forEach(field => {
        const count = filteredData.filter(row => 
            row[field] !== null && row[field] !== undefined && row[field] !== ''
        ).length;
        
        const percentage = filteredData.length > 0 ? (count / filteredData.length) * 100 : 0;
        
        fieldStats[field] = {
            count,
            percentage: Math.round(percentage * 10) / 10, 
            repositories: count
        };
    });
    
    console.log('Field stats calculated:', Object.keys(fieldStats).length, 'fields');
}

function updateStats() {
    const totalRepos = matrixData.length;
    const archivedRepos = matrixData.filter(row => isArchived(row)).length;
    const activeRepos = totalRepos - archivedRepos;
    
    const reposWithMetadata = filteredData.filter(row => {
        return Object.keys(row).some(key => 
            key !== 'repo' && key !== 'archived' && row[key] !== null && row[key] !== undefined && row[key] !== ''
        );
    }).length;
    
    const totalFields = Object.keys(fieldStats).length;
    const completenessRate = filteredData.length > 0 ? ((reposWithMetadata / filteredData.length) * 100).toFixed(1) : '0';
    
    document.getElementById('total-repos').textContent = totalRepos.toLocaleString();
    document.getElementById('active-repos').textContent = activeRepos.toLocaleString();
    document.getElementById('archived-repos').textContent = archivedRepos.toLocaleString();
    document.getElementById('repos-with-metadata').textContent = reposWithMetadata.toLocaleString();
    document.getElementById('total-fields').textContent = totalFields.toLocaleString();
    document.getElementById('completeness-rate').textContent = `${completenessRate}%`;
}

function updateLastUpdated() {
    const now = new Date();
    document.getElementById('last-updated').textContent = now.toLocaleString();
}

function renderAllCharts() {
    renderFieldFrequencyChart();
    renderCompletenessChart();
    renderTopFieldsChart();
    renderBottomFieldsChart();
    renderFieldDetailsTable();
}

function renderFieldFrequencyChart() {
    const ctx = document.getElementById('field-frequency-chart').getContext('2d');
    
    // Destroy previous chart if exists
    if (charts.fieldFrequency) charts.fieldFrequency.destroy();
    
    const sortedFields = Object.entries(fieldStats)
        .sort(([,a], [,b]) => b.count - a.count)
        .slice(0, 15); // Top 15 fields
    
    const backgroundColors = generateColors(sortedFields.length, 0.7);
    const borderColors = generateColors(sortedFields.length, 1);
    
    charts.fieldFrequency = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedFields.map(([field]) => formatFieldName(field)),
            datasets: [{
                label: 'Repositories with Field',
                data: sortedFields.map(([, stats]) => stats.count),
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 2,
                borderRadius: 4
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
                    callbacks: {
                        label: function(context) {
                            const percentage = sortedFields[context.dataIndex][1].percentage;
                            return `${context.parsed.y} repos (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Repositories'
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        callback: function(value) {
                            const label = this.getLabelForValue(value);
                            return label.length > 20 ? label.substring(0, 20) + '...' : label;
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function renderCompletenessChart() {
    const ctx = document.getElementById('completeness-chart').getContext('2d');
    
    // Calculate completeness distribution using filtered data
    const completenessRanges = {
        '0%': 0,
        '1-25%': 0,
        '26-50%': 0,
        '51-75%': 0,
        '76-99%': 0,
        '100%': 0
    };
    
    filteredData.forEach(row => {
        const totalFields = Object.keys(fieldStats).length;
        const filledFields = Object.keys(row).filter(key => 
            key !== 'repo' && key !== 'archived' && row[key] !== null && row[key] !== undefined && row[key] !== ''
        ).length;
        
        const percentage = totalFields > 0 ? (filledFields / totalFields) * 100 : 0;
        
        if (percentage === 0) completenessRanges['0%']++;
        else if (percentage <= 25) completenessRanges['1-25%']++;
        else if (percentage <= 50) completenessRanges['26-50%']++;
        else if (percentage <= 75) completenessRanges['51-75%']++;
        else if (percentage < 100) completenessRanges['76-99%']++;
        else completenessRanges['100%']++;
    });
    
    if (charts.completeness) charts.completeness.destroy();
    
    charts.completeness = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(completenessRanges),
            datasets: [{
                data: Object.values(completenessRanges),
                backgroundColor: [
                    '#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e', '#15803d'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '50%',
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = filteredData.length;
                            const value = context.parsed;
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0';
                            return `${context.label}: ${value} repos (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderTopFieldsChart() {
    const ctx = document.getElementById('top-fields-chart').getContext('2d');
    
    const topFields = Object.entries(fieldStats)
        .sort(([,a], [,b]) => b.percentage - a.percentage)
        .slice(0, 10);
    
    if (charts.topFields) charts.topFields.destroy();
    
    charts.topFields = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: topFields.map(([field]) => formatFieldName(field)),
            datasets: [{
                data: topFields.map(([, stats]) => stats.percentage),
                backgroundColor: generateColors(10, 0.8),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const field = topFields[context.dataIndex][0];
                            const count = topFields[context.dataIndex][1].count;
                            return `${formatFieldName(field)}: ${context.parsed}% (${count} repos)`;
                        }
                    }
                }
            }
        }
    });
}

function renderBottomFieldsChart() {
    const ctx = document.getElementById('bottom-fields-chart').getContext('2d');
    
    const bottomFields = Object.entries(fieldStats)
        .filter(([, stats]) => stats.percentage > 0) 
        .sort(([,a], [,b]) => a.percentage - b.percentage)
        .slice(0, 10);
    
    if (charts.bottomFields) charts.bottomFields.destroy();
    
    charts.bottomFields = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: bottomFields.map(([field]) => formatFieldName(field)),
            datasets: [{
                data: bottomFields.map(([, stats]) => stats.percentage),
                backgroundColor: generateColors(10, 0.8),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const field = bottomFields[context.dataIndex][0];
                            const count = bottomFields[context.dataIndex][1].count;
                            return `${formatFieldName(field)}: ${context.parsed.toFixed(1)}% (${count} repos)`;
                        }
                    }
                }
            }
        }
    });
}

function renderFieldDetailsTable() {
    const tbody = document.getElementById('field-details-body');
    const sortedFields = Object.entries(fieldStats)
        .sort(([,a], [,b]) => b.percentage - a.percentage);
    
    if (sortedFields.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No field data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = sortedFields.map(([field, stats]) => `
        <tr>
            <td><strong>${formatFieldName(field)}</strong></td>
            <td>${stats.count} / ${filteredData.length}</td>
            <td>${stats.percentage}%</td>
            <td>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${Math.min(stats.percentage, 100)}%"></div>
                </div>
            </td>
        </tr>
    `).join('');
}

// Utility functions
function formatFieldName(field) {
    return field
        .replace(/[_-]/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

function generateColors(count, opacity = 1) {
    const baseColor = [251, 126, 0]; 
    const colors = [];
    
    for (let i = 0; i < count; i++) {
        const hue = (i * 137.5) % 360; // Golden angle approximation
        const saturation = 70 + (i % 3) * 10;
        const lightness = 50 + (i % 2) * 10;
        
        colors.push(`hsla(${hue}, ${saturation}%, ${lightness}%, ${opacity})`);
    }
    
    return colors;
}

function showLoadingStates() {
    document.querySelectorAll('.loading-chart').forEach(el => {
        el.style.display = 'flex';
    });
}

function hideLoadingStates() {
    document.querySelectorAll('.loading-chart').forEach(el => {
        el.style.display = 'none';
    });
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #ef4444;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    errorDiv.textContent = message;
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        document.body.removeChild(errorDiv);
    }, 5000);
}

// Event Listeners
document.getElementById('toggle-theme').addEventListener('click', () => {
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
    // Refresh charts to update colors
    setTimeout(renderAllCharts, 100);
});

document.getElementById('refresh-charts').addEventListener('click', () => {
    loadData();
});

document.getElementById('chart-archive-filter').addEventListener('change', (e) => {
    archiveFilter = e.target.value;
    filteredData = getFilteredData();
    calculateFieldStats();
    renderAllCharts();
    updateStats();
});

document.getElementById('export-charts').addEventListener('click', () => {
    const archivedCount = matrixData.filter(row => isArchived(row)).length;
    const activeCount = matrixData.length - archivedCount;
    
    const dataStr = JSON.stringify({
        stats: fieldStats,
        summary: {
            totalRepositories: matrixData.length,
            activeRepositories: activeCount,
            archivedRepositories: archivedCount,
            totalFields: Object.keys(fieldStats).length,
            filterApplied: archiveFilter,
            generated: new Date().toISOString()
        }
    }, null, 2);
    
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `owasp-metadata-analytics-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// Initialize theme
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark');
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', loadData);