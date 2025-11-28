import { formatDate } from "../libs/utils.js";


// Render weekly updates
export function renderWeeklyUpdates(updates) {
    const timeline = document.getElementById('weekly-updates');
    if (updates && updates.length > 0) {
        timeline.innerHTML = updates.map(update => `
            <div class="timeline-item">
                <h4>${update.title}</h4>
                <p>${update.summary}</p>
                <div class="timeline-date">
                    <i class="fas fa-calendar"></i> ${formatDate(update.date)}
                </div>
            </div>
        `).join('');
    } else {
        timeline.innerHTML = '<p style="color: var(--text-secondary);">No weekly updates yet. Add your updates to data/weekly-updates.json</p>';
    }
}
