/* ------------------------------------------------------------------ */
/*  CONSTANTS & STATE                                                   */
/* ------------------------------------------------------------------ */
const ORG  = 'OWASP-BLT';
const API  = 'https://api.github.com';
const PER_PAGE = 100;            // max allowed by GitHub API
const MAX_LANGUAGES_DISPLAYED = 12; // sidebar language filter cap

// Project board URLs sourced from https://github.com/OWASP-BLT/.github/blob/main/scripts/project_urls.json
const PROJECT_URLS = {
  'BLT':                          'https://github.com/orgs/OWASP-BLT/projects/2',
  'BLT-Flutter':                  'https://github.com/orgs/OWASP-BLT/projects/60',
  'BLT-Extension':                'https://github.com/orgs/OWASP-BLT/projects/59',
  'BLT-Lettuce':                  'https://github.com/orgs/OWASP-BLT/projects/65',
  'BLT-Sammich':                  'https://github.com/orgs/OWASP-BLT/projects/55',
  'BLT-Github-Sportscaster':      'https://github.com/orgs/OWASP-BLT/projects/63',
  'BLT-NetGuardian':              'https://github.com/orgs/OWASP-BLT/projects/81',
  'BLT-Rewards':                  'https://github.com/orgs/OWASP-BLT/projects/70',
  'BLT-Toasty':                   'https://github.com/orgs/OWASP-BLT/projects/54',
  'BLT-Leaf':                     'https://github.com/orgs/OWASP-BLT/projects/83',
  'BLT-Hackathons':               'https://github.com/orgs/OWASP-BLT/projects/47',
  'BLT-Personal-Privacy-Protection': 'https://github.com/orgs/OWASP-BLT/projects/73',
  'BLT-Panini':                   'https://github.com/orgs/OWASP-BLT/projects/78',
  'BLT-Sizzle':                   'https://github.com/orgs/OWASP-BLT/projects/76',
  'BLT-API':                      'https://github.com/orgs/OWASP-BLT/projects/80',
  'BLT-Newsletter':               'https://github.com/orgs/OWASP-BLT/projects/78',
};

const LANG_COLORS = {
  Python:'#3572A5', JavaScript:'#f1e05a', TypeScript:'#2b7489', HTML:'#e34c26',
  CSS:'#563d7c', Shell:'#89e051', Java:'#b07219', Go:'#00ADD8', Ruby:'#701516',
  PHP:'#4F5D95', 'C++':'#f34b7d', C:'#555555', Rust:'#dea584', Kotlin:'#F18E33',
  Swift:'#F05138', Dart:'#00B4AB', Vue:'#41b883', Dockerfile:'#384d54',
};

let allRepos   = [];
let filtered   = [];
let currentSort   = localStorage.getItem('blt-sort') || 'updated_at';
let currentFilter = 'all';
let currentLang   = '';
let currentSearch = '';
let currentLabel  = '';
let currentView   = localStorage.getItem('blt-view') || (window.innerWidth < 768 ? 'card' : 'table');
let tableSortCol  = localStorage.getItem('blt-table-sort-col') || 'updated_at';
let tableSortDir  = localStorage.getItem('blt-table-sort-dir') || 'desc';
let allLabels     = [];

/* ------------------------------------------------------------------ */
/*  DARK MODE                                                           */
/* ------------------------------------------------------------------ */
(function initDark() {
  const saved = localStorage.getItem('blt-dark');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (saved === 'dark' || (!saved && prefersDark)) {
    document.documentElement.classList.add('dark');
    document.getElementById('dark-icon').className = 'fa-solid fa-sun text-sm';
  }
})();

document.getElementById('dark-toggle').addEventListener('click', () => {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('blt-dark', isDark ? 'dark' : 'light');
  document.getElementById('dark-icon').className = isDark
    ? 'fa-solid fa-sun text-sm'
    : 'fa-solid fa-moon text-sm';
});

/* ------------------------------------------------------------------ */
/*  UTILITY HELPERS                                                     */
/* ------------------------------------------------------------------ */
function formatNumber(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return n;
}

