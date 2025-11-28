const METADATA_URL = "data/metadata.json";

// State
let projectData = [];
let filteredData = [];

// Load and process data
async function loadData() {
    try {
        const response = await fetch(METADATA_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const rawData = await response.json();
        
        // Filter projects with type metadata
        projectData = rawData.filter(item => 
            item.type && item.title && item.repo
        ).map(item => ({
            repo: item.repo,
            title: item.title,
            type: normalizeType(item.type),
            level: parseLevel(item.level),
            tags: item.tags || '',
            pitch: item.pitch || ''
        }));
        
        console.log(`Loaded ${projectData.length} projects with metadata`);
        
        applyFilters();
        updateLastUpdated();
        
    } catch (error) {
        console.error('Failed to load data:', error);
        showError('Failed to load project data. Please ensure data/metadata.json exists.');
    }
}

// Normalize project type to standard categories
function normalizeType(type) {
    if (!type) return 'other';
    
    const lowerType = type.toLowerCase().trim();
    
    if (lowerType.includes('tool')) return 'tool';
    if (lowerType.includes('documentation') || lowerType.includes('doc')) return 'documentation';
    if (lowerType.includes('code')) return 'code';
    if (lowerType.includes('standard')) return 'standards';
    
    // Map specific types
    const typeMap = {
        'tool': 'tool',
        'documentation': 'documentation',
        'code': 'code',
        'standards': 'standards',
        'example': 'other',
        'chapter': 'other',
        'other': 'other',
        'project': 'other',
        'working group': 'other'
    };
    
    return typeMap[lowerType] || 'other';
}

// Parse level to numeric value
function parseLevel(level) {
    if (level === null || level === undefined) return 0;
    const parsed = parseFloat(level);
    return isNaN(parsed) ? 0 : parsed;
}

// Get maturity category based on level
function getMaturityCategory(level) {
    if (level >= 4) return 'flagship';
    if (level === 3.5) return 'production';
    if (level >= 2) return 'lab';
    return 'incubator';
}

// Apply filters and regenerate diagram
function applyFilters() {
    const typeFilter = document.getElementById('type-filter').value;
    const levelFilter = document.getElementById('level-filter').value;
    
    filteredData = projectData.filter(project => {
        // Type filter
        if (typeFilter !== 'all' && project.type !== typeFilter) {
            return false;
        }
        
        // Level filter
        if (levelFilter !== 'all') {
            const maturity = getMaturityCategory(project.level);
            if (maturity !== levelFilter) {
                return false;
            }
        }
        
        return true;
    });
    
    updateProjectCount();
    renderDiagram();
}

// Update project count display
function updateProjectCount() {
    const countEl = document.getElementById('project-count');
    countEl.textContent = `${filteredData.length} projects shown`;
}

// Escape HTML to prevent XSS
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Render the diagram as an interactive HTML tree
function renderDiagram() {
    const container = document.getElementById('mermaid-diagram');
    
    if (filteredData.length === 0) {
        container.innerHTML = '<div class="loading-message">No projects match the selected filters.</div>';
        return;
    }
    
    // Group projects by type and maturity
    const groupedByType = {};
    
    filteredData.forEach(project => {
        if (!groupedByType[project.type]) {
            groupedByType[project.type] = {
                flagship: [],
                production: [],
                lab: [],
                incubator: []
            };
        }
        
        const maturity = getMaturityCategory(project.level);
        groupedByType[project.type][maturity].push(project);
    });
    
    const typeLabels = {
        'tool': '🔧 Tools',
        'documentation': '📚 Documentation',
        'code': '💻 Code',
        'standards': '📋 Standards',
        'other': '📦 Other'
    };
    
    const maturityLabels = {
        'flagship': '⭐ Flagship',
        'production': '🚀 Production',
        'lab': '🔬 Lab',
        'incubator': '🌱 Incubator'
    };
    
    const typeOrder = ['tool', 'documentation', 'code', 'standards', 'other'];
    const maturityOrder = ['flagship', 'production', 'lab', 'incubator'];
    
    // Build HTML tree diagram
    let html = `
        <div class="tree-diagram">
            <div class="tree-root">
                <div class="tree-node root-node">
                    <span class="node-icon">🛡️</span>
                    <span class="node-label">OWASP Projects</span>
                    <span class="node-count">${filteredData.length}</span>
                </div>
                <div class="tree-children type-level">
    `;
    
    typeOrder.forEach(type => {
        if (!groupedByType[type]) return;
        
        const typeData = groupedByType[type];
        const totalCount = typeData.flagship.length + typeData.production.length + typeData.lab.length + typeData.incubator.length;
        
        if (totalCount === 0) return;
        
        html += `
            <div class="tree-branch type-branch type-${type}">
                <div class="tree-node type-node" data-type="${type}">
                    <span class="node-label">${typeLabels[type]}</span>
                    <span class="node-count">${totalCount}</span>
                </div>
                <div class="tree-children maturity-level">
        `;
        
        maturityOrder.forEach(maturity => {
            const projects = typeData[maturity];
            if (projects.length === 0) return;
            
            // Sort projects by level (highest first)
            const sortedProjects = [...projects].sort((a, b) => b.level - a.level);
            
            html += `
                <div class="tree-branch maturity-branch maturity-${maturity}">
                    <div class="tree-node maturity-node">
                        <span class="node-label">${maturityLabels[maturity]}</span>
                        <span class="node-count">${projects.length}</span>
                    </div>
                    <div class="tree-children project-level">
            `;
            
            // Show up to 8 projects per maturity level
            const maxToShow = 8;
            const projectsToShow = sortedProjects.slice(0, maxToShow);
            
            projectsToShow.forEach(project => {
                const shortTitle = project.title.length > 35 
                    ? project.title.substring(0, 32) + '...' 
                    : project.title;
                
                const repoUrl = `https://github.com/${project.repo}`;
                
                html += `
                    <div class="tree-branch project-branch">
                        <a href="${repoUrl}" target="_blank" rel="noopener" class="tree-node project-node type-${type}" title="${escapeHtml(project.pitch || project.title)}">
                            <span class="node-label">${escapeHtml(shortTitle)}</span>
                            <span class="level-badge">L${project.level}</span>
                        </a>
                    </div>
                `;
            });
            
            if (projects.length > maxToShow) {
                const remaining = projects.length - maxToShow;
                html += `
                    <div class="tree-branch project-branch">
                        <div class="tree-node more-node">
                            <span class="node-label">+${remaining} more projects...</span>
                        </div>
                    </div>
                `;
            }
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    html += `
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Show error message
function showError(message) {
    const container = document.getElementById('mermaid-diagram');
    container.innerHTML = `<div class="error-message">${message}</div>`;
}

// Update last updated timestamp
function updateLastUpdated() {
    const now = new Date();
    document.getElementById('last-updated').textContent = now.toLocaleString();
}

// Download as HTML
function downloadDiagram() {
    const diagramHtml = document.getElementById('mermaid-diagram').innerHTML;
    const fullHtml = `<!DOCTYPE html>
<html>
<head>
    <title>OWASP Project Diagram</title>
    <style>
        ${getTreeStyles()}
    </style>
</head>
<body>
    <h1>OWASP Projects Organization</h1>
    ${diagramHtml}
</body>
</html>`;
    
    const blob = new Blob([fullHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `owasp-project-diagram-${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Get tree styles for export
function getTreeStyles() {
    return `
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }
        .tree-diagram { padding: 20px; }
        .tree-root { display: flex; flex-direction: column; align-items: center; }
        .tree-node { padding: 12px 20px; border-radius: 8px; display: inline-flex; align-items: center; gap: 8px; }
        .root-node { background: #fb7e00; color: white; font-weight: bold; font-size: 18px; }
        .type-node { background: #f1f5f9; color: #1e293b; font-weight: 600; cursor: pointer; }
        .maturity-node { background: #e2e8f0; color: #475569; font-size: 14px; }
        .project-node { background: white; border: 1px solid #e2e8f0; font-size: 13px; text-decoration: none; color: inherit; }
        .node-count { background: rgba(0,0,0,0.1); padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .tree-children { display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; margin-top: 20px; padding-left: 20px; border-left: 2px solid #e2e8f0; }
        .tree-branch { display: flex; flex-direction: column; align-items: flex-start; }
        .type-tool .type-node { border-left: 4px solid #3b82f6; }
        .type-documentation .type-node { border-left: 4px solid #10b981; }
        .type-code .type-node { border-left: 4px solid #8b5cf6; }
        .type-standards .type-node { border-left: 4px solid #f59e0b; }
        .type-other .type-node { border-left: 4px solid #6b7280; }
    `;
}

// Toggle theme
function toggleTheme() {
    document.body.classList.toggle('dark');
    const isDark = document.body.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// Event listeners
document.getElementById('toggle-theme').addEventListener('click', toggleTheme);
document.getElementById('download-svg').addEventListener('click', downloadDiagram);
document.getElementById('refresh-diagram').addEventListener('click', () => {
    loadData();
});
document.getElementById('type-filter').addEventListener('change', applyFilters);
document.getElementById('level-filter').addEventListener('change', applyFilters);

// Initialize theme from localStorage
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark');
}

// Load data on page load
document.addEventListener('DOMContentLoaded', loadData);
