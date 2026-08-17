const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createCveCardHtml(index, overrides = {}) {
  const category = overrides.category || 'A03';
  const severity = overrides.severity || 'HIGH';
  const kev = overrides.kev || 'false';
  const search = overrides.search || `CVE-2026-${1000 + index} acme portal`;
  return `<article data-cve-card data-category="${category}" data-severity="${severity}" data-kev="${kev}" data-search="${search}"></article>`;
}

const chartCategories = [
  { id: 'A03', name: 'Injection', count: 30, known_exploited: 5, labs: [{ slug: 'sql_injection', title: 'SQL Injection', reason: 'Practise safe database queries.' }], monthly_counts: [{ month: '2026-05', count: 10, complete: true }, { month: '2026-06', count: 20, complete: true }, { month: '2026-07', count: 8, complete: false }] },
  { id: 'A01', name: 'Broken Access Control', count: 50, known_exploited: 4, labs: [{ slug: 'insecure_direct_object_reference', title: 'Insecure Direct Object Reference', reason: 'Practise object-level authorization.' }], monthly_counts: [{ month: '2026-05', count: 15, complete: true }, { month: '2026-06', count: 35, complete: true }, { month: '2026-07', count: 5, complete: false }] },
  { id: 'A02', name: 'Cryptographic Failures', count: 40, known_exploited: 2, labs: [{ slug: 'sensitive_data_exposure', title: 'Sensitive Data Exposure', reason: 'Protect sensitive information.' }], monthly_counts: [{ month: '2026-05', count: 22, complete: true }, { month: '2026-06', count: 18, complete: true }, { month: '2026-07', count: 2, complete: false }] },
  { id: 'A04', name: 'Insecure Design', count: 20, known_exploited: 1, labs: [], monthly_counts: [] },
  { id: 'A05', name: 'Security Misconfiguration', count: 10, known_exploited: 0, labs: [], monthly_counts: [] },
  { id: 'A06', name: 'Vulnerable Components', count: 5, known_exploited: 0, labs: [], monthly_counts: [] }
];

const labCatalog = [
  { slug: 'sql-injection', url: '/labs/sql_injection/', task_count: 3 },
  { slug: 'insecure-direct-object-reference', url: '/labs/insecure_direct_object_reference/', task_count: 2 },
  { slug: 'sensitive-data-exposure', url: '/labs/sensitive_data_exposure/', task_count: 2 }
];

function renderDashboard(chartConstructor) {
  document.body.innerHTML = `
    <main data-vulnerability-dashboard>
      <span data-format-number>12345</span>
      <div data-mini-chart="3,6,0" data-mini-chart-months="2026-05,2026-06,2026-07" data-mini-chart-complete="true,true,false"></div>
      <p class="hidden" data-chart-selection-status></p>
      <h2 id="categories-heading">Categories</h2>
      <select data-category-filter><option value="all">All</option><option value="A01">A01 · Broken Access Control</option><option value="A03">A03 · Injection</option></select>
      <div data-category-card="A03"></div><div data-category-card="A01"></div>
      <input data-cve-search>
      <select data-cve-category><option value="all">All</option><option value="A01">A01</option><option value="A03">A03</option></select>
      <select data-cve-severity><option value="all">All</option><option value="CRITICAL">Critical</option></select>
      <input data-cve-kev type="checkbox">
      <div>
        ${Array.from({ length: 9 }, (_, index) => createCveCardHtml(index, index === 0 ? { category: 'A01' } : {})).join('')}
        ${createCveCardHtml(10, { severity: 'CRITICAL', kev: 'true', search: 'CVE-2026-9999 special product' })}
      </div>
      <div class="hidden" data-cve-empty></div>
      <div><button data-cve-more></button></div>
      <canvas data-dashboard-chart="bar"></canvas><p class="hidden" data-chart-fallback="bar"></p>
      <canvas data-dashboard-chart="pie"></canvas><p class="hidden" data-chart-fallback="pie"></p>
      <canvas data-dashboard-chart="line"></canvas><p class="hidden" data-chart-fallback="line"></p>
      <article data-learning-recommendation>
        <span data-recommendation-category></span><h3 data-recommendation-title></h3><p data-recommendation-reason></p>
        <span data-recommendation-frequency></span><span data-recommendation-kev></span><span data-recommendation-progress></span><span data-recommendation-score></span>
        <a data-start-learning href="#">Start learning <i></i></a>
      </article>
    </main>
    <script id="dashboard-chart-data" type="application/json">${JSON.stringify({ categories: chartCategories, labs: labCatalog })}</script>`;

  const source = fs.readFileSync(path.join(__dirname, '..', '..', 'assets/js/dashboard.js'), 'utf8');
  const context = { document, Intl, Chart: chartConstructor };
  vm.runInNewContext(source, context);
}