function formatSize(kb) {
  if (!kb) return '—';
  if (kb < 1024) return kb + ' KB';
  if (kb < 1024 * 1024) return (kb / 1024).toFixed(1) + ' MB';
  return (kb / (1024 * 1024)).toFixed(1) + ' GB';
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60)   return 'just now';
  if (secs < 3600) return Math.floor(secs / 60) + 'm ago';
  if (secs < 86400)return Math.floor(secs / 3600) + 'h ago';
  if (secs < 2592000) return Math.floor(secs / 86400) + 'd ago';
  if (secs < 31536000) return Math.floor(secs / 2592000) + 'mo ago';
  return Math.floor(secs / 31536000) + 'y ago';
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function sparklineSVG(data, width = 80, height = 20, className = 'text-brand opacity-70') {
  if (!data || data.length < 2) return '';
  const max = Math.max(...data, 1);
  const step = width / (data.length - 1);
  const pts = data.map((v, i) => {
    const x = (i * step).toFixed(1);
    const y = (height - (v / max) * (height - 2) - 1).toFixed(1);
    return `${x},${y}`;
  }).join(' ');
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" class="sparkline ${className}" aria-hidden="true"><polyline fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" points="${pts}"/></svg>`;
}

/* ------------------------------------------------------------------ */
/*  PROJECT MATURITY SCORE (0 – 100)                                   */
/*  Weighted formula using available repo fields:                       */
/*    commits       25 pts  (saturates at 1,000 commits)               */
/*    contributors  20 pts  (saturates at 10 contributors)             */
/*    stars         15 pts  (saturates at 100 stars)                   */
/*    readme docs   15 pts  (saturates at 5,000 chars)                 */
/*    forks         10 pts  (saturates at 50 forks)                    */
/*    recent activity 10 pts (commits in last 4 weeks, sat. at 20)     */
/*    topics         5 pts  (saturates at 5 topics)                    */
/* ------------------------------------------------------------------ */
function maturityScore(r) {
  let score = 0;
  score += Math.min((r.total_commits || 0) / 1000, 1) * 25;
  score += Math.min(((r.contributors || []).length) / 10, 1) * 20;
  score += Math.min((r.stargazers_count || 0) / 100, 1) * 15;
  score += Math.min((r.readme_chars || 0) / 5000, 1) * 15;
  score += Math.min((r.forks_count || 0) / 50, 1) * 10;
  const recentCommits = (r.weekly_commits || []).slice(-4).reduce((a, b) => a + b, 0);
  score += Math.min(recentCommits / 20, 1) * 10;
  score += Math.min(((r.topics || []).length) / 5, 1) * 5;
  return Math.round(score);
}

function maturityMeta(score) {
  if (score >= 75) return { label: 'Mature',     color: 'text-green-700 dark:text-green-400',   bg: 'bg-green-50 dark:bg-green-900/30' };
  if (score >= 50) return { label: 'Beta',       color: 'text-blue-700 dark:text-blue-400',     bg: 'bg-blue-50 dark:bg-blue-900/30' };
  if (score >= 25) return { label: 'Alpha',      color: 'text-yellow-700 dark:text-yellow-400', bg: 'bg-yellow-50 dark:bg-yellow-900/30' };
  return              { label: 'Incubating', color: 'text-gray-500 dark:text-gray-400',     bg: 'bg-gray-100 dark:bg-gray-700' };
}

/* ------------------------------------------------------------------ */
/*  GITHUB API FETCH (paginated)                                        */
/* ------------------------------------------------------------------ */
async function fetchAllPages(url) {
  const results = [];
  let page = 1;
  while (true) {
    const sep = url.includes('?') ? '&' : '?';
    const resp = await fetch(`${url}${sep}per_page=${PER_PAGE}&page=${page}`, {
      headers: { 'Accept': 'application/vnd.github+json' }
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ message: 'Failed to parse error response' }));
      throw new Error(err.message || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    if (!Array.isArray(data) || data.length === 0) break;
    results.push(...data);
    if (data.length < PER_PAGE) break;
    page++;
  }
  return results;
}

/* ------------------------------------------------------------------ */
/*  LOAD REPOS                                                          */
/* ------------------------------------------------------------------ */

/**
 * Try to load pre-baked data.json (written every hour by the GitHub Action).
 * Falls back to live GitHub API calls if the file is missing or stale.
 */
async function loadRepos() {
  document.getElementById('error-state').classList.add('hidden');
  try {
    // Attempt to load the pre-generated snapshot first.
    // Add a cache-buster so the browser fetches the latest version.
    const resp = await fetch(`data.json?t=${Date.now()}`);
    if (resp.ok) {
      const payload = await resp.json();
      allRepos = payload.repos || [];
      buildLangFilter(allRepos);
      buildLabelFilter(allRepos);
      buildStats(allRepos, payload.cumulative);
      applyFilters();
      const generatedAt = payload.generated_at
        ? new Date(payload.generated_at).toLocaleString()
        : 'unknown';
      document.getElementById('footer-ts').innerHTML =
        `Stats generated by hourly action at <strong>${generatedAt}</strong>` +
        ` &nbsp;·&nbsp; <a href="data.json" class="text-brand hover:underline" target="_blank" rel="noopener">data.json</a>`;
      return;
    }
  } catch (err) {
    // data.json not available yet (action may not have run) – fall through to live API
    console.warn('data.json not available, falling back to live API:', err.message);
  }

  // Fallback: fetch live from the GitHub REST API
  try {
    const repos = await fetchAllPages(`${API}/orgs/${ORG}/repos`);
    allRepos = repos;
    buildLangFilter(repos);
    buildLabelFilter(repos);
    buildStats(repos, null);
    applyFilters();
    document.getElementById('footer-ts').textContent =
      'Live data fetched at ' + new Date().toLocaleString() +
      ' (data.json not yet available – action may not have run)';
  } catch (err) {
    showError(err.message);
  }
}

/* ------------------------------------------------------------------ */
/*  STATS BAR                                                           */
/* ------------------------------------------------------------------ */

/** Returns the number of real open issues (excluding PRs) for a repo. */
function repoIssueCount(r) {
  return Math.max(0, (r.open_issues_count || 0) - (r.open_pr_count || 0));
}

/**
 * @param {Array}  repos       - repo list
 * @param {object|null} cumulative - pre-computed cumulative block from data.json
 */
function buildStats(repos, cumulative) {
  // Prefer richer pre-computed totals; fall back to summing repo fields.
  const totalRepos    = cumulative ? cumulative.total_repos      : repos.length;
  const totalStars    = cumulative ? cumulative.total_stars      : repos.reduce((s, r) => s + r.stargazers_count, 0);
  const totalForks    = cumulative ? cumulative.total_forks      : repos.reduce((s, r) => s + r.forks_count, 0);
  const totalIssues   = cumulative ? cumulative.total_open_issues: repos.reduce((s, r) => s + repoIssueCount(r), 0);
  const totalPRs      = cumulative ? (cumulative.total_open_prs || 0) : repos.reduce((s, r) => s + (r.open_pr_count || 0), 0);
  const totalSizeKb   = cumulative ? cumulative.total_size_kb    : repos.reduce((s, r) => s + (r.size || 0), 0);
  const totalTopics   = cumulative ? cumulative.total_topics     : new Set(repos.flatMap(r => r.topics || [])).size;
  const totalReadmeChars = cumulative ? cumulative.total_readme_chars : repos.reduce((s, r) => s + (r.readme_chars || 0), 0);
  const totalBranches    = cumulative ? cumulative.total_branches     : repos.reduce((s, r) => s + (r.branch_count || 0), 0);
  // Use lang_bytes for an accurate count of all languages used (lang_repo_count only lists primary languages)
  const langCount     = cumulative
    ? Object.keys(cumulative.lang_bytes || cumulative.lang_repo_count || {}).length
    : new Set(repos.map(r => r.language).filter(Boolean)).size;

  const sizeMb = totalSizeKb > 0 ? `${(totalSizeKb / 1024).toFixed(1)} MB` : '—';

  const stats = [
    { icon: 'fa-solid fa-box',         label: 'Repos',       value: formatNumber(totalRepos),        color: 'text-indigo-500', href: `https://github.com/orgs/${ORG}/repositories` },
    { icon: 'fa-solid fa-star',        label: 'Stars',        value: formatNumber(totalStars),        color: 'text-yellow-500', href: `https://github.com/orgs/${ORG}/repositories?sort=stargazers` },
    { icon: 'fa-solid fa-code-fork',   label: 'Forks',        value: formatNumber(totalForks),        color: 'text-green-500',  href: `https://github.com/orgs/${ORG}/repositories?type=fork` },
    { icon: 'fa-solid fa-circle-dot',  label: 'Issues',       value: formatNumber(totalIssues),       color: 'text-brand',      href: `https://github.com/search?q=org%3A${ORG}+is%3Aissue+is%3Aopen&type=issues` },
    { icon: 'fa-solid fa-code-pull-request', label: 'PRs',         value: formatNumber(totalPRs),          color: 'text-teal-500',   href: `https://github.com/search?q=org%3A${ORG}+is%3Apr+is%3Aopen&type=pullrequests` },
    { icon: 'fa-solid fa-code',        label: 'Languages',    value: formatNumber(langCount),         color: 'text-purple-500', href: null },
    { icon: 'fa-solid fa-tags',        label: 'Topics',       value: formatNumber(totalTopics),       color: 'text-orange-500', href: null },
    { icon: 'fa-solid fa-database',    label: 'Size',         value: sizeMb,                          color: 'text-cyan-500',   href: null },
    { icon: 'fa-solid fa-file-lines',  label: 'README',       value: formatNumber(totalReadmeChars),  color: 'text-pink-500',   href: null },
    { icon: 'fa-solid fa-code-branch', label: 'Branches',     value: formatNumber(totalBranches),     color: 'text-violet-500', href: null },
  ];

  document.getElementById('stats-bar').innerHTML = stats.map(s => {
    const inner = `
      <i class="${s.icon} ${s.color} text-sm" aria-hidden="true"></i>
      <span class="text-xs font-bold text-gray-900 dark:text-white">${s.value}</span>
      <span class="text-xs text-gray-500 dark:text-gray-400">${s.label}</span>`;
    const cls = `bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 flex items-center gap-1.5 shadow-sm ${s.href ? 'hover:border-brand hover:shadow-md transition-all cursor-pointer' : 'opacity-60 cursor-default'}`;
    return s.href
      ? `<a href="${s.href}" target="_blank" rel="noopener noreferrer" class="${cls}" aria-label="${s.label}: ${s.value}">${inner}</a>`
      : `<div class="${cls}" title="No link available">${inner}</div>`;
  }).join('');
}

