/**
 * The extension talks to the legacy Django app (blt-legacy) on legacy.owaspblt.org.
 * bugheist.com and blt.owasp.org are old hosts and must not come back.
 */
const fs = require('fs');
const path = require('path');

const read = (file) => fs.readFileSync(path.join(__dirname, '..', file), 'utf8');

describe('Backend endpoints', () => {
  const sources = ['event.js', 'background.js', 'popup.js', 'trademark-scanner.js'];

  it.each(sources)('%s does not use the old bugheist.com or blt.owasp.org hosts', (file) => {
    const src = read(file);
    expect(src).not.toMatch(/bugheist\.com/);
    expect(src).not.toMatch(/blt\.owasp\.org/);
  });

  it('uploads screenshots to the legacy app upload route', () => {
    expect(read('event.js')).toContain('"https://legacy.owaspblt.org/upload/{time}/{hash}/"');
  });

  it('opens the legacy report page after an upload', () => {
    expect(read('event.js')).toContain("'https://legacy.owaspblt.org/report/?hash='");
  });

  it('searches trademarks on the legacy API (with the trailing slash Django expects)', () => {
    expect(read('background.js')).toContain('https://legacy.owaspblt.org/api/trademarks/search/?query=');
  });
});