function getVisibleCveCards() {
  return [...document.querySelectorAll('[data-cve-card]')].filter((element) => !element.classList.contains('hidden'));
}

describe('vulnerability dashboard interactions', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('formats large summary numbers for the page locale', () => {
    renderDashboard();

    expect(document.querySelector('[data-format-number]').textContent).toMatch(/12.345|12,345/);
  });

  it('renders one mini chart bar per month of CVE counts', () => {
    renderDashboard();

    expect(document.querySelectorAll('[data-mini-chart] span')).toHaveLength(3);
  });

  it('labels mini chart bars by month and marks partial months', () => {
    renderDashboard();

    const bars = [...document.querySelectorAll('[data-mini-chart] span')];
    expect(bars[0].title).toBe('2026-05: 3 CVEs');

    // The trailing month is only partly covered, so it must not read as a real drop.
    // The muted fill is the only cue for someone scanning the bars without hovering,
    // so it is pinned here alongside the hover text.
    expect(bars[2].title).toBe('2026-07: 0 CVEs (partial month)');
    expect(bars[2].className).toContain('bg-gray-200');
  });

  it('paginates the initial CVE list', () => {
    renderDashboard();

    expect(getVisibleCveCards()).toHaveLength(8);
    document.querySelector('[data-cve-more]').click();
    expect(document.querySelectorAll('[data-cve-card].hidden')).toHaveLength(0);
  });

  it('labels the show more button with the number of CVEs still hidden', () => {
    renderDashboard();

    expect(document.querySelector('[data-cve-more]').textContent).toBe('Show 2 more CVEs');
  });

  it('uses the singular CVE label when one result remains hidden', () => {
    renderDashboard();

    document.querySelectorAll('[data-cve-card]').forEach((card, index) => {
      card.dataset.search = index < 9 ? 'single-result-page' : 'other-result';
    });
    const searchInput = document.querySelector('[data-cve-search]');
    searchInput.value = 'single-result-page';
    searchInput.dispatchEvent(new Event('input'));

    expect(document.querySelector('[data-cve-more]').textContent).toBe('Show 1 more CVE');
  });

  it('shows only the CVEs whose text matches the search query', () => {
    renderDashboard();

    const searchInput = document.querySelector('[data-cve-search]');
    searchInput.value = 'special';
    searchInput.dispatchEvent(new Event('input'));

    const visibleCards = getVisibleCveCards();
    expect(visibleCards).toHaveLength(1);
    expect(visibleCards[0].dataset.search).toContain('CVE-2026-9999');
  });

  it('reveals the empty state when nothing matches and hides it once the search is cleared', () => {
    renderDashboard();

    const searchInput = document.querySelector('[data-cve-search]');
    const emptyState = document.querySelector('[data-cve-empty]');

    searchInput.value = 'no such advisory';
    searchInput.dispatchEvent(new Event('input'));
    expect(getVisibleCveCards()).toHaveLength(0);
    expect(emptyState.classList.contains('hidden')).toBe(false);

    searchInput.value = '';
    searchInput.dispatchEvent(new Event('input'));
    expect(emptyState.classList.contains('hidden')).toBe(true);
    expect(getVisibleCveCards()).toHaveLength(8);
  });

  it('combines severity and KEV filters', () => {
    renderDashboard();

    const severitySelect = document.querySelector('[data-cve-severity]');
    severitySelect.value = 'CRITICAL';
    severitySelect.dispatchEvent(new Event('change'));
    const kevCheckbox = document.querySelector('[data-cve-kev]');
    kevCheckbox.checked = true;
    kevCheckbox.dispatchEvent(new Event('change'));

    const visibleCards = getVisibleCveCards();
    expect(visibleCards).toHaveLength(1);
    expect(visibleCards[0].dataset.search).toContain('CVE-2026-9999');
  });

  it('filters category cards independently', () => {
    renderDashboard();

    const categoryFilterSelect = document.querySelector('[data-category-filter]');
    categoryFilterSelect.value = 'A03';
    categoryFilterSelect.dispatchEvent(new Event('change'));
    expect(document.querySelector('[data-category-card="A03"]').classList.contains('hidden')).toBe(false);
    expect(document.querySelector('[data-category-card="A01"]').classList.contains('hidden')).toBe(true);
  });

  it('renders the proposal bar, pie, and line charts from category data', () => {
    const chartCalls = [];
    function MockChart(element, configuration) {
      chartCalls.push({ element, configuration });
    }

    renderDashboard(MockChart);

    expect(chartCalls.map((chartCall) => chartCall.configuration.type)).toEqual(['bar', 'pie', 'line']);
    expect(chartCalls[0].configuration.data.labels).toEqual([
      'A01 · Broken Access Control',
      'A02 · Cryptographic Failures',
      'A03 · Injection',
      'A04 · Insecure Design',
      'A05 · Security Misconfiguration'
    ]);
    expect(chartCalls[1].configuration.data.labels).toHaveLength(chartCategories.length);
    expect(chartCalls[2].configuration.data.labels).toEqual(['May 2026', 'Jun 2026']);
    expect(chartCalls[2].configuration.data.datasets).toHaveLength(3);
  });

  it('uses chart selections to filter category cards and the CVE explorer', () => {
    const configurations = [];
    function MockChart(_element, configuration) {
      configurations.push(configuration);
    }
    renderDashboard(MockChart);

    configurations[0].options.onClick(null, [{ index: 0 }]);

    expect(document.querySelector('[data-category-filter]').value).toBe('A01');
    expect(document.querySelector('[data-cve-category]').value).toBe('A01');
    expect(document.querySelector('[data-category-card="A01"]').classList).not.toContain('hidden');
    expect(document.querySelector('[data-category-card="A03"]').classList).toContain('hidden');
    expect(getVisibleCveCards()).toHaveLength(1);
    expect(document.querySelector('[data-chart-selection-status]').textContent).toContain('Broken Access Control');

    configurations[1].options.onClick(null, [{ index: 2 }]);
    expect(document.querySelector('[data-recommendation-title]').textContent).toBe('SQL Injection');
    expect(document.querySelector('[data-start-learning]').getAttribute('href')).toBe('/labs/sql_injection/');
  });

  it('moves past a completed lab when choosing the next learning step', () => {
    localStorage.setItem('blt-lab-progress', JSON.stringify({
      'insecure-direct-object-reference': {
        0: { completed: true },
        1: { completed: true }
      }
    }));

    renderDashboard();

    expect(document.querySelector('[data-recommendation-title]').textContent).toBe('SQL Injection');
    expect(document.querySelector('[data-recommendation-progress]').textContent).toBe('0% complete');
    expect(document.querySelector('[data-start-learning]').getAttribute('href')).toBe('/labs/sql_injection/');
  });

  it('invites the learner to continue the only lab they have started but not finished', () => {
    localStorage.setItem('blt-lab-progress', JSON.stringify({
      'sql-injection': { 0: { completed: true }, 1: { completed: true }, 2: { completed: true } },
      'sensitive-data-exposure': { 0: { completed: true }, 1: { completed: true } },
      'insecure-direct-object-reference': { 0: { completed: true } }
    }));

    renderDashboard();

    expect(document.querySelector('[data-recommendation-title]').textContent).toBe('Insecure Direct Object Reference');
    expect(document.querySelector('[data-recommendation-progress]').textContent).toBe('50% complete');
    const startLink = document.querySelector('[data-start-learning]');
    expect(startLink.firstChild.textContent).toBe('Continue learning ');
    expect(startLink.getAttribute('href')).toBe('/labs/insecure_direct_object_reference/');
  });

  it('shows readable fallbacks when Chart.js is unavailable', () => {
    renderDashboard();

    ['bar', 'pie', 'line'].forEach((kind) => {
      expect(document.querySelector(`[data-dashboard-chart="${kind}"]`).classList).toContain('hidden');
      expect(document.querySelector(`[data-chart-fallback="${kind}"]`).classList).not.toContain('hidden');
    });
  });
});
