/** @jest-environment jsdom */

const fs = require('node:fs');
const path = require('node:path');

const SCRIPT_PATH = path.join(__dirname, '..', 'assets', 'js', 'main.js');

function initializeMain() {
  const runScript = new Function(
    'window',
    'document',
    'localStorage',
    'URLSearchParams',
    fs.readFileSync(SCRIPT_PATH, 'utf8')
  );
  runScript(window, document, localStorage, URLSearchParams);
}

describe('shared page behavior', () => {
  beforeAll(() => {
    initializeMain();
  });

  beforeEach(() => {
    document.body.innerHTML = `
      <a data-return-course href="/university/courses/" class="hidden">Return to course</a>
    `;
  });

  afterEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('keeps the configured base URL when linking back to a course', () => {
    window.history.replaceState({}, '', '/university/labs/example/?course=cloud-security-essentials');

    document.dispatchEvent(new Event('DOMContentLoaded'));

    const link = document.querySelector('[data-return-course]');
    expect(link.getAttribute('href')).toBe('/university/courses/cloud-security-essentials/');
    expect(link.classList.contains('hidden')).toBe(false);
  });

  it('does not build a return URL from an invalid course slug', () => {
    window.history.replaceState({}, '', '/university/labs/example/?course=../../admin');

    document.dispatchEvent(new Event('DOMContentLoaded'));

    const link = document.querySelector('[data-return-course]');
    expect(link.getAttribute('href')).toBe('/university/courses/');
    expect(link.classList.contains('hidden')).toBe(true);
  });
});
