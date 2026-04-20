/**
 * OWASP BLT – Leaders Page JavaScript
 * Handles elections, nominations, voting via GitHub Issues (zero-backend).
 * License: AGPLv3
 */

/* ── State ── */
let leadersData = null;
let currentUser = null; // { login, avatar_url, html_url } from localStorage
let activeTab = 'elections';

/* ── Bootstrap ── */
document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  initMobileMenu();
  initTabs();
  restoreSession();   // must be before loadLeadersData so currentUser is set on first render
  loadLeadersData();
  document.getElementById('footer-year').textContent = new Date().getFullYear();
});

/* ── Dark Mode ── */
function initDarkMode() {
  const btn = document.getElementById('dark-toggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('blt-theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
  });
}

/* ── Mobile Menu ── */
function initMobileMenu() {
  const toggle = document.getElementById('mobile-menu-toggle');
  const menu = document.getElementById('mobile-menu');
  if (!toggle || !menu) return;
  toggle.addEventListener('click', () => {
    const open = menu.classList.toggle('hidden');
    toggle.setAttribute('aria-expanded', String(!open));
  });
  menu.querySelectorAll('a').forEach(l => l.addEventListener('click', () => {
    menu.classList.add('hidden');
    toggle.setAttribute('aria-expanded', 'false');
  }));
}

/* ── Tabs ── */
function initTabs() {
  document.querySelectorAll('[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      activeTab = btn.dataset.tab;
      document.querySelectorAll('[data-tab]').forEach(b => {
        const active = b.dataset.tab === activeTab;
        b.classList.toggle('border-primary', active);
        b.classList.toggle('text-primary', active);
        b.classList.toggle('border-transparent', !active);
        b.classList.toggle('text-gray-500', !active);
      });
      document.querySelectorAll('[data-panel]').forEach(p => {
        p.classList.toggle('hidden', p.dataset.panel !== activeTab);
      });
    });
  });
}

/* ── Load Data ── */
async function loadLeadersData() {
  try {
    const res = await fetch('data/leaders.json');
    if (!res.ok) throw new Error('fetch failed');
    leadersData = await res.json();
  } catch {
    leadersData = { projects: [], elections: [], nominations: [], past_winners: [] };
  }
  // Merge org repos from GitHub API (non-GSoC) into projects list
  await mergeOrgRepos();
  renderAll();
}

/**
 * Fetches all public repos from the OWASP-BLT org via GitHub API.
 * Filters out repos tagged with the "gsoc" topic.
 * Merges with manually pinned projects in leaders.json (manual entries take precedence).
 */
async function mergeOrgRepos() {
  try {
    const res = await fetch(
      `https://api.github.com/orgs/${BLT_CONFIG.REPO_OWNER}/repos?per_page=100&sort=updated&type=public`,
      { headers: { Accept: 'application/vnd.github+json' } }
    );
    if (!res.ok) return; // silently skip if rate-limited
    const repos = await res.json();
    if (!Array.isArray(repos)) return;

    const existing = new Set((leadersData.projects || []).map(p => p.repo_url));

    const fetched = repos
      .filter(r => !r.archived && !(r.topics || []).includes('gsoc'))
      .map(r => ({
        id: r.name.toLowerCase(),
        name: r.name,
        description: r.description || '',
        repo_url: r.html_url,
        maintainer: BLT_CONFIG.REPO_OWNER,
        active: !r.archived,
        gsoc: (r.topics || []).includes('gsoc'),
        _fromApi: true  // flag so we can style these differently
      }))
      .filter(r => !existing.has(r.repo_url)); // don't duplicate manually pinned ones

    leadersData.projects = [...(leadersData.projects || []), ...fetched];
  } catch {
    // GitHub API unavailable — use only leaders.json projects
  }
}

/**
 * Derives election status from timestamps at runtime.
 * Donnie only needs to set dates — transitions happen automatically.
 *
 * Rules:
 *   before nomination_start          → draft
 *   nomination_start → nomination_end → nominations_open
 *   voting_start → voting_end         → voting_open
 *   after voting_end                  → closed
 *   status === 'finalized' is sticky  → finalized (admin-set, never auto-overridden)
 */
