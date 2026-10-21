/* ------------------------------------------------------------------ */
/*  CONSTANTS & STATE                                                   */
/* ------------------------------------------------------------------ */
const ORG  = 'OWASP-BLT';
const API  = 'https://api.github.com';
const PER_PAGE = 100;            // max allowed by GitHub API
const MAX_LANGUAGES_DISPLAYED = 12; // sidebar language filter cap
const APP_VERSION = 'v0.3.0';
const DATA_SOURCES = {
  main: {
    label: 'Main',
    file: 'main_data.csv',
    fallbackFile: 'main_data.json',
    type: 'csv',
  },
  github: {
    label: 'GitHub',
    file: 'github_data.json',
    orgUrl: 'https://git.owaspblt.org/BLT',
    generatedBy: 'archived GitHub record from',
  },
  // Per-folder data of the monorepo on git.owaspblt.org (scripts/generate_forge_data.py, daily,
  // served from KV). Stars, forks, languages, releases, branches and sizes do not exist per folder.
  forge: {
    label: 'Forge',
    file: 'forge_data.json',
    orgUrl: 'https://git.owaspblt.org/BLT',
    generatedBy: 'generated daily from git.owaspblt.org at',
  },
};
const FORGE_WEB = 'https://git.owaspblt.org/BLT';

// Project board URLs sourced from https://git.owaspblt.org/BLT/dot_github/blob/main/scripts/project_urls.json
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
let currentView   = 'table';
let tableSortCol  = localStorage.getItem('blt-table-sort-col') || 'updated_at';
let tableSortDir  = localStorage.getItem('blt-table-sort-dir') || 'desc';
let allLabels     = [];
let currentDataSource = 'main';

/* ------------------------------------------------------------------ */
/*  DARK MODE                                                           */
/* ------------------------------------------------------------------ */
// The theme is applied before paint by theme-init.js and toggled from the BLT top bar.

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

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
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

function updateDataSourceTabs() {
  document.querySelectorAll('.data-source-tab').forEach(tab => {
    const isActive = tab.dataset.source === currentDataSource;
    tab.setAttribute('aria-selected', String(isActive));
    tab.setAttribute('aria-current', isActive ? 'page' : 'false');
    tab.classList.toggle('ring-2', isActive);
    tab.classList.toggle('ring-offset-1', isActive);
    tab.classList.toggle('dark:ring-offset-gray-900', isActive);
    tab.classList.toggle('ring-brand', isActive && currentDataSource === 'github');
    tab.classList.toggle('ring-green-500', isActive && currentDataSource === 'forge');
    tab.classList.toggle('ring-gray-500', isActive && currentDataSource === 'main');
    tab.classList.toggle('shadow-sm', isActive);
    tab.classList.toggle('scale-[1.03]', isActive);
    tab.classList.toggle('font-bold', isActive);
    tab.classList.toggle('opacity-60', !isActive);
    tab.classList.toggle('grayscale', !isActive);
  });
}

function resetDataSourceFilters(source) {
  currentSearch = '';
  currentFilter = 'all';
  currentLang = '';
  currentLabel = '';

  if (source === 'github' || source === 'forge') {
    currentView = 'table';
    localStorage.setItem('blt-view', currentView);
  }

  const searchInput = document.getElementById('search-input');
  const labelSearchInput = document.getElementById('label-search-input');
  const filterMobile = document.getElementById('filter-select-mobile');
  const labelDropdown = document.getElementById('label-dropdown');
  if (searchInput) searchInput.value = '';
  if (labelSearchInput) labelSearchInput.value = '';
  if (filterMobile) filterMobile.value = 'all';
  if (labelDropdown) labelDropdown.classList.add('hidden');
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.filter === 'all'));
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.lang === ''));
  document.querySelectorAll('.label-option').forEach(b => b.classList.remove('nav-active', 'text-brand'));
  updateViewButtons();
}

function repoDisplayName(r) {
  if (String(r.name || '').toLowerCase() === 'blt-waypoint') return 'BLT-Waypoint';
  return r.name;
}

function repoDescription(r) {
  if (String(r.name || '').toLowerCase() === 'blt-waypoint') {
    return 'OWASP BLT project directory and deployment waypoint';
  }
  return r.description || '';
}

function isOrgMetaRepo(r) {
  return ['.github', 'dot_github'].includes(String(r.name || '').toLowerCase());
}

function orgMetaRepoLast(a, b) {
  if (isOrgMetaRepo(a) === isOrgMetaRepo(b)) return 0;
  return isOrgMetaRepo(a) ? 1 : -1;
}

// Canonical project artwork from https://blt-logo.vercel.app/. Every PNG is
// normalized to a 512×512 transparent canvas. Projects without a published
// mark use the core BLT logo instead of a broken image.
const PROJECT_LOGOS = {
  '.github': 'project-logos/.github.svg',
  'blt': 'project-logos-v2/BLT-Core.svg',
  'blt-core': 'project-logos-v2/BLT-Core.svg',
  'blt-legacy': 'project-logos-v2/BLT-Legacy.svg',
  'dot_github': 'project-logos/.github.svg',
  'blt-gitcaster': 'canonical-logos/github-sport-caster.png',
  'blt-vanish': 'canonical-logos/blt-vanish.png',
  'blt-autopatch': 'project-logos-v2/BLT-Autopatch.svg',
  'blt-action': 'canonical-logos/blt-action.png',
  'blt-api': 'canonical-logos/blt-api.png',
  'blt-bacon': 'canonical-logos/blt-bacon.png',
  'blt-byte': 'canonical-logos/blt-bytes.png',
  'blt-cve': 'canonical-logos/blt-cve.png',
  'blt-design': 'canonical-logos/blt-design.png',
  'blt-design-contest': 'project-logos-v2/BLT-Design-Contest.svg',
  'blt-dash': 'project-logos-v2/BLT-Dash.svg',
  'blt-docs': 'canonical-logos/blt-docs.png',
  'blt-extension': 'canonical-logos/blt-extension.png',
  'blt-github-sportscaster': 'canonical-logos/github-sport-caster.png',
  'blt-gsoc': 'canonical-logos/blt-gsoc.png',
  'blt-hackathon': 'canonical-logos/blt-hackathon.png',
  'blt-hackathons': 'canonical-logos/blt-hackathon.png',
  'blt-jobs': 'canonical-logos/blt-jobs.png',
  'blt-ketchup': 'project-logos-v2/BLT-Ketchup.svg',
  'blt-leaf': 'canonical-logos/blt-leaf.png',
  'blt-mcp': 'canonical-logos/blt-mcp.png',
  'blt-monitor': 'project-logos/BLT-Monitor.svg',
  'blt-netguardian': 'canonical-logos/blt-netguardian.png',
  'blt-netguardian-client': 'project-logos/BLT-NetGuardian-Client.svg',
  'blt-newsletter': 'canonical-logos/blt-newletter.png',
  'blt-next': 'canonical-logos/blt-next.png',
  'blt-nexus': 'project-logos-v2/BLT-Nexus.svg',
  'blt-ossh': 'canonical-logos/blt-ossh.png',
  'blt-owasp-bumper': 'canonical-logos/blt-bumper.png',
  'blt-owasp-metadata': 'project-logos/BLT-OWASP-metadata.svg',
  'blt-owasp-projects': 'project-logos/BLT-OWASP-Projects.svg',
  'blt-owasp-wich': 'canonical-logos/blt-wich.png',
  'blt-panini': 'project-logos/BLT-Panini.svg',
  'blt-pages': 'canonical-logos/blt-pages.png',
  'blt-pool': 'project-logos-v2/BLT-Pool.svg',
  'blt-preflight': 'canonical-logos/blt-preflight.png',
  'blt-safecloak': 'canonical-logos/blt-safecloack.png',
  'blt-sammich': 'canonical-logos/blt-sammich.png',
  'blt-sizzle': 'canonical-logos/sizzle.png',
  'blt-start': 'project-logos-v2/BLT-Start.svg',
  'blt-toasty': 'project-logos/BLT-Toasty.svg',
  'blt-timer-flutter': 'canonical-logos/blt-timer.png',
  'blt-timer-web': 'canonical-logos/blt-timer.png',
  'blt-tomato': 'canonical-logos/blt-tomato.png',
  'blt-university': 'canonical-logos/blt-university.png',
  'blt-vanish-flutter': 'canonical-logos/blt-vanish.png',
  'blt-vanish-web': 'canonical-logos/blt-vanish.png',
  'blt-waypoint': 'project-logos-v2/BLT-Waypoint.svg',
  'blt-zero': 'canonical-logos/blt-zero.png',
  'blt-cli': 'project-logos-v2/BLT-CLI.svg',
  'blt-enforcement': 'project-logos-v2/BLT-Enforcement.svg',
  'blt-flutter': 'project-logos/BLT-Flutter.svg',
  'blt-ideas': 'project-logos/BLT-Ideas.svg',
  'blt-lettuce': 'project-logos/BLT-Lettuce.svg',
  'blt-profiles': 'project-logos-v2/BLT-Profiles.svg',
  'blt-rewards': 'project-logos-v2/BLT-Rewards.svg',
  'coderabbit': 'project-logos-v2/CodeRabbit.svg',
  'my-gsoc-tool': 'canonical-logos/blt-gsoc-tool.png',
};

