// GSoC progress tracker data (was scripts/update_progress.py, run nightly by a workflow that
// committed data/progress.json). For each contributor in data/contributors.json it counts their
// GitLab commits in their OWASP-BLT project repositories and checks the Slack search API (both
// workspaces) for a message on the day, then stores data/progress.json in KV:
//
//   {"updated": "...", "days": {"2026-06-11": {"Pritz395": {"commits": 3, "checkin": true,
//     "slack": {"owasp": true, "blt": false}}}}}
//
// A day is about 40 requests (one per repository, two Slack searches per contributor), so
// runChunked() spreads it over blt-cron's 23:07-23:11 calls with a budget of 30 per call.

import { putData, readAssetJson, readJsonOrAsset, runChunked, utcDay } from "../../scripts/worker-data/kv-data.js";

export const KEY = "data/progress.json";
const SLACK_SERVERS = { owasp: "SLACK_TOKEN_OWASP", blt: "SLACK_TOKEN_BLT" };

export function dayWindow(day) {
  const start = new Date(`${day}T00:00:00Z`);
  const end = new Date(start.getTime() + 86400000);
  const fmt = (d) => d.toISOString().replace(".000Z", "Z");
  return [fmt(start), fmt(end)];
}

export function gitlabProjectPaths(contributor) {
  const repos = contributor.repos || [contributor.repo || contributor.project];
  return repos.filter(Boolean).map((repo) => `OWASP-BLT/${repo}`);
}

const normalized = (value) => String(value || "").toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
const localpart = (value) => String(value || "").split("@", 1)[0];

export function commitAuthorAliases(contributor) {
  const aliases = [
    contributor.name, contributor.github, contributor.gitlab,
    localpart(contributor.github), localpart(contributor.gitlab),
    ...(contributor.commit_authors || []),
  ];
  return new Set(aliases.filter(Boolean).map(normalized));
}

export function commitMatchesContributor(commit, contributor) {
  const aliases = commitAuthorAliases(contributor);
  return [commit.author_name, commit.committer_name, localpart(commit.author_email), localpart(commit.committer_email)]
    .filter(Boolean)
    .some((identity) => aliases.has(normalized(identity)));
}

export function contributorCost(contributor) {
  return gitlabProjectPaths(contributor).length + Object.keys(SLACK_SERVERS).length;
}

async function projectCommitsForDay(env, projectPath, day) {
  const [since, until] = dayWindow(day);
  const api = env.GITLAB_API || "https://gitlab.com/api/v4";
  const id = encodeURIComponent(projectPath);
  const commits = [];
  // Rarely more than one page; stop at 3 to bound subrequests.
  for (let page = 1; page <= 3; page++) {
    const params = new URLSearchParams({ all: "true", since, until, per_page: "100", page: String(page) });
    const headers = { "User-Agent": "BLT-GSOC-progress-tracker" };
    if (env.GITLAB_TOKEN) headers["PRIVATE-TOKEN"] = env.GITLAB_TOKEN;
    const res = await fetch(`${api}/projects/${id}/repository/commits?${params}`, { headers });
    if (!res.ok) {
      console.warn(`GitLab API ${res.status} for ${projectPath}`);
      return commits;
    }
    const batch = await res.json();
    commits.push(...batch);
    if (batch.length < 100) break;
  }
  return commits;
}

async function slackSentMessage(token, username, day) {
  const params = new URLSearchParams({ query: `from:@${username} on:${day}`, count: "1" });
  try {
    const res = await fetch(`https://slack.com/api/search.messages?${params}`, {
      headers: { "User-Agent": "BLT-GSOC-progress-tracker", Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!data.ok) {
      console.warn(`Slack API: ${data.error} for ${username}`);
      return false;
    }
    return ((data.messages && data.messages.total) || 0) > 0;
  } catch (error) {
    console.warn(`Slack API error for ${username}: ${error.message}`);
    return false;
  }
}

export async function progressForDay(env, contributor, day) {
  let commits = 0;
  for (const path of gitlabProjectPaths(contributor)) {
    for (const commit of await projectCommitsForDay(env, path, day)) {
      if (commitMatchesContributor(commit, contributor)) commits += 1;
    }
  }
  const slack = {};
  const info = contributor.slack || "";
  for (const [server, envVar] of Object.entries(SLACK_SERVERS)) {
    const username = typeof info === "object" ? info[server] : info;
    slack[server] = Boolean(env[envVar] && username) && (await slackSentMessage(env[envVar], username, day));
  }
  return { commits, checkin: Object.values(slack).some(Boolean), slack };
}

// `day` (YYYY-MM-DD) backfills a past day, like update_progress.py --date did; send `reset` on
// the first call to redo a day that already finished, then repeat the call until `done`.
export async function refreshProgress(env, { scheduledTime = Date.now(), reset = false, day, budget = 30 } = {}) {
  const target = day && /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : utcDay(scheduledTime);
  const contributors = (await readAssetJson(env, "/data/contributors.json")) || [];
  if (!Array.isArray(contributors) || contributors.length === 0) throw new Error("no contributors");
  const items = contributors.map((c) => ({ ...c, id: c.github }));
  return runChunked(env, {
    name: "progress",
    run: target,
    items,
    cost: contributorCost,
    budget,
    reset,
    process: (contributor) => progressForDay(env, contributor, target),
    finish: async (dayData) => {
      const progress = (await readJsonOrAsset(env, KEY)) || {};
      const days = { ...(progress.days || {}), [target]: dayData };
      const updated = new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
      const sorted = Object.fromEntries(Object.entries(days).sort(([a], [b]) => a.localeCompare(b)));
      await putData(env, KEY, JSON.stringify({ ...progress, days: sorted, updated }, null, 2) + "\n");
    },
  });
}