function deriveStatus(el) {
  if (el.status === 'finalized') return 'finalized'; // admin locks this manually
  const now = Date.now();
  const nomStart  = el.nomination_start ? new Date(el.nomination_start).getTime() : null;
  const nomEnd    = el.nomination_end   ? new Date(el.nomination_end).getTime()   : null;
  const voteStart = el.voting_start     ? new Date(el.voting_start).getTime()     : null;
  const voteEnd   = el.voting_end       ? new Date(el.voting_end).getTime()       : null;

  if (voteEnd   && now > voteEnd)   return 'closed';
  if (voteStart && now >= voteStart) return 'voting_open';
  if (nomEnd    && now > nomEnd)    return 'closed'; // between nom end and vote start
  if (nomStart  && now >= nomStart) return 'nominations_open';
  return 'draft';
}

function renderAll() {
  // Auto-derive status for every election from its timestamps
  (leadersData.elections || []).forEach(el => { el.status = deriveStatus(el); });
  renderElections();
  renderProjects();
  renderPastWinners();
}

/* ── Session (GitHub login stored in localStorage) ── */
function restoreSession() {
  try {
    const saved = localStorage.getItem('blt-gh-user');
    if (saved) {
      currentUser = JSON.parse(saved);
      updateAuthUI();
    }
  } catch { currentUser = null; }
}

function updateAuthUI() {
  const loginBtn = document.getElementById('gh-login-btn');
  const userChip = document.getElementById('gh-user-chip');
  const userAvatar = document.getElementById('gh-user-avatar');
  const userLogin = document.getElementById('gh-user-login');
  const logoutBtn = document.getElementById('gh-logout-btn');
  if (!loginBtn || !userChip) return;
  if (currentUser) {
    loginBtn.classList.add('hidden');
    userChip.classList.remove('hidden');
    userChip.classList.add('flex');  // must be flex, not block
    if (userAvatar) userAvatar.src = currentUser.avatar_url || `https://github.com/${currentUser.login}.png`;
    if (userLogin) userLogin.textContent = currentUser.login;
  } else {
    loginBtn.classList.remove('hidden');
    userChip.classList.add('hidden');
    userChip.classList.remove('flex');
  }
  if (logoutBtn) {
    logoutBtn.onclick = logout; // use onclick to avoid stacking listeners
  }
}

function logout() {
  currentUser = null;
  localStorage.removeItem('blt-gh-user');
  updateAuthUI();
  renderAll();
}

/* ── GitHub OAuth (Device Flow redirect pattern) ── */
// Since this is a static site, we use GitHub OAuth App redirect.
// The user is sent to GitHub, then back to this page with ?gh_login=<login>&gh_avatar=<url>
// In production, a lightweight serverless function (Vercel/Netlify) handles the token exchange.
// For the static demo, we simulate login via a prompt (contributors enter their GitHub username).
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  if (params.get('gh_login')) {
    currentUser = {
      login: params.get('gh_login'),
      avatar_url: params.get('gh_avatar') || `https://github.com/${params.get('gh_login')}.png`,
      html_url: `https://github.com/${params.get('gh_login')}`
    };
    localStorage.setItem('blt-gh-user', JSON.stringify(currentUser));
    window.history.replaceState({}, '', window.location.pathname);
    updateAuthUI();
    renderAll();
  }

  const loginBtn = document.getElementById('gh-login-btn');
  const loginBtnMobile = document.getElementById('gh-login-btn-mobile');

  function doLogin() {
    const login = prompt('Enter your GitHub username to simulate login (replace with real OAuth):');
    if (!login || !login.trim()) return;
    currentUser = {
      login: login.trim(),
      avatar_url: `https://github.com/${login.trim()}.png`,
      html_url: `https://github.com/${login.trim()}`
    };
    localStorage.setItem('blt-gh-user', JSON.stringify(currentUser));
    updateAuthUI();
    renderAll();
  }

  if (loginBtn) loginBtn.addEventListener('click', doLogin);
  if (loginBtnMobile) loginBtnMobile.addEventListener('click', doLogin);
});

/* ── Elections Panel ── */
function renderElections() {
  const container = document.getElementById('elections-list');
  if (!container || !leadersData) return;
  const elections = leadersData.elections || [];

  // Render "Request Election" button for logged-in users
  const addBtn = document.getElementById('add-election-btn');
  if (addBtn) {
    addBtn.classList.toggle('hidden', !currentUser);
    addBtn.onclick = openRequestElectionForm;
  }

  if (!elections.length) {
    container.innerHTML = emptyState('fa-circle-dot', 'No active elections right now. Check back soon.');
    return;
  }
  container.innerHTML = elections.map(el => electionCard(el)).join('');
  container.querySelectorAll('[data-open-election]').forEach(btn => {
    btn.addEventListener('click', () => openElectionModal(btn.dataset.openElection));
  });
}

