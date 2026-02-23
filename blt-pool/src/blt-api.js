'use strict';

const axios = require('axios');

const BLT_API_BASE_URL = process.env.BLT_API_URL || 'https://blt-api.owasp-blt.workers.dev';

/**
 * Report a bug to the BLT API from a GitHub issue.
 * @param {Object} issueData - Data from the GitHub issue
 * @returns {Promise<Object|null>} The created bug data or null on error
 */
async function reportBugToBLT(issueData) {
  const { url, description, githubUrl, label } = issueData;

  try {
    const response = await axios.post(`${BLT_API_BASE_URL}/bugs`, {
      url: url || githubUrl,
      description: description,
      github_url: githubUrl,
      label: label || 'general',
      status: 'open',
    }, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });

    if (response.data && response.data.success) {
      return response.data.data;
    }
    return null;
  } catch (err) {
    console.error('Failed to report bug to BLT API:', err.message);
    return null;
  }
}

/**
 * Fetch bugs from BLT API, optionally filtered by domain or status.
 * @param {Object} options
 * @returns {Promise<Array>}
 */
async function fetchBugsFromBLT(options = {}) {
  const { page = 1, perPage = 10, status, domain } = options;
  const params = { page, per_page: perPage };
  if (status) params.status = status;
  if (domain) params.domain = domain;

  try {
    const response = await axios.get(`${BLT_API_BASE_URL}/bugs`, { params, timeout: 10000 });
    if (response.data && response.data.success) {
      return response.data.data || [];
    }
    return [];
  } catch (err) {
    console.error('Failed to fetch bugs from BLT API:', err.message);
    return [];
  }
}

/**
 * Search bugs in BLT API.
 * @param {string} query
 * @returns {Promise<Array>}
 */
async function searchBugsInBLT(query) {
  try {
    const response = await axios.get(`${BLT_API_BASE_URL}/bugs/search`, {
      params: { q: query, limit: 10 },
      timeout: 10000,
    });
    if (response.data && response.data.success) {
      return response.data.data || [];
    }
    return [];
  } catch (err) {
    console.error('Failed to search bugs in BLT API:', err.message);
    return [];
  }
}

module.exports = { reportBugToBLT, fetchBugsFromBLT, searchBugsInBLT };
