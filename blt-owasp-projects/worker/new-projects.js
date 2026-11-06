// New OWASP repository alert: blt-cron calls POST /__scheduled with {task: "new-projects"} every hour.
// One GitHub request lists the 100 most recently created OWASP repositories; each one whose id was
// not seen before is posted to Slack (#project-new-projects, through the SLACK_WEBHOOK_URL secret),
// one compact line per repository. A www-project-* repository's line comes from its index.md front
// matter (title, level, type, pitch) and leaders.md; any other repository's from its GitHub
// description and language. KV keeps `state:new-project-ids`: {ids, since}, the ids seen and the
// newest created_at seen. Only a repository created after `since` and not seen alerts, so the first
// run (no state yet: it only records the listing) posts nothing, and an old repository that slides
// into the newest 100 when a newer one is deleted posts nothing either. Repositories transferred in
// or made public long after they were created are not caught.

export const STATE_KEY = "state:new-project-ids";
export const ORG = "owasp";
export const PREFIX = "www-project";
const MAX_SEEN = 1000;
// Two raw reads per project repository; this keeps a run under the free plan's 50 subrequests.
const MAX_DETAILED = 20;
const MAX_PITCH = 160;

function githubHeaders(env) {
  const headers = { accept: "application/vnd.github+json", "user-agent": "blt-owasp-projects" };
  if (env.GH_API_TOKEN) headers.authorization = `Bearer ${env.GH_API_TOKEN}`;
  return headers;
}

async function newestRepos(env) {
  const url = `https://api.github.com/orgs/${ORG}/repos?sort=created&direction=desc&per_page=100`;
  const response = await fetch(url, { headers: githubHeaders(env) });
  if (!response.ok) throw new Error(`GitHub answered ${response.status} for ${ORG} repositories`);
  return response.json();
}

async function rawFile(repo, path) {
  try {
    const response = await fetch(`https://raw.githubusercontent.com/${repo.full_name}/${repo.default_branch || "main"}/${path}`);
    return response.ok ? await response.text() : "";
  } catch {
    return "";
  }
}

function clip(text, max = MAX_PITCH) {
  const flat = String(text || "").replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1).trimEnd()}…` : flat;
}

const unquote = (value) => value.trim().replace(/^(["'])(.*)\1$/, "$2").trim();

// index.md: front matter fields (lowercased keys) plus the first two sentences of the body.
export function parseIndex(content) {
  const fields = {};
  let body = content.trim();
  if (content.startsWith("---")) {
    const parts = content.split("---");
    if (parts.length >= 3) {
      for (const line of parts[1].split("\n")) {
        const match = line.match(/^([A-Za-z_]+):\s*(.*)$/);
        if (match && match[2].trim()) fields[match[1].toLowerCase()] = unquote(match[2]);
      }
      body = parts.slice(2).join("---").trim();
    }
  }
  const text = body.split("\n").map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#") && !line.startsWith("<") && !line.startsWith("{")).join(" ");
  fields.summary = text.split(/(?<=[.!?])\s+/).slice(0, 2).join(" ").replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").trim();
  return fields;
}

// leaders.md: the names in its markdown links, e.g. "* [Jane Doe](mailto:jane@owasp.org)".
export function parseLeaders(content) {
  return [...new Set([...content.matchAll(/\[([^\]]+)\]\([^)]*\)/g)].map((m) => m[1].trim()).filter(Boolean))];
}

const escape = (text) => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// One line: link · facts — pitch. Facts are the OWASP level and type (or language and "fork"),
// then the leaders.
export function repoLine(repo, index = null, leaders = []) {
  const name = index && index.title ? index.title : repo.name;
  const facts = index
    ? [index.level && `level ${index.level}`, index.type].filter(Boolean)
    : [repo.language, repo.fork && "fork"].filter(Boolean);
  if (leaders.length) facts.push(`👤 ${leaders.slice(0, 3).join(", ")}${leaders.length > 3 ? ` +${leaders.length - 3}` : ""}`);
  const pitch = clip(index ? index.pitch || index.summary || repo.description : repo.description);
  return `• <${repo.html_url}|${escape(name)}>${facts.length ? ` · ${escape(facts.join(" · "))}` : ""}${pitch ? ` — ${escape(pitch)}` : ""}`;
}

export function slackMessage(lines) {
  const n = lines.length;
  return { text: `*${n} new OWASP repo${n === 1 ? "" : "s"}*\n${lines.join("\n")}`, unfurl_links: false, unfurl_media: false };
}

async function describe(repo, detailed) {
  if (!repo.name.startsWith(PREFIX) || !detailed) return repoLine(repo);
  const [index, leaders] = await Promise.all([rawFile(repo, "index.md"), rawFile(repo, "leaders.md")]);
  return repoLine(repo, index ? parseIndex(index) : {}, leaders ? parseLeaders(leaders) : []);
}

export async function checkNewProjects(env) {
  const repos = await newestRepos(env);
  const state = await env.DATA.get(STATE_KEY, { type: "json" });
  const seen = new Set(state ? state.ids : []);
  const since = (state && state.since) || "";
  const fresh = repos.filter((repo) => !seen.has(repo.id) && String(repo.created_at || "") > since).reverse();
  const ids = [...repos.map((repo) => repo.id), ...(state ? state.ids : [])];
  const newest = repos.reduce((max, repo) => (String(repo.created_at || "") > max ? repo.created_at : max), since);
  const save = () => env.DATA.put(STATE_KEY, JSON.stringify({ ids: [...new Set(ids)].slice(0, MAX_SEEN), since: newest }));

  if (!state || !state.since) {
    await save();
    return { seeded: repos.length, posted: 0 };
  }
  if (fresh.length === 0) return { posted: 0 };
  if (!env.SLACK_WEBHOOK_URL) throw new Error("SLACK_WEBHOOK_URL is not set");

  let detailed = 0;
  const lines = [];
  for (const repo of fresh) {
    const project = repo.name.startsWith(PREFIX) && detailed++ < MAX_DETAILED;
    lines.push(await describe(repo, project));
  }
  const response = await fetch(env.SLACK_WEBHOOK_URL, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(slackMessage(lines)),
  });
  if (!response.ok) throw new Error(`Slack answered ${response.status}`);
  await save();
  return { posted: fresh.length, repos: fresh.map((repo) => repo.full_name) };
}