function statusBadge(status) {
  const map = {
    draft:            ['bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300', 'Draft'],
    nominations_open: ['bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400', 'Nominations Open'],
    voting_open:      ['bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', 'Voting Open'],
    closed:           ['bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400', 'Closed'],
    finalized:        ['bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', 'Finalized'],
  };
  const [cls, label] = map[status] || map.draft;
  return `<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}">${label}</span>`;
}

function electionCard(el) {
  const project = (leadersData.projects || []).find(p => p.id === el.project_id) || {};
  const noms = (leadersData.nominations || []).filter(n => n.election_id === el.id && n.status === 'accepted');
  const roles = (el.roles || []).join(' + ');
  const nomEnd = el.nomination_end ? new Date(el.nomination_end).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
  const voteEnd = el.voting_end ? new Date(el.voting_end).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
  return `<article class="surface-card rounded-2xl p-6 flex flex-col gap-4">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">${escHtml(project.name || el.project_id)}</p>
        <h3 class="text-lg font-bold text-gray-900 dark:text-white">${escHtml(el.term)}</h3>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Roles: <span class="font-medium text-gray-700 dark:text-gray-300">${escHtml(roles)}</span></p>
      </div>
      ${statusBadge(el.status)}
    </div>
    <div class="grid grid-cols-2 gap-3 text-sm">
      <div class="rounded-xl bg-gray-50 dark:bg-gray-800 px-3 py-2">
        <p class="text-xs text-gray-400 mb-0.5">Nominations close</p>
        <p class="font-semibold text-gray-800 dark:text-gray-200">${nomEnd}</p>
      </div>
      <div class="rounded-xl bg-gray-50 dark:bg-gray-800 px-3 py-2">
        <p class="text-xs text-gray-400 mb-0.5">Voting closes</p>
        <p class="font-semibold text-gray-800 dark:text-gray-200">${voteEnd}</p>
      </div>
    </div>
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <p class="text-sm text-gray-500 dark:text-gray-400">${noms.length} nominee${noms.length !== 1 ? 's' : ''}</p>
      <button data-open-election="${escHtml(el.id)}"
        class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors">
        View Election
        <svg class="fa-icon" aria-hidden="true"><use href="#fa-arrow-right"></use></svg>
      </button>
    </div>
  </article>`;
}

/* ── Election Modal ── */
async function openElectionModal(electionId) {
  const el = (leadersData.elections || []).find(e => e.id === electionId);
  if (!el) return;
  const project = (leadersData.projects || []).find(p => p.id === el.project_id) || {};
  const modal = document.getElementById('election-modal');
  const body = document.getElementById('election-modal-body');
  if (!modal || !body) return;

  // Show modal immediately with a loading state
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  body.innerHTML = `<div class="py-12 text-center text-gray-400">
    <p class="text-sm">Loading nominees and vote counts…</p>
  </div>`;

  // Fetch live 👍 counts from GitHub reactions API
  const canVote = el.status === 'voting_open';
  if (canVote) await loadVoteCounts(electionId);

  const noms = (leadersData.nominations || []).filter(n => n.election_id === electionId && n.status === 'accepted');
  const canNominate = el.status === 'nominations_open';
  const roles = el.roles || [];

  const nomineesByRole = roles.map(role => {
    const roleNoms = noms.filter(n => n.role === role)
      .sort((a, b) => (b.votes || 0) - (a.votes || 0)); // sort by votes desc
    const maxVotes = roleNoms.reduce((m, n) => Math.max(m, n.votes || 0), 1);
    return `<div class="mb-6">
      <h4 class="text-base font-bold text-gray-800 dark:text-gray-200 mb-3 flex items-center gap-2">
        <svg class="fa-icon text-primary" aria-hidden="true"><use href="#fa-trophy"></use></svg>
        ${escHtml(role)}
      </h4>
      ${roleNoms.length
        ? roleNoms.map(n => nomineeCard(n, canVote, maxVotes)).join('')
        : `<p class="text-sm text-gray-400 italic">No nominees yet for this role.</p>`}
    </div>`;
  }).join('');

  const nominateBtn = canNominate
    ? `<button id="modal-nominate-btn" data-election="${escHtml(electionId)}"
        class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors">
        <svg class="fa-icon" aria-hidden="true"><use href="#fa-plus"></use></svg>
        Nominate / Self-Nominate
      </button>` : '';

  body.innerHTML = `
    <div class="flex items-start justify-between gap-3 mb-4 flex-wrap">
      <div>
        <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide">${escHtml(project.name || el.project_id)}</p>
        <h3 class="text-xl font-extrabold text-gray-900 dark:text-white mt-0.5">${escHtml(el.term)}</h3>
      </div>
      ${statusBadge(el.status)}
    </div>
    ${el.eligibility_note ? `<p class="text-sm text-gray-500 dark:text-gray-400 mb-4 p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
      <svg class="fa-icon mr-1 text-primary" aria-hidden="true"><use href="#fa-circle-info"></use></svg>
      ${escHtml(el.eligibility_note)}</p>` : ''}
    ${canVote ? `<p class="text-xs text-gray-400 mb-4 flex items-center gap-1.5">
      <svg class="fa-icon text-primary" aria-hidden="true"><use href="#fa-circle-info"></use></svg>
      Vote counts are live 👍 reactions on each nomination's GitHub Issue. Click "Vote on GitHub" to cast yours.
    </p>` : ''}
    <div id="modal-nominees">${nomineesByRole}</div>
    <div class="mt-4 flex gap-3 flex-wrap">${nominateBtn}</div>`;

  document.getElementById('modal-nominate-btn')?.addEventListener('click', () => {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    openNominationForm(electionId);
  });
}

