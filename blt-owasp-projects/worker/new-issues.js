// New OWASP issue alert: blt-cron calls POST /__scheduled with {task: "new-issues"} every hour.
// One GitHub search lists the 100 most recently created issues across the OWASP organization; each
// one not seen before is posted to Slack (SLACK_NEW_ISSUES_WEBHOOK), one compact line per issue,
// all in one message. KV keeps `state:new-issue-ids`: {ids, since}, the ids seen and the newest
// created_at seen. Search indexing can lag, so an issue alerts when it is unseen and created after
// `since` minus LAG_MS; anything older (an issue sliding into the newest 100 when others are
// deleted) never alerts. The first run only records the listing. Without the webhook secret the
// task still keeps the state current, so setting the secret later does not flood the channel.

export const STATE_KEY = "state:new-issue-ids";
export const ORG = "OWASP";
const MAX_SEEN = 2000;
const MAX_LINES = 30;
const LAG_MS = 60 * 60 * 1000;
const MAX_TITLE = 100;

async function newestIssues(env) {
  const q = encodeURIComponent(`org:${ORG} is:issue`);
  const url = `https://api.github.com/search/issues?q=${q}&sort=created&order=desc&per_page=100`;
  const headers = { accept: "application/vnd.github+json", "user-agent": "blt-owasp-projects" };
  if (env.GH_API_TOKEN) headers.authorization = `Bearer ${env.GH_API_TOKEN}`;
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error(`GitHub answered ${response.status} for ${ORG} issues`);
  return (await response.json()).items || [];
}

const escape = (text) => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function clip(text, max = MAX_TITLE) {
  const flat = String(text || "").replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1).trimEnd()}…` : flat;
}

// "• <url|repo#12> Title · author · label, label"
export function issueLine(issue) {
  const repo = String(issue.repository_url || "").split("/").pop();
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
