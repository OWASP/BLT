// The directory of live GSoC dashboards. gsoc-tool.owaspblt.org refreshes data/directory.json
// daily; a fork without that Worker (GitHub Pages) reads the shared copy instead.
const DIRECTORY_SOURCES = ['data/directory.json', 'https://gsoc-tool.owaspblt.org/data/directory.json'];

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function httpsUrl(url) {
    const value = String(url || '').trim();
    return /^https:\/\/[^\s"'<>]+$/i.test(value) ? value : '';
}

async function loadDirectory() {
    let fallback = null;
    for (const source of DIRECTORY_SOURCES) {
        try {
            const response = await fetch(source);
            if (!response.ok) continue;
            const data = await response.json();
            if (data && Array.isArray(data.sites) && data.sites.length) return data;
            fallback = fallback || data;
        } catch (error) {
            console.warn(`directory: ${source}`, error);
        }
    }
    return fallback || { sites: [] };
}

const number = (value) => (typeof value === 'number' ? value : null);
const ownContent = (site) => Object.values(site.content || {}).reduce((sum, n) => sum + (n || 0), 0);
const thisSite = () => location.origin + location.pathname.replace(/[^/]*$/, '');

function relativeTime(iso) {
    const then = Date.parse(iso);
    if (!then) return '';
    const days = Math.floor((Date.now() - then) / 86400000);
    if (days < 1) return 'today';
    if (days === 1) return 'yesterday';
    if (days < 30) return `${days} days ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`;
    const years = Math.floor(days / 365);
    return `${years} year${years === 1 ? '' : 's'} ago`;
}

const SORTS = {
    merged: (a, b) => (number(b.stats.mergedPullRequests) ?? -1) - (number(a.stats.mergedPullRequests) ?? -1),
    prs: (a, b) => (number(b.stats.pullRequests) ?? -1) - (number(a.stats.pullRequests) ?? -1),
    content: (a, b) => ownContent(b) - ownContent(a),
    pushed: (a, b) => (Date.parse(b.pushedAt) || 0) - (Date.parse(a.pushedAt) || 0),
    name: (a, b) => String(a.name).localeCompare(String(b.name)),
};

function statCell(value, label) {
    const shown = number(value) == null ? '–' : number(value).toLocaleString();
    return `<div class="site-stat"><strong>${shown}</strong><span>${label}</span></div>`;
}

function contentChips(content) {
    const chips = [
        ['blogPosts', 'fa-blog', 'post'],
        ['weeklyUpdates', 'fa-calendar-week', 'update'],
        ['milestones', 'fa-trophy', 'milestone'],
        ['feedback', 'fa-comments', 'feedback note'],
    ].filter(([key]) => content && content[key] > 0)
        .map(([key, icon, word]) => {
            const n = content[key];
            return `<span class="chip"><i class="fas ${icon}" aria-hidden="true"></i> ${n} ${word}${n === 1 ? '' : 's'}</span>`;
        });
    return chips.join('');
}

function renderSite(site, here) {
    const url = httpsUrl(site.url);
    const avatar = httpsUrl(site.avatar) || 'assets/images/sample-avatar.svg';
    const project = site.project || {};
    const repoUrl = httpsUrl(site.repoUrl);
    const github = site.username ? `https://github.com/${encodeURIComponent(site.username)}` : '';
    const isHere = url && url === here;
    const updated = relativeTime(site.pushedAt);
    return `
        <article class="site-card${isHere ? ' is-here' : ''}">
            <div class="site-head">
                <img class="site-avatar" src="${escapeHtml(avatar)}" alt="" loading="lazy" data-fallback="assets/images/sample-avatar.svg">
                <div class="site-who">
                    <h3><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(site.name || site.username || 'GSoC student')}</a></h3>
                    ${site.username ? `<p class="site-handle">@${escapeHtml(site.username)}</p>` : ''}
                </div>
                ${isHere ? '<span class="here-badge">This site</span>' : ''}
            </div>
            <p class="site-project${project.title ? '' : ' is-empty'}">${escapeHtml(project.title || 'Project not filled in yet')}</p>
            ${project.organization ? `<p class="site-org"><i class="fas fa-building" aria-hidden="true"></i> ${escapeHtml(project.organization)}</p>` : ''}
            <div class="site-stats">
                ${statCell(site.stats && site.stats.pullRequests, 'PRs')}
                ${statCell(site.stats && site.stats.mergedPullRequests, 'Merged')}
                ${statCell(site.stats && site.stats.issues, 'Issues')}
            </div>
            <div class="chips">${contentChips(site.content)}</div>
            <div class="site-links">
                <a class="site-visit" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Visit dashboard <i class="fas fa-arrow-right" aria-hidden="true"></i></a>
                <span class="site-meta">
                    ${github ? `<a href="${escapeHtml(github)}" target="_blank" rel="noopener noreferrer" aria-label="GitHub profile"><i class="fab fa-github"></i></a>` : ''}
                    ${repoUrl ? `<a href="${escapeHtml(repoUrl)}" target="_blank" rel="noopener noreferrer" aria-label="Dashboard source"><i class="fas fa-code-branch"></i></a>` : ''}
                    ${updated ? `<span title="Last push to the dashboard's repository">updated ${escapeHtml(updated)}</span>` : ''}
                </span>
            </div>
        </article>
    `;
}

function renderTotals(sites, data) {
    const sum = (pick) => sites.reduce((total, site) => total + (number(pick(site)) || 0), 0);
    document.getElementById('total-sites').textContent = sites.length;
    document.getElementById('total-prs').textContent = sum((s) => s.stats.pullRequests).toLocaleString();
    document.getElementById('total-merged').textContent = sum((s) => s.stats.mergedPullRequests).toLocaleString();
    document.getElementById('total-posts').textContent = sites.reduce((total, s) => total + ownContent(s), 0);
    document.getElementById('directory-checked').textContent = data.checked || sites.length;
    document.getElementById('directory-updated').textContent = data.lastUpdated ? relativeTime(data.lastUpdated) : 'not yet';
}

function initDirectory(data) {
    const sites = data.sites.map((site) => ({ ...site, stats: site.stats || {}, content: site.content || {} }));
    const grid = document.getElementById('directory-grid');
    const search = document.getElementById('directory-search');
    const sort = document.getElementById('directory-sort');
    const here = thisSite();
    renderTotals(sites, data);

    const draw = () => {
        const query = search.value.trim().toLowerCase();
        const shown = sites
            .filter((site) => !query || [site.name, site.username, site.project.title, site.project.organization]
                .some((field) => String(field || '').toLowerCase().includes(query)))
            .sort(SORTS[sort.value] || SORTS.merged);
        grid.innerHTML = shown.length
            ? shown.map((site) => renderSite(site, here)).join('')
            : `<p class="empty-note">${sites.length ? 'No dashboard matches that search.' : 'No dashboards found yet.'}</p>`;
    };
    search.addEventListener('input', draw);
    sort.addEventListener('change', draw);
    draw();
}

// Broken avatar links (a placeholder GitHub user, say) fall back to the sample picture.
document.addEventListener('error', (event) => {
    const img = event.target;
    if (img.tagName === 'IMG' && img.dataset.fallback && !img.src.endsWith(img.dataset.fallback)) img.src = img.dataset.fallback;
}, true);

document.addEventListener('DOMContentLoaded', async () => initDirectory(await loadDirectory()));
