// GSoC 2026 project stats (was scripts/update_gsoc2026_stats.js, run daily by a workflow that
// committed js/gsoc2026_stats.generated.js). The Worker now refreshes it from blt-cron and keeps
// it in KV under the same path, so gsoc2026.html is unchanged.
//
// A full refresh is about 90 GitHub requests, 78 of them search queries (limit: 30 per minute).
// That is over the free plan's 50 subrequests per invocation, so runChunked() does a couple of
// projects per call (budget 24, at most 24 searches a minute) on blt-cron's 02:17-02:31 calls.
// A count that fails keeps yesterday's value instead of turning into null.

import { putData, runChunked, utcDay } from "../../scripts/worker-data/kv-data.js";

export const KEY = "js/gsoc2026_stats.generated.js";
const GH_API = "https://api.github.com";
const PREFIX = "window.GSOC2026_STATS = ";

export const PROJECTS = [
    { id: 'blt-netguardian', repos: ['OWASP-BLT/BLT-NetGuardian-Client', 'OWASP-BLT/BLT-NetGuardian'], users: ['Pritz395'] },
    { id: 'blt-university', repos: ['OWASP-BLT/BLT-University'], users: ['e-esakman'] },
    { id: 'blt-next', repos: ['OWASP-BLT/BLT-Next'], users: ['mdkaifansari04'] },
    { id: 'blt-vanish', repos: ['OWASP-BLT/BLT-Vanish-Web', 'OWASP-BLT/BLT-Vanish-Flutter'], users: ['ananya-09'] },
    { id: 'blt-preflight', repos: ['OWASP-BLT/BLT-Preflight'], users: ['S3DFX-CYBER'] },
    { id: 'blt-toasty', repos: ['OWASP-BLT/BLT-Toasty'], users: ['ojaswa072'] },
    { id: 'blt-mcp', repos: ['OWASP-BLT/BLT-MCP'], users: ['Nachiket-Roy'] },
    { id: 'blt-safecloak', repos: ['OWASP-BLT/BLT-Safecloak'], users: ['karunarapolu'] },
    { id: 'blt-hackerhouse', repos: ['OWASP-BLT/BLT-Hackerhouse'], users: ['Rudra-rps'] },
    { id: 'blt-autopatch', repos: ['OWASP-BLT/BLT-Autopatch'], users: ['Sidd190'] },
    { id: 'blt-mayo', repos: ['OWASP-BLT/BLT-MAYO'], users: ['Jayant2908'] },
];

// GitHub requests one project needs: 5 per repository, 2 per user and repository.
export function projectCost(project) {
    return project.repos.length * (5 + 2 * project.users.length);
}

export function parseLastPage(linkHeader) {
    if (!linkHeader) return null;
    const last = linkHeader.split(',').map((part) => part.trim()).find((part) => /rel="last"/.test(part));
    const match = last && last.match(/<([^>]+)>/);
    if (!match) return null;
    try {
        const page = new URL(match[1]).searchParams.get('page');
        return page ? Number(page) : null;
    } catch {
        return null;
    }
}

async function ghRequest(env, url) {
    const headers = {
        Accept: 'application/vnd.github+json',
        'User-Agent': 'BLT-GSOC-Stats-Updater',
        'X-GitHub-Api-Version': '2022-11-28',
    };
    if (env.GH_API_TOKEN) headers.Authorization = `Bearer ${env.GH_API_TOKEN}`;
    const res = await fetch(url, { headers });
    let data = null;
    try {
        data = await res.json();
    } catch {
        data = null;
    }
    if (!res.ok) console.warn(`GitHub API ${res.status} for ${url}`);
    return { ok: res.ok, status: res.status, data, headers: res.headers };
}

async function searchCount(env, query) {
    const result = await ghRequest(env, `${GH_API}/search/issues?q=${encodeURIComponent(query)}&per_page=1`);
    if (!result.ok || !result.data) return null;
    return Number(result.data.total_count) || 0;
}

