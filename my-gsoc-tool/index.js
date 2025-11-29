import { IS_EDITABLE } from "./libs/constants.js";
import { renderHeader } from "./components/header.js";
import { renderProjectInfo } from "./components/project.js";
import { renderGitHubStats, renderSlackInfo } from "./components/stats.js";
import { renderBlogPosts } from "./components/blogs.js";
import { renderMentorInfo } from "./components/mentor.js";
import { renderWeeklyUpdates } from "./components/updates.js";
import { renderMilestones } from "./components/milestones.js";
import { renderEditableButtonSection, updateLastUpdated } from "./libs/utils.js";
import { loadConfig, loadGitHubData, loadBlogPosts, loadMentorConfig, loadWeeklyUpdates, loadMilestones } from "./libs/config-loader.js";

// Initialize dashboard
async function initDashboard() {
  try {
    const config = await loadConfig();
    const githubData = await loadGitHubData(config);
    const blogPosts = await loadBlogPosts();
    const mentorConfig = await loadMentorConfig();
    const weeklyUpdates = await loadWeeklyUpdates();
    const milestones = await loadMilestones();

    // Render all sections
    renderEditableButtonSection();
    renderHeader(config);
    renderProjectInfo(config);
    renderGitHubStats(githubData);
    renderSlackInfo(config);
    renderBlogPosts(blogPosts, config);
    renderMentorInfo(mentorConfig);
    renderWeeklyUpdates(weeklyUpdates);
    renderMilestones(milestones);
    updateLastUpdated();
  } catch (error) {
    console.error("Error initializing dashboard:", error);
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", initDashboard);
