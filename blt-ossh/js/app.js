// Dark mode toggle
const darkToggle = document.getElementById('dark-toggle');
const html = document.documentElement;

// Check for saved theme preference or default to light mode
const currentTheme = localStorage.getItem('theme') || 'light';
if (currentTheme === 'dark') {
  html.classList.add('dark');
}

darkToggle.addEventListener('click', () => {
  html.classList.toggle('dark');
  const theme = html.classList.contains('dark') ? 'dark' : 'light';
  localStorage.setItem('theme', theme);
});

// Form submission
const form = document.getElementById('ossh-form');
const submitBtn = document.getElementById('submit-btn');
const btnText = document.getElementById('btn-text');
const loadingSpinner = document.getElementById('loading-spinner');
const loadingIndicator = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');
const usernameInput = document.getElementById('github-username');

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const username = usernameInput.value.trim();

  if (!username) {
    showError('Please enter a GitHub username');
    return;
  }

  // Validate username format
  if (username.length > 39 || !/^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$/.test(username)) {
    showError('Please enter a valid GitHub username');
    return;
  }

  // Reset error state
  hideError();

  // Show loading state
  submitBtn.disabled = true;
  btnText.textContent = 'Analyzing...';
  loadingSpinner.classList.remove('hidden');
  if (loadingIndicator) loadingIndicator.style.display = 'block';

  try {
    // Fetch user profile from GitHub API
    const userResponse = await fetch(
      `https://api.github.com/users/${encodeURIComponent(username)}`,
      { headers: { Accept: 'application/vnd.github+json' } }
    );

    if (userResponse.status === 404) {
      throw new Error('GitHub user not found. Please check the username and try again.');
    }
    if (userResponse.status === 403) {
      throw new Error('GitHub API rate limit exceeded. Please wait a few minutes and try again.');
    }
    if (!userResponse.ok) {
      throw new Error(`GitHub API error (${userResponse.status}). Please try again later.`);
    }

    const userData = await userResponse.json();

    // Fetch user repositories
    const reposResponse = await fetch(
      `https://api.github.com/users/${encodeURIComponent(username)}/repos?sort=updated&per_page=100`,
      { headers: { Accept: 'application/vnd.github+json' } }
    );
    const reposData = reposResponse.ok ? await reposResponse.json() : [];

    // Build and display results
    const data = await buildRecommendations(userData, reposData);
    displayResults(data);

  } catch (error) {
    console.error('Error:', error);
    showError(error.message || 'Failed to analyze GitHub profile. Please try again.');
  } finally {
    // Reset button state
    submitBtn.disabled = false;
    btnText.textContent = 'Find My Projects';
    loadingSpinner.classList.add('hidden');
    if (loadingIndicator) loadingIndicator.style.display = 'none';
  }
});

const CATALOG_URL = "data/ossh_catalog.json";
let _catalogCache = null;

const HOUSES = {
  buggleton: { name: 'Buggleton', icon: '\u{1F41B}', desc: 'Bug hunters & QA champions',
    color: 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-700',
    languages: ['Python', 'JavaScript', 'TypeScript', 'Java'],
    keywords: ['bug', 'test', 'qa', 'selenium', 'cypress', 'jest', 'pytest', 'mocha', 'testing', 'quality'] },
  cybermoose: { name: 'Cybermoose', icon: '\u{1F6E1}\uFE0F', desc: 'Security & cybersecurity experts',
    color: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700',
    languages: ['Python', 'C', 'Go', 'Rust', 'JavaScript'],
    keywords: ['security', 'pentest', 'exploit', 'vuln', 'owasp', 'hack', 'crypto', 'encrypt', 'auth', 'xss', 'sqli'] },
  bufferbit: { name: 'Bufferbit', icon: '\u2699\uFE0F', desc: 'Infrastructure & DevOps builders',
    color: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-700',
    languages: ['Shell', 'Python', 'Go', 'HCL', 'YAML', 'Dockerfile'],
    keywords: ['docker', 'kubernetes', 'terraform', 'ansible', 'ci', 'devops', 'infra', 'deploy', 'pipeline', 'cloud'] },
  darkram: { name: 'Darkram', icon: '\u26A1', desc: 'Backend & systems engineers',
    color: 'bg-violet-100 dark:bg-violet-900/40 text-violet-800 dark:text-violet-300 border-violet-300 dark:border-violet-700',
    languages: ['C', 'C++', 'Rust', 'Go', 'Python', 'Java'],
    keywords: ['backend', 'system', 'kernel', 'embedded', 'compiler', 'database', 'api', 'server', 'performance'] }
};

