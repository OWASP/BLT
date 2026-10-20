#!/usr/bin/env node
// Regression test: public/index.html's escapeHtml must be safe in quoted attributes, and PR/repo
// values must not reach attributes or hrefs unescaped.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'public', 'index.html'), 'utf8');
const pick = (name) => {
  const m = html.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n        \\}`));
  assert.ok(m, `${name} not found`);
  return m[0];
};
const { escapeHtml, safeHttpUrl } = new Function(`${pick('escapeHtml')}\n${pick('safeHttpUrl')}\nreturn { escapeHtml, safeHttpUrl };`)();

assert.strictEqual(escapeHtml(`" onmouseover="alert(1)`), '&quot; onmouseover=&quot;alert(1)');
assert.strictEqual(escapeHtml(`'<b>&`), '&#39;&lt;b&gt;&amp;');
assert.strictEqual(escapeHtml(null), '');
assert.strictEqual(safeHttpUrl('javascript:alert(1)'), '#');
assert.strictEqual(safeHttpUrl('https://github.com/a/b/pull/1'), 'https://github.com/a/b/pull/1');
assert.ok(!/data-repo-(owner|name)="\$\{repo\./.test(html), 'data-repo-* must be escaped');
assert.ok(!/href="https:\/\/github\.com\/\$\{repo\./.test(html), 'repo href must be encoded');
assert.ok(html.includes('href="${escapeHtml(safeHttpUrl(pr.pr_url))}"'), 'pr_url must be http(s) only');
console.log('escape-html: ok');
