const METADATA_URL = "data/metadata.json";

// State
let projectData = [];
let zoomLevel = 1;

// SDLC Phase definitions with their associated project categories
const sdlcPhases = {
    requirements: {
        label: "Requirements",
        categories: {
            docs: ["ASVS", "MASVS", "Security RAT", "SKF"]
        }
    },
    design: {
        label: "Design",
        categories: {
            threatModeling: ["Threat Dragon", "pytm", "Cornucopia", "Threat Modeling"]
        }
    },
    implementation: {
        label: "Implementation",
        categories: {
            docs: ["Proactive Controls", "Go SCP", "Cheat Sheet"],
            dependencies: ["Dependency-Check", "Dependency-Track", "CycloneDX"],
            secureLibraries: ["ESAPI", "CSRFGuard", "Secure Headers"]
        }
    },
    verification: {
        label: "Verification",
        categories: {
            guides: ["WSTG", "MSTG", "Web Security Testing"],
            tools: ["Amass", "Nettacker", "Secure Headers", "Code Pulse", "OWTF"]
        }
    },
    operation: {
        label: "Operation",
        categories: {
            tools: ["Coraza", "ModSecurity"]
        }
    },
    policyGap: {
        label: "Policy Gap\\nEvaluation",
        categories: {
            guides: ["SAMM", "ASVS", "MASVS"]
        }
    },
    metrics: {
        label: "Metrics",
        categories: {}
    },
    training: {
        label: "Training/\\nEducation",
        categories: {
            tools: ["Juice Shop", "WebGoat", "Security Shepherd", "PyGoat", "Snakes", "Wrong Secrets", "Top 10", "API Top 10", "Mobile Top 10"]
        }
    },
    culture: {
        label: "Culture\\nBuilding &\\nProcess\\nMaturing",
        categories: {
            docs: ["Security Champions", "SAMM", "ASVS", "MASVS"]
        }
    }
};