function projectLogoPath(r) {
  const filename = PROJECT_LOGOS[String(r.folder || '').toLowerCase()] || PROJECT_LOGOS[String(r.name || '').toLowerCase()];
  return filename ? `./imgs/${filename}` : './imgs/project-logos-v2/BLT-Core.svg';
}

function projectLogoHTML(r, classes = 'h-9 w-9') {
  const path = projectLogoPath(r);
  return `<span class="${classes} shrink-0 rounded-full overflow-hidden flex items-center justify-center"><img src="${escapeHtml(path)}" alt="${escapeHtml(repoDisplayName(r))} logo" class="h-full w-full object-contain" loading="lazy" /></span>`;
}

// Forge URLs of a project folder (rows of every source carry `folder` or a folder html_url).
function repoFolder(r) {
  if (r.folder) return r.folder;
  const match = /^https:\/\/git\.owaspblt\.org\/BLT\/tree\/main\/([^/?#]+)/.exec(r.html_url || '');
  return match ? match[1] : '';
}

function repoLinks(r) {
  const folder = repoFolder(r);
  if (!folder) {
    const base = r.html_url || '';
    return { repo: base, issues: `${base}/issues`, newIssue: `${base}/issues/new`, pulls: `${base}/pulls`, commits: `${base}/commits`, stars: `${base}/stargazers`, forks: `${base}/forks`, branches: `${base}/branches` };
  }
  const repo = `${FORGE_WEB}/tree/main/${folder}`;
  return {
    repo,
    issues: `${FORGE_WEB}/issues?label=${encodeURIComponent(folder)}`,
    newIssue: `${FORGE_WEB}/issues/new`,
    pulls: `${FORGE_WEB}/pulls`,
    commits: repo,
    stars: '',
    forks: '',
    branches: '',
  };
}

// A stat that links when the forge has a page for it, else plain text.
function statLink(url, cls, title, inner) {
  return url
    ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(title)}" class="${cls}">${inner}</a>`
    : `<span title="${escapeHtml(title)}">${inner}</span>`;
}

function hasValue(v) {
  return v !== null && v !== undefined;
}

function updateVersionLabel() {
  const label = document.getElementById('version-label');
  if (label) label.textContent = APP_VERSION;
}

const CLOUDFLARE_LIVE_SITES = {
  'blt-action': 'https://action.owaspblt.org/',
  'blt-api': 'https://api.owaspblt.org/',
  'blt-autopatch': 'https://autopatch.owaspblt.org/',
  'blt-byte': 'https://byte.owaspblt.org/',
  'blt-cli': 'https://cli.owaspblt.org/',
  'blt-cve': 'https://cve.owaspblt.org/',
  'blt-dash': 'https://dash.owaspblt.org/',
  'blt-design': 'https://design.owaspblt.org/',
  'blt-design-contest': 'https://contest.owaspblt.org/',
  'blt-docs': 'https://docs.owaspblt.org/',
  'blt-enforcement': 'https://enforcement.owaspblt.org/',
  'blt-extension': 'https://extension.owaspblt.org/',
  'blt-flutter': 'https://flutter.owaspblt.org/',
  'blt-github-sportscaster': 'https://gitcaster.owaspblt.org/',
  'blt-gitcaster': 'https://gitcaster.owaspblt.org/',
  'blt-gsoc': 'https://gsoc.owaspblt.org/',
  'blt-hackerhouse': 'https://hackerhouse.owaspblt.org/',
  'blt-hackathons': 'https://hackathons.owaspblt.org/',
  'blt-ideas': 'https://ideas.owaspblt.org/',
  'blt-jobs': 'https://jobs.owaspblt.org/',
  'blt-ketchup': 'https://ketchup.owaspblt.org/',
  'blt-leaf': 'https://leaf.owaspblt.org/',
  'blt-lettuce': 'https://lettuce.owaspblt.org/',
  'blt-mcp': 'https://mcp.owaspblt.org/',
  'blt-mayo': 'https://mayo.owaspblt.org/',
  'blt-monitor': 'https://monitor.owaspblt.org/',
  'blt-netguardian': 'https://netguardian.owaspblt.org/',
  'blt-newsletter': 'https://newsletter.owaspblt.org/',
  'blt-next': 'https://next.owaspblt.org/',
  'blt-nexus': 'https://nexus.owaspblt.org/',
  'blt-ossh': 'https://ossh.owaspblt.org/',
  'blt-owasp-bumper': 'https://bumper.owaspblt.org/',
  'blt-owasp-metadata': 'https://metadata.owaspblt.org/',
  'blt-owasp-projects': 'https://projects.owaspblt.org/',
  'blt-owasp-wich': 'https://wich.owaspblt.org/',
  'blt-pages': 'https://pages.owaspblt.org/',
  'blt-panini': 'https://panini.owaspblt.org/',
  'blt-pool': 'https://pool.owaspblt.org/',
  'blt-preflight': 'https://preflight.owaspblt.org/',
  'blt-profiles': 'https://profiles.owaspblt.org/',
  'blt-rewards': 'https://rewards.owaspblt.org/',
  'blt-safecloak': 'https://safecloak.owaspblt.org/',
  'blt-sammich': 'https://sammich.owaspblt.org/',
  'blt-sizzle': 'https://sizzle.owaspblt.org/',
  'blt-start': 'https://start.owaspblt.org/',
  'blt-timer-web': 'https://timer.owaspblt.org/',
  'blt-toasty': 'https://toasty.owaspblt.org/',
  'blt-tomato': 'https://tomato.owaspblt.org/',
  'blt-university': 'https://university.owaspblt.org/',
  'blt-vanish': 'https://vanish.owaspblt.org/',
  'blt-vanish-web': 'https://vanish.owaspblt.org/',
  'blt-waypoint': 'https://waypoint.owaspblt.org/',
  'blt-zero': 'https://zero.owaspblt.org/',
  'my-gsoc-tool': 'https://gsoc-tool.owaspblt.org/',
};

function liveSiteMeta(r) {
  const liveUrl = CLOUDFLARE_LIVE_SITES[String(r.name || '').toLowerCase()] || r.homepage;
  if (!liveUrl) {
    return {
      url: '',
      label: 'No live site',
      classes: 'text-gray-300 dark:text-gray-600',
      icon: 'fa-solid fa-minus',
    };
  }

  let host = '';
  try {
    host = new URL(liveUrl).hostname.toLowerCase();
  } catch (e) {
    host = '';
  }

  const isGitHubPage = host === 'github.io' || host.endsWith('.github.io') || host === 'github.owaspblt.org';
  const isOwaspBlt = host === 'owaspblt.org' || host.endsWith('.owaspblt.org');
  if (isGitHubPage) {
    return {
      url: liveUrl,
      label: 'GitHub Pages',
      classes: 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 ring-red-200 dark:ring-red-800',
      icon: 'fa-brands fa-github',
    };
  }
  if (isOwaspBlt) {
    return {
      url: liveUrl,
      label: 'owaspblt.org',
      classes: 'text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/30 ring-green-200 dark:ring-green-800',
      icon: 'fa-solid fa-globe',
    };
  }
  return {
    url: liveUrl,
    label: 'Live site',
    classes: 'text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 ring-gray-200 dark:ring-gray-700',
    icon: 'fa-solid fa-arrow-up-right-from-square',
  };
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        value += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      row.push(value);
      value = '';
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') i++;
      row.push(value);
      if (row.some(cell => cell.trim() !== '')) rows.push(row);
      row = [];
      value = '';
    } else {
      value += char;
    }
  }

  if (value || row.length) {
    row.push(value);
    if (row.some(cell => cell.trim() !== '')) rows.push(row);
  }

  return rows;
}

