
// Load configuration
export async function loadConfig() {
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

export async function loadProjectInfo() {
    try {
        const response = await fetch('data/project.json');
        if (!response.ok) {
            throw new Error('Project info file not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading project info:', error);
        return {};
    }
}

export async function loadSlackInfo() {
    try {
        const response = await fetch('data/slack.json');
        if (!response.ok) {
            throw new Error('Slack info file not found');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading slack info:', error);
        return {};
    }
}

// Default configuration
export function getDefaultConfig() {
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
export async function loadGitHubData(config) {
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
export async function loadBlogPosts() {
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
export async function loadMentorConfig() {
    try {
        const response = await fetch('data/mentor.json');
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
export async function loadWeeklyUpdates() {
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
export async function loadMilestones() {
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