async function commitCount(env, repo) {
    const result = await ghRequest(env, `${GH_API}/repos/${repo}/commits?per_page=1`);
    if (!result.ok) return result.status === 409 ? 0 : null;
    const lastPage = parseLastPage(result.headers.get('link'));
    if (lastPage) return lastPage;
    return Array.isArray(result.data) ? result.data.length : 0;
}

function safeAdd(current, next) {
    return Number.isFinite(current) && Number.isFinite(next) ? current + next : null;
}

const REPO_FIELDS = ['openPR', 'mergedPR', 'openIssues', 'closedIssues', 'totalCommits'];

// Sequential on purpose: the search API counts requests per minute.
export async function fetchProject(env, project) {
    const aggregate = { openPR: 0, mergedPR: 0, openIssues: 0, closedIssues: 0, totalCommits: 0 };
    for (const repo of project.repos) {
        const stats = {
            openPR: await searchCount(env, `repo:${repo} is:pr is:open`),
            mergedPR: await searchCount(env, `repo:${repo} is:pr is:merged`),
            openIssues: await searchCount(env, `repo:${repo} is:issue is:open`),
            closedIssues: await searchCount(env, `repo:${repo} is:issue is:closed`),
            totalCommits: await commitCount(env, repo),
        };
        for (const field of REPO_FIELDS) aggregate[field] = safeAdd(aggregate[field], stats[field]);
    }
    const userStats = {};
    for (const user of project.users) {
        let prTotal = 0;
        let closedIssues = 0;
        for (const repo of project.repos) {
            prTotal = safeAdd(prTotal, await searchCount(env, `repo:${repo} is:pr author:${user}`));
            closedIssues = safeAdd(closedIssues, await searchCount(env, `repo:${repo} is:issue is:closed author:${user}`));
        }
        userStats[user] = { prTotal, closedIssues };
    }
    return { repos: project.repos, repoStats: aggregate, userStats };
}

// Fill nulls (failed requests) from the previous payload.
export function keepPrevious(next, previous) {
    if (!previous) return next;
    for (const field of REPO_FIELDS) {
        if (next.repoStats[field] === null && previous.repoStats && Number.isFinite(previous.repoStats[field])) {
            next.repoStats[field] = previous.repoStats[field];
        }
    }
    for (const [user, stats] of Object.entries(next.userStats)) {
        const old = previous.userStats && previous.userStats[user];
        if (!old) continue;
        for (const field of ['prTotal', 'closedIssues']) {
            if (stats[field] === null && Number.isFinite(old[field])) stats[field] = old[field];
        }
    }
    return next;
}

export function parseScript(text) {
    if (typeof text !== 'string') return null;
    const body = text.trim().replace(/^window\.GSOC2026_STATS\s*=\s*/, '').replace(/;\s*$/, '');
    try {
        return JSON.parse(body);
    } catch {
        return null;
    }
}

export function renderScript(payload) {
    return PREFIX + JSON.stringify(payload, null, 4) + ';\n';
}

async function previousPayload(env) {
    const stored = await env.DATA.get(KEY);
    if (stored) return parseScript(stored);
    if (!env.ASSETS) return null;
    try {
        const res = await env.ASSETS.fetch(new Request(`https://assets.local/${KEY}`));
        return res.ok ? parseScript(await res.text()) : null;
    } catch {
        return null;
    }
}

export async function refreshGsoc2026Stats(env, { scheduledTime = Date.now(), reset = false, budget = 24 } = {}) {
    return runChunked(env, {
        name: 'gsoc2026-stats',
        run: utcDay(scheduledTime),
        items: PROJECTS,
        cost: projectCost,
        budget,
        reset,
        process: (project) => fetchProject(env, project),
        finish: async (results) => {
            const previous = await previousPayload(env);
            const projects = {};
            for (const project of PROJECTS) {
                projects[project.id] = keepPrevious(results[project.id], previous && previous.projects && previous.projects[project.id]);
            }
            const updatedAt = new Date().toISOString();
            await putData(env, KEY, renderScript({ updatedAt, projects }), { updatedAt });
        },
    });
}
