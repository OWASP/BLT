// Live numbers for the homepage. Every summariser takes the raw JSON of one
// public source and returns a small object, or null when the data is missing
// or malformed. The page hides any number whose source returned null; it never
// shows a placeholder value.

export const SOURCES = {
  forge: "https://git.owaspblt.org/api/repo/owasp-blt/BLT/stats",
  pool: "https://pool.owaspblt.org/api/leaderboard",
  pages: "https://pages.owaspblt.org/data/leaderboard.json",
};

const BOT_NAME = /\[bot\]|\bbot$|^github actions?$|^copilot$|dependabot|coderabbit|renovate|pre-commit/i;

const isCount = (n) => Number.isInteger(n) && n >= 0;

// git.owaspblt.org repository stats for the BLT monorepo.
export function summariseForge(data) {
  if (!data || typeof data !== "object") return null;
  const out = {};
  if (isCount(data.commitCount)) out.commits = data.commitCount;
  if (Array.isArray(data.contributors) && !data.contributorsTruncated) {
    const people = new Set();
    for (const c of data.contributors) {
      const name = typeof c?.name === "string" ? c.name.trim() : "";
      if (name && !BOT_NAME.test(name)) people.add(name.toLowerCase());
    }
    if (people.size) out.contributors = people.size;
  }
  const weeks = weeklyCommits(data);
  if (weeks) {
    out.weeks = weeks.counts;
    out.weeksStart = weeks.start;
    out.recentCommits = weeks.counts.slice(-4).reduce((a, b) => a + b, 0);
  }
  const counts = data.counts || {};
  if (isCount(counts.openIssues)) out.openIssues = counts.openIssues;
  if (isCount(counts.openPulls)) out.openPulls = counts.openPulls;
  return Object.keys(out).length ? out : null;
}

// BLT-Pool's monthly contribution leaderboard.
export function summarisePool(data, top = 3) {
  if (!data || typeof data.users !== "object" || data.users === null) return null;
  const rows = Object.entries(data.users)
    .filter(([login, s]) => login && s && isCount(s.total) && s.total > 0 && !BOT_NAME.test(login))
    .sort((a, b) => b[1].total - a[1].total || a[0].localeCompare(b[0]));
  if (!rows.length) return null;
  return {
    month: typeof data.month === "string" && /^\d{4}-\d{2}$/.test(data.month) ? data.month : null,
    top: rows.slice(0, top).map(([login, s]) => ({ login: String(login).slice(0, 39), points: s.total })),
  };
}

// Commits per week by people (bots left out), oldest first, from each
// contributor's activityWeeks. Null unless every contributor is present and
// the series has at least 12 weeks.
export function weeklyCommits(data, maxWeeks = 52) {
  if (!Array.isArray(data?.contributors) || data.contributorsTruncated) return null;
  const start = Date.parse(data.activityStart);
  let totals = null;
  for (const c of data.contributors) {
    const name = typeof c?.name === "string" ? c.name.trim() : "";
    const weeks = c?.activityWeeks;
    if (!Array.isArray(weeks) || BOT_NAME.test(name)) continue;
    if (!totals) totals = new Array(weeks.length).fill(0);
    if (weeks.length !== totals.length) return null;
    weeks.forEach((n, i) => { if (isCount(n)) totals[i] += n; });
  }
  if (!totals || totals.length < 12 || !Number.isFinite(start)) return null;
  const skip = Math.max(0, totals.length - maxWeeks);
  return {
    counts: totals.slice(skip),
    start: new Date(start + skip * 7 * 86400e3).toISOString().slice(0, 10),
  };
}

// BLT-Pages public bug reports (forge issues on the blt-pages project).
export function summarisePages(data, top = 3) {
  if (!data || !isCount(data.total_bugs)) return null;
  const leaders = Array.isArray(data.leaderboard) ? data.leaderboard : [];
  return {
    bugs: data.total_bugs,
    domains: isCount(data.total_domains) ? data.total_domains : null,
    // Rows are {login, count} (blt-pages/scripts/generate_leaderboard.py).
    top: leaders
      .filter((r) => r && typeof r.login === "string" && r.login && isCount(r.count))
      .slice(0, top)
      .map((r) => ({ login: r.login.slice(0, 39), bugs: r.count })),
  };
}

const SUMMARISERS = { forge: summariseForge, pool: summarisePool, pages: summarisePages };

async function fetchJson(fetcher, url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetcher(url, {
      signal: controller.signal,
      headers: { accept: "application/json", "user-agent": "blt-home (+https://owaspblt.org)" },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// Fetch every source in parallel; a failing source becomes null.
export async function collectStats({ fetcher = fetch, now = Date.now(), timeoutMs = 6000 } = {}) {
  const names = Object.keys(SOURCES);
  const raw = await Promise.all(names.map((n) => fetchJson(fetcher, SOURCES[n], timeoutMs)));
  const out = { generatedAt: new Date(now).toISOString() };
  names.forEach((n, i) => {
    let value = null;
    try {
      value = raw[i] == null ? null : SUMMARISERS[n](raw[i]);
    } catch {
      value = null;
    }
    out[n] = value;
  });
  return out;
}
