/**
 * Where the extension sends things. The old hosts (bugheist.com, blt.owasp.org) and the legacy
 * Django app (legacy.owaspblt.org, offline while its data is migrated) must not come back:
 * bug reports go through the new report page on next.owaspblt.org.
 */
const fs = require('fs');
const path = require('path');

const read = (file) => fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
const code = (file) => read(file).replace(/^\s*\/\/.*$/gm, ''); // ignore comments

describe('Backend endpoints', () => {
  const sources = ['event.js', 'background.js', 'popup.js', 'trademark-scanner.js', 'content.js'];

  it.each(sources)('%s does not call the old BLT hosts', (file) => {
    const src = code(file);
    expect(src).not.toMatch(/bugheist\.com/);
    expect(src).not.toMatch(/blt\.owasp\.org/);
    expect(src).not.toMatch(/legacy\.owaspblt\.org/);
  });

  it('opens the new report page with the page URL filled in', () => {
    const src = code('event.js');
    expect(src).toContain('var BLT_REPORT_PAGE = "https://next.owaspblt.org/pages/report-bug";');
    expect(src).toContain('BLT_REPORT_PAGE + "?url=" + encodeURIComponent(global_url || "")');
  });
});

describe('Trademark search', () => {
  let listener;

  beforeAll(() => {
    chrome.runtime.onMessage.addListener.mockClear();
    global.fetch = jest.fn();
    jest.isolateModules(() => require('../background.js'));
    listener = chrome.runtime.onMessage.addListener.mock.calls[0][0];
  });

  it('answers "not available yet" without a network request', () => {
    const sendResponse = jest.fn();
    const keepOpen = listener({ type: 'CHECK_TRADEMARK', keyword: 'TestBrand' }, {}, sendResponse);
    expect(keepOpen).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
    expect(sendResponse).toHaveBeenCalledWith({ ok: false, error: expect.stringContaining('not available yet') });
  });
});
