const METADATA_URL = "data/metadata.json";

// State
let projectData = [];
let categorizedProjects = {};
let zoomLevel = 1;

// Keywords used to categorize projects into SDLC phases
const sdlcKeywords = {
    requirements: {
        title: ['verification standard', 'asvs', 'masvs', 'security rat', 'skf', 'security knowledge framework', 'requirements'],
        tags: ['asvs', 'masvs', 'requirements', 'standards', 'verification'],
        type: ['standards']
    },
    design: {
        title: ['threat model', 'threat dragon', 'pytm', 'cornucopia', 'design', 'architecture'],
        tags: ['threat-modeling', 'threatmodeling', 'threat', 'design', 'architecture'],
        type: []
    },
    implementation: {
        title: ['cheat sheet', 'secure coding', 'proactive controls', 'esapi', 'csrfguard', 'encoder', 'dependency-check', 'dependency-track', 'cyclonedx', 'sbom', 'secure headers', 'code review'],
        tags: ['secure-coding', 'cheat', 'esapi', 'dependency', 'sbom', 'sca', 'supply chain', 'headers', 'implementation', 'coding', 'builder', 'builders'],
        type: ['code']
    },
    verification: {
        title: ['testing guide', 'wstg', 'mstg', 'testing', 'scanner', 'amass', 'nettacker', 'owtf', 'zap', 'penetration', 'pentest', 'security testing', 'find security bugs'],
        tags: ['testing', 'scanner', 'pentest', 'breaker', 'breakers', 'verification', 'sast', 'dast', 'osint'],
        type: ['tool']
    },
    operation: {
        title: ['waf', 'modsecurity', 'coraza', 'crs', 'firewall', 'runtime', 'appsensor'],
        tags: ['waf', 'firewall', 'runtime', 'defense', 'operation', 'crs'],
        type: []
    },
    policyGap: {
        title: ['samm', 'maturity', 'benchmark', 'assessment'],
        tags: ['samm', 'maturity', 'assessment', 'policy'],
        type: []
    },
    metrics: {
        title: ['metrics', 'measurement', 'kpi', 'dashboard'],
        tags: ['metrics', 'measurement', 'kpi'],
        type: []
    },
    training: {
        title: ['goat', 'juice shop', 'webgoat', 'security shepherd', 'vulnerable', 'lab', 'training', 'education', 'ctf', 'challenge', 'wrong secrets', 'top 10', 'top ten', 'dojo'],
        tags: ['training', 'education', 'vulnerable', 'lab', 'ctf', 'top10', 'goat'],
        type: []
    },
    culture: {
        title: ['champions', 'awareness', 'culture', 'devsecops', 'integration', 'process'],
        tags: ['champions', 'awareness', 'culture', 'devsecops'],
        type: []
    }
};

// Initialize mermaid with securityLevel loose to enable click handlers
// Note: 'loose' is required for Mermaid's click callback functionality to work.
// The click handlers only call our validated openProject function which uses
// a whitelist (window.projectUrls) of pre-validated GitHub URLs.
mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    securityLevel: 'loose',
    themeVariables: {
        primaryColor: '#34568b',
        primaryTextColor: '#fff',
        primaryBorderColor: '#1e3a5f',
        lineColor: '#5a6c7d',
        secondaryColor: '#8c9aac',
        tertiaryColor: '#f5f5f5',
        fontSize: '14px'
    },
    flowchart: {
        htmlLabels: true,
        curve: 'basis',
        rankSpacing: 80,
        nodeSpacing: 50,
        padding: 15,
        useMaxWidth: false
    }
});

// Store project URLs for click handlers
window.projectUrls = {};

