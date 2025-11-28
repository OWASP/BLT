import { IS_EDITABLE } from "./libs/constants.js";
import { renderHeader } from "./components/header.js";
import { renderProjectInfo } from "./components/project.js";
import { renderGitHubStats, renderSlackInfo } from "./components/stats.js";
import { renderBlogPosts } from "./components/blogs.js";
import { renderMentorInfo } from "./components/mentor.js";
import { renderWeeklyUpdates } from "./components/updates.js";
import { renderMilestones } from "./components/milestones.js";
import { renderEditableButtonSection, updateLastUpdated } from "./libs/utils.js";
import { loadConfig, loadGitHubData, loadBlogPosts, loadFeedback, loadWeeklyUpdates, loadMilestones } from "./libs/config-loader.js";

// Initialize dashboard
async function initDashboard() {
    try {
        console.log('Starting dashboard initialization...');
        
        // Load all data
        console.log('Loading config...');
        const config = await loadConfig();
        console.log('Config loaded:', config);
        
        console.log('Loading GitHub data...');
        const githubData = await loadGitHubData(config);
        console.log('GitHub data loaded:', githubData);
        
        console.log('Loading blog posts...');
        const blogPosts = await loadBlogPosts();
        console.log('Blog posts loaded:', blogPosts);
        
        console.log('Loading feedback...');
        const feedback = await loadFeedback();
        console.log('Feedback loaded:', feedback);
        
        console.log('Loading weekly updates...');
        const weeklyUpdates = await loadWeeklyUpdates();
        console.log('Weekly updates loaded:', weeklyUpdates);
        
        console.log('Loading milestones...');
        const milestones = await loadMilestones();
        console.log('Milestones loaded:', milestones);

        // Render all sections
        console.log('Rendering components...');
        renderEditableButtonSection();
        renderHeader(config);
        renderProjectInfo(config);
        renderGitHubStats(githubData);
        renderSlackInfo(config);
        renderBlogPosts(blogPosts, config);
        renderMentorInfo(config, feedback);
        renderWeeklyUpdates(weeklyUpdates);
        renderMilestones(milestones);
        updateLastUpdated();
        
        console.log('Dashboard initialization complete!');
    } catch (error) {
        console.error('Error initializing dashboard:', error);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);