function csvToMainPayload(text) {
  const rows = parseCsv(text);
  if (!rows.length) return { generated_at: '', source: 'main', org: ORG, repos: [] };

  const headers = rows[0].map(header => header.trim());
  const repos = rows.slice(1).map(cells => {
    const raw = {};
    headers.forEach((header, index) => {
      raw[header] = (cells[index] || '').trim();
    });

    return {
      id: raw.id ? Number(raw.id) : undefined,
      name: raw.name,
      full_name: raw.full_name,
      html_url: raw.html_url,
      description: raw.description,
      homepage: raw.homepage || null,
      topics: raw.topics ? raw.topics.split('|').map(t => t.trim()).filter(Boolean) : [],
      language: raw.language || null,
      fork: (raw.fork || '').toLowerCase() === 'true',
      archived: (raw.archived || '').toLowerCase() === 'true',
      updated_at: raw.updated_at,
      folder: raw.folder || '',
    };
  }).filter(repo => repo.name);

  return {
    generated_at: '',
    source: 'main',
    org: ORG,
    repos,
  };
}

async function fetchSnapshotPayload(source) {
  if (source.type === 'csv' && window.BLT_MAIN_DATA_CSV) {
    const payload = csvToMainPayload(window.BLT_MAIN_DATA_CSV);
    if (!payload.repos || payload.repos.length === 0) {
      throw new Error('Embedded main_data.js did not contain repository rows');
    }
    return payload;
  }

  const resp = await fetch(`${source.file}?t=${Date.now()}`);
  if (!resp.ok) {
    throw new Error(`${source.file} returned HTTP ${resp.status}`);
  }

  const payload = source.type === 'csv'
    ? csvToMainPayload(await resp.text())
    : await resp.json();

  if (!payload.repos || payload.repos.length === 0) {
    throw new Error(`${source.file} did not contain repository rows`);
  }

  return payload;
}