function nomineeCard(nom, canVote, maxVotes) {
  const pct = Math.round(((nom.votes || 0) / Math.max(maxVotes, 1)) * 100);
  const selfTag = nom.self_nominated
    ? `<span class="ml-2 text-xs bg-active-bg text-primary dark:bg-red-950/30 dark:text-red-400 rounded-full px-2 py-0.5">self-nominated</span>`
    : '';

  let voteBtn = '';
  if (canVote && nom.issue_number) {
    voteBtn = `<button
      onclick="openVoteIssue(${nom.issue_number}, '${escHtml(nom.nominee_login)}', '${escHtml(nom.role)}')"
      class="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-primary px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary hover:text-white transition-colors">
      👍 Vote on GitHub
    </button>`;
  }

  const voteDisplay = nom.votes != null
    ? `<p class="text-lg font-extrabold text-primary dark:text-red-400">${nom.votes}</p><p class="text-xs text-gray-400">👍 votes</p>`
    : `<p class="text-xs text-gray-400 italic">votes loading…</p>`;

  const skills = (nom.skills || []).map(s =>
    `<span class="rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300">${escHtml(s)}</span>`
  ).join('');

  const issueLink = nom.issue_number
    ? `<a href="https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues/${nom.issue_number}"
         target="_blank" rel="noopener noreferrer"
         class="text-xs text-gray-400 hover:text-primary transition-colors mt-1 inline-flex items-center gap-1">
         <svg class="fa-icon" aria-hidden="true"><use href="#fa-github"></use></svg>#${nom.issue_number}
       </a>` : '';

  return `<div class="surface-card rounded-xl p-4 mb-3">
    <div class="flex items-center gap-3 mb-2">
      <img src="${escHtml(nom.nominee_avatar || `https://github.com/${nom.nominee_login}.png`)}"
           alt="${escHtml(nom.nominee_login)}" class="w-9 h-9 rounded-full border border-neutral-border dark:border-gray-700" loading="lazy"
           onerror="this.src='https://github.com/identicons/${escHtml(nom.nominee_login)}.png'" />
      <div class="min-w-0 flex-1">
        <a href="https://github.com/${escHtml(nom.nominee_login)}" target="_blank" rel="noopener noreferrer"
           class="font-bold text-gray-900 dark:text-white hover:text-primary transition-colors text-sm">
          ${escHtml(nom.nominee_login)}
        </a>${selfTag}
        <p class="text-xs text-gray-400">${escHtml(nom.contributions || '')}</p>
        ${issueLink}
      </div>
      <div class="ml-auto text-right flex-shrink-0">${voteDisplay}</div>
    </div>
    <p class="text-sm text-gray-600 dark:text-gray-300 mb-2 line-clamp-3">${escHtml(nom.statement || '')}</p>
    <div class="flex flex-wrap gap-1 mb-2">${skills}</div>
    <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mb-1">
      <div class="bg-primary h-1.5 rounded-full transition-all" style="width:${pct}%"></div>
    </div>
    ${voteBtn}
  </div>`;
}

/* ── Nomination Form ── */
function openNominationForm(electionId) {
  const el = (leadersData.elections || []).find(e => e.id === electionId);
  if (!el) return;
  const project = (leadersData.projects || []).find(p => p.id === el.project_id) || {};
  const formModal = document.getElementById('nomination-modal');
  const formBody = document.getElementById('nomination-modal-body');
  if (!formModal || !formBody) return;

  if (!currentUser) {
    alert('Please sign in with GitHub before nominating.');
    return;
  }

  const roleOptions = (el.roles || []).map(r => `<option value="${escHtml(r)}">${escHtml(r)}</option>`).join('');

  formBody.innerHTML = `
    <h3 class="text-xl font-extrabold text-gray-900 dark:text-white mb-1">Submit Nomination</h3>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">${escHtml(project.name || el.project_id)} — ${escHtml(el.term)}</p>
    <form id="nomination-form" class="space-y-4">
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="nom-role">Role</label>
        <select id="nom-role" class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
          ${roleOptions}
        </select>
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="nom-nominee">Nominee GitHub Username</label>
        <input id="nom-nominee" type="text" value="${escHtml(currentUser.login)}"
          class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="github-username" />
        <p class="text-xs text-gray-400 mt-1">Leave as your username to self-nominate.</p>
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="nom-statement">Statement / Manifesto</label>
        <textarea id="nom-statement" rows="4"
          class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          placeholder="Why should the community elect this person? What will they contribute as Lead/Co-Lead?"></textarea>
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="nom-skills">Skills (comma-separated)</label>
        <input id="nom-skills" type="text"
          class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="JavaScript, Security, Documentation" />
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="nom-contributions">Prior Contributions</label>
        <input id="nom-contributions" type="text"
          class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="e.g. 10 merged PRs, 5 issues resolved" />
      </div>
      <div class="flex gap-3 pt-2">
        <button type="submit"
          class="flex-1 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors">
          Submit Nomination
        </button>
        <button type="button" id="nom-cancel"
          class="rounded-xl border border-neutral-border dark:border-gray-600 px-4 py-2.5 text-sm font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          Cancel
        </button>
      </div>
    </form>`;

  formModal.classList.remove('hidden');
  formModal.classList.add('flex');

  document.getElementById('nom-cancel').addEventListener('click', () => {
    formModal.classList.add('hidden');
    formModal.classList.remove('flex');
  });

  document.getElementById('nomination-form').addEventListener('submit', e => {
    e.preventDefault();
    submitNomination(electionId, el, project);
  });
}

/* ── Submit Nomination (via GitHub Issue) ── */
function submitNomination(electionId, el, project) {
  const role = document.getElementById('nom-role').value.trim();
  const nominee = document.getElementById('nom-nominee').value.trim();
  const statement = document.getElementById('nom-statement').value.trim();
  const skills = document.getElementById('nom-skills').value.trim();
  const contributions = document.getElementById('nom-contributions').value.trim();

  if (!nominee || !statement) {
    alert('Please fill in the nominee username and statement.');
    return;
  }

  const selfNom = nominee.toLowerCase() === currentUser.login.toLowerCase();
  const title = `[NOMINATION] ${el.term} — ${role}: ${nominee}`;
  const body = [
    `## BLT Leadership Nomination`,
    ``,
    `**Election:** ${el.term} (${electionId})`,
    `**Project:** ${project.name || el.project_id}`,
    `**Role:** ${role}`,
    `**Nominee:** @${nominee}`,
    `**Nominator:** @${currentUser.login}`,
    `**Self-Nomination:** ${selfNom ? 'Yes' : 'No'}`,
    ``,
    `### Statement`,
    statement,
    ``,
    `### Skills`,
    skills || '_Not provided_',
    ``,
    `### Prior Contributions`,
    contributions || '_Not provided_',
    ``,
    `---`,
    `_Submitted via BLT Leaders page_`
  ].join('\n');

  const issueUrl = `https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues/new?`
    + `title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}&labels=nomination,leadership`;

  window.open(issueUrl, '_blank', 'noopener,noreferrer');

  document.getElementById('nomination-modal').classList.add('hidden');
  document.getElementById('nomination-modal').classList.remove('flex');

  showToast('Nomination opened as a GitHub Issue. Submit it to complete your nomination.');
}

