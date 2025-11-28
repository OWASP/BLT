
import { formatDate } from "../libs/utils.js";

// Render milestones
export function renderMilestones(milestones) {
    const milestoneList = document.getElementById('milestones');
    if (milestones && milestones.length > 0) {
        milestoneList.innerHTML = milestones.map(milestone => `
            <div class="milestone-item">
                <div class="milestone-icon">
                    <i class="fas fa-${milestone.icon || 'trophy'}"></i>
                </div>
                <div class="milestone-content">
                    <h4>${milestone.title}</h4>
                    <p>${milestone.description}</p>
                    <div class="milestone-date">
                        <i class="fas fa-calendar"></i> ${formatDate(milestone.date)}
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        milestoneList.innerHTML = '<p style="color: var(--text-secondary);">No milestones yet. Add your achievements to data/milestones.json</p>';
    }
}
