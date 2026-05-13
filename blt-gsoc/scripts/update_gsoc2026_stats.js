#!/usr/bin/env node
'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');

const GH_API = 'https://api.github.com';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';

const PROJECTS = [
    {
        id: 'blt-netguardian',
        repos: ['OWASP-BLT/BLT-NetGuardian-Client', 'OWASP-BLT/BLT-NetGuardian'],
        users: ['Pritz395'],
    },
    {
        id: 'blt-university',
        repos: ['OWASP-BLT/BLT-University'],
        users: ['e-esakman'],
    },
    {
        id: 'blt-next',
        repos: ['OWASP-BLT/BLT-Next'],
        users: ['mdkaifansari04'],
    },
    {
        id: 'blt-vanish',
        repos: ['OWASP-BLT/BLT-Vanish-Web', 'OWASP-BLT/BLT-Vanish-Flutter'],
        users: ['ananya-09'],
    },
    {
        id: 'blt-preflight',
        repos: ['OWASP-BLT/BLT-Preflight'],
        users: ['S3DFX-CYBER'],
    },
    {
        id: 'blt-toasty',
        repos: ['OWASP-BLT/BLT-Toasty'],
        users: ['ojaswa072'],
    },
    {
        id: 'blt-mcp',
        repos: ['OWASP-BLT/BLT-MCP'],
        users: ['Nachiket-Roy'],
    },
    {
        id: 'blt-safecloak',
        repos: ['OWASP-BLT/BLT-Safecloak'],
        users: ['karunarapolu'],
    },
    {
        id: 'blt-hackerhouse',
        repos: ['OWASP-BLT/BLT-Hackerhouse'],
        users: ['Rudra-rps'],
    },
    {
        id: 'blt-autopatch',
        repos: ['OWASP-BLT/BLT-Autopatch'],
        users: ['Sidd190'],
    },
    {
        id: 'blt-mayo',
        repos: ['OWASP-BLT/BLT-MAYO'],
        users: ['Jayant2908'],
    },
];

function parseLastPage(linkHeader) {
    if (!linkHeader) {
        return null;
    }

    const segments = linkHeader.split(',').map((part) => part.trim());
    const lastSegment = segments.find((part) => /rel="last"/.test(part));

    if (!lastSegment) {
        return null;
    }

    const urlMatch = lastSegment.match(/<([^>]+)>/);
    if (!urlMatch) {
        return null;
    }

    try {
        const parsed = new URL(urlMatch[1]);
        const page = parsed.searchParams.get('page');
        return page ? Number(page) : null;
    } catch {
        return null;
    }
}

async function ghRequest(url) {
    const headers = {
        Accept: 'application/vnd.github+json',
        'User-Agent': 'BLT-GSOC-Stats-Updater',
        'X-GitHub-Api-Version': '2022-11-28',
    };

    if (GITHUB_TOKEN) {
        headers.Authorization = `Bearer ${GITHUB_TOKEN}`;
    }

    const res = await fetch(url, { headers });

    let data = null;
    let text = '';

    try {
        data = await res.json();
    } catch {
        try {
            text = await res.text();
        } catch {
            text = '';
        }
    }

    if (!res.ok) {
        console.warn(`GitHub API ${res.status} for ${url}`);
        return { ok: false, status: res.status, data, text, headers: res.headers };
    }

    return { ok: true, status: res.status, data, headers: res.headers };
}

async function searchCount(query) {
    const url = `${GH_API}/search/issues?q=${encodeURIComponent(query)}&per_page=1`;
    const result = await ghRequest(url);
    if (!result.ok || !result.data) {
        return null;
    }
    return Number(result.data.total_count) || 0;
}

async function commitCount(repo) {
    const url = `${GH_API}/repos/${repo}/commits?per_page=1`;
    const result = await ghRequest(url);
    if (!result.ok) {
        return result.status === 409 ? 0 : null;
    }

    const link = result.headers.get('link');
    const lastPage = parseLastPage(link);
    if (lastPage) {
        return lastPage;
    }

    if (Array.isArray(result.data)) {
        return result.data.length;
    }

    return 0;
}

async function repoStats(repo) {
    const [openPR, mergedPR, openIssues, closedIssues, totalCommits] = await Promise.all([
        searchCount(`repo:${repo} is:pr is:open`),
        searchCount(`repo:${repo} is:pr is:merged`),
        searchCount(`repo:${repo} is:issue is:open`),
        searchCount(`repo:${repo} is:issue is:closed`),
        commitCount(repo),
    ]);

    return { openPR, mergedPR, openIssues, closedIssues, totalCommits };
}

function safeAdd(current, next) {
    if (!Number.isFinite(current) || !Number.isFinite(next)) {
        return null;
    }
    return current + next;
}

async function userStatsForProject(repos, user) {
    if (repos.length === 0) {
        return { prTotal: null, closedIssues: null };
    }

    let prTotal = 0;
    let closedIssues = 0;

    for (const repo of repos) {
        const repoPrTotal = await searchCount(`repo:${repo} is:pr author:${user}`);
        const repoClosedIssues = await searchCount(`repo:${repo} is:issue is:closed author:${user}`);
        prTotal = safeAdd(prTotal, repoPrTotal);
        closedIssues = safeAdd(closedIssues, repoClosedIssues);
    }

    return { prTotal, closedIssues };
}

function mergeRepoStats(total, next) {
    total.openPR = safeAdd(total.openPR, next.openPR);
    total.mergedPR = safeAdd(total.mergedPR, next.mergedPR);
    total.openIssues = safeAdd(total.openIssues, next.openIssues);
    total.closedIssues = safeAdd(total.closedIssues, next.closedIssues);
    total.totalCommits = safeAdd(total.totalCommits, next.totalCommits);
    return total;
}

async function buildStats() {
    const projects = {};

    for (const project of PROJECTS) {
        const repos = project.repos;

        let aggregate = {
            openPR: null,
            mergedPR: null,
            openIssues: null,
            closedIssues: null,
            totalCommits: null,
        };

        if (repos.length > 0) {
            aggregate = { openPR: 0, mergedPR: 0, openIssues: 0, closedIssues: 0, totalCommits: 0 };
            for (const repo of repos) {
                const repoData = await repoStats(repo);
                aggregate = mergeRepoStats(aggregate, repoData);
            }
        }

        const userStats = {};
        for (const user of project.users) {
            userStats[user] = await userStatsForProject(repos, user);
        }

        projects[project.id] = {
            repos,
            repoStats: aggregate,
            userStats,
        };
    }

    return {
        updatedAt: new Date().toISOString(),
        projects,
    };
}

async function writeOutput(payload) {
    const outPath = path.join(process.cwd(), 'js', 'gsoc2026_stats.generated.js');
    const body = 'window.GSOC2026_STATS = ' + JSON.stringify(payload, null, 4) + ';\n';
    await fs.writeFile(outPath, body, 'utf8');
    console.log('Updated', outPath);
}

(async function main() {
    try {
        const payload = await buildStats();
        await writeOutput(payload);
    } catch (error) {
        console.error(error instanceof Error ? error.message : String(error));
        process.exitCode = 1;
    }
})();
