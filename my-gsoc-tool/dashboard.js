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
            avatar: "https://via.placeholder.com/120",
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
        mentor: {
            name: "Mentor Name",
            email: "",
            avatar: "https://via.placeholder.com/80",
            role: "Project Mentor"
        }
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

// Render header
function renderHeader(config) {
    document.getElementById('student-name').textContent = config.student.name;
    document.getElementById('student-bio').textContent = config.student.bio;
    document.getElementById('student-avatar').src = config.student.avatar;
    document.getElementById('student-avatar').alt = config.student.name;

    const socialLinks = document.getElementById('social-links');
    socialLinks.innerHTML = '';

    if (config.student.github) {
        socialLinks.innerHTML += `
            <a href="${config.student.github}" target="_blank">
                <i class="fab fa-github"></i> GitHub
            </a>
        `;
    }

    if (config.student.linkedin) {
        socialLinks.innerHTML += `
            <a href="${config.student.linkedin}" target="_blank">
                <i class="fab fa-linkedin"></i> LinkedIn
            </a>
        `;
    }

    if (config.student.email) {
        socialLinks.innerHTML += `
            <a href="mailto:${config.student.email}">
                <i class="fas fa-envelope"></i> Email
            </a>
        `;
    }

    if (config.student.blog) {
        socialLinks.innerHTML += `
            <a href="${config.student.blog}" target="_blank">
                <i class="fas fa-blog"></i> Blog
            </a>
        `;
    }
}

// Render project info
function renderProjectInfo(config) {
    document.getElementById('project-title').textContent = config.project.title;
    document.getElementById('project-description').textContent = config.project.description;
    document.getElementById('organization').innerHTML = `
        <i class="fas fa-building"></i> Organization: ${config.project.organization}
    `;
    document.getElementById('timeline').innerHTML = `
        <i class="fas fa-calendar"></i> Timeline: ${config.project.timeline}
    `;
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
function renderSlackInfo(config) {
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

// Render blog posts
function renderBlogPosts(posts, config) {
    const blogList = document.getElementById('blog-posts');
    const blogLink = document.getElementById('blog-link');

    if (posts && posts.length > 0) {
        blogList.innerHTML = posts.map(post => `
            <div class="blog-post">
                <h3 onclick="window.open('${post.url}', '_blank')">${post.title}</h3>
                <div class="post-meta">
                    <i class="fas fa-calendar"></i> ${formatDate(post.date)}
                    ${post.readTime ? `| <i class="fas fa-clock"></i> ${post.readTime}` : ''}
                </div>
                <p>${post.excerpt}</p>
            </div>
        `).join('');
    } else {
        blogList.innerHTML = '<p style="color: var(--text-secondary);">No blog posts yet. Add your posts to data/blog-posts.json</p>';
    }

    if (config.student.blog) {
        blogLink.href = config.student.blog;
        blogLink.style.display = 'inline-block';
    }
}

// Render mentor info
function renderMentorInfo(config, feedback) {
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

// Render weekly updates
function renderWeeklyUpdates(updates) {
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

// Render milestones
function renderMilestones(milestones) {
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

// Format date helper
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// Update last updated timestamp
function updateLastUpdated() {
    const lastUpdated = document.getElementById('last-updated');
    lastUpdated.textContent = new Date().toLocaleString();
}

// Initialize dashboard
async function initDashboard() {
    try {
        // Load all data
        const config = await loadConfig();
        const githubData = await loadGitHubData(config);
        const blogPosts = await loadBlogPosts();
        const feedback = await loadFeedback();
        const weeklyUpdates = await loadWeeklyUpdates();
        const milestones = await loadMilestones();

        // Render all sections
        renderHeader(config);
        renderProjectInfo(config);
        renderGitHubStats(githubData);
        renderSlackInfo(config);
        renderBlogPosts(blogPosts, config);
        renderMentorInfo(config, feedback);
        renderWeeklyUpdates(weeklyUpdates);
        renderMilestones(milestones);
        updateLastUpdated();
    } catch (error) {
        console.error('Error initializing dashboard:', error);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);
