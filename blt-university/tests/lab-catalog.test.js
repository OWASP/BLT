/** @jest-environment jsdom */

const fs = require('node:fs');
const path = require('node:path');

const SCRIPT_PATH = path.join(__dirname, '..', 'assets', 'js', 'main.js');

function loadMainScript() {
  const runScript = new Function(
    'window',
    'document',
    'localStorage',
    fs.readFileSync(SCRIPT_PATH, 'utf8')
  );
  runScript(window, document, localStorage);
  document.dispatchEvent(new Event('DOMContentLoaded'));
}

describe('lab catalog learning-track filter', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    delete Element.prototype.scrollIntoView;
  });

  it('shows shared labs in either track and updates the accessible result summary', () => {
    document.body.innerHTML = `
      <select id="lab-category-filter"><option value="">All categories</option></select>
      <select id="lab-level-filter"><option value="">All levels</option></select>
      <input id="lab-search-filter">
      <p id="lab-results-summary"></p>
      <button data-track-choice="professional" data-track-label="Professional Security" aria-pressed="false"></button>
      <button data-track-choice="hygiene" data-track-label="Cyber Hygiene" aria-pressed="false"></button>
      <div id="lab-catalog"></div>
      <div id="labs-grid">
        <article id="professional-lab" class="lab-card" data-category="web-security" data-level="intermediate" data-track="professional" data-search="professional"></article>
        <article id="hygiene-lab" class="lab-card" data-category="cyber-hygiene" data-level="beginner" data-track="hygiene" data-search="hygiene"></article>
        <article id="shared-lab" class="lab-card" data-category="web-security" data-level="beginner" data-track="both" data-search="shared"></article>
      </div>
      <div id="lab-no-results" class="hidden"></div>
    `;
    Element.prototype.scrollIntoView = jest.fn();
    loadMainScript();

    const professionalChoice = document.querySelector('[data-track-choice="professional"]');
    const hygieneChoice = document.querySelector('[data-track-choice="hygiene"]');
    const professionalLab = document.getElementById('professional-lab');
    const hygieneLab = document.getElementById('hygiene-lab');
    const sharedLab = document.getElementById('shared-lab');
    const summary = document.getElementById('lab-results-summary');

    professionalChoice.click();

    expect(professionalChoice.getAttribute('aria-pressed')).toBe('true');
    expect(hygieneChoice.getAttribute('aria-pressed')).toBe('false');
    expect(professionalLab.classList.contains('hidden')).toBe(false);
    expect(hygieneLab.classList.contains('hidden')).toBe(true);
    expect(sharedLab.classList.contains('hidden')).toBe(false);
    expect(summary.textContent).toBe('Professional Security · Showing 2 labs');

    professionalChoice.click();

    expect(professionalChoice.getAttribute('aria-pressed')).toBe('false');
    expect(professionalLab.classList.contains('hidden')).toBe(false);
    expect(hygieneLab.classList.contains('hidden')).toBe(false);
    expect(sharedLab.classList.contains('hidden')).toBe(false);
    expect(summary.textContent).toBe('Showing 3 labs');
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledTimes(2);
  });
});
