// Render project info
export function renderProjectInfo(config) {
    document.getElementById('project-title').textContent = config.project.title;
    document.getElementById('project-description').textContent = config.project.description;
    document.getElementById('organization').innerHTML = `
        <i class="fas fa-building"></i> Organization: ${config.project.organization}
    `;
    document.getElementById('timeline').innerHTML = `
        <i class="fas fa-calendar"></i> Timeline: ${config.project.timeline}
    `;
}