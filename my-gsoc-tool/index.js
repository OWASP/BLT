import { IS_EDITABLE } from "./libs/constants.js";
import { renderHeader } from "./components/header.js";
import { renderProjectInfo } from "./components/project.js";
import { renderGitHubStats, renderCommunityParticipation } from "./components/stats.js";
import { renderBlogPosts } from "./components/blogs.js";
import { renderMentorInfo } from "./components/mentor.js";
import { renderWeeklyUpdates } from "./components/updates.js";
import { renderMilestones } from "./components/milestones.js";
import { updateLastUpdated } from "./libs/utils.js";
import { loadConfig, loadGitHubData, loadBlogPosts, loadMentorConfig, loadWeeklyUpdates, loadMilestones, loadProjectInfo, loadCommunityInfo } from "./libs/config-loader.js";
import { setGitHubToken, hasToken } from "./libs/api.js";

// Initialize dashboard
async function initDashboard() {
  try {
    const config = await loadConfig();
    const githubData = await loadGitHubData(config);
    const blogPosts = await loadBlogPosts();
    const mentorConfig = await loadMentorConfig();
    const weeklyUpdates = await loadWeeklyUpdates();
    const milestones = await loadMilestones();
    const projectData = await loadProjectInfo()
    const communityInfo = await loadCommunityInfo()
    // Render all sections
    renderHeader(config);
    renderProjectInfo(projectData);
    renderGitHubStats(githubData);
    renderCommunityParticipation(communityInfo);
    renderBlogPosts(blogPosts, config);
    renderMentorInfo(mentorConfig);
    renderWeeklyUpdates(weeklyUpdates);
    renderMilestones(milestones);
    updateLastUpdated();
    initEditMode();
  } catch (error) {
    console.error("Error initializing dashboard:", error);
  }
}

function initEditMode() {
  const editModeBtn = document.getElementById('edit-mode-btn');
  const tokenSection = document.getElementById('token-section');
  const githubTokenInput = document.getElementById('github-token');
  const saveTokenBtn = document.getElementById('save-token-btn');
  const removeTokenBtn = document.getElementById('remove-token-btn');

  function updateTokenUI() {
    if (hasToken()) {
      githubTokenInput.placeholder = 'Token saved ✓';
      githubTokenInput.disabled = true;
      githubTokenInput.value = '';
      removeTokenBtn.style.display = 'inline-block';
      saveTokenBtn.textContent = 'Update Token';
    } else {
      githubTokenInput.placeholder = 'GitHub Token (repo scope)';
      githubTokenInput.disabled = false;
      githubTokenInput.value = '';
      removeTokenBtn.style.display = 'none';
      saveTokenBtn.textContent = 'Save Token';
    }
  }

  if (IS_EDITABLE) {
    tokenSection.style.display = 'block';
    updateTokenUI();
  } else {
    editModeBtn.style.display = 'inline-block';
  }

  editModeBtn?.addEventListener('click', () => {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set('edit', 'true');
    window.location.href = currentUrl.toString();
  });

  saveTokenBtn?.addEventListener('click', () => {
    if (saveTokenBtn.textContent === 'Update Token') {
      // Switch to edit mode
      githubTokenInput.disabled = false;
      githubTokenInput.placeholder = 'Enter new token';
      githubTokenInput.value = '';
      githubTokenInput.focus();
      saveTokenBtn.textContent = 'Save Token';
      removeTokenBtn.style.display = 'none';
    } else {
      // Save token
      const tokenValue = githubTokenInput.value.trim();
      if (tokenValue) {
        setGitHubToken(tokenValue);
        updateTokenUI();
      }
    }
  });

  removeTokenBtn?.addEventListener('click', () => {
    setGitHubToken(null);
    updateTokenUI();
  });
}

document.addEventListener("DOMContentLoaded", initDashboard);