function assignHouse(userData, repos, languages) {
  const scores = { buggleton: 0, cybermoose: 0, bufferbit: 0, darkram: 0 };
  const text = [(userData.bio || '').toLowerCase(), ...repos.map(r => [r.name, r.description, r.full_name].filter(Boolean).join(' ').toLowerCase())].join(' ');
  Object.keys(HOUSES).forEach(houseId => {
    const house = HOUSES[houseId];
    house.languages.forEach(lang => { if (languages.includes(lang)) scores[houseId] += 3; });
    house.keywords.forEach(kw => {
      const regex = new RegExp(`\\b${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
      if (regex.test(text)) scores[houseId] += 2;
    });
  });
  const sorted = Object.entries(scores).sort((a, b) => {
    if (b[1] !== a[1]) return b[1] - a[1];
    return a[0].localeCompare(b[0]);
  });
  const winner = sorted[0];
  if (!winner || winner[1] === 0) return null;
  const house = HOUSES[winner[0]];
  return { id: winner[0], ...house, score: winner[1] };
}

const TAG_NORMALIZATION = {
  js: "javascript",
  node: "nodejs",
  "c++": "cpp",
  csharp: "c#",
  golang: "go",
  py: "python",
};

function normalizeTag(tag) {
  if (!tag) return "";
  const t = String(tag).trim().toLowerCase();
  return TAG_NORMALIZATION[t] || t;
}

function tokenize(text) {
  if (!text) return [];
  let s = String(text).replace(/([a-z])([A-Z])/g, "$1 $2");
  s = s.replace(/[^a-zA-Z0-9\s]/g, " ");
  return s
    .split(/\s+/)
    .map((w) => normalizeTag(w))
    .filter(Boolean);
}

async function loadCatalog() {
  if (_catalogCache) return _catalogCache;
  const resp = await fetch(CATALOG_URL);
  if (!resp.ok) throw new Error(`Failed to load catalog (${resp.status})`);
  _catalogCache = await resp.json();
  return _catalogCache;
}

function buildAllowedTagSet(catalog) {
  const s = new Set();
  const addTags = (arr) => {
    (arr || []).forEach((t) => s.add(normalizeTag(t)));
  };

  (catalog.repos || []).forEach((r) => addTags(r.tags));
  (catalog.communities || []).forEach((c) => addTags(c.tags));
  (catalog.discussion_channels || []).forEach((c) => addTags(c.tags));
  (catalog.articles || []).forEach((a) => addTags(a.tags));

  (catalog.repos || []).forEach((r) => r.primary_language && s.add(normalizeTag(r.primary_language)));
  (catalog.communities || []).forEach((c) => c.primary_language && s.add(normalizeTag(c.primary_language)));

  return s;
}

function preprocessUser(repos, allowedTags) {
  const tagCounts = new Map();
  const langCounts = new Map();

  const bump = (k, n = 1) => tagCounts.set(k, (tagCounts.get(k) || 0) + n);

  for (const repo of repos || []) {
    if (repo.language) {
      const lang = normalizeTag(repo.language);
      langCounts.set(lang, (langCounts.get(lang) || 0) + 1);
      if (allowedTags.has(lang)) bump(lang, 2);
    }

    for (const w of tokenize(repo.description || "")) {
      if (allowedTags.has(w)) bump(w, 1);
    }

    for (const topic of (repo.topics || [])) {
      const t = normalizeTag(topic);
      if (allowedTags.has(t)) bump(t, 3);
    }
  }

  const userTags = [...tagCounts.entries()].sort((a, b) => b[1] - a[1]);

  const total = [...langCounts.values()].reduce((a, b) => a + b, 0) || 1;
  const languageWeights = {};
  for (const [lang, count] of langCounts.entries()) {
    const pct = (count / total) * 100;
    if (pct >= 5) languageWeights[lang] = pct;
  }

  return { userTags, languageWeights };
}

function recommendGeneric(items, userTags, languageWeights, opts) {
  const tagWeight = Object.fromEntries(userTags);
  const topN = opts?.topN ?? 12;
  const usesLanguage = !!opts?.usesLanguage;

  const out = new Map();
  for (const item of items || []) {
    const itemTags = (item.tags || []).map(normalizeTag);
    const tagScore = itemTags.reduce((sum, t) => sum + (tagWeight[t] || 0), 0);

    let langScore = 0;
    let matchingLanguages = [];
    if (usesLanguage && item.primary_language) {
      const l = normalizeTag(item.primary_language);
      if (languageWeights[l]) {
        langScore = languageWeights[l];
        matchingLanguages = [item.primary_language];
      }
    }

    const relevance = tagScore + langScore;
    if (relevance <= 0) continue;

    const matchingTags = itemTags.filter((t) => tagWeight[t]).slice(0, 12);
    const reasons = [];
    if (matchingTags.length) reasons.push(`Matching tags: ${matchingTags.join(", ")}`);
    if (matchingLanguages.length) reasons.push(`Matching language: ${matchingLanguages.join(", ")}`);

    const scored = {
      item,
      relevance_score: relevance,
      reasoning: reasons.join(" | ") || "No specific reason",
      matching_tags: matchingTags,
    };
    const key = item.html_url || item.url || item.invite_url || item.full_name || item.name;
    const existing = out.get(key);
    if (!existing || existing.relevance_score < scored.relevance_score) {
      out.set(key, scored);
    }
  }

  return [...out.values()]
    .sort((a, b) => b.relevance_score - a.relevance_score)
    .slice(0, topN);
}

async function buildRecommendations(userData, repos) {
  const languageCounts = {};
  (repos || []).forEach(repo => {
    if (repo.language) languageCounts[repo.language] = (languageCounts[repo.language] || 0) + 1;
  });
  const languages = Object.keys(languageCounts).sort((a, b) => languageCounts[b] - languageCounts[a]).slice(0, 10);
  const house = assignHouse(userData, repos || [], languages);

  let catalog;
  try {
    catalog = await loadCatalog();
  } catch (e) {
    console.warn(e);
    return {
      github_stats: {
        username: userData.login,
        name: userData.name || userData.login,
        avatar_url: userData.avatar_url,
        bio: userData.bio,
        public_repos: userData.public_repos,
        followers: userData.followers,
        following: userData.following,
        languages: [],
      },
      house,
      recommended_repos: [],
      recommended_communities: [],
      recommended_articles: [],
      recommended_discussion_channels: [],
    };
  }

  const allowedTags = buildAllowedTagSet(catalog);
  const { userTags, languageWeights } = preprocessUser(repos, allowedTags);

  const github_stats = {
    username: userData.login,
    name: userData.name || userData.login,
    avatar_url: userData.avatar_url,
    bio: userData.bio,
    public_repos: userData.public_repos,
    followers: userData.followers,
    following: userData.following,
    languages: Object.entries(languageWeights)
      .sort(([, a], [, b]) => b - a)
      .map(([lang]) => lang)
      .slice(0, 10),
  };

  const recommended_repos = recommendGeneric(catalog.repos, userTags, languageWeights, { topN: 6, usesLanguage: true });
  const recommended_communities = recommendGeneric(catalog.communities, userTags, languageWeights, { topN: 6, usesLanguage: true });
  const recommended_discussion_channels = recommendGeneric(catalog.discussion_channels, userTags, languageWeights, { topN: 6, usesLanguage: false });
  const recommended_articles = recommendGeneric(catalog.articles, userTags, languageWeights, { topN: 8, usesLanguage: false });

  return {
    github_stats,
    house,
    recommended_repos,
    recommended_communities,
    recommended_articles,
    recommended_discussion_channels,
  };
}

function showError(message) {
  errorText.textContent = message;
  errorMessage.classList.remove('hidden');
}

function hideError() {
  errorMessage.classList.add('hidden');
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function sanitizeExternalUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, window.location.origin);
    return ['http:', 'https:'].includes(url.protocol) ? url.toString() : '#';
  } catch {
    return '#';
  }
}

function renderTagChips(tags, limit = 12) {
  const safe = (tags || []).slice(0, limit);
  if (!safe.length) return '';
  return `
    <div class="flex flex-wrap gap-2 mt-3">
      ${safe.map(t =>
        `<span class="px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full text-xs font-semibold">
          ${escapeHtml(t)}
        </span>`
      ).join('')}
    </div>
  `;
}

function renderScoreReason(row) {
  if (!row || typeof row !== 'object') return '';
  const score = row.relevance_score;
  const reason = row.reasoning;
  const hasScore = typeof score === 'number' && isFinite(score);
  const hasReason = typeof reason === 'string' && reason.trim().length > 0;

  if (!hasScore && !hasReason) return '';

  return `
    <div class="mt-3 space-y-1">
      ${hasScore ? `<div class="text-sm text-gray-700 dark:text-gray-300">
        <span class="text-gray-500 dark:text-gray-400">Relevance Score:</span>
        <span class="font-semibold text-green-600 dark:text-green-400">${escapeHtml(String(Math.round(score * 100) / 100))}</span>
      </div>` : ''}
      ${hasReason ? `<div class="text-sm text-gray-700 dark:text-gray-300">
        <span class="text-gray-500 dark:text-gray-400">Reason:</span>
        ${escapeHtml(reason)}
      </div>` : ''}
    </div>
  `;
}

function displayResults(data) {
  const resultsSection = document.getElementById('results-section');
  const githubStats = data.github_stats;

  // Populate GitHub Stats
  document.getElementById('user-avatar').src = githubStats.avatar_url || 'static/logo.png';
  document.getElementById('user-name').textContent = githubStats.name || githubStats.username;
  const houseBadge = document.getElementById('house-badge');
  if (houseBadge && data.house) {
    houseBadge.className = `inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold border ${data.house.color}`;
    houseBadge.title = data.house.desc;
    houseBadge.setAttribute('aria-describedby', 'house-desc');
    const houseIcon = document.getElementById('house-icon');
    const houseName = document.getElementById('house-name');
    const houseDesc = document.getElementById('house-desc');
    if (houseIcon) houseIcon.textContent = data.house.icon;
    if (houseName) houseName.textContent = data.house.name;
    if (houseDesc) houseDesc.textContent = data.house.desc;
    houseBadge.classList.remove('hidden');
  } else if (houseBadge) {
    houseBadge.classList.add('hidden');
  }
  document.getElementById('user-bio').textContent = githubStats.bio || 'No bio available';
  document.getElementById('user-repos').textContent = githubStats.public_repos || 0;
  document.getElementById('user-followers').textContent = githubStats.followers || 0;
  document.getElementById('user-following').textContent = githubStats.following || 0;

  // Display languages
  const languagesContainer = document.getElementById('user-languages');
  languagesContainer.innerHTML = '';
  (githubStats.languages || []).forEach(lang => {
    const badge = document.createElement('span');
    badge.className = 'px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full text-xs font-semibold';
    badge.textContent = lang;
    languagesContainer.appendChild(badge);
  });

  // Recommended repositories
  const reposContainer = document.getElementById('recommended-repos');
  reposContainer.innerHTML = '';

  (data.recommended_repos || []).forEach(row => {
    const repo = row?.item ? row.item : row;
    const repoName = repo.full_name || repo.name || '';
    const repoDesc = repo.description || '';
    const repoStars = (repo.stars != null) ? repo.stars : (repo.stargazers_count != null ? repo.stargazers_count : 0);
    const repoUrl = repo.url || repo.html_url || '#';

    const repoCard = document.createElement('div');
    repoCard.className = 'surface-card rounded-xl p-5 hover:shadow-lg transition';
    repoCard.innerHTML = `
      <div class="flex items-start justify-between mb-3 gap-3">
        <h4 class="font-bold text-gray-900 dark:text-white text-lg break-words">${escapeHtml(repoName)}</h4>
        <span class="text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 px-2 py-1 rounded-full whitespace-nowrap">
          <i class="fas fa-star"></i> ${escapeHtml(String(repoStars))}
        </span>
      </div>
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">${escapeHtml(repoDesc)}</p>
      ${renderTagChips(repo.tags || row?.matching_tags)}
      ${renderScoreReason(row?.item ? row : null)}
      <a href="${escapeHtml(sanitizeExternalUrl(repoUrl))}" target="_blank" rel="noopener noreferrer"
        class="inline-flex items-center gap-2 text-red-600 dark:text-red-400 font-semibold text-sm hover:underline mt-4">
        <i class="fab fa-github"></i> View Repository
      </a>
    `;
    reposContainer.appendChild(repoCard);
  });

  // Recommended communities
  const communitiesContainer = document.getElementById('recommended-communities');
  communitiesContainer.innerHTML = '';

  (data.recommended_communities || []).forEach(row => {
    const community = row?.item ? row.item : row;
    const cName = community.name || '';
    const cDesc = community.description || '';
    const cMembers = community.members || (community.member_count != null ? String(community.member_count) : '');
    const cUrl = community.url || community.invite_url || '#';

    const communityCard = document.createElement('div');
    communityCard.className = 'surface-card rounded-xl p-5 hover:shadow-lg transition';
    communityCard.innerHTML = `
      <h4 class="font-bold text-gray-900 dark:text-white mb-2">${escapeHtml(cName)}</h4>
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">${escapeHtml(cDesc)}</p>
      <div class="flex justify-between items-center">
        <span class="text-xs text-gray-500 dark:text-gray-400">
          <i class="fas fa-users"></i> ${escapeHtml(String(cMembers || '\u2014'))}
        </span>
        <a href="${escapeHtml(cUrl)}" target="_blank" rel="noopener noreferrer"
          class="text-red-600 dark:text-red-400 font-semibold text-sm hover:underline">
          Visit <i class="fas fa-external-link-alt ml-1"></i>
        </a>
      </div>
      ${renderTagChips(community.tags || row?.matching_tags)}
      ${renderScoreReason(row?.item ? row : null)}
    `;
    communitiesContainer.appendChild(communityCard);
  });

  // Recommended articles
  const articlesContainer = document.getElementById('recommended-articles');
  articlesContainer.innerHTML = '';

  (data.recommended_articles || []).forEach(row => {
    const article = row?.item ? row.item : row;
    const aTitle = article.title || '';
    const aCategory = article.category || '';
    const aUrl = article.url || '#';

    const articleCard = document.createElement('div');
    articleCard.className = 'surface-card rounded-xl p-5 hover:shadow-lg transition';
    articleCard.innerHTML = `
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
          <i class="fas fa-file-alt text-red-600 dark:text-red-400"></i>
        </div>
        <div class="flex-1">
          <h4 class="font-semibold text-gray-900 dark:text-white mb-1">${escapeHtml(aTitle)}</h4>
          <span class="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-1 rounded">
            ${escapeHtml(aCategory)}
          </span>
          ${renderTagChips(article.tags || row?.matching_tags)}
          ${renderScoreReason(row?.item ? row : null)}
          <a href="${escapeHtml(aUrl)}" target="_blank" rel="noopener noreferrer"
            class="block mt-3 text-red-600 dark:text-red-400 font-semibold text-sm hover:underline">
            Read More <i class="fas fa-arrow-right ml-1"></i>
          </a>
        </div>
      </div>
    `;
    articlesContainer.appendChild(articleCard);
  });

  // Discussion channels
  const channelsContainer = document.getElementById('discussion-channels');
  channelsContainer.innerHTML = '';

  (data.recommended_discussion_channels || []).forEach(row => {
    const channel = row?.item ? row.item : row;
    const chName = channel.name || '';
    const chDesc = channel.description || '';
    const chSource = channel.source || channel.platform || '\u2014';
    const chMembers = (channel.member_count != null) ? channel.member_count : (channel.members != null ? channel.members : '\u2014');
    const chUrl = channel.invite_url || channel.url || '#';
    const chTags = channel.tags || row?.matching_tags || [];

    const channelCard = document.createElement('div');
    channelCard.className = 'surface-card rounded-xl p-5 hover:shadow-lg transition';
    channelCard.innerHTML = `
      <h4 class="font-bold text-gray-900 dark:text-white mb-2">${escapeHtml(chName)}</h4>
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">${escapeHtml(chDesc)}</p>
      <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
        <span class="font-semibold">Source:</span> ${escapeHtml(String(chSource))} &nbsp; \u2022 &nbsp;
        <span class="font-semibold">Members:</span> ${escapeHtml(String(chMembers))}
      </div>
      ${renderTagChips(chTags)}
      ${renderScoreReason(row?.item ? row : null)}
      <a href="${escapeHtml(chUrl)}" target="_blank" rel="noopener noreferrer"
        class="inline-flex items-center gap-2 text-red-600 dark:text-red-400 font-semibold text-sm hover:underline mt-4">
        Join <i class="fas fa-arrow-right ml-1"></i>
      </a>
    `;
    channelsContainer.appendChild(channelCard);
  });

  // Update GitHub profile links
  const profileLink = document.getElementById('github-profile-link');
  if (profileLink) {
    profileLink.href = `https://github.com/${encodeURIComponent(githubStats.username)}`;
    const span = profileLink.querySelector('span');
    if (span) span.textContent = `View ${githubStats.username}'s GitHub profile`;
  }

  // Setup create profile button
  setupCreateProfileButton(data);

  // Update GitHub profile link
  document.getElementById('view-github-profile').href =
    `https://github.com/${encodeURIComponent(githubStats.username)}`;

  // Show results section and scroll to it
  resultsSection.classList.remove('hidden');
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Hide features section
  document.querySelector('.grid.gap-6.md\\:grid-cols-3.mb-12')?.classList.add('hidden');
  document.querySelector('.surface-card.rounded-2xl.p-8.sm\\:p-10')?.classList.add('hidden');
}

function setupCreateProfileButton(data) {
  const createProfileBtn = document.getElementById('create-profile-btn');
  if (!createProfileBtn) return;

  // Remove existing listener by cloning
  const newBtn = createProfileBtn.cloneNode(true);
  createProfileBtn.parentNode.replaceChild(newBtn, createProfileBtn);

  // Add click handler
  newBtn.addEventListener('click', () => {
    const profileUrl = buildProfileIssueUrl(data);
    window.open(profileUrl, '_blank');
  });
}

function buildProfileIssueUrl(data) {
  const githubStats = data.github_stats;
  const baseUrl = 'https://github.com/OWASP-BLT/BLT-OSSH/issues/new';

  const skills = (githubStats.languages || []).slice(0, 10).join(', ');
  const topLanguages = (githubStats.languages || []).slice(0, 3).join(', ');
  const communityNames = (data.recommended_communities || []).map(c => (c.item || c).name).filter(Boolean).join(', ');
  const lookingFor = [
    topLanguages ? `Looking to contribute to open source projects in ${topLanguages}.` : 'Looking to contribute to open source projects.',
    `Interested in ${communityNames || 'open source'}.`,
  ].join(' ');

  const recommendedProjects = (data.recommended_repos || [])
    .slice(0, 5)
    .map(r => { const repo = r.item || r; return `- [${repo.full_name || repo.name}](${repo.html_url || repo.url || '#'}) \u2B50 ${repo.stars != null ? repo.stars : (repo.stargazers_count || 0)} - ${repo.description || ''}`; })
    .join('\n');

  const recommendedCommunities = (data.recommended_communities || [])
    .map(c => { const comm = c.item || c; return `- [${comm.name}](${comm.url || comm.invite_url || '#'}) - ${comm.description || ''} (${comm.members || comm.member_count || '\u2014'} members)`; })
    .join('\n');

  const recommendedArticles = (data.recommended_articles || [])
    .map(a => { const art = a.item || a; return `- [${art.title}](${art.url || '#'}) - ${art.category || ''}`; })
    .join('\n');

  const bodyContent = `# \u{1F3AF} OSSH Analysis Summary

> **Profile analyzed on:** ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}

## \u{1F4CA} GitHub Stats
- **Your House:** ${data.house ? `${data.house.icon} ${data.house.name} \u2014 ${data.house.desc}` : '\u2014'}
- **Username:** [@${githubStats.username}](https://github.com/${githubStats.username})
- **Name:** ${githubStats.name || githubStats.username}
- **Bio:** ${githubStats.bio || 'No bio provided'}
- **Repositories:** ${githubStats.public_repos}
- **Followers:** ${githubStats.followers}
- **Following:** ${githubStats.following}
- **Top Languages:** ${(githubStats.languages || []).slice(0, 5).join(', ')}

## \u{1F31F} Your Top Recommended Projects
${recommendedProjects}

## \u{1F465} Recommended Communities to Join
${recommendedCommunities}

## \u{1F4DA} Recommended Articles for You
${recommendedArticles}

## \u{1F4AC} Discussion Channels
${(data.recommended_discussion_channels || []).map(ch => { const c = ch.item || ch; return `- [${c.name}](${c.invite_url || c.url || '#'}) - ${c.platform || c.source || '\u2014'}`; }).join('\n')}

---

**\u{1F916} Generated by:** [OSSH - Open Source Sorting Hat](https://github.com/OWASP-BLT/BLT-OSSH)

**\u270F\uFE0F Note:** The information above has been automatically populated based on your GitHub profile analysis. Please review and edit the profile fields below before submitting. You can modify your bio, add interests, specify what you're looking for, and fill in optional fields like location and social links.`;

  const recommendedProjectsDisplay = (data.recommended_repos || [])
    .slice(0, 6)
    .map(r => { const repo = r.item || r; return `**${repo.full_name || repo.name}** \u2B50 ${repo.stars != null ? repo.stars : (repo.stargazers_count || 0)}\n${repo.description || ''}\n\u{1F517} [View](${repo.html_url || repo.url || '#'})`; })
    .join('\n\n');

  const recommendedCommunitiesDisplay = (data.recommended_communities || [])
    .map(c => { const comm = c.item || c; return `**${comm.name}** (${comm.members || comm.member_count || '\u2014'} members)\n${comm.description || ''}\n\u{1F517} [Visit](${comm.url || comm.invite_url || '#'})`; })
    .join('\n\n');

  const recommendedArticlesDisplay = (data.recommended_articles || [])
    .map(a => { const art = a.item || a; return `**${art.title}** - ${art.category || ''}\n\u{1F517} [Read](${art.url || '#'})`; })
    .join('\n\n');

  const params = new URLSearchParams({
    template: 'user_profile.yml',
    title: `[PROFILE] ${githubStats.name || githubStats.username}`,
    labels: 'profile',
    'github_username': githubStats.username,
    'display_name': githubStats.name || githubStats.username,
    'bio': githubStats.bio || `Open source developer passionate about ${topLanguages}`,
    'skills': skills,
    'looking_for': lookingFor,
    'recommended_projects': recommendedProjectsDisplay,
    'recommended_communities': recommendedCommunitiesDisplay,
    'recommended_reading': recommendedArticlesDisplay,
  });

  params.append('body', bodyContent);

  return `${baseUrl}?${params.toString()}`;
}

// Analyze another profile button handler
document.addEventListener('DOMContentLoaded', () => {
  const analyzeAnotherBtn = document.getElementById('analyze-another');
  if (analyzeAnotherBtn) {
    analyzeAnotherBtn.addEventListener('click', () => {
      document.getElementById('results-section').classList.add('hidden');
      document.querySelector('.grid.gap-6.md\\:grid-cols-3.mb-12').classList.remove('hidden');
      document.querySelector('.surface-card.rounded-2xl.p-8.sm\\:p-10').classList.remove('hidden');
      usernameInput.value = '';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
});

// Set footer year
document.getElementById('footer-year').textContent = new Date().getFullYear();
