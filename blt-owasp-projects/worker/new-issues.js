import { readJsonOrAsset } from "../../scripts/worker-data/kv-data.js";

// New OWASP issue alert: blt-cron calls POST /__scheduled with {task: "new-issues"} every hour.
// GitHub searches list the 100 most recently created issues across the OWASP organization, plus the
// 100 newest in each batch of owasp.org projects whose code lives outside it (zaproxy/zaproxy,
// juice-shop/juice-shop, coreruleset/coreruleset...: every repo_name in repo_status.json not under
// OWASP/, cached daily in `state:outside-repos` so the large file is parsed once a day). Each issue
// not seen before is posted to Slack (SLACK_NEW_ISSUES_WEBHOOK), one compact line per issue,
// all in one message. KV keeps `state:new-issue-ids`: {ids, since}, the ids seen and the newest
// created_at seen. Search indexing can lag, so an issue alerts when it is unseen and created after
// `since` minus LAG_MS; anything older (an issue sliding into the newest 100 when others are
// deleted) never alerts. The first run only records the listing. Without the webhook secret the
// task still keeps the state current, so setting the secret later does not flood the channel.

export const STATE_KEY = "state:new-issue-ids";
export const ORG = "OWASP";
export const REPOS_KEY = "state:outside-repos";
const REPOS_TTL_MS = 24 * 60 * 60 * 1000;
const REPOS_PER_SEARCH = 40;
const MAX_SEEN = 2000;
const MAX_LINES = 30;
const LAG_MS = 60 * 60 * 1000;
const MAX_TITLE = 100;

// "owner/repo" of every active project repository outside the OWASP organization.
export function outsideRepos(projects) {
  const repos = new Set();
  for (const project of projects || []) {
    const name = String((project && project.repo_name) || "");
    if (!project || project.archived || !/^[\w.-]+\/[\w.-]+$/.test(name)) continue;
    if (name.split("/")[0].toLowerCase() !== ORG.toLowerCase()) repos.add(name);
  }
  return [...repos].sort();
}

async function projectRepos(env) {
  const cached = await env.DATA.get(REPOS_KEY, { type: "json" });
  if (cached && Date.now() - Date.parse(cached.at) < REPOS_TTL_MS) return cached.repos;
  const projects = await readJsonOrAsset(env, "repo_status.json");
  if (!Array.isArray(projects)) return cached ? cached.repos : [];
  const repos = outsideRepos(projects);
  await env.DATA.put(REPOS_KEY, JSON.stringify({ repos, at: new Date().toISOString() }));
  return repos;
}

export function searchQueries(repos) {
  const queries = [`org:${ORG} is:issue`];
  for (let i = 0; i < repos.length; i += REPOS_PER_SEARCH) {
    queries.push(`is:issue ${repos.slice(i, i + REPOS_PER_SEARCH).map((repo) => `repo:${repo}`).join(" ")}`);
  }
  return queries;
}

async function search(env, query) {
  const url = `https://api.github.com/search/issues?q=${encodeURIComponent(query)}&sort=created&order=desc&per_page=100`;
  const headers = { accept: "application/vnd.github+json", "user-agent": "blt-owasp-projects" };
  if (env.GH_API_TOKEN) headers.authorization = `Bearer ${env.GH_API_TOKEN}`;
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error(`GitHub answered ${response.status} for ${query.slice(0, 60)}`);
  return (await response.json()).items || [];
}

// Newest first, each issue once.
async function newestIssues(env) {
  const byId = new Map();
  for (const query of searchQueries(await projectRepos(env))) {
    for (const issue of await search(env, query)) byId.set(issue.id, issue);
  }
  return [...byId.values()].sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
}

const escape = (text) => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function clip(text, max = MAX_TITLE) {
  const flat = String(text || "").replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1).trimEnd()}…` : flat;
}

// "• <url|repo#12> Title · author · label, label"; a repository outside OWASP shows its owner too.
export function issueLine(issue) {
  const [owner, name] = String(issue.repository_url || "").split("/").slice(-2);
  const repo = String(owner).toLowerCase() === ORG.toLowerCase() ? name : `${owner}/${name}`;
  const labels = (issue.labels || []).map((label) => label.name).filter(Boolean).slice(0, 3);
  const facts = [issue.user && issue.user.login, labels.join(", ")].filter(Boolean);
  return `• <${issue.html_url}|${escape(repo)}#${issue.number}> ${escape(clip(issue.title))}${facts.length ? ` · ${escape(facts.join(" · "))}` : ""}`;
}

export function slackMessage(issues) {
  const n = issues.length;
  const lines = issues.slice(0, MAX_LINES).map(issueLine);
  if (n > MAX_LINES) lines.push(`…and ${n - MAX_LINES} more`);
  return { text: `*${n} new OWASP issue${n === 1 ? "" : "s"}*\n${lines.join("\n")}`, unfurl_links: false, unfurl_media: false };
}

export async function checkNewIssues(env) {
  const issues = await newestIssues(env);
  const state = await env.DATA.get(STATE_KEY, { type: "json" });
  const seen = new Set(state ? state.ids : []);
  const since = (state && state.since) || "";
  const floor = since ? new Date(Date.parse(since) - LAG_MS).toISOString() : "";
  const fresh = issues.filter((issue) => !seen.has(issue.id) && String(issue.created_at || "") > floor).reverse();
  const ids = [...issues.map((issue) => issue.id), ...(state ? state.ids : [])];
  const newest = issues.reduce((max, issue) => (String(issue.created_at || "") > max ? issue.created_at : max), since);
  const save = () => env.DATA.put(STATE_KEY, JSON.stringify({ ids: [...new Set(ids)].slice(0, MAX_SEEN), since: newest }));

  if (!state || !state.since) {
    await save();
    return { seeded: issues.length, posted: 0 };
  }
  if (fresh.length === 0) return { posted: 0 };
  if (!env.SLACK_NEW_ISSUES_WEBHOOK) {
    await save();
    return { posted: 0, skipped: fresh.length, reason: "SLACK_NEW_ISSUES_WEBHOOK is not set" };
  }
  const response = await fetch(env.SLACK_NEW_ISSUES_WEBHOOK, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(slackMessage(fresh)),
  });
  if (!response.ok) throw new Error(`Slack answered ${response.status}`);
  await save();
  return { posted: fresh.length };
}
