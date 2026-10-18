// Daily data for the dashboard, refreshed by the Worker (called by blt-cron) and kept in KV.
// It replaces two workflows that committed to git:
//   data/github-contributions.json  the student's recent public GitHub events (was
//                                   scripts/fetch-github-data.js); 1 GitHub request
//   data/forks.json                 forks of the template repository (was scripts/update-forks.sh,
//                                   which rewrote a README section); 1 GitHub request
import { putData, readAssetJson } from "../../scripts/worker-data/kv-data.js";

export const CONTRIBUTIONS_KEY = "data/github-contributions.json";
export const FORKS_KEY = "data/forks.json";
export const DEFAULT_FORKS_REPO = "OWASP-BLT/MY-GSOC-TOOL";

async function github(env, path) {
  const headers = { "User-Agent": "GSoC-Dashboard", Accept: "application/vnd.github.v3+json" };
  if (env.GH_API_TOKEN) headers.Authorization = `token ${env.GH_API_TOKEN}`;
  const res = await fetch(`https://api.github.com${path}`, { headers });
  if (!res.ok) throw new Error(`GitHub API ${res.status} for ${path}`);
  return res.json();
}

export function usernameFromConfig(config) {
  const url = (config && config.student && config.student.github) || "";
  return url.split("/").filter(Boolean).pop() || "";
}

const day = (iso) => String(iso || "").split("T")[0];

export function summarizeEvents(events) {
  const stats = { commits: 0, pullRequests: 0, issues: 0, reviews: 0 };
  const contributions = [];
  const seen = new Set();
  for (const event of Array.isArray(events) ? events : []) {
    if (seen.has(event.id)) continue;
    seen.add(event.id);
    const payload = event.payload || {};
    if (event.type === "PushEvent") {
      stats.commits += (payload.commits && payload.commits.length) || 0;
      contributions.push({
        title: `Pushed commits to ${event.repo.name}`,
        description: (payload.commits && payload.commits[0] && payload.commits[0].message) || "Code changes",
        date: day(event.created_at),
        url: `https://github.com/${event.repo.name}`,
        type: "commit",
      });
    } else if (event.type === "PullRequestEvent") {
      stats.pullRequests += 1;
      contributions.push({
        title: `${payload.action} PR: ${payload.pull_request.title}`,
        description: (payload.pull_request.body || "").substring(0, 150) || "Pull request",
        date: day(event.created_at),
        url: payload.pull_request.html_url,
        type: "pull_request",
      });
    } else if (event.type === "IssuesEvent") {
      stats.issues += 1;
      contributions.push({
        title: `${payload.action} issue: ${payload.issue.title}`,
        description: (payload.issue.body || "").substring(0, 150) || "Issue",
        date: day(event.created_at),
        url: payload.issue.html_url,
        type: "issue",
      });
    } else if (event.type === "PullRequestReviewEvent") {
      stats.reviews += 1;
      contributions.push({
        title: `Reviewed PR: ${payload.pull_request.title}`,
        description: "Pull request review",
        date: day(event.created_at),
        url: payload.pull_request.html_url,
        type: "review",
      });
    }
  }
  contributions.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  return { stats, contributions: contributions.slice(0, 20) };
}

export async function refreshContributions(env) {
  const config = await readAssetJson(env, "/config.json");
  const username = usernameFromConfig(config);
  if (!username) throw new Error("config.json has no student.github");
  const events = await github(env, `/users/${encodeURIComponent(username)}/events/public?per_page=100`);
  const lastUpdated = new Date().toISOString();
  const output = { ...summarizeEvents(events), lastUpdated };
  await putData(env, CONTRIBUTIONS_KEY, JSON.stringify(output, null, 2), { updatedAt: lastUpdated, metadata: { username } });
  return { username, stats: output.stats };
}

export async function refreshForks(env) {
  const repo = env.FORKS_REPO || DEFAULT_FORKS_REPO;
  const forks = await github(env, `/repos/${repo}/forks?per_page=100&sort=stargazers`);
  if (!Array.isArray(forks)) throw new Error("unexpected forks response");
  const lastUpdated = new Date().toISOString();
  const output = {
    repository: repo,
    forks: forks.map((f) => ({ full_name: f.full_name, html_url: f.html_url, stargazers_count: f.stargazers_count || 0 })),
    lastUpdated,
  };
  await putData(env, FORKS_KEY, JSON.stringify(output, null, 2), { updatedAt: lastUpdated });
  return { repository: repo, forks: output.forks.length };
}