async function fetchFallbackSnapshotPayload(source) {
  if (!source.fallbackFile) throw new Error('No fallback snapshot configured');

  const resp = await fetch(`${source.fallbackFile}?t=${Date.now()}`);
  if (!resp.ok) {
    throw new Error(`${source.fallbackFile} returned HTTP ${resp.status}`);
  }

  const payload = await resp.json();
  if (!payload.repos || payload.repos.length === 0) {
    throw new Error(`${source.fallbackFile} did not contain repository rows`);
  }

  return payload;
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
 * Try to load a pre-baked data snapshot. GitHub is the default source and
 * falls back to live GitHub API calls if its snapshot is missing.
 */
async function loadRepos() {
  const errorEl = document.getElementById('error-state');
  if (errorEl) errorEl.classList.add('hidden');
  updateDataSourceTabs();

  const source = DATA_SOURCES[currentDataSource] || DATA_SOURCES.github;

  // Track whether the snapshot was successfully fetched and parsed so that any
  // downstream processing error is not silently swallowed and the live-API
  // fallback is not invoked when the snapshot was actually available.
  let snapshotLoaded = false;

  try {
    // Attempt to load the pre-generated snapshot first.
    // Add a cache-buster so the browser fetches the latest version.
    let payload;
    let loadedFile = source.file;
    try {
      payload = await fetchSnapshotPayload(source);
    } catch (primaryErr) {
      if (!source.fallbackFile) throw primaryErr;
      console.warn(`${source.file} not available, falling back to ${source.fallbackFile}:`, primaryErr.message);
      payload = await fetchFallbackSnapshotPayload(source);
      loadedFile = source.fallbackFile;
    }
    snapshotLoaded = true;
    allRepos = payload.repos || [];
    buildLangFilter(allRepos);
    buildLabelFilter(allRepos);
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.placeholder = `Search ${allRepos.length} repositories…`;
    
    // Pre-calculate expensive metrics
    allRepos.forEach(r => {
      r._maturityScore = maturityScore(r);
      r._maturityMeta = maturityMeta(r._maturityScore);
    });

    applyFilters();
    const generatedAt = payload.generated_at
      ? new Date(payload.generated_at).toLocaleString()
      : 'unknown';
    const footerTs = document.getElementById('footer-ts');
    if (footerTs) {
      if (source.type === 'csv') {
        const loadedFromEmbeddedCsv = loadedFile === source.file && window.BLT_MAIN_DATA_CSV;
        footerTs.innerHTML =
          `${source.label} data loaded from ${loadedFromEmbeddedCsv ? 'embedded CSV cache' : loadedFile === source.file ? 'editable CSV' : 'fallback JSON'}` +
          ` &nbsp;·&nbsp; <a href="${loadedFile}" class="text-brand hover:underline" target="_blank" rel="noopener">${loadedFile}</a>`;
      } else {
        footerTs.innerHTML =
          `${source.label} data ${source.generatedBy || 'generated at'} <strong>${generatedAt}</strong>` +
          ` &nbsp;·&nbsp; <a href="${loadedFile}" class="text-brand hover:underline" target="_blank" rel="noopener">${loadedFile}</a>` +
          (source.orgUrl ? ` &nbsp;·&nbsp; <a href="${source.orgUrl}" class="text-brand hover:underline" target="_blank" rel="noopener">${source.label} org</a>` : '');
      }
    }
    return;
  } catch (err) {
    if (snapshotLoaded) {
      // The snapshot was available but processing/rendering failed - surface the
      // error directly rather than falling through to the live-API path where
      // the same failure would repeat and produce a confusing error message.
      console.error('Repository render error:', err);
      showError('Failed to render repository data. Please try refreshing the page.');
      return;
    }
    if (currentDataSource !== 'github') {
      console.error(`${source.file} not available:`, err);
      showError(`Unable to load ${source.label} repository data. Please try again later.`);
      return;
    }
    // GitHub snapshot not available yet (action may not have run) - fall through to live API
    console.warn(`${source.file} not available, falling back to live API:`, err.message);
  }

  // Fallback: fetch live from the GitHub REST API
  try {
    const repos = await fetchAllPages(`${API}/orgs/${ORG}/repos`);
    allRepos = repos;
    buildLangFilter(repos);
    buildLabelFilter(repos);
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.placeholder = `Search ${allRepos.length} repositories…`;
    
    // Pre-calculate expensive metrics
    allRepos.forEach(r => {
      r._maturityScore = maturityScore(r);
      r._maturityMeta = maturityMeta(r._maturityScore);
    });

    applyFilters();
    const footerTs = document.getElementById('footer-ts');
    if (footerTs) {
      footerTs.textContent =
        'Live data fetched at ' + new Date().toLocaleString() +
        ` (${source.file} not yet available - action may not have run)`;
    }
  } catch (err) {
    console.error('Failed to load repositories:', err);
    showError('Unable to load repositories. Please try again later.');
  }
}

/* ------------------------------------------------------------------ */
/*  ISSUE COUNT HELPER                                                  */
/* ------------------------------------------------------------------ */

/** Returns the number of real open issues (excluding PRs) for a repo. */
function repoIssueCount(r) {
  // Forge rows count issues only; GitHub's open_issues_count included pull requests.
  if (r.folder && hasValue(r.commits_365d)) return r.open_issues_count || 0;
  return Math.max(0, (r.open_issues_count || 0) - (r.open_pr_count || 0));
}

/* ------------------------------------------------------------------ */
/*  LANGUAGE FILTER SIDEBAR                                             */
/* ------------------------------------------------------------------ */
function buildLangFilter(repos) {
  const langCount = {};
  repos.forEach(r => { if (r.language) langCount[r.language] = (langCount[r.language] || 0) + 1; });

  const sorted = Object.entries(langCount).sort((a, b) => b[1] - a[1]).slice(0, MAX_LANGUAGES_DISPLAYED);

  const list = document.getElementById('lang-list');
  if (!list) return;
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
  if (!searchInput || !dropdown || !labelList) return;

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
      repoDisplayName(r).toLowerCase().includes(q) ||
      repoDescription(r).toLowerCase().includes(q) ||
      (r.topics || []).some(t => t.toLowerCase().includes(q))
    );
  }

  // Sort (card view only; table view sorts in renderTableView)
  if (currentView === 'card') {
    repos.sort((a, b) => {
      const metaOrder = orgMetaRepoLast(a, b);
      if (metaOrder) return metaOrder;
      if (currentSort === 'name') return a.name.localeCompare(b.name);
      if (currentSort === 'updated_at' || currentSort === 'created_at')
        return new Date(b[currentSort]) - new Date(a[currentSort]);
      if (currentSort === 'maturity') return (b._maturityScore || 0) - (a._maturityScore || 0);
      if (currentSort === 'latest_pr') {
        const ta = (a.latest_pr && a.latest_pr.updated_at) ? new Date(a.latest_pr.updated_at) : null;
        const tb = (b.latest_pr && b.latest_pr.updated_at) ? new Date(b.latest_pr.updated_at) : null;
        if (!ta && !tb) return 0;
        if (!ta) return 1;
        if (!tb) return -1;
        return tb - ta;
      }
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

  if (!grid || !table || !empty) return;

  if (repos.length === 0) {
    grid.innerHTML  = '';
    table.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }

  empty.classList.add('hidden');

  if (currentDataSource === 'main') {
    grid.classList.add('hidden');
    table.classList.remove('hidden');
    const sidebar = document.getElementById('main-sidebar');
    const layout = document.getElementById('main-layout');
    const header = document.querySelector('header');
    if (sidebar) sidebar.classList.add('force-hidden');
    if (layout) layout.classList.add('table-view');
    if (header) header.classList.add('table-view-header');
    renderMainSummaryView(repos, table);
    return;
  }

  if (currentView === 'table') {
    grid.classList.add('hidden');
    table.classList.remove('hidden');
    const sidebar = document.getElementById('main-sidebar');
    const layout = document.getElementById('main-layout');
    const header = document.querySelector('header');
    if (sidebar) sidebar.classList.add('force-hidden');
    if (layout) layout.classList.add('table-view');
    if (header) header.classList.add('table-view-header');
    renderTableView(repos, table);
  } else {
    table.classList.add('hidden');
    grid.classList.remove('hidden');
    const sidebar = document.getElementById('main-sidebar');
    const layout = document.getElementById('main-layout');
    const header = document.querySelector('header');
    if (sidebar) sidebar.classList.remove('force-hidden');
    if (layout) layout.classList.remove('table-view');
    if (header) header.classList.remove('table-view-header');
    
    // Use DocumentFragment for more efficient DOM insertion
    const fragment = document.createDocumentFragment();
    repos.forEach(repo => {
      const temp = document.createElement('div');
      temp.innerHTML = repoCardHTML(repo);
      fragment.appendChild(temp.firstElementChild);
    });
    grid.innerHTML = '';
    grid.appendChild(fragment);

    // Attach error handlers for screenshot images to show placeholder on load failure
    grid.querySelectorAll('img[data-screenshot-placeholder]').forEach(img => {
      img.addEventListener('error', function() {
        const link = this.closest('.card-screenshot-link');
        if (!link) return;
        const placeholder = document.createElement('div');
        placeholder.className = 'w-full h-full flex items-center justify-center text-gray-300 dark:text-gray-600';
        const icon = document.createElement('i');
        icon.className = 'fa-solid fa-image text-2xl';
        icon.setAttribute('aria-hidden', 'true');
        placeholder.appendChild(icon);
        link.replaceChildren(placeholder);
      });
    });
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
  const contributors = (r.contributors || []).filter(c => c.avatar_url).slice(0, 10);
  const avatarStack = contributors.length
    ? `<div class="avatar-stack" title="Top contributors: ${contributors.map(c => escapeHtml(c.login)).join(', ')}">
        ${contributors.map(c => `<a href="${escapeHtml(c.html_url || `https://github.com/${c.login}`)}" target="_blank" rel="noopener noreferrer"><img src="${escapeHtml(c.avatar_url)}&amp;s=44" alt="${escapeHtml(c.login)}" title="${escapeHtml(c.login)} (${c.contributions} commits)" loading="lazy" /></a>`).join('')}
      </div>`
    : '';

  // Activity sparkline
  const sparkline = sparklineSVG(r.weekly_commits);

  // Star history sparkline
  const starSparkline = sparklineSVG(r.star_history, 80, 20, 'text-yellow-400 opacity-80');

  // Maturity score badge (using pre-calculated values)
  const score = r._maturityScore || 0;
  const { label: matLabel, color: matColor, bg: matBg } = r._maturityMeta || maturityMeta(0);
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
  const links = repoLinks(r);

  return `
  <article class="repo-card${hasGsoc ? ' gsoc-card' : ''} bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden flex flex-col shadow-sm" aria-label="Repository: ${escapeHtml(r.name)}">

    ${r.homepage ? `
    <!-- Screenshot thumbnail -->
    <a href="${escapeHtml(r.homepage)}" target="_blank" rel="noopener noreferrer"
       class="card-screenshot-link block overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0"
       style="height:130px;" tabindex="-1" aria-hidden="true">
      <img
        src="./imgs/screenshots/${escapeHtml(r.name)}.png"
        alt="Screenshot of ${escapeHtml(r.name)} website"
        class="w-full h-full object-cover object-top hover:scale-105 transition-transform duration-300"
        loading="lazy"
        data-screenshot-placeholder="1"
      />
    </a>
    ` : ''}

    <div class="p-5 flex flex-col gap-3 flex-1">

    <!-- Header -->
    <div class="flex items-start gap-3">
      ${projectLogoHTML(r, 'h-11 w-11')}
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap mb-1">
          <a
            href="${escapeHtml(links.repo)}"
            target="_blank"
            rel="noopener noreferrer"
            class="font-semibold text-brand hover:underline underline-offset-2 truncate text-sm"
          >${escapeHtml(repoDisplayName(r))}</a>
          ${archiveBadge}${forkBadge}${privateBadge}
          ${maturityBadge}
          ${wranglerIcon}${pagesIcon}
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 leading-relaxed">
          ${escapeHtml(repoDescription(r)) || '<span class="italic">No description</span>'}
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
      ${hasValue(r.stargazers_count) ? statLink(links.stars, 'hover:text-yellow-500 transition-colors', 'Stars', `<i class="fa-solid fa-star mr-1 text-yellow-400" aria-hidden="true"></i>${formatNumber(r.stargazers_count)}`) : ''}
      ${hasValue(r.forks_count) ? statLink(links.forks, 'hover:text-green-600 transition-colors', 'Forks', `<i class="fa-solid fa-code-fork mr-1 text-green-500" aria-hidden="true"></i>${formatNumber(r.forks_count)}`) : ''}
      ${statLink(links.issues, 'hover:text-brand transition-colors', 'Open issues', `<i class="fa-solid fa-circle-dot mr-1 text-brand" aria-hidden="true"></i>${formatNumber(repoIssueCount(r))}`)}
      ${r.open_pr_count ? statLink(links.pulls, 'hover:text-teal-500 transition-colors', 'Open pull requests', `<i class="fa-solid fa-code-pull-request mr-1 text-teal-500" aria-hidden="true"></i>${formatNumber(r.open_pr_count)}`) : ''}
      ${r.agent_pr_count ? statLink(links.pulls, 'hover:text-purple-500 transition-colors', 'Open bot/agent pull requests', `<i class="fa-solid fa-robot mr-1 text-purple-500" aria-hidden="true"></i>${formatNumber(r.agent_pr_count)}`) : ''}
      ${r.size ? `<span title="Repository size"><i class="fa-solid fa-database mr-1 text-cyan-400" aria-hidden="true"></i>${formatSize(r.size)}</span>` : ''}
      ${r.file_count ? `<span title="Total files (recursive)"><i class="fa-solid fa-file mr-1 text-teal-400" aria-hidden="true"></i>${formatNumber(r.file_count)} files</span>` : ''}
      ${r.branch_count ? statLink(links.branches, 'hover:text-violet-500 transition-colors', 'Branches', `<i class="fa-solid fa-code-branch mr-1 text-violet-400" aria-hidden="true"></i>${formatNumber(r.branch_count)} branches`) : ''}
      ${r.total_commits ? statLink(links.commits, 'hover:text-blue-500 transition-colors', 'Total commits', `<i class="fa-solid fa-code-commit mr-1 text-blue-400" aria-hidden="true"></i>${formatNumber(r.total_commits)} commits`) : ''}
      ${hasValue(r.commits_365d) ? statLink(links.commits, 'hover:text-blue-500 transition-colors', 'Commits in the last 30 days / year (bots excluded)', `<i class="fa-solid fa-code-commit mr-1 text-blue-400" aria-hidden="true"></i>${formatNumber(r.commits_30d || 0)} / ${formatNumber(r.commits_365d)}${r.commits_truncated ? '+' : ''} commits (30d / 1y)`) : ''}
      ${r.contributor_count ? `<span title="Distinct commit authors in the last year"><i class="fa-solid fa-users mr-1 text-indigo-400" aria-hidden="true"></i>${formatNumber(r.contributor_count)} authors</span>` : ''}
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
        ${r.default_branch ? `<span title="Default branch"><i class="fa-solid fa-code-branch mr-1" aria-hidden="true"></i>${escapeHtml(r.default_branch)}</span>` : ''}
      </div>
      <span class="text-xs text-gray-400 dark:text-gray-500" title="Last updated: ${escapeHtml(r.updated_at)}">
        <i class="fa-solid fa-clock mr-1" aria-hidden="true"></i>${r.updated_at ? timeAgo(r.updated_at) : '—'}
      </span>
    </div>

    <!-- Action buttons -->
    <div class="flex gap-2 flex-wrap">
      <a
        href="${escapeHtml(links.repo)}"
        target="_blank"
        rel="noopener noreferrer"
        class="flex-1 text-center text-xs font-semibold px-3 py-1.5 bg-brand text-white rounded-md hover:bg-red-700 transition-colors"
      >
        <i class="fa-solid fa-code-branch mr-1.5" aria-hidden="true"></i>View Source
      </a>
      ${r.homepage ? (() => {
        let isGithubPages = false;
        try { const h = new URL(r.homepage).hostname; isGithubPages = h === 'github.io' || h.endsWith('.github.io'); } catch (e) { /* invalid URL */ }
        return `
        <a
          href="${escapeHtml(r.homepage)}"
          target="_blank"
          rel="noopener noreferrer"
          class="flex-1 text-center text-xs font-semibold px-3 py-1.5 border border-brand text-brand rounded-md hover:bg-brand hover:text-white transition-colors"
          title="${isGithubPages ? 'Hosted on GitHub Pages' : 'Custom domain'}"
        >
          <i class="${isGithubPages ? 'fa-brands fa-github' : 'fa-solid fa-globe'} mr-1.5" aria-hidden="true"></i>${isGithubPages ? 'GitHub Pages' : 'Live Site'}
        </a>
      `;
      })() : `
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
        href="${escapeHtml(links.newIssue)}"
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
    </div>
  </article>`;
}

/* ------------------------------------------------------------------ */
/*  RENDER MAIN SUMMARY                                                 */
/* ------------------------------------------------------------------ */
function renderMainSummaryView(repos, container) {
  const sorted = [...repos].sort((a, b) => orgMetaRepoLast(a, b) || a.name.localeCompare(b.name));

  const rows = sorted.map((r, i) => {
    const live = liveSiteMeta(r);
    const links = repoLinks(r);
    const rowBg = i % 2 === 0
      ? 'bg-white dark:bg-gray-900'
      : 'bg-gray-50/60 dark:bg-gray-800/60';
    const liveCell = live.url
      ? `<a href="${escapeHtml(live.url)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ring-1 max-w-[28rem] ${live.classes}" title="${escapeHtml(live.label)}: ${escapeHtml(live.url)}"><i class="${live.icon}" aria-hidden="true"></i><span class="truncate">${escapeHtml(live.url)}</span></a>`
      : `<span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${live.classes}"><i class="${live.icon}" aria-hidden="true"></i>${escapeHtml(live.label)}</span>`;
    const folder = repoFolder(r);

    return `<tr class="${rowBg} border-b border-gray-100 dark:border-gray-700 hover:bg-red-50/40 dark:hover:bg-red-900/10 transition-colors">
      <td class="px-3 py-2 font-medium">
        <div class="flex items-center gap-2">
          ${projectLogoHTML(r, 'h-9 w-9')}
          <div class="min-w-0">
            <a href="${escapeHtml(links.repo)}" target="_blank" rel="noopener noreferrer" class="text-brand hover:underline underline-offset-2 text-sm whitespace-nowrap">${escapeHtml(repoDisplayName(r))}</a>
            ${repoDescription(r) ? `<p class="text-xs text-gray-400 dark:text-gray-500 truncate max-w-sm mt-0.5">${escapeHtml(repoDescription(r))}</p>` : ''}
          </div>
        </div>
      </td>
      <td class="px-3 py-2">${liveCell}</td>
      <td class="px-3 py-2 whitespace-nowrap">
        ${folder
          ? `<a href="${escapeHtml(links.repo)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-gray-800 ring-1 ring-gray-200 dark:ring-gray-700" title="${escapeHtml(links.repo)}"><i class="fa-solid fa-code-branch" aria-hidden="true"></i>${escapeHtml(folder)}</a>`
          : `<span class="text-gray-300 dark:text-gray-600">-</span>`}
      </td>
    </tr>`;
  }).join('');

  container.innerHTML = `
    <table class="border-collapse text-sm w-max">
      <caption class="caption-top text-left px-3 pb-3 text-sm text-gray-600 dark:text-gray-300">
        Every project is a folder of <a href="${FORGE_WEB}" target="_blank" rel="noopener noreferrer" class="text-brand hover:underline">git.owaspblt.org/BLT</a>.
      </caption>
      <thead class="bg-gray-50 dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700">
        <tr>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Repository (${formatNumber(repos.length)})</th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Live Site URL</th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Source</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

/* ------------------------------------------------------------------ */
/*  RENDER TABLE VIEW                                                   */
/* ------------------------------------------------------------------ */
// `only` limits a column to some data sources; the forge has no stars, forks, languages,
// releases, branches or sizes per folder, so those columns are hidden there.
const NOT_FORGE = ['github'];
const TABLE_COLS = [
  { key: 'name',              label: 'Repository' },
  { key: 'topics',            label: 'Labels'     },
  { key: 'language',          label: 'Language',    only: NOT_FORGE },
  { key: 'stargazers_count',  label: 'Stars',       only: NOT_FORGE },
  { key: 'forks_count',       label: 'Forks',       only: NOT_FORGE },
  { key: 'open_issues_count', label: 'Issues'     },
  { key: 'open_pr_count',     label: 'PRs'        },
  { key: 'agent_pr_count',    label: 'Agent PRs',   only: NOT_FORGE },
  { key: 'total_commits',     label: 'Commits',     only: NOT_FORGE },
  { key: 'commits_30d',       label: 'Commits 30d', only: ['forge'] },
  { key: 'commits_90d',       label: 'Commits 90d', only: ['forge'] },
  { key: 'commits_365d',      label: 'Commits 1y',  only: ['forge'] },
  { key: 'contributor_count', label: 'Authors 1y',  only: ['forge'] },
  { key: 'branch_count',      label: 'Branches',    only: NOT_FORGE },
  { key: 'size',              label: 'Size',        only: NOT_FORGE },
  { key: 'readme_chars',      label: 'README Size' },
  { key: 'maturity',          label: 'Maturity',    only: NOT_FORGE },
  { key: 'latest_release',    label: 'Release',     only: NOT_FORGE },
  { key: 'latest_commit',     label: 'Last Commit' },
  { key: 'latest_pr',         label: 'Last PR'    },
  { key: 'updated_at',        label: 'Updated'    },
  { key: 'latest_issue',      label: 'Latest Issue' },
  { key: 'infra',             label: 'Infra'        },
];

function visibleTableCols() {
  return TABLE_COLS.filter(col => !col.only || col.only.includes(currentDataSource));
}

function byDate(get) {
  return (a, b) => {
    const ta = get(a) ? new Date(get(a)) : null;
    const tb = get(b) ? new Date(get(b)) : null;
    if (!ta && !tb) return 0;
    if (!ta) return -1;
    if (!tb) return 1;
    return ta - tb;
  };
}

const EMPTY_CELL = `<span class="text-gray-300 dark:text-gray-600">—</span>`;

function renderTableView(repos, container) {
  const cols = visibleTableCols();
  const sortCol = cols.some(c => c.key === tableSortCol) ? tableSortCol : 'updated_at';
  const sorted = [...repos].sort((a, b) => {
    const metaOrder = orgMetaRepoLast(a, b);
    if (metaOrder) return metaOrder;
    let v;
    if (sortCol === 'name')       v = a.name.localeCompare(b.name);
    else if (sortCol === 'maturity') v = (a._maturityScore || 0) - (b._maturityScore || 0);
    else if (sortCol === 'updated_at' || sortCol === 'created_at' || sortCol === 'pushed_at') {
      v = byDate(r => r[sortCol])(a, b);
    }
    else if (sortCol === 'open_issues_count') v = repoIssueCount(a) - repoIssueCount(b);
    else if (sortCol === 'topics') v = (a.topics || []).length - (b.topics || []).length;
    else if (sortCol === 'latest_release') v = byDate(r => r.latest_release && r.latest_release.published_at)(a, b);
    else if (sortCol === 'latest_commit') v = byDate(r => r.latest_commit && r.latest_commit.date)(a, b);
    else if (sortCol === 'latest_pr') v = byDate(r => r.latest_pr && r.latest_pr.updated_at)(a, b);
    else if (sortCol === 'latest_issue') {
      v = (a.latest_issue ? a.latest_issue.number : 0) - (b.latest_issue ? b.latest_issue.number : 0);
    }
    else v = (a[sortCol] || 0) - (b[sortCol] || 0);
    return tableSortDir === 'asc' ? v : -v;
  });

  const sum = key => repos.reduce((s, r) => s + (r[key] || 0), 0);
  const colTotals = {
    name:               repos.length,
    stargazers_count:   sum('stargazers_count'),
    forks_count:        sum('forks_count'),
    open_issues_count:  repos.reduce((s, r) => s + repoIssueCount(r), 0),
    open_pr_count:      sum('open_pr_count'),
    agent_pr_count:     sum('agent_pr_count'),
    total_commits:      sum('total_commits'),
    commits_30d:        sum('commits_30d'),
    commits_90d:        sum('commits_90d'),
    commits_365d:       sum('commits_365d'),
    branch_count:       sum('branch_count'),
    size:               sum('size'),
    readme_chars:       sum('readme_chars'),
    language:           new Set(repos.map(r => r.language).filter(Boolean)).size,
    topics:             new Set(repos.flatMap(r => r.topics || [])).size,
  };

  const headerCells = cols.map(col => {
    const isActive = sortCol === col.key;
    const arrow = isActive ? (tableSortDir === 'asc' ? ' ▲' : ' ▼') : '';
    const activeCls = isActive ? ' text-brand dark:text-red-400 font-bold' : '';
    const total = colTotals[col.key];
    const totalStr = total !== undefined ? ` (${formatNumber(total)})` : '';
    return `<th data-col="${col.key}" class="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap transition-colors${activeCls}" title="Sort by ${escapeHtml(col.label)}">${escapeHtml(col.label)}${totalStr}<span class="ml-1">${arrow}</span></th>`;
  }).join('');

  const num = 'px-3 py-2 text-right whitespace-nowrap text-sm tabular-nums';
  const rows = sorted.map((r, i) => {
    const links = repoLinks(r);
    const langColor = LANG_COLORS[r.language] || '#8b949e';
    const score = r._maturityScore || 0;
    const { label: matLabel, color: matColor, bg: matBg } = r._maturityMeta || maturityMeta(0);
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
    const live = liveSiteMeta(r);
    const topics = r.topics || [];
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
    const count = (key, title) => `<td class="${num}">${r[key]
      ? statLink(links.commits, 'hover:text-blue-500 transition-colors', title, `<i class="fa-solid fa-code-commit text-blue-400 mr-1" aria-hidden="true"></i>${formatNumber(r[key])}${key === 'commits_365d' && r.commits_truncated ? '+' : ''}`)
      : EMPTY_CELL}</td>`;

    const cells = {
      name: `<td class="px-3 py-2 font-medium">
        <div class="flex items-center gap-2">
          ${projectLogoHTML(r, 'h-9 w-9')}
          <div class="min-w-0">
            <div class="flex items-center gap-1 flex-wrap">
              <a href="${escapeHtml(links.repo)}" target="_blank" rel="noopener noreferrer" class="text-brand hover:underline underline-offset-2 text-sm whitespace-nowrap">${escapeHtml(repoDisplayName(r))}</a>${archiveBadge}${forkBadge}${gsocBadge}
            </div>
            ${repoDescription(r) ? `<p class="text-xs text-gray-400 dark:text-gray-500 truncate max-w-xs mt-0.5">${escapeHtml(repoDescription(r))}</p>` : ''}
          </div>
        </div>
      </td>`,
      topics: `<td class="px-3 py-2 text-center whitespace-nowrap text-sm tabular-nums">
        ${topics.length > 0 ? `<span class="inline-block bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full">${topics.length}</span>` : EMPTY_CELL}
      </td>`,
      language: `<td class="px-3 py-2 whitespace-nowrap text-sm">
        ${r.language
          ? `<span class="lang-dot" style="background:${langColor}"></span><span class="text-gray-600 dark:text-gray-300">${escapeHtml(r.language)}</span>`
          : EMPTY_CELL}
      </td>`,
      stargazers_count: `<td class="${num}">${statLink(links.stars, 'hover:text-yellow-500 transition-colors', 'Stars', `<i class="fa-solid fa-star text-yellow-400 mr-1" aria-hidden="true"></i>${formatNumber(r.stargazers_count || 0)}`)}</td>`,
      forks_count: `<td class="${num}">${statLink(links.forks, 'hover:text-green-600 transition-colors', 'Forks', `<i class="fa-solid fa-code-fork text-green-500 mr-1" aria-hidden="true"></i>${formatNumber(r.forks_count || 0)}`)}</td>`,
      open_issues_count: `<td class="${num}">${statLink(links.issues, 'hover:text-brand transition-colors', 'Open issues', `<i class="fa-solid fa-circle-dot text-brand mr-1" aria-hidden="true"></i>${formatNumber(repoIssueCount(r))}`)}</td>`,
      open_pr_count: `<td class="${num}">${r.open_pr_count
        ? statLink(links.pulls, 'hover:text-teal-500 transition-colors', 'Open pull requests', `<i class="fa-solid fa-code-pull-request text-teal-500 mr-1" aria-hidden="true"></i>${formatNumber(r.open_pr_count)}`)
        : EMPTY_CELL}</td>`,
      agent_pr_count: `<td class="${num}">${r.agent_pr_count
        ? statLink(links.pulls, 'hover:text-purple-500 transition-colors', 'Open agent pull requests', `<i class="fa-solid fa-robot text-purple-500 mr-1" aria-hidden="true"></i>${formatNumber(r.agent_pr_count)}`)
        : EMPTY_CELL}</td>`,
      total_commits: count('total_commits', 'Total commits'),
      commits_30d: count('commits_30d', 'Commits in the last 30 days (bots excluded)'),
      commits_90d: count('commits_90d', 'Commits in the last 90 days (bots excluded)'),
      commits_365d: count('commits_365d', r.commits_truncated ? 'Commits in the last year (at least; history page cap reached)' : 'Commits in the last year (bots excluded)'),
      contributor_count: `<td class="${num}" title="${escapeHtml((r.contributors || []).map(c => c.login).join(', '))}">${r.contributor_count
        ? `<i class="fa-solid fa-users text-indigo-400 mr-1" aria-hidden="true"></i>${formatNumber(r.contributor_count)}`
        : EMPTY_CELL}</td>`,
      branch_count: `<td class="${num}">${r.branch_count
        ? statLink(links.branches, 'hover:text-violet-500 transition-colors', 'Branches', `<i class="fa-solid fa-code-branch text-violet-400 mr-1" aria-hidden="true"></i>${formatNumber(r.branch_count)}`)
        : EMPTY_CELL}</td>`,
      size: `<td class="${num}"><i class="fa-solid fa-database text-cyan-400 mr-1" aria-hidden="true"></i>${formatSize(r.size)}</td>`,
      readme_chars: `<td class="${num}">${r.readme_chars ? `<i class="fa-solid fa-file-lines text-pink-400 mr-1" aria-hidden="true"></i>${formatNumber(r.readme_chars)}` : EMPTY_CELL}</td>`,
      maturity: `<td class="px-3 py-2 whitespace-nowrap">
        <span class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${matBg} ${matColor}" title="Maturity score: ${score}/100">${matLabel} ${score}</span>
      </td>`,
      latest_release: `<td class="px-3 py-2 whitespace-nowrap text-xs">
        ${r.latest_release
          ? `<a href="${escapeHtml(r.latest_release.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-green-600 transition-colors text-gray-600 dark:text-gray-300" title="Latest release${r.latest_release.published_at ? ': ' + r.latest_release.published_at : ''}"><i class="fa-solid fa-tag text-green-500 mr-1" aria-hidden="true"></i>${escapeHtml(r.latest_release.tag_name)}</a>`
          : EMPTY_CELL}
      </td>`,
      latest_commit: `<td class="px-3 py-2 text-xs max-w-[16rem]">
        ${r.latest_commit
          ? `<a href="${escapeHtml(r.latest_commit.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors text-gray-600 dark:text-gray-300 truncate block" title="${escapeHtml(r.latest_commit.message)}${r.latest_commit.author ? ' by ' + escapeHtml(r.latest_commit.author) : ''}"><i class="fa-solid fa-code-commit text-blue-400 mr-1" aria-hidden="true"></i>${r.latest_commit.author_avatar ? `<img src="${escapeHtml(r.latest_commit.author_avatar)}&amp;s=20" alt="${escapeHtml(r.latest_commit.author)}" title="${escapeHtml(r.latest_commit.author)}" class="inline-block w-4 h-4 rounded-full mr-1 align-middle" loading="lazy" />` : ''}${escapeHtml(r.latest_commit.message)}${r.latest_commit.author ? `<span class="ml-1 text-gray-400 dark:text-gray-500">by ${escapeHtml(r.latest_commit.author)}</span>` : ''}</a>`
          : EMPTY_CELL}
      </td>`,
      latest_pr: `<td class="px-3 py-2 text-xs max-w-[16rem]">
        ${r.latest_pr ? (() => {
          const prState = r.latest_pr.state;
          const prIcon = prState === 'merged'
            ? `<i class="fa-solid fa-code-merge text-purple-500 mr-1" aria-hidden="true" title="Merged"></i>`
            : prState === 'open'
              ? `<i class="fa-solid fa-code-pull-request text-green-500 mr-1" aria-hidden="true" title="Open"></i>`
              : `<i class="fa-solid fa-circle-xmark text-red-500 mr-1" aria-hidden="true" title="Closed"></i>`;
          return `<a href="${escapeHtml(r.latest_pr.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-blue-500 hover:underline transition-colors text-gray-600 dark:text-gray-300 truncate block" title="#${r.latest_pr.number}: ${escapeHtml(r.latest_pr.title)}${r.latest_pr.author ? ' by ' + escapeHtml(r.latest_pr.author) : ''} [${prState}]">${prIcon}${r.latest_pr.author_avatar ? `<img src="${escapeHtml(r.latest_pr.author_avatar)}&amp;s=20" alt="${escapeHtml(r.latest_pr.author)}" title="${escapeHtml(r.latest_pr.author)}" class="inline-block w-4 h-4 rounded-full mr-1 align-middle" loading="lazy" />` : ''}#${r.latest_pr.number}: ${escapeHtml(r.latest_pr.title)}${r.latest_pr.author ? `<span class="ml-1 text-gray-400 dark:text-gray-500">by ${escapeHtml(r.latest_pr.author)}</span>` : ''}</a>`;
        })() : EMPTY_CELL}
      </td>`,
      updated_at: `<td class="px-3 py-2 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400" title="Last updated: ${escapeHtml(r.updated_at)}">${r.updated_at ? timeAgo(r.updated_at) : '—'}</td>`,
      latest_issue: `<td class="px-3 py-2 text-xs max-w-[14rem]">
        ${r.latest_issue
          ? `<a href="${escapeHtml(r.latest_issue.html_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-brand hover:underline transition-colors text-gray-600 dark:text-gray-300 truncate block" title="#${r.latest_issue.number}: ${escapeHtml(r.latest_issue.title)}"><i class="fa-solid fa-circle-dot text-brand mr-1" aria-hidden="true"></i>#${r.latest_issue.number}: ${escapeHtml(r.latest_issue.title)}</a>`
          : EMPTY_CELL}
      </td>`,
      infra: `<td class="px-3 py-2 whitespace-nowrap text-center">
        <div class="flex items-center justify-center gap-1.5">
          ${wranglerIcon}${pagesIcon}${(!wranglerIcon && !pagesIcon) ? EMPTY_CELL : ''}
        </div>
      </td>`,
    };

    return `<tr class="${rowBg} border-b border-gray-100 dark:border-gray-700 hover:bg-red-50/40 dark:hover:bg-red-900/10 transition-colors">
      ${cols.map(col => cells[col.key]).join('')}
      <td class="px-3 py-2 whitespace-nowrap">
        <div class="flex gap-1.5">
          <a href="${escapeHtml(links.repo)}" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 bg-brand text-white rounded hover:bg-red-700 transition-colors" title="View source on git.owaspblt.org"><i class="fa-solid fa-code-branch" aria-hidden="true"></i></a>
          ${live.url ? `<a href="${escapeHtml(live.url)}" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 border border-brand text-brand rounded hover:bg-brand hover:text-white transition-colors" title="${escapeHtml(live.label)}"><i class="${live.icon}" aria-hidden="true"></i></a>` : `<span role="button" aria-disabled="true" class="text-xs px-2 py-1 border border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-600 rounded cursor-not-allowed" title="No live site"><i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i></span>`}
          ${projectUrl ? `<a href="${escapeHtml(projectUrl)}" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 border border-brand text-brand rounded hover:bg-brand hover:text-white transition-colors" title="Project Board"><i class="fa-solid fa-rocket" aria-hidden="true"></i></a>` : `<span role="button" aria-disabled="true" class="text-xs px-2 py-1 border border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-600 rounded cursor-not-allowed" title="No project board"><i class="fa-solid fa-rocket" aria-hidden="true"></i></span>`}
          <a href="${escapeHtml(links.newIssue)}" target="_blank" rel="noopener noreferrer" class="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 rounded hover:border-brand hover:text-brand transition-colors" title="New Issue"><i class="fa-solid fa-circle-plus" aria-hidden="true"></i></a>
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
      if (sortCol === col) {
        tableSortDir = tableSortDir === 'desc' ? 'asc' : 'desc';
      } else {
        tableSortDir = 'desc';
      }
      tableSortCol = col;
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
  const grid = document.getElementById('repo-grid');
  const table = document.getElementById('repo-table');
  const errorState = document.getElementById('error-state');
  const errorMsg = document.getElementById('error-msg');
  if (grid) grid.innerHTML = '';
  if (table) table.innerHTML = '';
  if (errorState) errorState.classList.remove('hidden');
  if (errorMsg) errorMsg.textContent = msg;
}

/* ------------------------------------------------------------------ */
/*  EVENT LISTENERS                                                     */
/* ------------------------------------------------------------------ */

// View toggle
function updateViewButtons() {
  const tableBtn = document.getElementById('view-table-btn');
  const cardBtn = document.getElementById('view-card-btn');
  if (tableBtn) tableBtn.classList.toggle('view-btn-active', currentView === 'table');
  if (cardBtn) cardBtn.classList.toggle('view-btn-active', currentView === 'card');
}

/** Safely add an event listener to an element selected by ID. */
function on(id, event, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener(event, handler);
}

on('view-table-btn', 'click', () => {
  currentView = 'table';
  localStorage.setItem('blt-view', 'table');
  updateViewButtons();
  applyFilters();
});

on('view-card-btn', 'click', () => {
  currentView = 'card';
  localStorage.setItem('blt-view', 'card');
  updateViewButtons();
  applyFilters();
});

document.querySelectorAll('.data-source-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const source = tab.dataset.source;
    if (!DATA_SOURCES[source]) return;
    if (source === currentDataSource) {
      resetDataSourceFilters(source);
      updateDataSourceTabs();
      applyFilters();
      return;
    }
    currentDataSource = source;
    resetDataSourceFilters(source);
    allRepos = [];
    filtered = [];
    updateDataSourceTabs();
    loadRepos();
  });
});

