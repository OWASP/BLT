
import { formatDate } from "../libs/utils.js";

export function renderGitHubStats(data) {
    document.getElementById('total-commits').textContent = data.stats.commits || 0;
    document.getElementById('total-prs').textContent = data.stats.pullRequests || 0;
    document.getElementById('total-issues').textContent = data.stats.issues || 0;
    document.getElementById('total-reviews').textContent = data.stats.reviews || 0;

    const contributionList = document.getElementById('contribution-list');
    if (data.contributions && data.contributions.length > 0) {
        contributionList.innerHTML = data.contributions.map(contrib => `
            <div class="contribution-item">
                <h4>${contrib.title}</h4>
                <p>${contrib.description}</p>
                <div class="date">
                    <i class="fas fa-clock"></i> ${formatDate(contrib.date)}
                    ${contrib.url ? `| <a href="${contrib.url}" target="_blank">View on GitHub</a>` : ''}
                </div>
            </div>
        `).join('');
    } else {
        contributionList.innerHTML = '<p style="color: var(--text-secondary);">No contributions data available yet. The GitHub Actions workflow will populate this automatically.</p>';
    }
}


// Render Slack info
export function renderSlackInfo(config) {
    const slackChannels = document.getElementById('slack-channels');
    const slackLink = document.getElementById('slack-link');

    if (config.slack.channels && config.slack.channels.length > 0) {
        slackChannels.innerHTML = config.slack.channels.map(channel => `
            <div class="channel-item">
                <i class="fas fa-hashtag"></i>
                <span>${channel}</span>
            </div>
        `).join('');
    } else {
        slackChannels.innerHTML = '<p style="color: var(--text-secondary);">Configure your Slack channels in config.json</p>';
    }

    if (config.slack.workspaceUrl) {
        slackLink.href = config.slack.workspaceUrl;
        slackLink.style.display = 'inline-block';
    }
}