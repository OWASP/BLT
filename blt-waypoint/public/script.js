/* BLT Waypoint: one script for the three pages (body[data-page] = dashboard | issues | screenshots).
   Data:
     forge_data.json         every folder of the monorepo on git.owaspblt.org (daily): repos[], open_issues[], generated_at,
                             rating_criteria[]; each repo has rating { tier, score, met, missing, na } and gold_issue
     screenshots/index.json  daily captures of the live sites: { generated_at, shots: { <folder>: { url, captured_at, live_url } } };
                             may 404 until the first capture runs, then every page shows "screenshot pending". */
(function () {
  'use strict';

  const FORGE = 'https://git.owaspblt.org/BLT';
  const DATA_URL = 'forge_data.json';
  const SHOTS_URL = 'screenshots/index.json';
  const SYMBOLS = 'https://owaspblt.org/_home/symbols/';
  const DAY = 864e5;
  const NOW = Date.now();

  /* ---------------- helpers ---------------- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  // A timestamp in ms, or null for missing / placeholder dates (the forge sometimes reports 1970).
  function ts(value) {
    if (!value) return null;
    const t = Date.parse(value);
    return Number.isFinite(t) && t > Date.UTC(2005, 0, 1) ? t : null;
  }

  function ago(value) {
    const t = typeof value === 'number' ? value : ts(value);
    if (t == null) return '';
    const s = Math.max(0, (NOW - t) / 1000);
    if (s < 60) return 'just now';
    const units = [[60, 'min'], [24, 'h'], [30, 'd'], [12, 'mo'], [Infinity, 'y']];
    let n = s / 60;
    for (const [size, label] of units) {
      if (n < size) return `${Math.floor(n)}${label === 'min' ? ' min' : label} ago`;
      n /= size;
    }
    return '';
  }

  function fullDate(value) {
    const t = typeof value === 'number' ? value : ts(value);
    if (t == null) return '';
    return new Date(t).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  }

  const num = n => (Number.isFinite(n) ? n.toLocaleString() : '–');

  function host(url) {
    try { return new URL(url).host.replace(/^www\./, ''); } catch (e) { return ''; }
  }

  function safeUrl(url) {
    return /^https?:\/\//i.test(String(url || '')) ? url : '';
  }

  const store = {
    get(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch (e) { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } },
  };

  function debounce(fn, wait) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
  }

  const params = () => new URLSearchParams(location.search);

  function setParams(values) {
    const p = params();
    for (const [k, v] of Object.entries(values)) {
      if (v === '' || v == null || v === false) p.delete(k); else p.set(k, v);
    }
    const q = p.toString();
    history.replaceState(null, '', q ? `?${q}` : location.pathname);
  }

  async function getJson(url) {
    const resp = await fetch(url, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`${url}: HTTP ${resp.status}`);
    return resp.json();
  }

  const loadForge = () => getJson(DATA_URL);

  // Screenshot index, or null while it does not exist yet (404) or cannot be read.
  async function loadShots() {
    try {
      const data = await getJson(SHOTS_URL);
      return data && typeof data.shots === 'object' && data.shots ? data : null;
    } catch (e) {
      return null;
    }
  }

  /* ---------------- project bits ---------------- */
  const shortName = r => String(r.name || r.folder || '').replace(/^(OWASP-)?BLT-/i, '') || r.folder;

  // The project's live site: live_url from its wrangler.toml custom domain. Until the data carries
  // live_url, the folder's info.json website (homepage) stands in.
  function liveUrl(r) {
    if (!r) return '';
    return safeUrl(Object.prototype.hasOwnProperty.call(r, 'live_url') ? r.live_url : r.homepage);
  }

  function folderUrl(folder) { return `${FORGE}/tree/main/${encodeURIComponent(folder)}`; }
  function issuesUrl(r) { return safeUrl(r.issues_url) || `${FORGE}/issues?label=${encodeURIComponent(r.folder)}`; }

  // The project's round symbol (the one the shared top bar shows) over a monogram. The monogram stays
  // when a folder has no symbol, even where the browser blocks the 404 without an error event.
  function symbol(folder, name, cls = '') {
    const letter = esc((String(name || folder).replace(/^(OWASP-)?BLT-/i, '')[0] || '?').toUpperCase());
    const img = folder ? `<img src="${SYMBOLS}${encodeURIComponent(folder)}.svg" alt="" loading="lazy" decoding="async" data-sym />` : '';
    return `<span class="sym ${cls}" data-l="${letter}" aria-hidden="true">${img}</span>`;
  }

  // Symbols and screenshots settle without inline handlers.
  document.addEventListener('load', event => {
    const img = event.target;
    if (img instanceof HTMLImageElement && img.dataset.sym != null) img.parentElement.classList.add('ok');
  }, true);
  document.addEventListener('error', event => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement)) return;
    if (img.dataset.sym != null) {
      img.remove();
    } else if (img.dataset.shot != null) {
      img.closest('.thumb')?.insertAdjacentHTML('beforeend', placeholder('pending'));
      img.remove();
    }
  }, true);

  function placeholder(kind) {
    const [icon, text] = kind === 'none' ? ['fa-regular fa-window-maximize', 'No live site'] : ['fa-regular fa-image', 'Screenshot pending'];
    return `<span class="ph" title="${text}"><i class="${icon}" aria-hidden="true"></i><span class="ph-t">${text}</span></span>`;
  }

  // The capture's image URL (served by the worker at /screenshots/<folder>.jpg), or '' when there is none.
  function shotUrl(shot) {
    if (!shot || typeof shot.url !== 'string' || !shot.url) return '';
    try { return safeUrl(new URL(shot.url, location.href).href); } catch (e) { return ''; }
  }

  function shotImg(shot, name) {
    const src = shotUrl(shot);
    return src
      ? `<img src="${esc(src)}" alt="${esc(name)} home page" loading="lazy" decoding="async" width="${+shot.width || 1280}" height="${+shot.height || 800}" data-shot />`
      : '';
  }

  // A thumbnail of the live site: the daily capture, "pending" until it exists, "no live site" without one.
  function thumb(live, shot, name) {
    const inner = shotImg(shot, name) || placeholder(live ? 'pending' : 'none');
    return live
      ? `<a class="thumb" href="${esc(live)}" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true">${inner}</a>`
      : `<span class="thumb" aria-hidden="true">${inner}</span>`;
  }

  function sparkline(weeks, w = 78, h = 16) {
    if (!Array.isArray(weeks) || !weeks.length) return '';
    const max = Math.max(...weeks, 1);
    const step = w / weeks.length;
    const bar = Math.max(1, step - 1);
    const bars = weeks.map((v, i) => {
      const bh = v > 0 ? Math.max(2, Math.round(Math.sqrt(v / max) * h)) : 1;
      return `<rect x="${(i * step).toFixed(1)}" y="${h - bh}" width="${bar.toFixed(1)}" height="${bh}" rx="0.5"${v > 0 ? '' : ' class="zero" fill="currentColor"'}/>`;
    }).join('');
    const total = weeks.reduce((a, b) => a + b, 0);
    return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" fill="currentColor" role="img" aria-label="${total} commits in the last ${weeks.length} weeks"><title>${total} commits in ${weeks.length} weeks</title>${bars}</svg>`;
  }

  /* ---------------- freshness: header chip and footer ---------------- */
  function showFreshness(generatedAt, what = 'Data') {
    const t = ts(generatedAt);
    if (t == null) return;
    const stale = NOW - t > 2 * DAY;
    $$('[data-fresh]').forEach(el => {
      el.hidden = false;
      el.classList.toggle('stale', stale);
      el.title = `${what} generated ${fullDate(t)}; it refreshes once a day`;
      el.innerHTML = `<span class="pulse" aria-hidden="true"></span>Updated ${esc(ago(t))} · daily`;
    });
    $$('[data-foot]').forEach(el => {
      el.innerHTML = `Data from <a href="${FORGE}" target="_blank" rel="noopener noreferrer">git.owaspblt.org</a>, last refreshed <time datetime="${esc(new Date(t).toISOString())}">${esc(fullDate(t))}</time>. It updates daily.`;
    });
  }

  function errorState(target, message, retry) {
    target.innerHTML = `<div class="panel state error"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>
      <b>Could not load the project data</b><span>${esc(message)}</span><br />
      <button type="button" class="btn primary"><i class="fa-solid fa-rotate-right" aria-hidden="true"></i>Retry</button></div>`;
    $('button', target).addEventListener('click', retry);
  }

  function emptyState(text, onClear) {
    const wrap = document.createElement('div');
    wrap.className = 'panel state';
    wrap.innerHTML = `<i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i><b>${esc(text)}</b>
      ${onClear ? '<button type="button" class="btn">Clear filters</button>' : ''}`;
    if (onClear) $('button', wrap).addEventListener('click', onClear);
    return wrap;
  }

  function stat(icon, value, label, title = '') {
    return `<div class="stat"${title ? ` title="${esc(title)}"` : ''}><b>${esc(value)}</b><span><i class="fa-solid ${icon}" aria-hidden="true"></i>${esc(label)}</span></div>`;
  }

  /* ---------------- ratings (scripts/ratings.py) ---------------- */
  const TIERS = { gold: 'Gold', silver: 'Silver', bronze: 'Bronze' };
  const TIER_RANK = { gold: 3, silver: 2, bronze: 1 };
  const TIER_NOTE = {
    bronze: 'The basics: a README, a description, a licence and a logo.',
    silver: 'It runs: tests in CI, an automatic deploy, a live site and steps to run it.',
    gold: 'It is looked after: the BLT theme, a contributing guide, recent commits, several contributors and triaged issues.',
  };

  // A small ribbon-and-coin medal in the tier's colours (styles.css: .mdl).
  function medalSvg(tier, size = 16) {
    return `<svg class="mdl ${tier}" width="${size}" height="${size}" viewBox="0 0 16 16" aria-hidden="true">`
      + '<path class="rib-l" d="M4.2 0h3.3l1.6 5.2-2.9 1.5z"/><path class="rib-r" d="M8.5 0h3.3L9.6 6.7 6.9 5.2z"/>'
      + '<circle class="coin" cx="8" cy="10.2" r="5.2"/><circle class="rim" cx="8" cy="10.2" r="3.6"/>'
      + '<path class="star" d="m8 7.9.7 1.4 1.5.2-1.1 1 .3 1.5L8 11.3l-1.4.7.3-1.5-1.1-1 1.5-.2z"/></svg>';
  }

  function medal(tier, score, folder) {
    if (!TIERS[tier]) return '<span class="faint" title="Repository configuration, not rated">–</span>';
    const label = `${TIERS[tier]}${Number.isFinite(score) ? ` · ${score}%` : ''}`;
    const attrs = folder ? ` type="button" data-rate="${esc(folder)}" title="${esc(label)}: see what ${esc(folder)} needs for gold"` : '';
    const tag = folder ? 'button' : 'span';
    return `<${tag} class="medal ${tier}"${attrs}>${medalSvg(tier)}<span class="medal-t">${TIERS[tier]}</span>${Number.isFinite(score) && tier !== 'gold' ? `<span class="medal-s">${score}%</span>` : ''}</${tag}>`;
  }

  // One dialog for every rating: a project's checklist, or (no project) how ratings work.
  function ratingDialog(criteria, p) {
    let dlg = $('#rating-dlg');
    if (!dlg) {
      dlg = document.createElement('dialog');
      dlg.id = 'rating-dlg';
      dlg.className = 'dlg';
      dlg.addEventListener('click', e => { if (e.target === dlg || e.target.closest('[data-close]')) dlg.close(); });
      document.body.append(dlg);
    }
    const rating = p && p.rating;
    const state = id => (!rating ? '' : rating.met.includes(id) ? 'met' : rating.missing.includes(id) ? 'missing' : 'na');
    const sections = ['bronze', 'silver', 'gold'].map(tier => {
      const items = criteria.filter(c => c.tier === tier).map(c => {
        const st = state(c.id);
        const icon = st === 'met' ? 'fa-circle-check' : st === 'missing' ? 'fa-circle-xmark' : st === 'na' ? 'fa-circle-minus' : 'fa-circle';
        const fix = !rating || st === 'missing' ? `<p>${esc(c.fix).replace(/`([^`]+)`/g, '<code>$1</code>')}</p>` : '';
        const na = st === 'na' ? ' <span class="faint">(does not apply)</span>' : '';
        return `<li class="crit ${st}"><i class="fa-solid ${icon}" aria-hidden="true"></i><div><b>${esc(c.label)}</b>${na}${fix}</div></li>`;
      }).join('');
      return `<section><h3>${medal(tier)}<span>${esc(TIER_NOTE[tier])}</span></h3><ul>${items}</ul></section>`;
    }).join('');
    const issue = p && safeUrl(p.r.gold_issue);
    const head = p
      ? `<div class="dlg-id">${symbol(p.folder, p.name, 'lg')}<div><h2>${esc(p.name)}</h2><span class="mono faint">${esc(p.folder)}/</span></div>${medal(rating.tier, rating.score)}</div>
         <div class="meter" role="img" aria-label="${rating.score}% of the checklist met"><span class="${rating.tier}" style="width:${Math.max(0, Math.min(100, rating.score))}%"></span></div>
         <p class="muted">${rating.tier === 'gold' ? 'Meets the whole BLT gold standard.' : `${rating.missing.length} step${rating.missing.length === 1 ? '' : 's'} to the gold standard.`}</p>`
      : `<div class="dlg-id"><div><h2>How ratings work</h2></div></div>
         <p class="muted">Every project is checked daily against one checklist, read from its folder in the monorepo and from the forge. A project is <b>gold</b> when it meets every check that applies to it, <b>silver</b> when it meets all the bronze and silver checks, and <b>bronze</b> otherwise. Site checks apply only to projects that deploy to Cloudflare.</p>`;
    const foot = p
      ? `<a class="btn primary" href="${esc(issue || issuesUrl(p.r))}" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-circle-dot" aria-hidden="true"></i>${issue ? 'Gold-standard issue' : 'Project issues'}</a>`
      : `<a class="btn" href="${FORGE}/issues?label=gold-standard" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-circle-dot" aria-hidden="true"></i>All gold-standard issues</a>`;
    dlg.innerHTML = `<div class="dlg-in" role="document">
      <button type="button" class="dlg-x" data-close aria-label="Close"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
      ${head}<div class="crits">${sections}</div>
      <div class="dlg-foot">${foot}<button type="button" class="btn" data-close>Close</button></div></div>`;
    dlg.showModal();
  }

  /* ================================================================ */
  /*  DASHBOARD                                                        */
  /* ================================================================ */
  function dashboard() {
    const results = $('#results');
    const search = $('#search');
    const sortSel = $('#sort');
    const filtersEl = $('#filters');
    const countEl = $('#count');

    const SORTS = {
      last: { dir: -1, get: p => p.last ?? -Infinity },
      name: { dir: 1, get: p => p.name.toLowerCase() },
      issues: { dir: -1, get: p => p.issues },
      prs: { dir: -1, get: p => p.prs },
      c30: { dir: -1, get: p => p.c30 },
      c365: { dir: -1, get: p => p.c365 },
      people: { dir: -1, get: p => p.people },
      rating: { dir: -1, get: p => p.rank * 1000 + p.score },
    };
    const STATUS = [
      ['all', 'All', null],
      ['active', 'Active', 'Commit in the last 30 days'],
      ['quiet', 'Quiet', 'Last commit 30 to 180 days ago'],
      ['dormant', 'Dormant', 'No commit for 180 days'],
    ];
    const TOGGLES = [
      ['live', 'Live site', 'fa-globe'],
      ['issues', 'Open issues', 'fa-circle-dot'],
      ['prs', 'Open PRs', 'fa-code-pull-request'],
    ];

    const p0 = params();
    const state = {
      q: p0.get('q') || '',
      status: STATUS.some(s => s[0] === p0.get('status')) ? p0.get('status') : 'all',
      toggles: new Set((p0.get('has') || '').split(',').filter(t => TOGGLES.some(x => x[0] === t))),
      tier: TIERS[p0.get('tier')] ? p0.get('tier') : '',
      sort: SORTS[p0.get('sort')] ? p0.get('sort') : (SORTS[store.get('waypoint-sort')] ? store.get('waypoint-sort') : 'last'),
      dir: 0,
      view: p0.get('view') || store.get('waypoint-view', matchMedia('(max-width: 720px)').matches ? 'cards' : 'table'),
    };
    if (!['table', 'cards'].includes(state.view)) state.view = 'table';
    state.dir = SORTS[state.sort].dir;
    search.value = state.q;
    sortSel.value = state.sort;

    let projects = [];
    let criteria = [];

    function toProject(r, shots) {
      const last = ts(r.last_commit_at) ?? ts(r.pushed_at);
      const days = last == null ? Infinity : (NOW - last) / DAY;
      const live = liveUrl(r);
      const rating = r.rating && TIERS[r.rating.tier] ? r.rating : null;
      return {
        r,
        rating,
        tier: rating ? rating.tier : '',
        rank: rating ? TIER_RANK[rating.tier] : 0,
        score: rating ? +rating.score || 0 : 0,
        folder: r.folder,
        name: r.name || r.folder,
        desc: r.description || '',
        live,
        liveHost: host(live),
        last,
        status: days <= 30 ? 'active' : days <= 180 ? 'quiet' : 'dormant',
        issues: r.open_issues_count || 0,
        prs: r.open_pr_count || 0,
        c30: r.commits_30d || 0,
        c365: r.commits_365d || 0,
        people: r.contributor_count || 0,
        weeks: r.weekly_commits,
        commit: r.latest_commit,
        shot: shots && shots.shots ? shots.shots[r.folder] : null,
        text: [r.name, r.folder, r.description, live, r.latest_commit && r.latest_commit.message].join(' ').toLowerCase(),
      };
    }

    function renderStats(data) {
      const sum = key => projects.reduce((a, p) => a + p[key], 0);
      const issues = Array.isArray(data.open_issues) ? data.open_issues.length : sum('issues');
      $('#stats').innerHTML = [
        stat('fa-folder', num(projects.length), 'Projects'),
        stat('fa-bolt', num(projects.filter(p => p.status === 'active').length), 'Active', 'Projects with a commit in the last 30 days'),
        stat('fa-globe', num(projects.filter(p => p.live).length), 'Live sites', 'Projects with a live site'),
        stat('fa-circle-dot', num(issues), 'Open issues'),
        stat('fa-code-pull-request', num(sum('prs')), 'Open PRs'),
        stat('fa-code-commit', num(sum('c30')), 'Commits 30d', 'Commits in the last 30 days, all folders'),
        `<button type="button" class="stat stat-rate" data-how title="How ratings work">${Object.keys(TIERS).map(t =>
          `<b class="t-${t}" title="${TIERS[t]}">${medalSvg(t, 18)}${num(projects.filter(p => p.tier === t).length)}</b>`).join('')}<span><i class="fa-solid fa-circle-info" aria-hidden="true"></i>Gold · silver · bronze</span></button>`,
      ].join('');
    }

    function renderFilters() {
      const count = fn => projects.filter(fn).length;
      const statusChips = STATUS.map(([key, label, title]) => {
        const n = key === 'all' ? projects.length : count(p => p.status === key);
        const dot = key === 'all' ? '' : `<span class="dot ${key}" aria-hidden="true"></span>`;
        return `<button type="button" class="chip" data-status="${key}" aria-pressed="${state.status === key}"${title ? ` title="${title}"` : ''}>${dot}${label} <span class="n">${n}</span></button>`;
      });
      const toggleChips = TOGGLES.map(([key, label, icon]) => {
        const n = count(p => (key === 'live' ? !!p.live : p[key] > 0));
        return `<button type="button" class="chip" data-toggle="${key}" aria-pressed="${state.toggles.has(key)}"><i class="fa-solid ${icon}" aria-hidden="true"></i>${label} <span class="n">${n}</span></button>`;
      });
      const tierChips = Object.keys(TIERS).map(t => `<button type="button" class="chip" data-tier="${t}" aria-pressed="${state.tier === t}">${medalSvg(t, 14)}${TIERS[t]} <span class="n">${count(p => p.tier === t)}</span></button>`);
      filtersEl.innerHTML = statusChips.join('') + '<span class="sep" aria-hidden="true"></span>' + toggleChips.join('') +
        '<span class="sep" aria-hidden="true"></span>' + tierChips.join('') +
        '<button type="button" class="chip ghost" data-how title="How ratings work"><i class="fa-regular fa-circle-question" aria-hidden="true"></i>Ratings</button>';
    }

    function visible() {
      const words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
      const { get } = SORTS[state.sort];
      return projects
        .filter(p => state.status === 'all' || p.status === state.status)
        .filter(p => [...state.toggles].every(t => (t === 'live' ? !!p.live : p[t] > 0)))
        .filter(p => !state.tier || p.tier === state.tier)
        .filter(p => words.every(w => p.text.includes(w)))
        .sort((a, b) => {
          const x = get(a), y = get(b);
          const c = x < y ? -1 : x > y ? 1 : 0;
          return c * state.dir || a.name.localeCompare(b.name);
        });
    }

    function issuesCell(p) {
      return p.issues
        ? `<a class="count" href="${esc(issuesUrl(p.r))}" target="_blank" rel="noopener noreferrer" title="Open issues of ${esc(p.folder)} on the forge">${p.issues}</a>`
        : `<a class="count zero" href="${esc(issuesUrl(p.r))}" target="_blank" rel="noopener noreferrer" title="No open issues; open the issue list">0</a>`;
    }

    function prsCell(p) {
      const latest = p.r.latest_pr && safeUrl(p.r.latest_pr.html_url);
      return p.prs
        ? `<a class="count" href="${esc(latest || `${FORGE}/pulls`)}" target="_blank" rel="noopener noreferrer">${p.prs}</a>`
        : '<span class="zero">0</span>';
    }

    function lastCommit(p) {
      if (p.last == null) return '<span class="faint">No commits</span>';
      const c = p.commit;
      const title = `${fullDate(p.last)}${c && c.message ? ` · ${c.message}` : ''}`;
      return `<span title="${esc(title)}"><span class="dot ${p.status}" aria-hidden="true"></span>${esc(ago(p.last))}</span>`;
    }

    function th(key, label, cls) {
      const sorted = state.sort === key;
      const aria = sorted ? ` aria-sort="${state.dir > 0 ? 'ascending' : 'descending'}"` : '';
      const arrow = sorted ? `<i class="fa-solid fa-arrow-${state.dir > 0 ? 'up' : 'down'} arrow" aria-hidden="true"></i>` : '';
      return `<th scope="col" class="${cls}"${aria}><button type="button" data-sort="${key}">${label}${arrow}</button></th>`;
    }

    function tableHTML(list) {
      const rows = list.map(p => `
        <tr>
          <td>
            <div class="proj">
              ${symbol(p.folder, p.name)}
              <div class="proj-main">
                <div class="proj-name"><a href="${esc(folderUrl(p.folder))}" target="_blank" rel="noopener noreferrer">${esc(p.name)}</a><span class="mono">${esc(p.folder)}/</span></div>
                <div class="proj-desc" title="${esc(p.desc)}">${esc(p.desc) || '<span class="faint">No description</span>'}</div>
                ${p.live ? `<a class="proj-live-m" href="${esc(p.live)}" target="_blank" rel="noopener noreferrer">${esc(p.liveHost)}</a>` : ''}
              </div>
            </div>
          </td>
          <td class="c-rate">${medal(p.tier, p.score, p.rating ? p.folder : '')}</td>
          <td class="c-site">${p.live
            ? `<div class="site">${thumb(p.live, p.shot, p.name)}<a class="host" href="${esc(p.live)}" target="_blank" rel="noopener noreferrer" title="${esc(p.live)}">${esc(p.liveHost)}</a></div>`
            : `<span class="faint">–</span>`}</td>
          <td><div class="last">${lastCommit(p)}${sparkline(p.weeks)}</div></td>
          <td class="num c-30d">${p.c30 || '<span class="zero">0</span>'}</td>
          <td class="num c-1y">${p.c365 || '<span class="zero">0</span>'}</td>
          <td class="num">${issuesCell(p)}</td>
          <td class="num c-prs">${prsCell(p)}</td>
          <td class="num c-people">${p.people || '<span class="zero">0</span>'}</td>
        </tr>`).join('');
      return `<div class="panel"><table class="tbl">
        <thead><tr>
          ${th('name', 'Project', '')}
          ${th('rating', 'Rating', 'c-rate w-rate')}
          <th scope="col" class="c-site w-site">Live site</th>
          ${th('last', 'Last commit', 'w-last')}
          ${th('c30', '30d', 'num w-n c-30d')}
          ${th('c365', '1y', 'num w-n c-1y')}
          ${th('issues', 'Issues', 'num w-n')}
          ${th('prs', 'PRs', 'num w-n c-prs')}
          ${th('people', 'People', 'num w-n c-people')}
        </tr></thead>
        <tbody>${rows}</tbody></table></div>`;
    }

    function cardHTML(p) {
      const c = p.commit;
      const commitLine = c && c.message
        ? `<a class="commit" href="${esc(safeUrl(c.html_url) || folderUrl(p.folder))}" target="_blank" rel="noopener noreferrer" title="${esc(c.message)}"><i class="fa-solid fa-code-commit" aria-hidden="true"></i> ${esc(c.message)}</a>`
        : '<span class="commit faint">No commits yet</span>';
      return `<article class="card">
        <div class="card-top">
          ${thumb(p.live, p.shot, p.name)}
          <div class="card-id">
            <div class="row">${symbol(p.folder, p.name)}<h2><a href="${esc(folderUrl(p.folder))}" target="_blank" rel="noopener noreferrer">${esc(p.name)}</a></h2>${p.rating ? medal(p.tier, p.score, p.folder) : ''}</div>
            <span class="mono faint">${esc(p.folder)}/</span>
            ${p.live ? `<a class="host ellipsis" href="${esc(p.live)}" target="_blank" rel="noopener noreferrer">${esc(p.liveHost)} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:9px" aria-hidden="true"></i></a>` : '<span class="none">No live site</span>'}
          </div>
        </div>
        <p class="desc">${esc(p.desc) || '<span class="faint">No description</span>'}</p>
        <dl class="facts">
          <div><dt>Last commit</dt><dd title="${p.last != null ? `${esc(p.status)} · ${esc(fullDate(p.last))}` : 'No commits'}"><span class="dot ${p.status}" aria-hidden="true"></span> ${p.last != null ? esc(ago(p.last)) : '–'}</dd></div>
          <div><dt>Issues</dt><dd><a href="${esc(issuesUrl(p.r))}" target="_blank" rel="noopener noreferrer">${p.issues}</a></dd></div>
          <div><dt>PRs</dt><dd>${p.prs}</dd></div>
          <div><dt>Commits 30d</dt><dd title="${p.c365} commits in a year">${p.c30}</dd></div>
        </dl>
        <div class="card-foot">${commitLine}
          <span class="links"><a href="${esc(issuesUrl(p.r))}" target="_blank" rel="noopener noreferrer" title="Issues on the forge"><i class="fa-solid fa-circle-dot" aria-hidden="true"></i><span class="sr-only">Issues</span></a>
          <a href="${esc(folderUrl(p.folder))}" target="_blank" rel="noopener noreferrer" title="Folder on the forge"><i class="fa-solid fa-folder-open" aria-hidden="true"></i><span class="sr-only">Folder</span></a></span>
        </div>
      </article>`;
    }

    function render() {
      $$('.seg [data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === state.view)));
      $$('[data-status]', filtersEl).forEach(b => b.setAttribute('aria-pressed', String(b.dataset.status === state.status)));
      $$('[data-toggle]', filtersEl).forEach(b => b.setAttribute('aria-pressed', String(state.toggles.has(b.dataset.toggle))));
      $$('[data-tier]', filtersEl).forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tier === state.tier)));
      const list = visible();
      const filteredOut = list.length !== projects.length;
      countEl.innerHTML = `${list.length} of ${projects.length} projects${filteredOut ? ' · <button type="button" data-clear>Clear filters</button>' : ''}`;
      results.textContent = '';
      if (!list.length) {
        results.append(emptyState('No project matches these filters', clear));
      } else if (state.view === 'cards') {
        results.innerHTML = `<div class="cards">${list.map(cardHTML).join('')}</div>`;
      } else {
        results.innerHTML = tableHTML(list);
      }
      setParams({
        q: state.q,
        status: state.status === 'all' ? '' : state.status,
        has: [...state.toggles].join(','),
        tier: state.tier,
        sort: state.sort === 'last' ? '' : state.sort,
      });
    }

    function clear() {
      state.q = ''; search.value = '';
      state.status = 'all';
      state.toggles.clear();
      state.tier = '';
      render();
    }

    function setSort(key, dir) {
      state.sort = key;
      state.dir = dir ?? SORTS[key].dir;
      sortSel.value = key;
      store.set('waypoint-sort', key);
      render();
    }

    search.addEventListener('input', debounce(() => { state.q = search.value.trim(); render(); }, 150));
    sortSel.addEventListener('change', () => setSort(sortSel.value));
    filtersEl.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.status) state.status = b.dataset.status;
      if (b.dataset.toggle) state.toggles[state.toggles.has(b.dataset.toggle) ? 'delete' : 'add'](b.dataset.toggle);
      if (b.dataset.tier) state.tier = state.tier === b.dataset.tier ? '' : b.dataset.tier;
      if (b.dataset.how != null) { ratingDialog(criteria); return; }
      render();
    });
    $$('.seg [data-view]').forEach(b => b.addEventListener('click', () => {
      state.view = b.dataset.view;
      store.set('waypoint-view', state.view);
      render();
    }));
    document.addEventListener('click', e => {
      const rate = e.target.closest('[data-rate]');
      if (rate) { const p = projects.find(x => x.folder === rate.dataset.rate); if (p && p.rating) ratingDialog(criteria, p); }
      else if (e.target.closest('#stats [data-how]')) ratingDialog(criteria);
    });
    results.addEventListener('click', e => {
      const b = e.target.closest('th button[data-sort]');
      if (!b) return;
      const key = b.dataset.sort;
      setSort(key, state.sort === key ? -state.dir : SORTS[key].dir);
    });
    countEl.addEventListener('click', e => { if (e.target.closest('[data-clear]')) clear(); });

    async function load() {
      try {
        const [data, shots] = await Promise.all([loadForge(), loadShots()]);
        projects = (data.repos || []).filter(r => r && r.folder).map(r => toProject(r, shots));
        criteria = Array.isArray(data.rating_criteria) ? data.rating_criteria : [];
        showFreshness(data.generated_at);
        renderStats(data);
        renderFilters();
        render();
      } catch (err) {
        $('#stats').textContent = '';
        countEl.textContent = '';
        errorState(results, err.message, load);
      }
    }
    load();
  }

  /* ================================================================ */
  /*  ISSUES                                                           */
  /* ================================================================ */
  function issuesPage() {
    const results = $('#results');
    const search = $('#search');
    const projectSel = $('#project');
    const sortSel = $('#sort');
    const groupBtn = $('#group');
    const labelsEl = $('#labels');
    const countEl = $('#count');
    const GENERAL = '_general';

    const p0 = params();
    const state = {
      q: p0.get('q') || '',
      project: p0.get('project') || '',
      labels: new Set((p0.get('label') || '').split(',').filter(Boolean)),
      sort: ['updated', 'newest', 'oldest', 'comments'].includes(p0.get('sort')) ? p0.get('sort') : 'updated',
      group: p0.get('group') === '1',
    };
    search.value = state.q;
    sortSel.value = state.sort;

    let issues = [];
    let names = {};
    let repoByFolder = {};

    function toIssue(i, folders) {
      const labels = (i.labels || []).map(l => (typeof l === 'string' ? l : l && l.name)).filter(Boolean);
      const folder = i.folder || labels.find(l => folders.has(l)) || '';
      const shown = labels.filter(l => l !== folder);
      // Titles often repeat the project ("blt-leaf: …", "[blt-leaf] …"); the project chip already says it.
      const title = folder
        ? String(i.title || '').replace(new RegExp(`^\\s*\\[?${folder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\]?\\s*:?\\s*`, 'i'), '') || i.title
        : i.title;
      const user = i.user && i.user.login ? i.user.login : '';
      return {
        number: i.number,
        title: title || '(no title)',
        fullTitle: i.title || '',
        url: safeUrl(i.html_url) || `${FORGE}/issues/${encodeURIComponent(i.number)}`,
        folder: folder || GENERAL,
        labels: shown,
        user,
        assignees: (i.assignees || []).map(a => a && a.login).filter(Boolean),
        comments: i.comments || 0,
        votes: i.votes || 0,
        prs: (i.linked_prs || []).length,
        created: ts(i.created_at),
        updated: ts(i.updated_at) ?? ts(i.created_at),
        text: [i.title, `#${i.number}`, user, folder, ...labels].join(' ').toLowerCase(),
      };
    }

    const projectName = f => (f === GENERAL ? 'General' : names[f] || f);

    function labelClass(l) {
      const k = l.toLowerCase();
      if (k === 'good first issue') return 'lbl gfi';
      if (k === 'bug') return 'lbl bug';
      if (k === 'hacktoberfest') return 'lbl hf';
      return 'lbl';
    }

    function renderControls() {
      const counts = {};
      issues.forEach(i => { counts[i.folder] = (counts[i.folder] || 0) + 1; });
      const folders = Object.keys(counts).sort((a, b) => (a === GENERAL) - (b === GENERAL) || projectName(a).localeCompare(projectName(b)));
      projectSel.innerHTML = `<option value="">All projects (${issues.length})</option>` +
        folders.map(f => `<option value="${esc(f)}">${esc(projectName(f))} (${counts[f]})</option>`).join('');
      if (state.project && !counts[state.project]) state.project = '';
      projectSel.value = state.project;

      const labelCounts = {};
      // Project labels are what the project picker is for; the chips offer the topic labels.
      issues.forEach(i => i.labels.forEach(l => { if (!names[l]) labelCounts[l] = (labelCounts[l] || 0) + 1; }));
      const top = Object.entries(labelCounts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 10);
      state.labels.forEach(l => { if (!labelCounts[l] && !issues.some(i => i.labels.includes(l))) state.labels.delete(l); });
      labelsEl.innerHTML = top.map(([l, n]) =>
        `<button type="button" class="chip" data-label="${esc(l)}" aria-pressed="${state.labels.has(l)}">${esc(l)} <span class="n">${n}</span></button>`).join('');

      const gfi = labelCounts['good first issue'] || 0;
      const unassigned = issues.filter(i => !i.assignees.length).length;
      $('#stats').innerHTML = [
        stat('fa-circle-dot', num(issues.length), 'Open issues'),
        stat('fa-folder', num(folders.filter(f => f !== GENERAL).length), 'Projects', 'Projects with open issues'),
        stat('fa-seedling', num(gfi), 'Good first', 'Issues labelled good first issue'),
        stat('fa-user-plus', num(unassigned), 'Unassigned', 'Open issues nobody is assigned to'),
      ].join('');
    }

    function visible() {
      const words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
      const by = {
        updated: (a, b) => (b.updated ?? 0) - (a.updated ?? 0),
        newest: (a, b) => (b.created ?? 0) - (a.created ?? 0) || b.number - a.number,
        oldest: (a, b) => (a.created ?? 0) - (b.created ?? 0) || a.number - b.number,
        comments: (a, b) => b.comments - a.comments || (b.updated ?? 0) - (a.updated ?? 0),
      }[state.sort];
      return issues
        .filter(i => !state.project || i.folder === state.project)
        .filter(i => [...state.labels].every(l => i.labels.includes(l)))
        .filter(i => words.every(w => i.text.includes(w)))
        .sort(by);
    }

    function rowHTML(i, showProject) {
      const labels = i.labels.map(l => `<span class="${labelClass(l)}">${esc(l)}</span>`).join('');
      const proj = showProject
        ? `<button type="button" class="proj-chip" data-project="${esc(i.folder)}" title="Only ${esc(projectName(i.folder))}">${i.folder === GENERAL ? symbol('', 'BLT') : symbol(i.folder, projectName(i.folder))}${esc(projectName(i.folder))}</button>`
        : '';
      const meta = [
        `<span class="mono">#${esc(i.number)}</span>`,
        `<span title="${esc(fullDate(i.created))}">opened ${esc(ago(i.created))}${i.user ? ` by ${esc(i.user)}` : ''}</span>`,
        i.updated && i.updated !== i.created ? `<span class="hide-sm" title="${esc(fullDate(i.updated))}">updated ${esc(ago(i.updated))}</span>` : '',
        i.comments ? `<span title="${i.comments} comments"><i class="fa-regular fa-comment" aria-hidden="true"></i>${i.comments}</span>` : '',
        i.prs ? `<span title="Linked pull requests"><i class="fa-solid fa-code-pull-request" aria-hidden="true"></i>${i.prs}</span>` : '',
        i.votes ? `<span title="Votes"><i class="fa-solid fa-thumbs-up" aria-hidden="true"></i>${i.votes}</span>` : '',
        i.assignees.length
          ? `<span title="Assigned"><i class="fa-solid fa-user-check" aria-hidden="true"></i>${esc(i.assignees.join(', '))}</span>`
          : '',
      ].filter(Boolean).join('');
      return `<li class="issue"><i class="fa-regular fa-circle-dot" aria-hidden="true"></i>
        <div class="issue-body">
          <div class="issue-title"><a href="${esc(i.url)}" target="_blank" rel="noopener noreferrer" title="${esc(i.fullTitle)}">${esc(i.title)}</a>${labels}</div>
          <div class="issue-meta">${proj}${meta}</div>
        </div></li>`;
    }

    function render() {
      projectSel.value = state.project;
      $$('[data-label]', labelsEl).forEach(b => b.setAttribute('aria-pressed', String(state.labels.has(b.dataset.label))));
      groupBtn.setAttribute('aria-pressed', String(state.group));
      const list = visible();
      const filteredOut = list.length !== issues.length;
      countEl.innerHTML = `${list.length} of ${issues.length} open issues${filteredOut ? ' · <button type="button" data-clear>Clear filters</button>' : ''}`;
      results.textContent = '';
      if (!list.length) {
        results.append(issues.length ? emptyState('No issue matches these filters', clear) : emptyState('No open issues'));
      } else if (state.group && !state.project) {
        const groups = new Map();
        list.forEach(i => { if (!groups.has(i.folder)) groups.set(i.folder, []); groups.get(i.folder).push(i); });
        const ordered = [...groups.entries()].sort((a, b) => b[1].length - a[1].length || projectName(a[0]).localeCompare(projectName(b[0])));
        results.innerHTML = `<div class="panel">${ordered.map(([f, items]) => {
          const repo = repoByFolder[f];
          const more = f === GENERAL ? `${FORGE}/issues` : repo ? issuesUrl(repo) : `${FORGE}/issues?label=${encodeURIComponent(f)}`;
          return `<section><div class="group-head">${f === GENERAL ? symbol('', 'BLT') : symbol(f, projectName(f))}${esc(projectName(f))} <span class="n">${items.length}</span>
            <a class="more" href="${esc(more)}" target="_blank" rel="noopener noreferrer">On the forge <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:9px" aria-hidden="true"></i></a></div>
            <ul class="issues">${items.map(i => rowHTML(i, false)).join('')}</ul></section>`;
        }).join('')}</div>`;
      } else {
        results.innerHTML = `<div class="panel"><ul class="issues">${list.map(i => rowHTML(i, !state.project)).join('')}</ul></div>`;
      }
      setParams({
        q: state.q,
        project: state.project,
        label: [...state.labels].join(','),
        sort: state.sort === 'updated' ? '' : state.sort,
        group: state.group ? '1' : '',
      });
    }

    function clear() {
      state.q = ''; search.value = '';
      state.project = '';
      state.labels.clear();
      render();
    }

    search.addEventListener('input', debounce(() => { state.q = search.value.trim(); render(); }, 150));
    projectSel.addEventListener('change', () => { state.project = projectSel.value; render(); });
    sortSel.addEventListener('change', () => { state.sort = sortSel.value; render(); });
    groupBtn.addEventListener('click', () => { state.group = !state.group; if (state.group) state.project = ''; render(); });
    labelsEl.addEventListener('click', e => {
      const b = e.target.closest('[data-label]');
      if (!b) return;
      state.labels[state.labels.has(b.dataset.label) ? 'delete' : 'add'](b.dataset.label);
      render();
    });
    results.addEventListener('click', e => {
      const b = e.target.closest('[data-project]');
      if (!b) return;
      state.project = b.dataset.project;
      state.group = false;
      render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    countEl.addEventListener('click', e => { if (e.target.closest('[data-clear]')) clear(); });

    async function load() {
      try {
        const data = await loadForge();
        const repos = (data.repos || []).filter(r => r && r.folder);
        names = Object.fromEntries(repos.map(r => [r.folder, r.name || r.folder]));
        repoByFolder = Object.fromEntries(repos.map(r => [r.folder, r]));
        const folders = new Set(Object.keys(names));
        issues = (data.open_issues || []).map(i => toIssue(i, folders));
        showFreshness(data.generated_at);
        renderControls();
        render();
      } catch (err) {
        $('#stats').textContent = '';
        countEl.textContent = '';
        errorState(results, err.message, load);
      }
    }
    load();
  }

  /* ================================================================ */
  /*  SCREENSHOTS                                                      */
  /* ================================================================ */
  function screenshotsPage() {
    const results = $('#results');
    const search = $('#search');
    const sortSel = $('#sort');
    const countEl = $('#count');
    const p0 = params();
    const state = { q: p0.get('q') || '', sort: p0.get('sort') === 'captured' ? 'captured' : 'name' };
    search.value = state.q;
    sortSel.value = state.sort;
    let sites = [];

    function cardHTML(s) {
      const when = s.captured != null
        ? `<span class="when" title="Captured ${esc(fullDate(s.captured))}">${esc(ago(s.captured))}</span>`
        : '<span class="when">pending</span>';
      return `<a class="shot" href="${esc(s.live)}" target="_blank" rel="noopener noreferrer" title="Open ${esc(s.live)}">
        <span class="thumb">${shotImg(s.shot, s.name) || placeholder('pending')}</span>
        <span class="shot-body">${symbol(s.folder, s.name, 'lg')}
          <span class="txt"><b>${esc(s.name)}${s.tier ? ` <span title="${TIERS[s.tier]}">${medalSvg(s.tier, 14)}</span>` : ''}</b><span class="host">${esc(host(s.live))}</span></span>${when}</span>
      </a>`;
    }

    function render() {
      const words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
      const list = sites
        .filter(s => words.every(w => s.text.includes(w)))
        .sort(state.sort === 'captured'
          ? (a, b) => (b.captured ?? 0) - (a.captured ?? 0) || a.name.localeCompare(b.name)
          : (a, b) => a.name.localeCompare(b.name));
      const captured = sites.filter(s => shotUrl(s.shot)).length;
      countEl.textContent = `${list.length} of ${sites.length} live sites · ${captured} captured`;
      results.textContent = '';
      if (!list.length) {
        results.append(sites.length
          ? emptyState('No site matches this search', () => { state.q = ''; search.value = ''; render(); })
          : emptyState('No project lists a live site yet'));
      } else {
        results.innerHTML = list.map(cardHTML).join('');
      }
      setParams({ q: state.q, sort: state.sort === 'name' ? '' : state.sort });
    }

    search.addEventListener('input', debounce(() => { state.q = search.value.trim(); render(); }, 150));
    sortSel.addEventListener('change', () => { state.sort = sortSel.value; render(); });

    async function load() {
      const [forge, shots] = await Promise.all([loadForge().catch(() => null), loadShots()]);
      if (!forge && !shots) {
        countEl.textContent = '';
        results.className = '';
        errorState(results, 'Neither forge_data.json nor the screenshot index could be read.', () => { results.className = 'shots'; load(); });
        return;
      }
      results.className = 'shots';
      const map = new Map();
      (forge && forge.repos || []).forEach(r => {
        const live = liveUrl(r);
        if (r && r.folder && live) map.set(r.folder, { folder: r.folder, name: r.name || r.folder, live, tier: r.rating && TIERS[r.rating.tier] ? r.rating.tier : '' });
      });
      Object.entries(shots ? shots.shots : {}).forEach(([folder, shot]) => {
        const site = map.get(folder) || { folder, name: folder, live: safeUrl(shot.live_url) };
        site.shot = shot;
        if (!site.live) site.live = safeUrl(shot.live_url);
        if (site.live) map.set(folder, site);
      });
      sites = [...map.values()].map(s => ({
        ...s,
        captured: s.shot ? ts(s.shot.captured_at) : null,
        text: [s.name, s.folder, s.live].join(' ').toLowerCase(),
      }));

      if (shots && ts(shots.generated_at) != null) {
        $('#sub').innerHTML = `Every BLT project with a live site. Captured once a day, last on <time datetime="${esc(shots.generated_at)}">${esc(fullDate(shots.generated_at))}</time>.`;
      }
      $('#notice').innerHTML = shots ? '' : `<div class="notice"><i class="fa-solid fa-hourglass-half" aria-hidden="true"></i>
        <span>The daily screenshot capture has not run yet, so every site shows a placeholder for now. Click a card to open the site.</span></div>`;
      if (forge) showFreshness(forge.generated_at);
      else if (shots) showFreshness(shots.generated_at, 'Screenshots');
      render();
    }
    load();
  }

  const page = document.body.dataset.page;
  if (page === 'dashboard') dashboard();
  else if (page === 'issues') issuesPage();
  else if (page === 'screenshots') screenshotsPage();
})();