// Initialize button states immediately
updateViewButtons();
updateDataSourceTabs();
updateVersionLabel();

// Initialize sort UI to reflect stored preference
const sortSelect = document.getElementById('sort-select');
const sortSelectMobile = document.getElementById('sort-select-mobile');
if (sortSelect) sortSelect.value = currentSort;
if (sortSelectMobile) sortSelectMobile.value = currentSort;
document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.sort === currentSort));

// Search (using the new robust debounce utility)
const debouncedApplyFilters = debounce(applyFilters, 300);
on('search-input', 'input', e => {
  currentSearch = e.target.value.trim();
  debouncedApplyFilters();
});

// Sort (header select)
on('sort-select', 'change', e => {
  currentSort = e.target.value;
  localStorage.setItem('blt-sort', currentSort);
  const mob = document.getElementById('sort-select-mobile');
  if (mob) mob.value = currentSort;
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.sort === currentSort));
  applyFilters();
});

// Sort (mobile select)
on('sort-select-mobile', 'change', e => {
  currentSort = e.target.value;
  localStorage.setItem('blt-sort', currentSort);
  const desk = document.getElementById('sort-select');
  if (desk) desk.value = currentSort;
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.sort === currentSort));
  applyFilters();
});

// Filter (mobile select)
on('filter-select-mobile', 'change', e => {
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
    const mob = document.getElementById('filter-select-mobile');
    if (mob) mob.value = currentFilter;
    applyFilters();
  });
});

