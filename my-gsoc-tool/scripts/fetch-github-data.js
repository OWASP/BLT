#!/usr/bin/env node
// Fetches the student's recent public GitHub activity into public/data/github-contributions.json.
// Run by .forkmesh/my-gsoc-tool--update-dashboard.yml (was generated inline by the GitHub workflow).
const fs = require('fs');
const https = require('https');

// Read config
const config = JSON.parse(fs.readFileSync('public/config.json', 'utf8'));

// Extract GitHub username from URL
const githubUrl = config.student?.github || '';
const username = githubUrl.split('/').pop() || 'example-user';
const repo = config.project?.repository ? config.project.repository.split('/').slice(-2).join('/') : '';

console.log(`Fetching data for user: ${username}`);

// Function to make GitHub API request
function makeRequest(path) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.github.com',
      path: path,
      headers: {
        'User-Agent': 'GSoC-Dashboard',
        ...(process.env.GITHUB_TOKEN ? { 'Authorization': `token ${process.env.GITHUB_TOKEN}` } : {}),
        'Accept': 'application/vnd.github.v3+json'
      }
    };

    https.get(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          resolve([]);
        }
      });
    }).on('error', reject);
  });
}

// Main function
async function fetchData() {
  try {
    // Get user events
    const events = await makeRequest(`/users/${username}/events/public?per_page=100`);
    
    // Count contributions
    const stats = {
      commits: 0,
      pullRequests: 0,
      issues: 0,
      reviews: 0
    };

    const contributions = [];
    const seenEvents = new Set();

    events.forEach(event => {
      const eventId = event.id;
      if (seenEvents.has(eventId)) return;
      seenEvents.add(eventId);

      if (event.type === 'PushEvent') {
        stats.commits += event.payload.commits?.length || 0;
        contributions.push({
          title: `Pushed commits to ${event.repo.name}`,
          description: event.payload.commits?.[0]?.message || 'Code changes',
          date: event.created_at.split('T')[0],
          url: `https://github.com/${event.repo.name}`,
          type: 'commit'
        });
      } else if (event.type === 'PullRequestEvent') {
        stats.pullRequests++;
        contributions.push({
          title: `${event.payload.action} PR: ${event.payload.pull_request.title}`,
          description: event.payload.pull_request.body?.substring(0, 150) || 'Pull request',
          date: event.created_at.split('T')[0],
          url: event.payload.pull_request.html_url,
          type: 'pull_request'
        });
      } else if (event.type === 'IssuesEvent') {
        stats.issues++;
        contributions.push({
          title: `${event.payload.action} issue: ${event.payload.issue.title}`,
          description: event.payload.issue.body?.substring(0, 150) || 'Issue',
          date: event.created_at.split('T')[0],
          url: event.payload.issue.html_url,
          type: 'issue'
        });
      } else if (event.type === 'PullRequestReviewEvent') {
        stats.reviews++;
        contributions.push({
          title: `Reviewed PR: ${event.payload.pull_request.title}`,
          description: 'Pull request review',
          date: event.created_at.split('T')[0],
          url: event.payload.pull_request.html_url,
          type: 'review'
        });
      }
    });

    // Sort by date and limit
    contributions.sort((a, b) => new Date(b.date) - new Date(a.date));
    const limitedContributions = contributions.slice(0, 20);

    const output = {
      stats,
      contributions: limitedContributions,
      lastUpdated: new Date().toISOString()
    };

    fs.writeFileSync('public/data/github-contributions.json', JSON.stringify(output, null, 2));
    console.log('GitHub data updated successfully!');
    console.log('Stats:', stats);
  } catch (error) {
    console.error('Error fetching GitHub data:', error);
    // Keep existing data on error
  }
}

fetchData();
