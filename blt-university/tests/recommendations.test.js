/** @jest-environment jsdom */

const fs = require('node:fs');
const path = require('node:path');

const SCRIPT_PATH = path.join(__dirname, '..', 'assets', 'js', 'recommendations.js');

function loadRecommendations(data, progress = {}) {
  const serializedData = JSON.stringify(data).replace(/<\//g, '<\\/');
  document.body.innerHTML = `<script id="adaptive-recommendation-data" type="application/json">${serializedData}</script>`;
  localStorage.setItem('blt-lab-progress', JSON.stringify(progress));
  const runScript = new Function('window', 'document', 'localStorage', fs.readFileSync(SCRIPT_PATH, 'utf8'));
  runScript(window, document, localStorage);
  return window.BltRecommendations;
}

describe('adaptive lab recommendations', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    localStorage.clear();
    delete window.BltRecommendations;
  });

  it('matches intelligence slugs to Jekyll ids and applies the configured scoring formula', () => {
    const recommendations = loadRecommendations({
      weights: { A01: 1, A03: 0.9 },
      categories: [
        { id: 'A01', count: 50, labs: [{ slug: 'insecure_direct_object_reference' }] },
        { id: 'A03', count: 100, labs: [{ slug: 'sql_injection' }] }
      ],
      labs: [
        { id: 'insecure-direct-object-reference', title: 'IDOR', url: '/idor/', taskCount: 2 },
        { id: 'sql-injection', title: 'SQL Injection', url: '/sqli/', taskCount: 2 }
      ]
    }, {
      'sql-injection': { 0: { completed: true } }
    });

    const ranked = recommendations.getRecommendations();

    expect(ranked.map(item => item.id)).toEqual(['insecure-direct-object-reference', 'sql-injection']);
    expect(ranked[0].score).toBeCloseTo(0.4 * 0.5 + 0.4 * 1 + 0.2 * 1);
    expect(ranked[1].score).toBeCloseTo(0.4 * 1 + 0.4 * 0.5 + 0.2 * 0.9);
  });

  it('normalizes the current lab id before excluding it and respects the result limit', () => {
    const recommendations = loadRecommendations({
      weights: {},
      categories: [],
      labs: [
        { id: 'sql-injection', title: 'SQL Injection', url: '/sqli/', taskCount: 2 },
        { id: 'open-redirect', title: 'Open Redirect', url: '/redirect/', taskCount: 2 },
        { id: 'phishing-awareness', title: 'Phishing Awareness', url: '/phishing/', taskCount: 2 }
      ]
    });

    const ranked = recommendations.getRecommendations({ currentLabId: 'sql_injection', limit: 1 });

    expect(ranked).toHaveLength(1);
    expect(ranked[0].id).not.toBe('sql-injection');
  });

  it('excludes completed labs even when their security priority is higher', () => {
    const recommendations = loadRecommendations({
      weights: { A01: 1, A10: 0.5 },
      categories: [
        { id: 'A01', count: 100, labs: [{ slug: 'completed_lab' }] },
        { id: 'A10', count: 1, labs: [{ slug: 'incomplete_lab' }] }
      ],
      labs: [
        { id: 'completed-lab', title: 'Completed Lab', url: '/completed/', taskCount: 1 },
        { id: 'incomplete-lab', title: 'Incomplete Lab', url: '/incomplete/', taskCount: 1 }
      ]
    }, {
      'completed-lab': { 0: { completed: true } }
    });

    const ranked = recommendations.getRecommendations();

    expect(ranked.map(item => item.id)).toEqual(['incomplete-lab']);
  });

  it('renders recommendation content as escaped text', () => {
    const recommendations = loadRecommendations({
      weights: {},
      categories: [],
      labs: [
        {
          id: 'safe-lab',
          title: '<img src=x onerror=alert(1)>',
          description: '<script>alert(1)</script>',
          url: '/safe-lab/',
          taskCount: 1
        }
      ]
    });
    const container = document.createElement('section');
    container.dataset.adaptiveRecommendations = '';
    document.body.append(container);

    recommendations.renderAll();

    expect(container.hidden).toBe(false);
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('<img src=x onerror=alert(1)>');
    expect(container.textContent).toContain('<script>alert(1)</script>');
  });

  it('returns no recommendations for malformed data shapes', () => {
    const recommendations = loadRecommendations({ categories: {}, labs: [] });

    expect(recommendations.getRecommendations()).toEqual([]);
  });

  it('ignores malformed category lab mappings', () => {
    const recommendations = loadRecommendations({
      weights: {},
      categories: [{ id: 'A01', count: 10, labs: [null, { slug: 'valid-lab' }] }],
      labs: [{ id: 'valid-lab', title: 'Valid Lab', url: '/valid/', taskCount: 1 }]
    });

    const ranked = recommendations.getRecommendations();

    expect(ranked).toHaveLength(1);
    expect(ranked[0].category).toMatchObject({ id: 'A01' });
  });
});