/* ------------------------------------------------------------------ */
/*  LANGUAGE FILTER SIDEBAR                                             */
/* ------------------------------------------------------------------ */
function buildLangFilter(repos) {
  const langCount = {};
  repos.forEach(r => { if (r.language) langCount[r.language] = (langCount[r.language] || 0) + 1; });

  const sorted = Object.entries(langCount).sort((a, b) => b[1] - a[1]).slice(0, MAX_LANGUAGES_DISPLAYED);

  const list = document.getElementById('lang-list');
  list.innerHTML = `
    <li>
      <button data-lang="" class="lang-btn w-full text-left px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors nav-active">
        All languages
      </button>
    </li>
  ` + sorted.map(([lang, count]) => `
    <li>
      <button data-lang="${escapeHtml(lang)}" class="lang-btn w-full text-left px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center justify-between">
        <span>
          <span class="lang-dot" style="background:${LANG_COLORS[lang] || '#8b949e'}"></span>${escapeHtml(lang)}
        </span>
        <span class="text-xs text-gray-400">${count}</span>
      </button>
    </li>
  `).join('');

  list.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      currentLang = btn.dataset.lang;
      list.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('nav-active', 'text-brand'));
      btn.classList.add('nav-active');
      applyFilters();
    });
  });
}

/* ------------------------------------------------------------------ */
/*  LABEL FILTER SIDEBAR                                                */
/* ------------------------------------------------------------------ */
function buildLabelFilter(repos) {
  // Extract all unique labels from topics
  const labelCount = {};
  repos.forEach(r => {
    (r.topics || []).forEach(label => {
      labelCount[label] = (labelCount[label] || 0) + 1;
    });
  });

  // Sort by count
  allLabels = Object.entries(labelCount)
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({ label, count }));

  // Initialize label search input
  const searchInput = document.getElementById('label-search-input');
  const dropdown = document.getElementById('label-dropdown');
  const labelList = document.getElementById('label-list');

  function renderLabelDropdown(filteredLabels = allLabels) {
    labelList.innerHTML = filteredLabels.map(({ label, count }) => `
      <li>
        <button
          data-label="${escapeHtml(label)}"
          class="label-option w-full text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center justify-between border-b border-gray-100 dark:border-gray-700 last:border-b-0"
        >
          <span class="text-gray-700 dark:text-gray-300 truncate">${escapeHtml(label)}</span>
          <span class="text-xs text-gray-400 ml-2 flex-shrink-0">${count}</span>
        </button>
      </li>
    `).join('');

    // Add click listeners to label options
    labelList.querySelectorAll('.label-option').forEach(btn => {
      btn.addEventListener('click', () => {
        currentLabel = btn.dataset.label;
        searchInput.value = currentLabel;
        dropdown.classList.add('hidden');
        document.querySelectorAll('.label-option').forEach(b => b.classList.remove('nav-active', 'text-brand'));
        btn.classList.add('nav-active', 'text-brand');
        applyFilters();
      });
    });
  }

  // Initial render
  renderLabelDropdown();

  // Search input listener
  searchInput.addEventListener('input', e => {
    const query = e.target.value.toLowerCase().trim();
    if (query === '') {
      renderLabelDropdown();
      dropdown.classList.add('hidden');
      if (currentLabel) {
        currentLabel = '';
        applyFilters();
      }
    } else {
      const filtered = allLabels.filter(({ label }) =>
        label.toLowerCase().includes(query)
      );

      if (filtered.length > 0) {
        renderLabelDropdown(filtered);
        dropdown.classList.remove('hidden');
      } else {
        labelList.innerHTML = `
          <li class="px-3 py-2 text-xs text-gray-400 dark:text-gray-500 italic">
            No labels found
          </li>
        `;
        dropdown.classList.remove('hidden');
      }
    }
  });

  // Focus listener to show dropdown
  searchInput.addEventListener('focus', () => {
    if (allLabels.length > 0) {
      renderLabelDropdown();
      dropdown.classList.remove('hidden');
    }
  });

  // Click outside to close dropdown
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });
}

/* ------------------------------------------------------------------ */
/*  FILTER & SORT                                                       */
/* ------------------------------------------------------------------ */
function applyFilters() {
  let repos = [...allRepos];

  // Type filter
  if (currentFilter === 'fork')     repos = repos.filter(r => r.fork);
  else if (currentFilter === 'source')   repos = repos.filter(r => !r.fork && !r.archived);
  else if (currentFilter === 'archived') repos = repos.filter(r => r.archived);

  // Language filter
  if (currentLang) repos = repos.filter(r => r.language === currentLang);

  // Label filter
  if (currentLabel) {
    repos = repos.filter(r =>
      (r.topics || []).some(t => t.toLowerCase() === currentLabel.toLowerCase())
    );
  }

  // Search
  if (currentSearch) {
    const q = currentSearch.toLowerCase();
    repos = repos.filter(r =>
      r.name.toLowerCase().includes(q) ||
      (r.description || '').toLowerCase().includes(q) ||
      (r.topics || []).some(t => t.toLowerCase().includes(q))
    );
  }

  // Sort (card view only; table view sorts in renderTableView)
  if (currentView === 'card') {
    repos.sort((a, b) => {
      if (currentSort === 'name') return a.name.localeCompare(b.name);
      if (currentSort === 'updated_at' || currentSort === 'created_at')
        return new Date(b[currentSort]) - new Date(a[currentSort]);
      if (currentSort === 'maturity') return maturityScore(b) - maturityScore(a);
      return (b[currentSort] || 0) - (a[currentSort] || 0);
    });
  }

  filtered = repos;
  renderRepos(repos);
}

/* ------------------------------------------------------------------ */
/*  RENDER REPOS (dispatches to table or card view)                    */
/* ------------------------------------------------------------------ */
function renderRepos(repos) {
  const grid  = document.getElementById('repo-grid');
  const table = document.getElementById('repo-table');
  const empty = document.getElementById('empty-state');
  const count = document.getElementById('results-count');

  if (repos.length === 0) {
    grid.innerHTML  = '';
    table.innerHTML = '';
    empty.classList.remove('hidden');
    count.textContent = '';
    return;
  }

  empty.classList.add('hidden');
  count.textContent = `Showing ${repos.length} of ${allRepos.length} repositories`;

  if (currentView === 'table') {
    grid.classList.add('hidden');
    table.classList.remove('hidden');
    document.getElementById('main-sidebar').classList.add('force-hidden');
    document.getElementById('main-layout').classList.add('table-view');
    document.querySelector('header').classList.add('table-view-header');
    renderTableView(repos, table);
  } else {
    table.classList.add('hidden');
    grid.classList.remove('hidden');
    document.getElementById('main-sidebar').classList.remove('force-hidden');
    document.getElementById('main-layout').classList.remove('table-view');
    document.querySelector('header').classList.remove('table-view-header');
    grid.innerHTML = repos.map(repo => repoCardHTML(repo)).join('');
  }
}