// Load and process data
async function loadData() {
    try {
        const response = await fetch(METADATA_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const rawData = await response.json();
        
        // Filter for www-project-* repos with title and type
        projectData = rawData.filter(item => 
            item.repo && 
            item.repo.includes('www-project-') && 
            item.title && 
            item.type
        ).map(item => ({
            repo: item.repo,
            title: item.title,
            type: (item.type || '').toLowerCase(),
            level: item.level || 0,
            tags: (item.tags || '').toLowerCase(),
            pitch: item.pitch || ''
        }));
        
        console.log(`Loaded ${projectData.length} www-project-* repos with metadata`);
        
        // Categorize projects into SDLC phases
        categorizeProjects();
        
        renderMermaidDiagram();
        updateLastUpdated();
        updateProjectCount();
        
    } catch (error) {
        console.error('Failed to load data:', error);
        showError('Failed to load project data. Please ensure data/metadata.json exists.');
    }
}

// Categorize projects into SDLC phases based on metadata
function categorizeProjects() {
    categorizedProjects = {
        requirements: [],
        design: [],
        implementation: [],
        verification: [],
        operation: [],
        policyGap: [],
        metrics: [],
        training: [],
        culture: []
    };
    
    const assigned = new Set();
    
    // First pass: categorize based on keywords
    projectData.forEach(project => {
        const titleLower = project.title.toLowerCase();
        const tagsLower = project.tags.toLowerCase();
        const typeLower = project.type.toLowerCase();
        
        // Check each phase for matches
        for (const [phase, keywords] of Object.entries(sdlcKeywords)) {
            // Check title keywords
            const titleMatch = keywords.title.some(kw => titleLower.includes(kw));
            // Check tag keywords
            const tagMatch = keywords.tags.some(kw => tagsLower.includes(kw));
            // Check type keywords
            const typeMatch = keywords.type.some(kw => typeLower.includes(kw));
            
            if (titleMatch || tagMatch || typeMatch) {
                if (!assigned.has(project.repo)) {
                    categorizedProjects[phase].push(project);
                    assigned.add(project.repo);
                    break; // Only assign to one phase
                }
            }
        }
    });
    
    // Second pass: assign remaining projects based on type alone
    projectData.forEach(project => {
        if (assigned.has(project.repo)) return;
        
        const typeLower = project.type.toLowerCase();
        
        // Default categorization based on type
        if (typeLower === 'tool') {
            categorizedProjects.verification.push(project);
        } else if (typeLower === 'documentation') {
            categorizedProjects.implementation.push(project);
        } else if (typeLower === 'code') {
            categorizedProjects.implementation.push(project);
        } else if (typeLower === 'standards') {
            categorizedProjects.requirements.push(project);
        } else {
            // Uncategorized projects go to implementation as default
            categorizedProjects.implementation.push(project);
        }
        assigned.add(project.repo);
    });
    
    // Log categorization results
    console.log('Project categorization:');
    for (const [phase, projects] of Object.entries(categorizedProjects)) {
        console.log(`  ${phase}: ${projects.length} projects`);
    }
}

// Update project count display
function updateProjectCount() {
    const countEl = document.querySelector('.project-count');
    if (countEl) {
        countEl.textContent = `Total Projects: ${projectData.length}`;
    }
}

// Find projects matching a search term
function findProject(searchTerm) {
    const term = searchTerm.toLowerCase();
    return projectData.find(p => 
        p.title.toLowerCase().includes(term) ||
        (p.tags && p.tags.toLowerCase().includes(term))
    );
}

// Generate safe ID for mermaid nodes
function safeId(str) {
    return str.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30);
}

