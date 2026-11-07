// Dashboard JavaScript for GSoC Student Dashboard

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('config.json');
        if (!response.ok) {
            throw new Error('Config file not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading config:', error);
        return getDefaultConfig();
    }
}

// Default configuration
function getDefaultConfig() {
    return {
        student: {
            name: "GSoC Student",
            bio: "Google Summer of Code Contributor",
            avatar: "assets/images/sample-avatar.svg",
            github: "",
            email: "",
            blog: "",
            linkedin: ""
        },
        project: {
            title: "My GSoC Project",
            description: "Working on an amazing open-source project through Google Summer of Code",
            organization: "Open Source Organization",
            timeline: "May 2024 - August 2024"
        },
        slack: {
            workspaceUrl: "",
            channels: []
        },
        mentors: [
            {
                name: "Mentor Name",
                email: "",
                avatar: "assets/images/sample-mentor.svg",
                role: "Lead Mentor"
            }
        ]
    };
}

// Load GitHub contributions data
async function loadGitHubData(config) {
    try {
        const response = await fetch('data/github-contributions.json');
        if (!response.ok) {
            throw new Error('GitHub data not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading GitHub data:', error);
        return {
            stats: { commits: 0, pullRequests: 0, issues: 0, reviews: 0 },
            contributions: []
        };
    }
}

// Load blog posts
async function loadBlogPosts() {
    try {
        const response = await fetch('data/blog-posts.json');
        if (!response.ok) {
            throw new Error('Blog data not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading blog posts:', error);
        return [];
    }
}

// Load feedback data
async function loadFeedback() {
    try {
        const response = await fetch('data/feedback.json');
        if (!response.ok) {
            throw new Error('Feedback data not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading feedback:', error);
        return [];
    }
}

// Load weekly updates
async function loadWeeklyUpdates() {
    try {
        const response = await fetch('data/weekly-updates.json');
        if (!response.ok) {
            throw new Error('Weekly updates not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading weekly updates:', error);
        return [];
    }
}

// Load milestones
async function loadMilestones() {
    try {
        const response = await fetch('data/milestones.json');
        if (!response.ok) {
            throw new Error('Milestones not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading milestones:', error);
        return [];
    }
}

// Values still holding the template's placeholders (config.example.json) are left out.
const PLACEHOLDER = /^(your\b|tbd$|mentor name$|co-mentor name$|lead mentor$|co-mentor [12]$)|example\.com|yourblog\.dev|YOUR-|MENTOR-USERNAME|PROJECT-REPOSITORY|20XX|\/xxx$/i;

function filled(value) {
    const text = String(value == null ? '' : value).trim();
    return text && !PLACEHOLDER.test(text) ? text : '';
}

// Render header
function renderHeader(config) {
    const student = config.student || {};
    const avatar = document.getElementById('student-avatar');
    document.getElementById('student-name').textContent = filled(student.name) || 'GSoC Student';
    document.getElementById('student-bio').textContent = filled(student.bio) || 'Google Summer of Code Contributor';
    if (httpsUrl(student.avatar)) avatar.src = httpsUrl(student.avatar);
    avatar.alt = filled(student.name) || 'Student avatar';
    document.title = `${filled(student.name) || 'GSoC Student'} | GSoC Dashboard`;

    const links = [
        [httpsUrl(filled(student.github)), 'fab fa-github', 'GitHub'],
        [httpsUrl(filled(student.linkedin)), 'fab fa-linkedin', 'LinkedIn'],
        [/^[^\s@<>"']+@[^\s@<>"']+$/.test(filled(student.email)) ? `mailto:${filled(student.email)}` : '', 'fas fa-envelope', 'Email'],
        [httpsUrl(filled(student.blog)), 'fas fa-blog', 'Blog'],
    ];
    document.getElementById('social-links').innerHTML = links
        .filter(([href]) => href)
        .map(([href, icon, label]) => `
            <a href="${escapeHtml(href)}"${href.startsWith('mailto:') ? '' : ' target="_blank" rel="noopener noreferrer"'}>
                <i class="${icon}"></i> ${label}
            </a>
        `).join('');
}

// Render project info
function renderProjectInfo(config) {
    const project = config.project || {};
    const repository = httpsUrl(filled(project.repository));
    document.getElementById('project-title').textContent = filled(project.title) || 'Project to be announced';
    document.getElementById('project-description').textContent = filled(project.description) || '';
    const meta = [
        ['fas fa-building', 'Organization', escapeHtml(filled(project.organization))],
        ['fas fa-calendar', 'Timeline', escapeHtml(filled(project.timeline))],
        ['fas fa-code-branch', 'Repository', repository
            ? `<a href="${escapeHtml(repository)}" target="_blank" rel="noopener noreferrer">${escapeHtml(repository.replace(/^https:\/\//, ''))}</a>` : ''],
    ].filter(([, , value]) => value);
    document.getElementById('project-meta').innerHTML = meta
        .map(([icon, label, value]) => `<span class="meta-item"><i class="${icon}"></i> ${label}: ${value}</span>`)
        .join('');
}

// Contributions come from GitHub event data, which carries other people's issue and PR titles
// and bodies: escape them, and link only https URLs.
function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function httpsUrl(url) {
    const value = String(url || '').trim();
    return /^https:\/\/[^\s"'<>]+$/i.test(value) ? value : '';
}

// Render GitHub stats
function renderGitHubStats(data) {
    document.getElementById('total-commits').textContent = data.stats.commits || 0;
    document.getElementById('total-prs').textContent = data.stats.pullRequests || 0;
    document.getElementById('total-issues').textContent = data.stats.issues || 0;
    document.getElementById('total-reviews').textContent = data.stats.reviews || 0;

    const contributionList = document.getElementById('contribution-list');
    if (data.contributions && data.contributions.length > 0) {
        contributionList.innerHTML = data.contributions.map(contrib => `
            <div class="contribution-item">
                <h4>${escapeHtml(contrib.title)}</h4>
                <p>${escapeHtml(contrib.description)}</p>
                <div class="date">
                    <i class="fas fa-clock"></i> ${escapeHtml(formatDate(contrib.date))}
                    ${httpsUrl(contrib.url) ? `| <a href="${escapeHtml(httpsUrl(contrib.url))}" target="_blank" rel="noopener noreferrer">View on GitHub</a>` : ''}
                </div>
            </div>
        `).join('');
    } else {
        contributionList.innerHTML = '<p class="empty-note">No public GitHub activity yet. It is refreshed daily from your GitHub profile.</p>';
    }
}

// Render Slack info
function renderSlackInfo(config) {
    const slackChannels = document.getElementById('slack-channels');
    const slackLink = document.getElementById('slack-link');

    config.slack = config.slack || {};
    if (config.slack.channels && config.slack.channels.length > 0) {
        slackChannels.innerHTML = config.slack.channels.map(channel => `
            <div class="channel-item">
                <i class="fas fa-hashtag"></i>
                <span>${escapeHtml(channel)}</span>
            </div>
        `).join('');
    } else {
        slackChannels.innerHTML = '<p class="empty-note">Configure your Slack channels in config.json</p>';
    }

    if (httpsUrl(filled(config.slack.workspaceUrl))) {
        slackLink.href = httpsUrl(config.slack.workspaceUrl);
        slackLink.hidden = false;
    }
}

// Render blog posts
function renderBlogPosts(posts, config) {
    const blogList = document.getElementById('blog-posts');
    const blogLink = document.getElementById('blog-link');

    if (posts && posts.length > 0) {
        blogList.innerHTML = posts.map(post => {
            const url = httpsUrl(filled(post.url));
            const title = escapeHtml(post.title);
            return `
            <div class="blog-post">
                <h3>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${title}</a>` : title}</h3>
                <div class="post-meta">
                    <i class="fas fa-calendar"></i> ${escapeHtml(formatDate(post.date))}
                    ${post.readTime ? `· <i class="fas fa-clock"></i> ${escapeHtml(post.readTime)}` : ''}
                </div>
                <p>${escapeHtml(post.excerpt)}</p>
            </div>
        `;
        }).join('');
    } else {
        blogList.innerHTML = '<p class="empty-note">No blog posts yet. Add your posts to data/blog-posts.json</p>';
    }

    if (httpsUrl(filled(config.student.blog))) {
        blogLink.href = httpsUrl(config.student.blog);
        blogLink.hidden = false;
    }
}

// Render mentor info
function renderMentorInfo(config, feedback) {
    if (!config) {
        console.warn('renderMentorInfo: missing config');
        return;
    }

    const mentorDetails = document.getElementById('mentor-details');
    const feedbackList = document.getElementById('feedback-list');

    if (!mentorDetails || !feedbackList) {
        console.warn('renderMentorInfo: required DOM elements missing');
        return;
    }

    // Normalize mentors: support both old single "mentor" and new "mentors" array
    let mentors = [];
    if (Array.isArray(config.mentors) && config.mentors.length > 0) {
        mentors = config.mentors;
    } else if (config.mentor) {
        mentors = [config.mentor];
    }

    // Only mentors with a real name are shown; a placeholder slot says how to add one.
    const shownMentors = mentors.filter((mentor) => mentor && filled(mentor.name));

    if (shownMentors.length === 0) {
        mentorDetails.innerHTML =
            '<p class="empty-note">Add your mentors to <code>mentors</code> in config.json.</p>';
    } else {
        mentorDetails.innerHTML = shownMentors
            .map((mentor, index) => {
                const github = httpsUrl(filled(mentor.github));
                const email = filled(mentor.email);
                return `
                <div class="mentor-card">
                    <img src="${escapeHtml(httpsUrl(filled(mentor.avatar)) || 'assets/images/sample-mentor.svg')}"
                         alt="" class="mentor-avatar" data-fallback="assets/images/sample-mentor.svg">
                    <div class="mentor-info">
                        <h3>${escapeHtml(filled(mentor.name))}</h3>
                        <p>${escapeHtml(filled(mentor.role) || (index === 0 ? 'Lead Mentor' : 'Co-Mentor'))}</p>
                        <p class="mentor-links">
                            ${github ? `<a href="${escapeHtml(github)}" target="_blank" rel="noopener noreferrer"><i class="fab fa-github"></i> GitHub</a>` : ''}
                            ${/^[^\s@<>"']+@[^\s@<>"']+$/.test(email) ? `<a href="mailto:${escapeHtml(email)}"><i class="fas fa-envelope"></i> Email</a>` : ''}
                        </p>
                    </div>
                </div>
                `;
            })
            .join('');
    }

    if (feedback && feedback.length > 0) {
        // Get all mentor names (actual mentors only, not placeholders)
        const actualMentorNames = shownMentors.map((m) => filled(m.name));
        const primaryMentorName = actualMentorNames[0] || 'Mentor';

        feedbackList.innerHTML = feedback
            .map((item, index) => {
                // Replace placeholder "Mentor Name" with actual mentor name, or use provided name
                let displayName = item.from;
                if (!displayName || displayName === 'Mentor Name') {
                    if (actualMentorNames.length > 0) {
                        const mentorIndex = index % actualMentorNames.length;
                        displayName = actualMentorNames[mentorIndex];
                    } else {
                        displayName = primaryMentorName;
                    }
                }

                const dateText = item.date ? formatDate(item.date) : '';

                return `
                <div class="feedback-item">
                    <div class="feedback-header">
                        <strong>${escapeHtml(displayName)}</strong>
                        <span class="feedback-date">${escapeHtml(dateText)}</span>
                    </div>
                    <div class="feedback-content">${escapeHtml(item.content)}</div>
                </div>
                `;
            })
            .join('');
    } else {
        feedbackList.innerHTML =
            '<p class="empty-note">No feedback yet. Feedback will appear here as your mentor provides input.</p>';
    }
}

// Render weekly updates
function renderWeeklyUpdates(updates) {
    const timeline = document.getElementById('weekly-updates');
    if (updates && updates.length > 0) {
        timeline.innerHTML = updates.map(update => `
            <div class="timeline-item">
                <h4>${escapeHtml(update.title)}</h4>
                <p>${escapeHtml(update.summary)}</p>
                <div class="timeline-date">
                    <i class="fas fa-calendar"></i> ${escapeHtml(formatDate(update.date))}
                </div>
            </div>
        `).join('');
    } else {
        timeline.innerHTML = '<p class="empty-note">No weekly updates yet. Add your updates to data/weekly-updates.json</p>';
    }
}

// Render milestones
function renderMilestones(milestones) {
    const milestoneList = document.getElementById('milestone-list');
    if (milestones && milestones.length > 0) {
        milestoneList.innerHTML = milestones.map(milestone => `
            <div class="milestone-item">
                <div class="milestone-icon">
                    <i class="fas fa-${/^[a-z0-9-]+$/.test(milestone.icon || '') ? milestone.icon : 'trophy'}"></i>
                </div>
                <div class="milestone-content">
                    <h4>${escapeHtml(milestone.title)}</h4>
                    <p>${escapeHtml(milestone.description)}</p>
                    <div class="milestone-date">
                        <i class="fas fa-calendar"></i> ${escapeHtml(formatDate(milestone.date))}
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        milestoneList.innerHTML = '<p class="empty-note">No milestones yet. Add your achievements to data/milestones.json</p>';
    }
}

// Format date helper
function formatDate(dateString) {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '';
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// When the GitHub activity was last refreshed
function updateLastUpdated(githubData) {
    const lastUpdated = document.getElementById('last-updated');
    const when = githubData && Date.parse(githubData.lastUpdated);
    lastUpdated.textContent = when ? new Date(when).toLocaleString() : 'not yet';
}

// A few other live dashboards, linking to the full directory (directory.js has the sources).
async function renderPeers(config) {
    const row = document.getElementById('peer-row');
    if (!row) return;
    let data = null;
    for (const source of ['data/directory.json', 'https://gsoc-tool.owaspblt.org/data/directory.json']) {
        try {
            const response = await fetch(source);
            if (response.ok) data = await response.json();
        } catch (error) {
            data = null;
        }
        if (data && Array.isArray(data.sites) && data.sites.length) break;
    }
    const here = location.origin + location.pathname.replace(/[^/]*$/, '');
    const sites = ((data && data.sites) || [])
        .filter((site) => httpsUrl(site.url) && site.url !== here)
        .sort((a, b) => ((b.stats || {}).mergedPullRequests || 0) - ((a.stats || {}).mergedPullRequests || 0));
    document.getElementById('peer-count').textContent = `${sites.length || 'Other'} students using this dashboard`;
    row.innerHTML = sites.slice(0, 12).map((site) => `
        <a class="peer" href="${escapeHtml(site.url)}" target="_blank" rel="noopener noreferrer">
            <img src="${escapeHtml(httpsUrl(site.avatar) || 'assets/images/sample-avatar.svg')}" alt="" loading="lazy" data-fallback="assets/images/sample-avatar.svg">
            <span>${escapeHtml(site.name || site.username)}</span>
            ${site.stats && site.stats.mergedPullRequests ? `<small title="Merged pull requests">${Number(site.stats.mergedPullRequests)}</small>` : ''}
        </a>
    `).join('') || '<p class="empty-note">No other dashboards found yet.</p>';
}

// Broken image links (a placeholder GitHub user, say) fall back to the sample picture.
document.addEventListener('error', (event) => {
    const img = event.target;
    if (img.tagName === 'IMG' && img.dataset.fallback && !img.src.endsWith(img.dataset.fallback)) img.src = img.dataset.fallback;
}, true);

// Initialize dashboard
async function initDashboard() {
    try {
        // Load all data
        const config = await loadConfig();
        const [githubData, blogPosts, feedback, weeklyUpdates, milestones] = await Promise.all([
            loadGitHubData(config), loadBlogPosts(), loadFeedback(), loadWeeklyUpdates(), loadMilestones(),
        ]);

        // Render all sections
        renderHeader(config);
        renderProjectInfo(config);
        renderGitHubStats(githubData);
        renderSlackInfo(config);
        renderBlogPosts(blogPosts, config);
        renderMentorInfo(config, feedback);
        renderWeeklyUpdates(weeklyUpdates);
        renderMilestones(milestones);
        updateLastUpdated(githubData);
        renderPeers(config);
    } catch (error) {
        console.error('Error initializing dashboard:', error);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);