function repoCardHTML(r) {
  const langColor = LANG_COLORS[r.language] || '#8b949e';
  const hasGsoc = (r.topics || []).some(t => t.toLowerCase().includes('gsoc'));
  const topics = (r.topics || []).slice(0, 5).map(t => {
    if (t.toLowerCase().includes('gsoc')) {
      return `<span class="inline-block gsoc-label text-xs px-2 py-0.5 rounded-full">${escapeHtml(t)}</span>`;
    }
    return `<span class="inline-block bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full">${escapeHtml(t)}</span>`;
  }).join('');

  const archiveBadge = r.archived
    ? `<span class="inline-block bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300 text-xs px-2 py-0.5 rounded-full font-medium">Archived</span>`
    : '';
  const forkBadge = r.fork
    ? `<span class="inline-block bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs px-2 py-0.5 rounded-full font-medium">Fork</span>`
    : '';
  const privateBadge = r.private
    ? `<span class="inline-block bg-red-50 dark:bg-red-900/30 text-brand text-xs px-2 py-0.5 rounded-full font-medium">Private</span>`
    : '';

  const license = r.license ? `<span title="License" class="text-xs text-gray-400 dark:text-gray-500"><i class="fa-solid fa-scale-balanced mr-1" aria-hidden="true"></i>${escapeHtml(r.license.spdx_id)}</span>` : '';

  // Contributor avatars (slightly overlapping)
  const contributors = (r.contributors || []).slice(0, 10);
  const avatarStack = contributors.length
    ? `<div class="avatar-stack" title="Top contributors: ${contributors.map(c => escapeHtml(c.login)).join(', ')}">
        ${contributors.map(c => `<a href="${escapeHtml(c.html_url || `https://github.com/${c.login}`)}" target="_blank" rel="noopener noreferrer"><img src="${escapeHtml(c.avatar_url)}&amp;s=44" alt="${escapeHtml(c.login)}" title="${escapeHtml(c.login)} (${c.contributions} commits)" loading="lazy" /></a>`).join('')}
      </div>`
    : '';

  // Activity sparkline
  const sparkline = sparklineSVG(r.weekly_commits);

  // Star history sparkline
  const starSparkline = sparklineSVG(r.star_history, 80, 20, 'text-yellow-400 opacity-80');

  // Maturity score badge
  const score = maturityScore(r);
  const { label: matLabel, color: matColor, bg: matBg } = maturityMeta(score);
  const maturityBadge = `<span class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${matBg} ${matColor}" title="Maturity score: ${score}/100"><i class="fa-solid fa-rocket" aria-hidden="true"></i>${matLabel} ${score}</span>`;

  // Cloud icon for repos with wrangler.toml
  const wranglerIcon = r.has_wrangler_toml
    ? `<i class="fa-solid fa-cloud text-sky-500 text-xs" title="Uses Cloudflare Workers (wrangler.toml)" aria-label="Cloudflare Workers"></i>`
    : '';

  // Page/scroll icon for repos with GitHub Pages enabled
  const pagesIcon = r.has_pages
    ? `<i class="fa-solid fa-scroll text-purple-500 text-xs" title="GitHub Pages enabled" aria-label="GitHub Pages"></i>`
    : '';

  // Project board URL (rocket button)
  const projectUrl = PROJECT_URLS[r.name];

  return `
  <article class="repo-card${hasGsoc ? ' gsoc-card' : ''} bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 flex flex-col gap-3 shadow-sm" aria-label="Repository: ${escapeHtml(r.name)}">

    <!-- Header -->
    <div class="flex items-start gap-3">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap mb-1">
          <a
            href="${escapeHtml(r.html_url)}"
            target="_blank"
            rel="noopener noreferrer"
            class="font-semibold text-brand hover:underline underline-offset-2 truncate text-sm"
          >${escapeHtml(r.name)}</a>
          ${archiveBadge}${forkBadge}${privateBadge}
          ${maturityBadge}
          ${wranglerIcon}${pagesIcon}
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 leading-relaxed">
          ${escapeHtml(r.description) || '<span class="italic">No description</span>'}
        </p>
      </div>
    </div>

    <!-- Topics -->
    ${topics ? `<div class="flex flex-wrap gap-1.5">${topics}</div>` : ''}

    <!-- Stats row -->
    <div class="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
      ${r.language ? `
        <span title="Primary language">
          <span class="lang-dot" style="background:${langColor}"></span>${escapeHtml(r.language)}
        </span>
      ` : ''}
      <a href="${escapeHtml(r.html_url)}/stargazers" target="_blank" rel="noopener noreferrer" title="Stars" class="hover:text-yellow-500 transition-colors"><i class="fa-solid fa-star mr-1 text-yellow-400" aria-hidden="true"></i>${formatNumber(r.stargazers_count)}</a>
      <a href="${escapeHtml(r.html_url)}/forks" target="_blank" rel="noopener noreferrer" title="Forks" class="hover:text-green-600 transition-colors"><i class="fa-solid fa-code-fork mr-1 text-green-500" aria-hidden="true"></i>${formatNumber(r.forks_count)}</a>
      <a href="${escapeHtml(r.html_url)}/issues" target="_blank" rel="noopener noreferrer" title="Open issues" class="hover:text-brand transition-colors"><i class="fa-solid fa-circle-dot mr-1 text-brand" aria-hidden="true"></i>${formatNumber(repoIssueCount(r))}</a>
      ${r.open_pr_count ? `<a href="${escapeHtml(r.html_url)}/pulls" target="_blank" rel="noopener noreferrer" title="Open pull requests" class="hover:text-teal-500 transition-colors"><i class="fa-solid fa-code-pull-request mr-1 text-teal-500" aria-hidden="true"></i>${formatNumber(r.open_pr_count)}</a>` : ''}
      ${r.agent_pr_count ? `<a href="${escapeHtml(r.html_url)}/pulls" target="_blank" rel="noopener noreferrer" title="Open bot/agent pull requests" class="hover:text-purple-500 transition-colors"><i class="fa-solid fa-robot mr-1 text-purple-500" aria-hidden="true"></i>${formatNumber(r.agent_pr_count)}</a>` : ''}
      ${r.size ? `<span title="Repository size"><i class="fa-solid fa-database mr-1 text-cyan-400" aria-hidden="true"></i>${formatSize(r.size)}</span>` : ''}
      ${r.file_count ? `<span title="Total files (recursive)"><i class="fa-solid fa-file mr-1 text-teal-400" aria-hidden="true"></i>${formatNumber(r.file_count)} files</span>` : ''}
      ${r.branch_count ? `<a href="${escapeHtml(r.html_url)}/branches" target="_blank" rel="noopener noreferrer" title="Branches" class="hover:text-violet-500 transition-colors"><i class="fa-solid fa-code-branch mr-1 text-violet-400" aria-hidden="true"></i>${formatNumber(r.branch_count)} branches</a>` : ''}
      ${r.total_commits ? `<a href="${escapeHtml(r.html_url)}/commits" target="_blank" rel="noopener noreferrer" title="Total commits" class="hover:text-blue-500 transition-colors"><i class="fa-solid fa-code-commit mr-1 text-blue-400" aria-hidden="true"></i>${formatNumber(r.total_commits)} commits</a>` : ''}
      ${r.readme_chars ? `<span title="README character count"><i class="fa-solid fa-file-lines mr-1 text-pink-400" aria-hidden="true"></i>${formatNumber(r.readme_chars)} chars</span>` : ''}
    </div>

    <!-- Latest open issue -->
    ${r.latest_issue ? `
    <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title="Most recent open issue">
      <i class="fa-solid fa-circle-dot mr-1 text-brand" aria-hidden="true"></i>
      <a href="${escapeHtml(r.latest_issue.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-brand hover:underline transition-colors truncate">
        #${r.latest_issue.number}: ${escapeHtml(r.latest_issue.title)}
      </a>
    </div>` : ''}

    <!-- Latest commit -->
    ${r.latest_commit ? `
    <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title="Most recent commit">
      <i class="fa-solid fa-code-commit mr-1 text-blue-400" aria-hidden="true"></i>
      <a href="${escapeHtml(r.latest_commit.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors">
        ${r.latest_commit.author_avatar ? `<img src="${escapeHtml(r.latest_commit.author_avatar)}&amp;s=20" alt="${escapeHtml(r.latest_commit.author)}" title="${escapeHtml(r.latest_commit.author)}" class="inline-block w-4 h-4 rounded-full mr-1 align-middle" loading="lazy" />` : ''}${escapeHtml(r.latest_commit.message)}
      </a>
      ${r.latest_commit.author ? `<span class="ml-1 text-gray-400 dark:text-gray-500">by ${r.latest_commit.author_html_url ? `<a href="${escapeHtml(r.latest_commit.author_html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors">${escapeHtml(r.latest_commit.author)}</a>` : escapeHtml(r.latest_commit.author)}</span>` : ''}
    </div>` : ''}

    <!-- Latest PR -->
    ${r.latest_pr ? `
    <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title="Most recent PR [${r.latest_pr.state}]">
      ${r.latest_pr.state === 'merged'
        ? `<i class="fa-solid fa-code-merge mr-1 text-purple-500" aria-hidden="true" title="Merged"></i>`
        : r.latest_pr.state === 'open'
          ? `<i class="fa-solid fa-code-pull-request mr-1 text-green-500" aria-hidden="true" title="Open"></i>`
          : `<i class="fa-solid fa-circle-xmark mr-1 text-red-500" aria-hidden="true" title="Closed"></i>`}
      <a href="${escapeHtml(r.latest_pr.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors">
        ${r.latest_pr.author_avatar ? `<img src="${escapeHtml(r.latest_pr.author_avatar)}&amp;s=20" alt="${escapeHtml(r.latest_pr.author)}" title="${escapeHtml(r.latest_pr.author)}" class="inline-block w-4 h-4 rounded-full mr-1 align-middle" loading="lazy" />` : ''}#${r.latest_pr.number}: ${escapeHtml(r.latest_pr.title)}
      </a>
      ${r.latest_pr.author ? `<span class="ml-1 text-gray-400 dark:text-gray-500">by ${r.latest_pr.author_html_url ? `<a href="${escapeHtml(r.latest_pr.author_html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors">${escapeHtml(r.latest_pr.author)}</a>` : escapeHtml(r.latest_pr.author)}</span>` : ''}
    </div>` : ''}

    <!-- Latest release -->
    ${r.latest_release ? `
    <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title="Latest release">
      <i class="fa-solid fa-tag mr-1 text-green-500" aria-hidden="true"></i>
      <a href="${escapeHtml(r.latest_release.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-green-600 hover:underline transition-colors truncate">
        ${escapeHtml(r.latest_release.tag_name)}${r.latest_release.name && r.latest_release.name !== r.latest_release.tag_name ? ` – ${escapeHtml(r.latest_release.name)}` : ''}
      </a>
    </div>` : ''}

    <!-- Sparkline + avatars row -->
    ${(sparkline || starSparkline || avatarStack) ? `
    <div class="flex items-center justify-between gap-2">
      ${avatarStack || '<span></span>'}
      <div class="flex items-center gap-1.5">
        ${starSparkline ? `<span title="Star activity (last 26 weeks)">${starSparkline}</span>` : ''}
        ${sparkline ? `<span title="Commit activity (last 26 weeks)">${sparkline}</span>` : ''}
      </div>
    </div>` : ''}

    <!-- Footer -->
    <div class="flex items-center justify-between flex-wrap gap-2 pt-1 border-t border-gray-100 dark:border-gray-700">
      <div class="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500 flex-wrap">
        ${license}
        <span title="Default branch"><i class="fa-solid fa-code-branch mr-1" aria-hidden="true"></i>${escapeHtml(r.default_branch)}</span>
      </div>
      <span class="text-xs text-gray-400 dark:text-gray-500" title="Last updated: ${escapeHtml(r.updated_at)}">
        <i class="fa-solid fa-clock mr-1" aria-hidden="true"></i>${timeAgo(r.updated_at)}
      </span>
    </div>

    <!-- Action buttons -->
    <div class="flex gap-2 flex-wrap">
      <a
        href="${escapeHtml(r.html_url)}"
        target="_blank"
        rel="noopener noreferrer"
        class="flex-1 text-center text-xs font-semibold px-3 py-1.5 bg-brand text-white rounded-md hover:bg-red-700 transition-colors"
      >
        <i class="fa-brands fa-github mr-1.5" aria-hidden="true"></i>View Repo
      </a>
      ${r.homepage ? `
        <a
          href="${escapeHtml(r.homepage)}"
          target="_blank"
          rel="noopener noreferrer"
          class="flex-1 text-center text-xs font-semibold px-3 py-1.5 border border-brand text-brand rounded-md hover:bg-brand hover:text-white transition-colors"
        >
          <i class="fa-solid fa-arrow-up-right-from-square mr-1.5" aria-hidden="true"></i>Live Site
        </a>
      ` : `
        <span
          role="button"
          aria-disabled="true"
          class="flex-1 text-center text-xs font-semibold px-3 py-1.5 border border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-600 rounded-md cursor-not-allowed"
          title="No live site"
        >
          <i class="fa-solid fa-arrow-up-right-from-square mr-1.5" aria-hidden="true"></i>Live Site
        </span>
      `}
      ${projectUrl ? `
        <a
          href="${escapeHtml(projectUrl)}"
          target="_blank"
          rel="noopener noreferrer"
          title="View Project Board"
          class="flex-1 text-center text-xs font-semibold px-3 py-1.5 border border-brand text-brand rounded-md hover:bg-brand hover:text-white transition-colors"
        >
          <i class="fa-solid fa-rocket mr-1.5" aria-hidden="true"></i>Project
        </a>
      ` : `
        <span
          role="button"
          aria-disabled="true"
          class="flex-1 text-center text-xs font-semibold px-3 py-1.5 border border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-600 rounded-md cursor-not-allowed"
          title="No project board"
        >
          <i class="fa-solid fa-rocket mr-1.5" aria-hidden="true"></i>Project
        </span>
      `}
    </div>
    <!-- Tiny action buttons -->
    <div class="flex gap-1.5 flex-wrap">
      <a
        href="${escapeHtml(r.html_url)}/issues/new"
        target="_blank"
        rel="noopener noreferrer"
        title="Create new issue"
        class="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 rounded hover:border-brand hover:text-brand dark:hover:text-brand transition-colors"
      >
        <i class="fa-solid fa-circle-plus mr-1" aria-hidden="true"></i>New Issue
      </a>
      <a
        href="https://github.com/${ORG}/${r.name}/agents"
        target="_blank"
        rel="noopener noreferrer"
        title="Open agent tasks for this repo"
        class="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 rounded hover:border-brand hover:text-brand dark:hover:text-brand transition-colors"
      >
        <i class="fa-solid fa-robot mr-1" aria-hidden="true"></i>Agent Task
      </a>
    </div>
  </article>`;
}

