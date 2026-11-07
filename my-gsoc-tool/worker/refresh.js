// Daily data for the dashboard, refreshed by the Worker (called by blt-cron) and kept in KV.
//   data/github-contributions.json  the student's recent public GitHub events (was
//                                   scripts/fetch-github-data.js); 1 GitHub request
//   data/forks.json                 forks of the template repository (was scripts/update-forks.sh,
//                                   which rewrote a README section); 2 GitHub requests
//   data/directory.json             every live dashboard among those forks (plus data/sites.json)
//                                   with its student, project and stats; chunked, see
//                                   refreshDirectory()
import { putData, readAssetJson, readJsonOrAsset, runChunked, utcDay } from "../../scripts/worker-data/kv-data.js";

export const CONTRIBUTIONS_KEY = "data/github-contributions.json";
export const FORKS_KEY = "data/forks.json";
export const DIRECTORY_KEY = "data/directory.json";
// OWASP-BLT/MY-GSOC-TOOL was deleted from GitHub; this copy became the root of its fork network.
export const DEFAULT_FORKS_REPO = "ananya-in-tech/MY-GSOC-TOOL";

async function github(env, path) {
  const headers = { "User-Agent": "GSoC-Dashboard", Accept: "application/vnd.github.v3+json" };
  if (env.GH_API_TOKEN) headers.Authorization = `token ${env.GH_API_TOKEN}`;
  const res = await fetch(`https://api.github.com${path}`, { headers });
  if (!res.ok) {
    const error = new Error(`GitHub API ${res.status} for ${path}`);
    error.status = res.status;
    throw error;
  }
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

const forkSummary = (f) => ({
  full_name: f.full_name,
  html_url: f.html_url,
  stargazers_count: f.stargazers_count || 0,
  homepage: f.homepage || "",
  has_pages: Boolean(f.has_pages),
  pushed_at: f.pushed_at || null,
});

export async function refreshForks(env) {
  const repo = env.FORKS_REPO || DEFAULT_FORKS_REPO;
  let forks;
  let source;
  try {
    source = await github(env, `/repos/${repo}`);
    forks = await github(env, `/repos/${repo}/forks?per_page=100&sort=stargazers`);
  } catch (error) {
    // The template repository was moved or deleted: keep serving the last list instead of
    // failing the daily run.
    if (error.status === 404) return { repository: repo, skipped: "repository_not_found" };
    throw error;
  }
  if (!Array.isArray(forks)) throw new Error("unexpected forks response");
  const lastUpdated = new Date().toISOString();
  const output = {
    repository: repo,
    source: forkSummary(source),
    forks: forks.map(forkSummary),
    lastUpdated,
  };
  await putData(env, FORKS_KEY, JSON.stringify(output, null, 2), { updatedAt: lastUpdated });
  return { repository: repo, forks: output.forks.length };
}

// The directory: which forks serve a dashboard, and what's on it. A dashboard is live when
// <site>/config.json answers with a student. Per site: 1-2 config probes, 3 GitHub search counts
// and 4 data files, so runChunked() does 3 sites per blt-cron call (budget 30, which also leaves
// GitHub's 30 searches a minute room).
const SITE_COST = 9;
const SEARCHES = { pullRequests: "type:pr", mergedPullRequests: "type:pr is:merged", issues: "type:issue" };
const CONTENT_FILES = { blogPosts: "data/blog-posts.json", weeklyUpdates: "data/weekly-updates.json", milestones: "data/milestones.json", feedback: "data/feedback.json" };
// Forks keep the homepage of the deleted original repository, which no longer serves anything.
const INHERITED_HOMEPAGE = /^https:\/\/owasp-blt\.github\.io\//i;
const PLACEHOLDER = /^(your\b|tbd$|gsoc project$|my gsoc project$|open source organization$|may 20xx)/i;

export function siteBase(url) {
  const value = String(url || "").trim();
  if (!/^https:\/\/[^\s"'<>]+$/i.test(value)) return "";
  try {
    const parsed = new URL(value);
    parsed.search = "";
    parsed.hash = "";
    return parsed.href.endsWith("/") ? parsed.href : `${parsed.href}/`;
  } catch {
    return "";
  }
}

export function siteCandidates(fork) {
  const urls = [];
  const home = siteBase(fork.homepage);
  if (home && !INHERITED_HOMEPAGE.test(home)) urls.push(home);
  const [owner, name] = String(fork.full_name || "").split("/");
  if (fork.has_pages && owner && name) urls.push(`https://${owner.toLowerCase()}.github.io/${name}/`);
  return [...new Set(urls)];
}

// Sites to probe: data/sites.json (dashboards outside the fork network, such as this one) first,
// then the network's source repository and its forks. One entry per base URL.
export function directoryItems(forks, extra) {
  const items = [];
  const seen = new Set();
  const add = (candidates, fork) => {
    const fresh = candidates.filter((url) => !seen.has(url));
    if (!fresh.length) return;
    fresh.forEach((url) => seen.add(url));
    items.push({
      id: fresh[0],
      candidates: fresh,
      repo: fork ? fork.full_name : null,
      repoUrl: fork ? fork.html_url : null,
      pushedAt: fork ? fork.pushed_at : null,
      stars: fork ? fork.stargazers_count || 0 : 0,
    });
  };
  for (const site of (extra && extra.sites) || []) {
    const url = siteBase(site.url);
    if (url) add([url], site.repo ? { full_name: site.repo, html_url: siteBase(site.repoUrl).replace(/\/$/, "") || null } : null);
  }
  const all = [forks && forks.source, ...((forks && forks.forks) || [])].filter(Boolean);
  for (const fork of all) add(siteCandidates(fork), fork);
  return items;
}

async function fetchJson(url) {
  try {
    const res = await fetch(url, { headers: { "User-Agent": "GSoC-Dashboard", Accept: "application/json" }, redirect: "follow" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

const text = (value, max = 200) => {
  const s = String(value == null ? "" : value).trim().slice(0, max);
  return PLACEHOLDER.test(s) ? "" : s;
};
// Feedback entries have no title; their text stands in for one.
const titles = (list) => (Array.isArray(list)
  ? list.slice(0, 50).map((entry) => text(entry && (entry.title || entry.content), 120)).filter(Boolean)
  : []);

async function searchCount(env, username, query) {
  try {
    const result = await github(env, `/search/issues?per_page=1&q=${encodeURIComponent(`author:${username} ${query}`)}`);
    return Number(result.total_count) || 0;
  } catch {
    return null;
  }
}

export async function probeSite(env, item) {
  let base = "";
  let config = null;
  for (const url of item.candidates) {
    const found = await fetchJson(`${url}config.json`);
    if (found && typeof found === "object" && found.student) {
      base = url;
      config = found;
      break;
    }
  }
  if (!config) return { url: item.id, live: false };
  const student = config.student || {};
  const project = config.project || {};
  const username = usernameFromConfig(config).replace(/[^A-Za-z0-9-]/g, "");
  const stats = {};
  if (username) {
    for (const [name, query] of Object.entries(SEARCHES)) stats[name] = await searchCount(env, username, query);
  }
  const files = await Promise.all(Object.values(CONTENT_FILES).map((path) => fetchJson(`${base}${path}`)));
  const content = Object.fromEntries(Object.keys(CONTENT_FILES).map((key, i) => [key, titles(files[i])]));
  return {
    url: base,
    live: true,
    repo: item.repo,
    repoUrl: item.repoUrl,
    pushedAt: item.pushedAt,
    stars: item.stars,
    name: text(student.name, 80) || username,
    bio: text(student.bio, 160),
    avatar: siteBase(student.avatar).replace(/\/$/, "") || (username ? `https://github.com/${username}.png` : ""),
    username,
    project: { title: text(project.title), organization: text(project.organization, 80), timeline: text(project.timeline, 60) },
    stats,
    content,
  };
}

// Entries still holding the template's sample text don't count as the student's own: the titles
// in this template's data files, and any title found on SHARED_TITLE_SITES or more dashboards
// (older copies of the template shipped other samples).
const SHARED_TITLE_SITES = 3;

export function sampleTitles(sites, templateTitles = []) {
  const samples = new Set(templateTitles);
  const seen = new Map();
  for (const site of sites) {
    for (const title of new Set(Object.values(site.content || {}).flat())) seen.set(title, (seen.get(title) || 0) + 1);
  }
  for (const [title, count] of seen) if (count >= SHARED_TITLE_SITES) samples.add(title);
  return samples;
}

export function summarizeSite(site, sampleTitles) {
  const { content, ...rest } = site;
  const counts = {};
  for (const key of Object.keys(CONTENT_FILES)) {
    const own = (content && content[key]) || [];
    counts[key] = own.filter((title) => !sampleTitles.has(title)).length;
  }
  return { ...rest, content: counts };
}

export function keepKnownStats(site, previous) {
  const old = (previous && previous.stats) || {};
  const stats = { ...site.stats };
  for (const key of Object.keys(SEARCHES)) if (stats[key] == null && old[key] != null) stats[key] = old[key];
  return { ...site, stats };
}

export async function refreshDirectory(env, { scheduledTime = Date.now(), reset = false, budget = 30 } = {}) {
  const forks = await readJsonOrAsset(env, FORKS_KEY);
  const extra = await readAssetJson(env, "/data/sites.json");
  const items = directoryItems(forks, extra);
  return runChunked(env, {
    name: "directory",
    run: utcDay(scheduledTime),
    items,
    cost: () => SITE_COST,
    budget,
    reset,
    process: (item) => probeSite(env, item),
    finish: async (results) => {
      const template = [];
      for (const path of Object.values(CONTENT_FILES)) {
        template.push(...titles(await readAssetJson(env, `/${path}`)));
      }
      const live = items.map((item) => results[item.id]).filter((site) => site && site.live);
      const samples = sampleTitles(live, template);
      // A search that failed (rate limit, say) keeps yesterday's count.
      const previous = new Map(((await readJsonOrAsset(env, DIRECTORY_KEY)) || { sites: [] }).sites.map((site) => [site.url, site]));
      const lastUpdated = new Date().toISOString();
      const sites = live.map((site) => keepKnownStats(summarizeSite(site, samples), previous.get(site.url)));
      const output = { checked: items.length, sites, lastUpdated };
      await putData(env, DIRECTORY_KEY, JSON.stringify(output, null, 2), { updatedAt: lastUpdated });
    },
  });
}