// Sort buttons (sidebar)
document.querySelectorAll('.sort-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentSort = btn.dataset.sort;
    localStorage.setItem('blt-sort', currentSort);
    const desk = document.getElementById('sort-select');
    const mob = document.getElementById('sort-select-mobile');
    if (desk) desk.value = currentSort;
    if (mob) mob.value = currentSort;
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('nav-active'));
    btn.classList.add('nav-active');
    applyFilters();
  });
});

// Retry button
on('retry-btn', 'click', () => {
  const errEl = document.getElementById('error-state');
  const gridEl = document.getElementById('repo-grid');
  if (errEl) errEl.classList.add('hidden');
  if (gridEl) gridEl.innerHTML = `
    <div class="skeleton h-48 rounded-xl"></div>
    <div class="skeleton h-48 rounded-xl"></div>
    <div class="skeleton h-48 rounded-xl"></div>
  `;
  loadRepos();
});

// Clear filters
on('clear-btn', 'click', () => {
  currentSearch = '';
  currentFilter = 'all';
  currentLang = '';
  currentLabel = '';
  const si = document.getElementById('search-input');
  const lsi = document.getElementById('label-search-input');
  const ss = document.getElementById('sort-select');
  const fm = document.getElementById('filter-select-mobile');
  const ld = document.getElementById('label-dropdown');
  if (si) si.value = '';
  if (lsi) lsi.value = '';
  if (ss) ss.value = currentSort;
  if (fm) fm.value = 'all';
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.filter === 'all'));
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('nav-active', b.dataset.lang === ''));
  document.querySelectorAll('.label-option').forEach(b => b.classList.remove('nav-active', 'text-brand'));
  if (ld) ld.classList.add('hidden');
  applyFilters();
});

