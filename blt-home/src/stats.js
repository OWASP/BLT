// Live numbers for the homepage. Every summariser takes the raw JSON of one
// public source and returns a small object, or null when the data is missing
// or malformed. The page hides any number whose source returned null; it never
// shows a placeholder value.

export const SOURCES = {
  forge: "https://git.owaspblt.org/api/repo/owasp-blt/BLT/stats",
  pool: "https://pool.owaspblt.org/api/leaderboard",
  monitor: "https://monitor.owaspblt.org/api/histories",
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

// BLT-Monitor check histories: how many monitored BLT sites passed their
// latest check. Monitors that have not run recently (removed or renamed) are
// left out; if the whole feed is stale the result is null.
export function summariseMonitor(data, now = Date.now(), { activeWindowMs = 3 * 3600e3, staleAfterMs = 6 * 3600e3 } = {}) {
  if (!data || typeof data !== "object") return null;
  const latest = [];
  for (const history of Object.values(data)) {
    if (!Array.isArray(history) || !history.length) continue;
    const last = history[history.length - 1];
    const t = Date.parse(last?.datetime);
    if (!Number.isFinite(t)) continue;
    latest.push({ t, ok: last.status === "success", ms: Number(last.duration_ms) });
  }
  if (!latest.length) return null;
  const newest = Math.max(...latest.map((x) => x.t));
  if (now - newest > staleAfterMs) return null;
  const active = latest.filter((x) => newest - x.t <= activeWindowMs);
  const times = active.filter((x) => x.ok && Number.isFinite(x.ms)).map((x) => x.ms).sort((a, b) => a - b);
  return {
    sites: active.length,
    up: active.filter((x) => x.ok).length,
    medianMs: times.length ? Math.round(times[Math.floor(times.length / 2)]) : null,
    checkedAt: new Date(newest).toISOString(),
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

const SUMMARISERS = { forge: summariseForge, pool: summarisePool, monitor: summariseMonitor, pages: summarisePages };

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
      value = raw[i] == null ? null : n === "monitor" ? SUMMARISERS[n](raw[i], now) : SUMMARISERS[n](raw[i]);
    } catch {
      value = null;
    }
    out[n] = value;
  });
  return out;
}