/* ── Voting via GitHub Reactions ── */
// Each nomination has an issue_number. Votes = 👍 reactions on that issue.
// To vote: user clicks "Vote on GitHub" → taken to the issue to react with 👍.
// Vote counts are fetched live from the GitHub reactions API.

/**
 * Fetch 👍 reaction count for a single issue number.
 * Returns 0 on failure (rate limit, network, etc.)
 */
async function fetchThumbsUp(issueNumber) {
  try {
    const res = await fetch(
      `https://api.github.com/repos/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues/${issueNumber}/reactions?content=%2B1&per_page=1`,
      { headers: { Accept: 'application/vnd.github+json' } }
    );
    if (!res.ok) return 0;
    // The Link header tells us total pages; count from array length or use total from list
    const data = await res.json();
    // GitHub doesn't return total count directly — fetch without per_page limit
    const full = await fetch(
      `https://api.github.com/repos/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues/${issueNumber}/reactions?content=%2B1&per_page=100`,
      { headers: { Accept: 'application/vnd.github+json' } }
    );
    if (!full.ok) return data.length;
    const all = await full.json();
    return Array.isArray(all) ? all.length : 0;
  } catch {
    return 0;
  }
}

/**
 * Fetch vote counts for all nominations in an election and update in-memory data.
 * Returns a promise that resolves when all counts are loaded.
 */