// Clear label filter
on('clear-label-btn', 'click', () => {
  currentLabel = '';
  const lsi = document.getElementById('label-search-input');
  const ld = document.getElementById('label-dropdown');
  if (lsi) lsi.value = '';
  document.querySelectorAll('.label-option').forEach(b => b.classList.remove('nav-active', 'text-brand'));
  if (ld) ld.classList.add('hidden');
  applyFilters();
});

/* ------------------------------------------------------------------ */
/*  RESIZING LOGIC                                                      */
/* ------------------------------------------------------------------ */
let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    const isMobile = window.innerWidth < 640;
    const targetView = isMobile ? 'card' : 'table';

    // Only auto-switch if the user hasn't explicitly set a preference in localStorage
    // OR if we are moving into mobile and still in table view.
    const savedView = localStorage.getItem('blt-view');
    
    if (!savedView) {
      if (currentView !== targetView) {
        currentView = targetView;
        updateViewButtons();
        applyFilters();
      }
    } else if (isMobile && currentView === 'table') {
      // Force card on mobile even if they chose table on desktop (as per user request)
      currentView = 'card';
      updateViewButtons();
      applyFilters();
    } else if (!isMobile && savedView === 'table' && currentView === 'card') {
      // Restore table on desktop if that was their preference
      currentView = 'table';
      updateViewButtons();
      applyFilters();
    }
  }, 150);
});

loadRepos();