/* ------------------------------------------------------------------ */
/*  RENDER TABLE VIEW                                                   */
/* ------------------------------------------------------------------ */
const TABLE_COLS = [
  { key: 'name',              label: 'Repository' },
  { key: 'topics',            label: 'Labels'     },
  { key: 'language',          label: 'Language'   },
  { key: 'stargazers_count',  label: 'Stars'      },
  { key: 'forks_count',       label: 'Forks'      },
  { key: 'open_issues_count', label: 'Issues'     },
  { key: 'open_pr_count',     label: 'PRs'        },
  { key: 'agent_pr_count',    label: 'Agent PRs'  },
  { key: 'total_commits',     label: 'Commits'    },
  { key: 'branch_count',      label: 'Branches'   },
  { key: 'size',              label: 'Size'       },
  { key: 'readme_chars',      label: 'README Size' },
  { key: 'maturity',          label: 'Maturity'   },
  { key: 'latest_release',    label: 'Release'    },
  { key: 'latest_commit',     label: 'Last Commit' },
  { key: 'latest_pr',        label: 'Last PR'    },
  { key: 'updated_at',        label: 'Updated'    },
  { key: 'latest_issue',      label: 'Latest Issue' },
  { key: 'infra',             label: 'Infra'        },
];

function renderTableView(repos, container) {
  // Sort repos by current table sort state
  const sorted = [...repos].sort((a, b) => {
    let v;
    if (tableSortCol === 'name')       v = a.name.localeCompare(b.name);
    else if (tableSortCol === 'updated_at') v = new Date(a.updated_at) - new Date(b.updated_at);
    else if (tableSortCol === 'maturity')   v = maturityScore(a) - maturityScore(b);
    else if (tableSortCol === 'open_issues_count') v = repoIssueCount(a) - repoIssueCount(b);
    else if (tableSortCol === 'topics') v = (a.topics || []).length - (b.topics || []).length;
    else if (tableSortCol === 'latest_release') {
      const ta = (a.latest_release && a.latest_release.published_at) ? new Date(a.latest_release.published_at) : null;
      const tb = (b.latest_release && b.latest_release.published_at) ? new Date(b.latest_release.published_at) : null;
      if (!ta && !tb) v = 0;
      else if (!ta) v = -1;
      else if (!tb) v = 1;
      else v = ta - tb;
    }
    else if (tableSortCol === 'latest_commit') {
      const ta = (a.latest_commit && a.latest_commit.date) ? new Date(a.latest_commit.date) : null;
      const tb = (b.latest_commit && b.latest_commit.date) ? new Date(b.latest_commit.date) : null;
      if (!ta && !tb) v = 0;
      else if (!ta) v = -1;
      else if (!tb) v = 1;
      else v = ta - tb;
    }
    else if (tableSortCol === 'latest_pr') {
      const ta = (a.latest_pr && a.latest_pr.updated_at) ? new Date(a.latest_pr.updated_at) : null;
      const tb = (b.latest_pr && b.latest_pr.updated_at) ? new Date(b.latest_pr.updated_at) : null;
      if (!ta && !tb) v = 0;
      else if (!ta) v = -1;
      else if (!tb) v = 1;
      else v = ta - tb;
    }
    else if (tableSortCol === 'latest_issue') {
      v = (a.latest_issue ? a.latest_issue.number : 0) - (b.latest_issue ? b.latest_issue.number : 0);
    }
    else v = (a[tableSortCol] || 0) - (b[tableSortCol] || 0);
    return tableSortDir === 'asc' ? v : -v;
  });

  // Build header cells
  const headerCells = TABLE_COLS.map(col => {
    const isActive = tableSortCol === col.key;
    const arrow = isActive ? (tableSortDir === 'asc' ? ' ▲' : ' ▼') : '';
    const activeCls = isActive ? ' text-brand dark:text-red-400 font-bold' : '';
    return `<th data-col="${col.key}" class="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap transition-colors${activeCls}" title="Sort by ${escapeHtml(col.label)}">${escapeHtml(col.label)}<span class="ml-1">${arrow}</span></th>`;
  }).join('');

  // Build rows
  const rows = sorted.map((r, i) => {
    const langColor = LANG_COLORS[r.language] || '#8b949e';
    const score = maturityScore(r);
    const { label: matLabel, color: matColor, bg: matBg } = maturityMeta(score);
    const rowBg = i % 2 === 0
      ? 'bg-white dark:bg-gray-900'
      : 'bg-gray-50/60 dark:bg-gray-800/60';
    const archiveBadge = r.archived
      ? `<span class="ml-1 text-xs bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300 px-1.5 rounded-full">Arc</span>`
      : '';
    const forkBadge = r.fork
      ? `<span class="ml-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 px-1.5 rounded-full">Fork</span>`
      : '';
    const projectUrl = PROJECT_URLS[r.name];
    const topics = r.topics || [];
    const topicCount = topics.length;
    const gsocTopic = topics.find(t => t.toLowerCase().includes('gsoc'));
    const gsocBadge = gsocTopic
      ? `<span class="inline-block gsoc-label text-xs px-2 py-0.5 rounded-full whitespace-nowrap ml-1">${escapeHtml(gsocTopic)}</span>`
      : '';
    const wranglerIcon = r.has_wrangler_toml
      ? `<i class="fa-solid fa-cloud text-sky-500 text-xs ml-1" title="Uses Cloudflare Workers (wrangler.toml)" aria-label="Cloudflare Workers"></i>`
      : '';
    const pagesIcon = r.has_pages
      ? `<i class="fa-solid fa-scroll text-purple-500 text-xs ml-1" title="GitHub Pages enabled" aria-label="GitHub Pages"></i>`
      : '';
    return `<tr class="${rowBg} border-b border-gray-100 dark:border-gray-700 hover:bg-red-50/40 dark:hover:bg-red-900/10 transition-colors">
      <td class="px-3 py-2 font-medium">
        <div class="flex items-center gap-1 flex-wrap">
          <a href="${escapeHtml(r.html_url)}" target="_blank" rel="noopener noreferrer" class="text-brand hover:underline underline-offset-2 text-sm whitespace-nowrap">${escapeHtml(r.name)}</a>${archiveBadge}${forkBadge}${gsocBadge}
        </div>
        ${r.description ? `<p class="text-xs text-gray-400 dark:text-gray-500 truncate max-w-xs mt-0.5">${escapeHtml(r.description)}</p>` : ''}
      </td>
      <td class="px-3 py-2 text-center whitespace-nowrap text-sm tabular-nums">
        ${topicCount > 0 ? `<span class="inline-block bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full">${topicCount}</span>` : '<span class="text-gray-300 dark:text-gray-600">—</span>'}
      </td>
      <td class="px-3 py-2 whitespace-nowrap text-sm">
        ${r.language
          ? `<span class="lang-dot" style="background:${langColor}"></span><span class="text-gray-600 dark:text-gray-300">${escapeHtml(r.language)}</span>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        <a href="${escapeHtml(r.html_url)}/stargazers" target="_blank" rel="noopener noreferrer" class="hover:text-yellow-500 transition-colors" title="Stars">
          <i class="fa-solid fa-star text-yellow-400 mr-1" aria-hidden="true"></i>${formatNumber(r.stargazers_count || 0)}
        </a>
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        <a href="${escapeHtml(r.html_url)}/forks" target="_blank" rel="noopener noreferrer" class="hover:text-green-600 transition-colors" title="Forks">
          <i class="fa-solid fa-code-fork text-green-500 mr-1" aria-hidden="true"></i>${formatNumber(r.forks_count || 0)}
        </a>
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        <a href="${escapeHtml(r.html_url)}/issues" target="_blank" rel="noopener noreferrer" class="hover:text-brand transition-colors" title="Open issues">
          <i class="fa-solid fa-circle-dot text-brand mr-1" aria-hidden="true"></i>${formatNumber(repoIssueCount(r))}
        </a>
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        ${r.open_pr_count
          ? `<a href="${escapeHtml(r.html_url)}/pulls" target="_blank" rel="noopener noreferrer" class="hover:text-teal-500 transition-colors" title="Open pull requests"><i class="fa-solid fa-code-pull-request text-teal-500 mr-1" aria-hidden="true"></i>${formatNumber(r.open_pr_count)}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        ${r.agent_pr_count
          ? `<a href="${escapeHtml(r.html_url)}/pulls" target="_blank" rel="noopener noreferrer" class="hover:text-purple-500 transition-colors" title="Open agent pull requests"><i class="fa-solid fa-robot text-purple-500 mr-1" aria-hidden="true"></i>${formatNumber(r.agent_pr_count)}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        ${r.total_commits
          ? `<a href="${escapeHtml(r.html_url)}/commits" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 transition-colors" title="Total commits"><i class="fa-solid fa-code-commit text-blue-400 mr-1" aria-hidden="true"></i>${formatNumber(r.total_commits)}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        ${r.branch_count
          ? `<a href="${escapeHtml(r.html_url)}/branches" target="_blank" rel="noopener noreferrer" class="hover:text-violet-500 transition-colors" title="Branches"><i class="fa-solid fa-code-branch text-violet-400 mr-1" aria-hidden="true"></i>${formatNumber(r.branch_count)}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        <i class="fa-solid fa-database text-cyan-400 mr-1" aria-hidden="true"></i>${formatSize(r.size)}
      </td>
      <td class="px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums">
        ${r.readme_chars ? `<i class="fa-solid fa-file-lines text-pink-400 mr-1" aria-hidden="true"></i>${formatNumber(r.readme_chars)}` : '<span class="text-gray-300 dark:text-gray-600">—</span>'}
      </td>
      <td class="px-3 py-2 whitespace-nowrap">
        <span class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${matBg} ${matColor}" title="Maturity score: ${score}/100">${matLabel} ${score}</span>
      </td>
      <td class="px-3 py-2 whitespace-nowrap text-xs">
        ${r.latest_release
          ? `<a href="${escapeHtml(r.latest_release.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-green-600 transition-colors text-gray-600 dark:text-gray-300" title="Latest release${r.latest_release.published_at ? ': ' + r.latest_release.published_at : ''}"><i class="fa-solid fa-tag text-green-500 mr-1" aria-hidden="true"></i>${escapeHtml(r.latest_release.tag_name)}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 text-xs max-w-[16rem]">
        ${r.latest_commit
          ? `<a href="${escapeHtml(r.latest_commit.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors text-gray-600 dark:text-gray-300 truncate block" title="${escapeHtml(r.latest_commit.message)}${r.latest_commit.author ? ' by ' + escapeHtml(r.latest_commit.author) : ''}"><i class="fa-solid fa-code-commit text-blue-400 mr-1" aria-hidden="true"></i>${r.latest_commit.author_avatar ? `<img src="${escapeHtml(r.latest_commit.author_avatar)}&amp;s=20" alt="${escapeHtml(r.latest_commit.author)}" title="${escapeHtml(r.latest_commit.author)}" class="inline-block w-4 h-4 rounded-full mr-1 align-middle" loading="lazy" />` : ''}${escapeHtml(r.latest_commit.message)}${r.latest_commit.author ? `<span class="ml-1 text-gray-400 dark:text-gray-500">by ${escapeHtml(r.latest_commit.author)}</span>` : ''}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 text-xs max-w-[16rem]">
        ${r.latest_pr ? (() => {
          const prState = r.latest_pr.state;
          const prIcon = prState === 'merged'
            ? `<i class="fa-solid fa-code-merge text-purple-500 mr-1" aria-hidden="true" title="Merged"></i>`
            : prState === 'open'
              ? `<i class="fa-solid fa-code-pull-request text-green-500 mr-1" aria-hidden="true" title="Open"></i>`
              : `<i class="fa-solid fa-circle-xmark text-red-500 mr-1" aria-hidden="true" title="Closed"></i>`;
          return `<a href="${escapeHtml(r.latest_pr.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors text-gray-600 dark:text-gray-300 truncate block" title="#${r.latest_pr.number}: ${escapeHtml(r.latest_pr.title)}${r.latest_pr.author ? ' by ' + escapeHtml(r.latest_pr.author) : ''} [${prState}]">${prIcon}${r.latest_pr.author_avatar ? `<img src="${escapeHtml(r.latest_pr.author_avatar)}&amp;s=20" alt="${escapeHtml(r.latest_pr.author)}" title="${escapeHtml(r.latest_pr.author)}" class="inline-block w-4 h-4 rounded-full mr-1 align-middle" loading="lazy" />` : ''}#${r.latest_pr.number}: ${escapeHtml(r.latest_pr.title)}${r.latest_pr.author ? `<span class="ml-1 text-gray-400 dark:text-gray-500">by ${escapeHtml(r.latest_pr.author)}</span>` : ''}</a>`;
        })() : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400" title="Last updated: ${escapeHtml(r.updated_at)}">${timeAgo(r.updated_at)}</td>
      <td class="px-3 py-2 text-xs max-w-[14rem]">
        ${r.latest_issue
          ? `<a href="${escapeHtml(r.latest_issue.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-brand hover:underline transition-colors text-gray-600 dark:text-gray-300 truncate block" title="#${r.latest_issue.number}: ${escapeHtml(r.latest_issue.title)}"><i class="fa-solid fa-circle-dot text-brand mr-1" aria-hidden="true"></i>#${r.latest_issue.number}: ${escapeHtml(r.latest_issue.title)}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">—</span>`}
      </td>
      <td class="px-3 py-2 whitespace-nowrap text-center">
        <div class="flex items-center justify-center gap-1.5">
          ${wranglerIcon}${pagesIcon}${(!wranglerIcon && !pagesIcon) ? '<span class="text-gray-300 dark:text-gray-600">—</span>' : ''}
        </div>
      </td>
      <td class="px-3 py-2 whitespace-nowrap">
        <div class="flex gap-1.5">
          <a href="${escapeHtml(r.html_url)}" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 bg-brand text-white rounded hover:bg-red-700 transition-colors" title="View on GitHub"><i class="fa-brands fa-github" aria-hidden="true"></i></a>
          ${r.homepage ? `<a href="${escapeHtml(r.homepage)}" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 border border-brand text-brand rounded hover:bg-brand hover:text-white transition-colors" title="Live Site"><i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i></a>` : `<span role="button" aria-disabled="true" class="text-xs px-2 py-1 border border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-600 rounded cursor-not-allowed" title="No live site"><i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i></span>`}
          ${projectUrl ? `<a href="${escapeHtml(projectUrl)}" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 border border-brand text-brand rounded hover:bg-brand hover:text-white transition-colors" title="Project Board"><i class="fa-solid fa-rocket" aria-hidden="true"></i></a>` : `<span role="button" aria-disabled="true" class="text-xs px-2 py-1 border border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-600 rounded cursor-not-allowed" title="No project board"><i class="fa-solid fa-rocket" aria-hidden="true"></i></span>`}
          <a href="${escapeHtml(r.html_url)}/issues/new" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 rounded hover:border-brand hover:text-brand transition-colors" title="New Issue"><i class="fa-solid fa-circle-plus" aria-hidden="true"></i></a>
          <a href="https://github.com/${ORG}/${r.name}/agents" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 rounded hover:border-brand hover:text-brand transition-colors" title="Open agent tasks for this repo"><i class="fa-solid fa-robot" aria-hidden="true"></i></a>
        </div>
      </td>
    </tr>`;
  }).join('');

  container.innerHTML = `
    <table class="border-collapse text-sm w-max">
      <thead class="bg-gray-50 dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700">
        <tr>
          ${headerCells}
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Links</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  // Add sort click listeners to column headers
  container.querySelectorAll('th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (tableSortCol === col) {
        tableSortDir = tableSortDir === 'desc' ? 'asc' : 'desc';
      } else {
        tableSortCol = col;
        tableSortDir = 'desc';
      }
      localStorage.setItem('blt-table-sort-col', tableSortCol);
      localStorage.setItem('blt-table-sort-dir', tableSortDir);
      renderTableView(filtered, container);
    });
  });
}

/* ------------------------------------------------------------------ */
/*  ERROR STATE                                                         */
/* ------------------------------------------------------------------ */
function showError(msg) {
  document.getElementById('repo-grid').innerHTML = '';
  document.getElementById('repo-table').innerHTML = '';
  document.getElementById('error-state').classList.remove('hidden');
  document.getElementById('error-msg').textContent = msg;
}

/* ------------------------------------------------------------------ */
/*  EVENT LISTENERS                                                     */
/* ------------------------------------------------------------------ */

// View toggle
function updateViewButtons() {
  document.getElementById('view-table-btn').classList.toggle('view-btn-active', currentView === 'table');
  document.getElementById('view-card-btn').classList.toggle('view-btn-active', currentView === 'card');
}

document.getElementById('view-table-btn').addEventListener('click', () => {
  currentView = 'table';
  localStorage.setItem('blt-view', 'table');
  updateViewButtons();
  applyFilters();
});

document.getElementById('view-card-btn').addEventListener('click', () => {
  currentView = 'card';
  localStorage.setItem('blt-view', 'card');
  updateViewButtons();
  applyFilters();
});

// Initialize button states immediately
updateViewButtons();

// Initialize sort UI to reflect stored preference
document.getElementById('sort-select').value = currentSort;
document.getElementById('sort-select-mobile').value = currentSort;
document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.sort === currentSort));