async function loadVoteCounts(electionId) {
  const noms = (leadersData.nominations || []).filter(
    n => n.election_id === electionId && n.status === 'accepted' && n.issue_number
  );
  await Promise.all(noms.map(async n => {
    n.votes = await fetchThumbsUp(n.issue_number);
  }));
}

/**
 * "Vote" button just takes the user to the GitHub issue to 👍 it.
 * No backend needed — GitHub enforces one reaction per account.
 */
function openVoteIssue(issueNumber, nomineeLogin, role) {
  if (!currentUser) {
    showToast('Sign in with GitHub first, then 👍 the nomination issue to vote.');
    return;
  }
  const url = `https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues/${issueNumber}`;
  window.open(url, '_blank', 'noopener,noreferrer');
  showToast(`👍 the issue on GitHub to cast your vote for @${nomineeLogin} as ${role}.`);
}

/* ── Request New Election (via GitHub Issue) ── */
function openRequestElectionForm() {
  if (!currentUser) { alert('Please sign in with GitHub first.'); return; }
  const formModal = document.getElementById('nomination-modal');
  const formBody = document.getElementById('nomination-modal-body');
  if (!formModal || !formBody) return;

  // Build project options from merged list (pinned + API-fetched)
  const projectOptions = (leadersData.projects || [])
    .map(p => `<option value="${escHtml(p.id)}">${escHtml(p.name)}</option>`)
    .join('');

  formBody.innerHTML = `
    <h3 class="text-xl font-extrabold text-gray-900 dark:text-white mb-1">Request an Election</h3>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">This opens a GitHub Issue for Donnie to review and approve.</p>
    <form id="election-request-form" class="space-y-4">
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="er-project">Project / Repo</label>
        <select id="er-project" class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
          <option value="">— select a project —</option>
          ${projectOptions}
          <option value="__other__">Other (specify below)</option>
        </select>
      </div>
      <div id="er-other-wrap" class="hidden">
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="er-other">Repo URL or name</label>
        <input id="er-other" type="text" class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" placeholder="https://github.com/OWASP-BLT/..." />
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="er-term">Term name</label>
        <input id="er-term" type="text" class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" placeholder="e.g. June 2026 Leadership" />
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Roles needed</label>
        <div class="flex gap-4">
          <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <input type="checkbox" id="er-role-lead" checked class="accent-primary" /> Lead
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <input type="checkbox" id="er-role-colead" checked class="accent-primary" /> Co-Lead
          </label>
        </div>
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="er-reason">Why now? (optional)</label>
        <textarea id="er-reason" rows="3" class="w-full rounded-xl border border-neutral-border dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none" placeholder="Context for the admin..."></textarea>
      </div>
      <div class="flex gap-3 pt-2">
        <button type="submit" class="flex-1 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors">
          Submit Request via GitHub Issue
        </button>
        <button type="button" id="er-cancel" class="rounded-xl border border-neutral-border dark:border-gray-600 px-4 py-2.5 text-sm font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          Cancel
        </button>
      </div>
    </form>`;

  formModal.classList.remove('hidden');
  formModal.classList.add('flex');

  document.getElementById('er-project').addEventListener('change', e => {
    document.getElementById('er-other-wrap').classList.toggle('hidden', e.target.value !== '__other__');
  });
  document.getElementById('er-cancel').addEventListener('click', () => {
    formModal.classList.add('hidden'); formModal.classList.remove('flex');
  });
  document.getElementById('election-request-form').addEventListener('submit', e => {
    e.preventDefault();
    submitElectionRequest();
  });
}

