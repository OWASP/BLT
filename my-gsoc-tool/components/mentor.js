import { formatDate } from "../libs/utils.js";

export function renderMentorInfo(config, feedback) {
    const mentorDetails = document.getElementById('mentor-details');
    mentorDetails.innerHTML = `
        <img src="${config.mentor.avatar}" alt="${config.mentor.name}" class="mentor-avatar">
        <div class="mentor-info">
            <h3>${config.mentor.name}</h3>
            <p>${config.mentor.role}</p>
            ${config.mentor.email ? `<p><i class="fas fa-envelope"></i> ${config.mentor.email}</p>` : ''}
        </div>
    `;

    const feedbackList = document.getElementById('feedback-list');
    if (feedback && feedback.length > 0) {
        feedbackList.innerHTML = feedback.map(item => `
            <div class="feedback-item">
                <div class="feedback-header">
                    <strong>${item.from || config.mentor.name}</strong>
                    <span class="feedback-date">${formatDate(item.date)}</span>
                </div>
                <div class="feedback-content">${item.content}</div>
            </div>
        `).join('');
    } else {
        feedbackList.innerHTML = '<p style="color: var(--text-secondary);">No feedback yet. Feedback will appear here as your mentor provides input.</p>';
    }
}