// Search (debounced)
let searchTimer;
document.getElementById('search-input').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentSearch = e.target.value.trim();
    applyFilters();
  }, 250);
});

// Sort (header select)
document.getElementById('sort-select').addEventListener('change', e => {
  currentSort = e.target.value;
  localStorage.setItem('blt-sort', currentSort);
  document.getElementById('sort-select-mobile').value = currentSort;
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.sort === currentSort));
  applyFilters();
});

// Sort (mobile select)
document.getElementById('sort-select-mobile').addEventListener('change', e => {
  currentSort = e.target.value;
  localStorage.setItem('blt-sort', currentSort);
  document.getElementById('sort-select').value = currentSort;
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.sort === currentSort));
  applyFilters();
});

// Filter (mobile select)
document.getElementById('filter-select-mobile').addEventListener('change', e => {
  currentFilter = e.target.value;
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.classList.toggle('nav-active', b.dataset.filter === currentFilter);
  });
  applyFilters();
});

// Filter buttons (sidebar)
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentFilter = btn.dataset.filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('nav-active'));
    btn.classList.add('nav-active');
    document.getElementById('filter-select-mobile').value = currentFilter;
    applyFilters();
  });
});

// Sort buttons (sidebar)
document.querySelectorAll('.sort-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentSort = btn.dataset.sort;
    localStorage.setItem('blt-sort', currentSort);
    document.getElementById('sort-select').value = currentSort;
    document.getElementById('sort-select-mobile').value = currentSort;
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('nav-active'));
    btn.classList.add('nav-active');
    applyFilters();
  });
});