function submitElectionRequest() {
  const projectSel = document.getElementById('er-project').value;
  const projectOther = document.getElementById('er-other').value.trim();
  const term = document.getElementById('er-term').value.trim();
  const wantLead = document.getElementById('er-role-lead').checked;
  const wantColead = document.getElementById('er-role-colead').checked;
  const reason = document.getElementById('er-reason').value.trim();

  const projectLabel = projectSel === '__other__'
    ? (projectOther || 'Not specified')
    : ((leadersData.projects || []).find(p => p.id === projectSel)?.name || projectSel);

  if (!projectSel || !term) { alert('Please select a project and enter a term name.'); return; }
  const roles = [wantLead && 'Lead', wantColead && 'Co-Lead'].filter(Boolean).join(', ') || 'Not specified';

  const title = `[ELECTION REQUEST] ${term} — ${projectLabel}`;
  const body = [
    `## Election Request`,
    ``,
    `**Requested by:** @${currentUser.login}`,
    `**Project:** ${projectLabel}`,
    `**Term:** ${term}`,
    `**Roles:** ${roles}`,
    ``,
    `### Reason / Context`,
    reason || '_No reason provided_',
    ``,
    `---`,
    `_Submitted via BLT Leaders page. Admin: please review and update \`data/leaders.json\` to create this election._`
  ].join('\n');

  const issueUrl = `https://github.com/${BLT_CONFIG.REPO_OWNER}/${BLT_CONFIG.REPO_NAME}/issues/new?`
    + `title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}&labels=election-request,leadership`;

  window.open(issueUrl, '_blank', 'noopener,noreferrer');
  document.getElementById('nomination-modal').classList.add('hidden');
  document.getElementById('nomination-modal').classList.remove('flex');
  showToast('Election request opened as a GitHub Issue. Donnie will review it.');
}