// Initialize mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
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
            type: item.type,
            level: item.level || 0,
            tags: item.tags || '',
            pitch: item.pitch || ''
        }));
        
        console.log(`Loaded ${projectData.length} projects with metadata`);
        
        renderMermaidDiagram();
        updateLastUpdated();
        
    } catch (error) {
        console.error('Failed to load data:', error);
        showError('Failed to load project data. Please ensure data/metadata.json exists.');
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
    
    %% Requirements phase projects
    ReqDocs[Docs]:::categoryStyle
    Requirements --> ReqDocs
`;

    // Add Requirements projects
    const reqProjects = ['SKF', 'Security RAT', 'ASVS', 'MASVS'];
    reqProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `ReqProj${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    ReqDocs --> ${nodeId}\n`;
    });

    // Design phase - Threat Modeling
    diagram += `
    %% Design phase projects
    DesignTM[Threat Modeling]:::categoryStyle
    Design --> DesignTM
`;
    const designProjects = ['Threat Dragon', 'pytm', 'Cornucopia', 'Threat Model'];
    designProjects.forEach((name, idx) => {
        const proj = findProject(name);
        if (proj || name === 'Cornucopia' || name === 'Threat Model') {
            const title = proj ? safeLabel(proj.title) : name;
            const nodeId = `DesignProj${idx}`;
            diagram += `    ${nodeId}((${title})):::projectStyle\n`;
            diagram += `    DesignTM --> ${nodeId}\n`;
        }
    });

    // Implementation phase
    diagram += `
    %% Implementation phase projects
    ImplDocs[Docs]:::categoryStyle
    ImplDeps[Dependencies]:::categoryStyle
    ImplLibs[Secure Libraries]:::categoryStyle
    Implementation --> ImplDocs
    Implementation --> ImplDeps
    ImplDeps --> ImplLibs
`;
    
    // Implementation Docs
    const implDocProjects = ['Proactive Controls', 'Go SCP', 'Cheat Sheet'];
    implDocProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `ImplDoc${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    ImplDocs --> ${nodeId}\n`;
    });

    // Implementation Dependencies
    const implDepProjects = ['Dependency-Check', 'Dependency-Track', 'CycloneDX'];
    implDepProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `ImplDep${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    ImplDeps --> ${nodeId}\n`;
    });

    // Implementation Secure Libraries
    const implLibProjects = ['ESAPI', 'CSRFGuard', 'Secure Headers'];
    implLibProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `ImplLib${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    ImplLibs --> ${nodeId}\n`;
    });

    // Verification phase
    diagram += `
    %% Verification phase projects
    VerGuides[Guides]:::categoryStyle
    VerTools[Tools]:::categoryStyle
    VerFrameworks[Frameworks]:::categoryStyle
    Verification --> VerGuides
    Verification --> VerTools
    VerTools --> VerFrameworks
`;

    // Verification Guides
    const verGuideProjects = ['WSTG', 'MSTG'];
    verGuideProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `VerGuide${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    VerGuides --> ${nodeId}\n`;
    });

    // Verification Tools
    const verToolProjects = ['Amass', 'Nettacker', 'Code Pulse', 'Secure Headers'];
    verToolProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `VerTool${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    VerTools --> ${nodeId}\n`;
    });

    // Verification Frameworks
    const verFrameworkProjects = ['OWTF', 'Glue', 'Dracon'];
    verFrameworkProjects.forEach((name, idx) => {
        const proj = findProject(name);
        if (proj) {
            const title = safeLabel(proj.title);
            const nodeId = `VerFw${idx}`;
            diagram += `    ${nodeId}((${title})):::projectStyle\n`;
            diagram += `    VerFrameworks --> ${nodeId}\n`;
        }
    });

    // Vulnerability Management
    diagram += `
    %% Vulnerability Management
    VulnMgmt[Vulnerability Management]:::categoryStyle
    VerFrameworks --> VulnMgmt
`;
    const vulnProjects = ['Defect Dojo'];
    vulnProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `Vuln${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    VulnMgmt --> ${nodeId}\n`;
    });

    // Operation phase
    diagram += `
    %% Operation phase projects
`;
    const opProjects = ['Coraza', 'ModSecurity'];
    opProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `Op${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    Operation --> ${nodeId}\n`;
    });

    // Policy Gap Evaluation phase
    diagram += `
    %% Policy Gap Evaluation
    PolicyGuides[Guides]:::categoryStyle
    PolicyGap --> PolicyGuides
`;
    const policyProjects = ['SAMM', 'ASVS', 'MASVS'];
    policyProjects.forEach((name, idx) => {
        const proj = findProject(name);
        const title = proj ? safeLabel(proj.title) : name;
        const nodeId = `Policy${idx}`;
        diagram += `    ${nodeId}((${title})):::projectStyle\n`;
        diagram += `    PolicyGuides --> ${nodeId}\n`;
    });

    // Training phase
    diagram += `
    %% Training/Education phase projects
`;
    const trainingProjects = ['Juice Shop', 'WebGoat', 'Security Shepherd', 'PyGoat', 'Snakes', 'Wrong Secrets', 'Top 10', 'API Security', 'Mobile Top 10'];
    trainingProjects.forEach((name, idx) => {
        const proj = findProject(name);
        if (proj) {
            const title = safeLabel(proj.title);
            const nodeId = `Train${idx}`;
            diagram += `    ${nodeId}((${title})):::projectStyle\n`;
            diagram += `    Training --> ${nodeId}\n`;
        }
    });

    // Culture phase
    diagram += `
    %% Culture Building phase projects
`;
    const cultureProjects = ['Security Champions', 'SAMM', 'ASVS', 'MASVS'];
    cultureProjects.forEach((name, idx) => {
        const proj = findProject(name);
        if (proj) {
            const title = safeLabel(proj.title);
            const nodeId = `Culture${idx}`;
            diagram += `    ${nodeId}((${title})):::projectStyle\n`;
            diagram += `    Culture --> ${nodeId}\n`;
        }
    });

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
    mermaid.initialize({
        startOnLoad: false,
        theme: isDark ? 'dark' : 'base',
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
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark');
    mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
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