// Escape label text for mermaid (remove special characters that break parsing)
function safeLabel(str) {
    return str
        .replace(/OWASP /gi, '')
        .replace(/[()]/g, '')
        .replace(/[<>]/g, '')
        .replace(/"/g, "'")
        .substring(0, 18);
}

// Render the mermaid diagram
function renderMermaidDiagram() {
    const container = document.getElementById('mermaid-chart');
    
    // Build the mermaid flowchart definition
    // Based on the screenshot layout with OpenCRE.org at center
    let diagram = `flowchart TB
    %% Styling
    classDef phaseStyle fill:#34568b,stroke:#1e3a5f,color:#fff,stroke-width:2px
    classDef centerStyle fill:#1e3a5f,stroke:#0d2137,color:#fff,stroke-width:3px
    classDef categoryStyle fill:#5a6c7d,stroke:#3d4d5c,color:#fff
    classDef projectStyle fill:#8c9aac,stroke:#6b7a8a,color:#333,rx:20,ry:20
    
    %% Center node
    OpenCRE((OpenCRE.org)):::centerStyle
    
    %% SDLC Phases
    Requirements[Requirements]:::phaseStyle
    Design[Design]:::phaseStyle
    Implementation[Implementation]:::phaseStyle
    Verification[Verification]:::phaseStyle
    Operation[Operation]:::phaseStyle
    PolicyGap[Policy Gap Evaluation]:::phaseStyle
    Metrics[Metrics]:::phaseStyle
    Training[Training Education]:::phaseStyle
    Culture[Culture Building]:::phaseStyle
    
    %% Main flow connections
    Requirements --> Design
    Design --> Implementation
    Implementation --> Verification
    Operation --> Requirements
    Verification -->|After N Iterations| PolicyGap
    PolicyGap --> Metrics
    Metrics --> Training
    Training --> Culture
    Culture --> OpenCRE
    OpenCRE --> Requirements
    OpenCRE --> Design
    OpenCRE --> Implementation
    OpenCRE --> Verification
`;

    // Helper function to add projects from a category
    // Shows ALL projects and makes them clickable
    function addProjects(projects, phaseNodeId, categoryLabel, categoryNodeId) {
        if (!projects || projects.length === 0) return '';
        
        let output = '';
        
        if (categoryLabel) {
            output += `    ${categoryNodeId}[${categoryLabel}]:::categoryStyle\n`;
            output += `    ${phaseNodeId} --> ${categoryNodeId}\n`;
        }
        
        // Show ALL projects (no limit)
        projects.forEach((proj, idx) => {
            const title = safeLabel(proj.title);
            const nodeId = `${categoryNodeId}Proj${idx}`;
            output += `    ${nodeId}((${title})):::projectStyle\n`;
            output += `    ${categoryLabel ? categoryNodeId : phaseNodeId} --> ${nodeId}\n`;
            
            // Store project URL for click handler
            // Validate repo format to prevent URL injection (must match owner/repo pattern)
            if (proj.repo && /^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(proj.repo)) {
                const repoUrl = `https://github.com/${proj.repo}`;
                window.projectUrls[nodeId] = repoUrl;
                
                // Add click handler for this project
                output += `    click ${nodeId} call openProject("${nodeId}")\n`;
            }
        });
        
        return output;
    }

    // Requirements phase - Standards and verification standards
    diagram += `
    %% Requirements phase projects
`;
    diagram += addProjects(categorizedProjects.requirements, 'Requirements', 'Standards', 'ReqDocs');

    // Design phase - Threat Modeling
    diagram += `
    %% Design phase projects
`;
    diagram += addProjects(categorizedProjects.design, 'Design', 'Threat Modeling', 'DesignTM');

    // Implementation phase - Various documentation and libraries
    diagram += `
    %% Implementation phase projects
`;
    diagram += addProjects(categorizedProjects.implementation, 'Implementation', 'Docs & Code', 'ImplDocs');

    // Verification phase - Testing guides and tools
    diagram += `
    %% Verification phase projects
`;
    diagram += addProjects(categorizedProjects.verification, 'Verification', 'Testing Tools', 'VerTools');

    // Operation phase - WAFs and runtime protection
    diagram += `
    %% Operation phase projects
`;
    diagram += addProjects(categorizedProjects.operation, 'Operation', 'Runtime', 'OpTools');

    // Policy Gap Evaluation phase
    diagram += `
    %% Policy Gap Evaluation
`;
    diagram += addProjects(categorizedProjects.policyGap, 'PolicyGap', 'Assessment', 'PolicyGuides');

    // Metrics phase
    diagram += `
    %% Metrics phase projects
`;
    diagram += addProjects(categorizedProjects.metrics, 'Metrics', 'Metrics', 'MetricsTools');

    // Training phase - Vulnerable applications and educational resources
    diagram += `
    %% Training/Education phase projects
`;
    diagram += addProjects(categorizedProjects.training, 'Training', 'Labs & Education', 'TrainTools');

    // Culture phase
    diagram += `
    %% Culture Building phase projects
`;
    diagram += addProjects(categorizedProjects.culture, 'Culture', 'Process', 'CultureDocs');

    // Add iterate connection from Operation to Requirements
    diagram += `
    %% Iterate connection
    Operation -.->|Iterate| Requirements
`;

    console.log('Mermaid diagram definition:', diagram);

    // Render the diagram
    container.innerHTML = `<div id="diagram-wrapper"><pre class="mermaid">${diagram}</pre></div>`;
    
    try {
        mermaid.run({
            nodes: container.querySelectorAll('.mermaid')
        });
    } catch (error) {
        console.error('Mermaid rendering error:', error);
        showError('Failed to render diagram. Check console for details.');
    }
}

// Show error message
function showError(message) {
    const container = document.getElementById('mermaid-chart');
    container.innerHTML = `<div class="error-message">${message}</div>`;
}

// Update last updated timestamp
function updateLastUpdated() {
    const now = new Date();
    document.getElementById('last-updated').textContent = now.toLocaleString();
}

// Download diagram as SVG
function downloadDiagram() {
    const svg = document.querySelector('#mermaid-chart svg');
    if (!svg) {
        alert('No diagram to download');
        return;
    }
    
    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `owasp-sdlc-diagram-${new Date().toISOString().split('T')[0]}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Zoom functions
function zoomIn() {
    zoomLevel = Math.min(zoomLevel + 0.2, 3);
    applyZoom();
}

function zoomOut() {
    zoomLevel = Math.max(zoomLevel - 0.2, 0.3);
    applyZoom();
}

function zoomReset() {
    zoomLevel = 1;
    applyZoom();
}

function applyZoom() {
    const wrapper = document.getElementById('diagram-wrapper');
    if (wrapper) {
        wrapper.style.transform = `scale(${zoomLevel})`;
    }
}

// Toggle theme
function toggleTheme() {
    document.body.classList.toggle('dark');
    const isDark = document.body.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    
    // Re-initialize mermaid with appropriate theme
    // Note: 'loose' is required for Mermaid's click callback functionality
    mermaid.initialize({
        startOnLoad: false,
        theme: isDark ? 'dark' : 'base',
        securityLevel: 'loose',
        themeVariables: isDark ? {
            primaryColor: '#4a6fa5',
            primaryTextColor: '#fff',
            primaryBorderColor: '#2d4a6f',
            lineColor: '#7a8a9a',
            secondaryColor: '#5a6a7a',
            tertiaryColor: '#2a3a4a',
            fontSize: '14px'
        } : {
            primaryColor: '#34568b',
            primaryTextColor: '#fff',
            primaryBorderColor: '#1e3a5f',
            lineColor: '#5a6c7d',
            secondaryColor: '#8c9aac',
            tertiaryColor: '#f5f5f5',
            fontSize: '14px'
        },
        flowchart: {
            htmlLabels: true,
            curve: 'basis',
            rankSpacing: 80,
            nodeSpacing: 50,
            padding: 15,
            useMaxWidth: false
        }
    });
    
    // Re-render diagram with new theme
    renderMermaidDiagram();
}

// Global callback function for Mermaid click handlers
// This opens the GitHub repository for a project
window.openProject = function(nodeId) {
    const url = window.projectUrls[nodeId];
    if (url) {
        window.open(url, '_blank', 'noopener');
    }
};

// Event listeners
document.getElementById('toggle-theme').addEventListener('click', toggleTheme);
document.getElementById('download-diagram').addEventListener('click', downloadDiagram);
document.getElementById('refresh-diagram').addEventListener('click', () => {
    loadData();
});
document.getElementById('zoom-in').addEventListener('click', zoomIn);
document.getElementById('zoom-out').addEventListener('click', zoomOut);
document.getElementById('zoom-reset').addEventListener('click', zoomReset);

// Initialize theme from localStorage
// Note: 'loose' is required for Mermaid's click callback functionality
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark');
    mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'loose',
        themeVariables: {
            primaryColor: '#4a6fa5',
            primaryTextColor: '#fff',
            primaryBorderColor: '#2d4a6f',
            lineColor: '#7a8a9a',
            secondaryColor: '#5a6a7a',
            tertiaryColor: '#2a3a4a',
            fontSize: '14px'
        },
        flowchart: {
            htmlLabels: true,
            curve: 'basis',
            rankSpacing: 80,
            nodeSpacing: 50,
            padding: 15,
            useMaxWidth: false
        }
    });
}

// Load data on page load
document.addEventListener('DOMContentLoaded', loadData);