/* ── Projects Panel ── */
function renderProjects() {
  const container = document.getElementById('projects-list');
  const countEl = document.getElementById('projects-count');
  if (!container || !leadersData) return;
  const projects = leadersData.projects || [];

  if (countEl) countEl.textContent = `${projects.length} repo${projects.length !== 1 ? 's' : ''} (GSoC excluded)`;

  if (!projects.length) {
    container.innerHTML = emptyState('fa-code-branch', 'No projects listed yet.');
    return;
  }
  container.innerHTML = projects.map(p => {
    const elections = (leadersData.elections || []).filter(e => e.project_id === p.id);
    const activeEl = elections.find(e => ['nominations_open','voting_open'].includes(e.status));
    const winners = getProjectCurrentLeaders(p.id);
    const gsocTag = p.gsoc ? `<span class="ml-2 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded-full px-2 py-0.5">GSoC</span>` : '';
    const leadersHtml = winners.length
      ? winners.map(w => `<span class="inline-flex items-center gap-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
          <img src="${escHtml(w.avatar || `https://github.com/${w.login}.png`)}" class="w-5 h-5 rounded-full" loading="lazy" />
          ${escHtml(w.login)} <span class="text-gray-400">(${escHtml(w.role)})</span>
        </span>`).join('')
      : `<span class="text-xs text-gray-400 italic">No leaders elected yet</span>`;
    return `<article class="surface-card rounded-2xl p-5 flex flex-col gap-3">
      <div class="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h3 class="font-bold text-gray-900 dark:text-white text-base">${escHtml(p.name)}${gsocTag}</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">${escHtml(p.description || '')}</p>
        </div>
        <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${p.active ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}">${p.active ? 'Active' : 'Inactive'}</span>
      </div>
      <div class="flex flex-wrap gap-2">${leadersHtml}</div>
      <div class="flex items-center justify-between gap-3 flex-wrap pt-1 border-t border-neutral-border dark:border-gray-700">
        <a href="${escHtml(p.repo_url || '#')}" target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-primary transition-colors">
          <svg class="fa-icon" aria-hidden="true"><use href="#fa-github"></use></svg>View Repo
        </a>
        ${activeEl ? `<button data-open-election="${escHtml(activeEl.id)}"
          class="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline">
          ${statusBadge(activeEl.status)}
        </button>` : ''}
      </div>
    </article>`;
  }).join('');

  container.querySelectorAll('[data-open-election]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelector('[data-tab="elections"]').click();
      openElectionModal(btn.dataset.openElection);
    });
  });
}

function getProjectCurrentLeaders(projectId) {
  const past = leadersData.past_winners || [];
  const projectWins = past.filter(pw => pw.project_id === projectId);
  if (!projectWins.length) return [];
  const latest = projectWins.sort((a, b) => new Date(b.finalized_at) - new Date(a.finalized_at))[0];
  return latest.winners || [];
}

/* ── Past Winners Panel ── */
function renderPastWinners() {
  const container = document.getElementById('winners-list');
  if (!container || !leadersData) return;
  const past = leadersData.past_winners || [];
  if (!past.length) {
    container.innerHTML = emptyState('fa-trophy', 'No finalized elections yet.');
    return;
  }
  const sorted = [...past].sort((a, b) => new Date(b.finalized_at) - new Date(a.finalized_at));
  container.innerHTML = sorted.map(pw => {
    const project = (leadersData.projects || []).find(p => p.id === pw.project_id) || {};
    const date = new Date(pw.finalized_at).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    const winnersHtml = (pw.winners || []).map(w => `
      <div class="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
        <img src="${escHtml(w.avatar || `https://github.com/${w.login}.png`)}"
             alt="${escHtml(w.login)}" class="w-10 h-10 rounded-full border-2 border-primary" loading="lazy"
             onerror="this.src='https://github.com/identicons/${escHtml(w.login)}.png'" />
        <div class="min-w-0">
          <a href="https://github.com/${escHtml(w.login)}" target="_blank" rel="noopener noreferrer"
             class="font-bold text-gray-900 dark:text-white hover:text-primary transition-colors text-sm">
            ${escHtml(w.login)}
          </a>
          <p class="text-xs text-gray-400">${escHtml(w.role)} · ${w.votes || 0} votes</p>
        </div>
        <svg class="fa-icon text-yellow-500 ml-auto flex-shrink-0" aria-hidden="true"><use href="#fa-trophy"></use></svg>
      </div>`).join('');
    return `<article class="surface-card rounded-2xl p-5">
      <div class="flex items-start justify-between gap-2 mb-3 flex-wrap">
        <div>
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide">${escHtml(project.name || pw.project_id)}</p>
          <h3 class="font-bold text-gray-900 dark:text-white">${escHtml(pw.term)}</h3>
        </div>
        <span class="text-xs text-gray-400">${date}</span>
      </div>
      <div class="grid gap-2 sm:grid-cols-2">${winnersHtml}</div>
    </article>`;
  }).join('');
}

/* ── Modal close handlers ── */
document.addEventListener('DOMContentLoaded', () => {
  ['election-modal', 'nomination-modal'].forEach(id => {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener('click', e => {
      if (e.target === modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
      }
    });
  });
  document.getElementById('election-modal-close')?.addEventListener('click', () => {
    document.getElementById('election-modal').classList.add('hidden');
    document.getElementById('election-modal').classList.remove('flex');
  });
  document.getElementById('nomination-modal-close')?.addEventListener('click', () => {
    document.getElementById('nomination-modal').classList.add('hidden');
    document.getElementById('nomination-modal').classList.remove('flex');
  });
});

/* ── Utilities ── */
function escHtml(str) {
  if (str == null) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function emptyState(icon, msg) {
  return `<div class="col-span-full text-center py-16 text-gray-400 dark:text-gray-500">
    <svg class="fa-icon text-4xl text-gray-300 dark:text-gray-600 block mb-3 mx-auto" aria-hidden="true"><use href="#fa-${icon}"></use></svg>
    <p class="text-sm">${escHtml(msg)}</p>
  </div>`;
}

function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm font-semibold px-5 py-3 rounded-xl shadow-lg transition-opacity duration-300';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 4000);
}