// Retry button
document.getElementById('retry-btn').addEventListener('click', () => {
  document.getElementById('error-state').classList.add('hidden');
  document.getElementById('repo-grid').innerHTML = `
    <div class="skeleton h-48 rounded-xl"></div>
    <div class="skeleton h-48 rounded-xl"></div>
    <div class="skeleton h-48 rounded-xl"></div>
  `;
  loadRepos();
});

// Clear filters
document.getElementById('clear-btn').addEventListener('click', () => {
  currentSearch = '';
  currentFilter = 'all';
  currentLang = '';
  currentLabel = '';
  document.getElementById('search-input').value = '';
  document.getElementById('label-search-input').value = '';
  document.getElementById('sort-select').value = currentSort;
  document.getElementById('filter-select-mobile').value = 'all';
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.filter === 'all'));
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.lang === ''));
  document.querySelectorAll('.label-option').forEach(b => b.classList.remove('nav-active', 'text-brand'));
  document.getElementById('label-dropdown').classList.add('hidden');
  applyFilters();
});

// Clear label filter
document.getElementById('clear-label-btn').addEventListener('click', () => {
  currentLabel = '';
  document.getElementById('label-search-input').value = '';
  document.querySelectorAll('.label-option').forEach(b => b.classList.remove('nav-active', 'text-brand'));
  document.getElementById('label-dropdown').classList.add('hidden');
  applyFilters();
});

/* ------------------------------------------------------------------ */
/*  BOOT                                                                */
/* ------------------------------------------------------------------ */
loadRepos();
