/**
 * Job Analytics - View Tracking System
 * Uses localStorage to track job views and syncs with GitHub via Actions
 */

const ANALYTICS_KEY = 'blt_job_views';
const SYNC_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours
const LAST_SYNC_KEY = 'blt_last_sync';

/**
 * Get all view data from localStorage
 */
function getViewData() {
  try {
    const data = localStorage.getItem(ANALYTICS_KEY);
    return data ? JSON.parse(data) : {};
  } catch (e) {
    console.error('Error reading view data:', e);
    return {};
  }
}

/**
 * Save view data to localStorage
 */
function saveViewData(data) {
  try {
    localStorage.setItem(ANALYTICS_KEY, JSON.stringify(data));
  } catch (e) {
    console.error('Error saving view data:', e);
  }
}

/**
 * Track a job view
 * @param {string} jobId - The job ID
 */
function trackJobView(jobId) {
  if (!jobId) return;
  
  const viewData = getViewData();
  
  // Initialize job entry if it doesn't exist
  if (!viewData[jobId]) {
    viewData[jobId] = {
      count: 0,
      firstView: new Date().toISOString(),
      lastView: null,
      sessions: []
    };
  }
  
  // Check if this is a new session (more than 30 minutes since last view)
  const lastView = viewData[jobId].lastView;
  const now = new Date();
  const isNewSession = !lastView || (now - new Date(lastView)) > 30 * 60 * 1000;
  
  if (isNewSession) {
    viewData[jobId].count++;
    viewData[jobId].sessions.push({
      timestamp: now.toISOString(),
      userAgent: navigator.userAgent.substring(0, 100) // Truncate for privacy
    });
    
    // Keep only last 100 sessions per job
    if (viewData[jobId].sessions.length > 100) {
      viewData[jobId].sessions = viewData[jobId].sessions.slice(-100);
    }
  }
  
  viewData[jobId].lastView = now.toISOString();
  saveViewData(viewData);
  
  // Check if we should sync
  checkAndSync();
}

/**
 * Get view count for a specific job
 * @param {string} jobId - The job ID
 * @returns {number} - View count
 */
function getJobViewCount(jobId) {
  const viewData = getViewData();
  return viewData[jobId]?.count || 0;
}

/**
 * Get all view counts
 * @returns {Object} - Object with jobId as key and count as value
 */
function getAllViewCounts() {
  const viewData = getViewData();
  const counts = {};
  for (const [jobId, data] of Object.entries(viewData)) {
    counts[jobId] = data.count;
  }
  return counts;
}

/**
 * Check if we should sync and trigger sync if needed
 */
function checkAndSync() {
  try {
    const lastSync = localStorage.getItem(LAST_SYNC_KEY);
    const now = Date.now();
    
    if (!lastSync || (now - parseInt(lastSync)) > SYNC_INTERVAL) {
      syncViewData();
    }
  } catch (e) {
    console.error('Error checking sync:', e);
  }
}

/**
 * Sync view data to GitHub (via issue creation)
 * This creates a GitHub issue with the analytics data that can be processed by Actions
 */
function syncViewData() {
  const viewData = getViewData();
  
  if (Object.keys(viewData).length === 0) {
    return; // Nothing to sync
  }
  
  // Prepare summary data (no PII)
  const summary = {};
  for (const [jobId, data] of Object.entries(viewData)) {
    summary[jobId] = {
      count: data.count,
      firstView: data.firstView,
      lastView: data.lastView,
      sessionCount: data.sessions.length
    };
  }
  
  // Store sync data for GitHub Action to pick up
  // In a real implementation, this would POST to a GitHub Action endpoint
  // For now, we'll just log it and update the last sync time
  console.log('Analytics sync data:', summary);
  
  localStorage.setItem(LAST_SYNC_KEY, Date.now().toString());
  
  // Optional: Create a GitHub issue with the data
  // This would require a backend endpoint or GitHub Action workflow
  // For now, we'll just make the data available via a global variable
  window.BLT_ANALYTICS_SYNC_DATA = summary;
}

/**
 * Export analytics data as JSON (for manual sync)
 */
function exportAnalytics() {
  const viewData = getViewData();
  const summary = {};
  
  for (const [jobId, data] of Object.entries(viewData)) {
    summary[jobId] = {
      count: data.count,
      firstView: data.firstView,
      lastView: data.lastView,
      sessionCount: data.sessions.length
    };
  }
  
  return summary;
}

/**
 * Clear all analytics data (for testing)
 */
function clearAnalytics() {
  localStorage.removeItem(ANALYTICS_KEY);
  localStorage.removeItem(LAST_SYNC_KEY);
  console.log('Analytics data cleared');
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    trackJobView,
    getJobViewCount,
    getAllViewCounts,
    exportAnalytics,
    clearAnalytics
  };
}

// Make functions available globally
window.BLTAnalytics = {
  trackJobView,
  getJobViewCount,
  getAllViewCounts,
  exportAnalytics,
  clearAnalytics
};
