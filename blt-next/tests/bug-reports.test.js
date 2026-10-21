// Tests for src/assets/js/bug-reports.js. Run with: node --test tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const reports = require('../src/assets/js/bug-reports.js');

// ---- a very small DOM, enough for the script ----------------------------------------------

class FakeClassList {
  constructor(el) { this.el = el; }
  get set() { return new Set(this.el.className.split(/\s+/).filter(Boolean)); }
  add(c) { const s = this.set; s.add(c); this.el.className = [...s].join(' '); }
  remove(c) { const s = this.set; s.delete(c); this.el.className = [...s].join(' '); }
  contains(c) { return this.set.has(c); }
}

class FakeElement {
  constructor(tag, doc) {
    this.tagName = tag.toUpperCase();
    this.ownerDocument = doc;
    this.children = [];
    this.attributes = {};
    this.className = '';
    this._text = '';
    this.listeners = {};
    this.classList = new FakeClassList(this);
    this.parent = null;
    this.disabled = false;
  }
  set id(v) { this.attributes.id = v; this.ownerDocument.ids[v] = this; }
  get id() { return this.attributes.id; }
  set textContent(v) { this.children = []; this._text = String(v); }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(''); }
  set innerHTML(v) { throw new Error('innerHTML must not be used'); }
  appendChild(child) { child.parent = this; this.children.push(child); return child; }
  setAttribute(k, v) { this.attributes[k] = String(v); if (k === 'id') this.id = v; }
  getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; }
  removeAttribute(k) { delete this.attributes[k]; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  focus() { this.ownerDocument.focused = this; }
  replaceWith(node) {
    const siblings = this.parent.children;
    siblings[siblings.indexOf(this)] = node;
    node.parent = this.parent;
    this.ownerDocument.replaced = node;
  }
  find(pred) {
    if (pred(this)) return this;
    for (const c of this.children) { const hit = c.find(pred); if (hit) return hit; }
    return null;
  }
}

class FakeDocument {
  constructor() { this.ids = {}; this.body = new FakeElement('body', this); }
  createElement(tag) { return new FakeElement(tag, this); }
  getElementById(id) { return this.ids[id] || null; }
}

function formPage(values) {
  const doc = new FakeDocument();
  const form = doc.body.appendChild(doc.createElement('form'));
  form.id = 'bugReportForm';
  form.values = values;
  for (const id of ['bugTitle', 'bugUrl', 'bugSeverity', 'bugType', 'bugDescription', 'bugSteps', 'bugSubmit']) {
    form.appendChild(doc.createElement('input')).id = id;
  }
  const box = doc.body.appendChild(doc.createElement('div'));
  box.id = 'custom-error-box';
  box.className = 'hidden p-3';
  doc.body.appendChild(doc.createElement('span')).id = 'custom-error-text';
  return { doc, form, box };
}

// FormData over the fake form.
global.FormData = class { constructor(form) { this.form = form; } entries() { return Object.entries(this.form.values); } };

async function submit(form) {
  let prevented = false;
  for (const fn of form.listeners.submit) await fn({ preventDefault() { prevented = true; } });
  assert.ok(prevented, 'the browser submit is replaced by fetch');
}

function jsonResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

const VALID = {
  title: 'XSS in search', url: 'https://example.com/s?q=1', severity: 'high', type: 'security',
  description: 'Reflected', steps: '', website: '',
};

// ---- tests --------------------------------------------------------------------------------

test('validate matches the server rules', () => {
  assert.equal(reports.validate(VALID), null);
  assert.equal(reports.validate({ ...VALID, title: ' ' }).field, 'title');
  assert.equal(reports.validate({ ...VALID, url: 'javascript:alert(1)' }).field, 'url');
  assert.equal(reports.validate({ ...VALID, url: 'ftp://x.example' }).field, 'url');
  assert.equal(reports.validate({ ...VALID, url: 'https://exa mple.com' }).field, 'url');
  assert.equal(reports.validate({ ...VALID, description: 'x'.repeat(5001) }).field, 'description');
  assert.equal(reports.validate({ ...VALID, severity: '' }).field, 'severity');
  assert.equal(reports.validate({ ...VALID, type: 'nope' }).field, 'type');
});

test('a valid form is posted urlencoded and replaced by the real result', async () => {
  const { doc, form } = formPage(VALID);
  const calls = [];
  reports.initForm(doc, async (url, init) => {
    calls.push([url, init]);
    return jsonResponse(201, { success: true, id: 42, link: '/pages/bugs.html?id=42' });
  });
  await submit(form);
  assert.equal(calls.length, 1);
  const [url, init] = calls[0];
  assert.equal(url, '/api/bugs');
  assert.equal(init.method, 'POST');
  assert.equal(init.headers.Accept, 'application/json');
  assert.equal(new URLSearchParams(init.body).get('title'), 'XSS in search');
  const panel = doc.replaced;
  assert.ok(panel, 'form replaced');
  assert.match(panel.textContent, /Report #42 submitted/);
  const link = panel.find((n) => n.tagName === 'A' && n.getAttribute('href') === '/pages/bugs.html?id=42');
  assert.ok(link, 'links to the saved report');
});

test('client-side problems are shown without a request', async () => {
  const { doc, form, box } = formPage({ ...VALID, url: 'not a url' });
  let called = false;
  reports.initForm(doc, async () => { called = true; });
  await submit(form);
  assert.equal(called, false);
  assert.equal(box.classList.contains('hidden'), false);
  assert.match(doc.getElementById('custom-error-text').textContent, /http/);
  assert.equal(doc.getElementById('bugUrl').getAttribute('aria-invalid'), 'true');
});

test('server errors are shown, not swallowed', async () => {
  const cases = [
    [jsonResponse(400, { success: false, error: 'Description is required.', field: 'description' }), /Description is required/],
    [jsonResponse(429, { success: false, error: 'Too many reports from your network.' }), /Too many/],
    [jsonResponse(503, { success: false, error: 'Bug reporting is not configured on this site yet.' }), /not configured/],
    [{ ok: false, status: 500, json: async () => { throw new Error('html'); } }, /could not be saved/],
  ];
  for (const [response, pattern] of cases) {
    const { doc, form, box } = formPage(VALID);
    reports.initForm(doc, async () => response);
    await submit(form);
    assert.equal(doc.replaced, undefined, 'the form stays so the user can retry');
    assert.equal(box.classList.contains('hidden'), false);
    assert.match(doc.getElementById('custom-error-text').textContent, pattern);
    assert.equal(doc.getElementById('bugSubmit').disabled, false);
  }
});

test('network failures are shown', async () => {
  const { doc, form } = formPage(VALID);
  reports.initForm(doc, async () => { throw new TypeError('Failed to fetch'); });
  await submit(form);
  assert.match(doc.getElementById('custom-error-text').textContent, /reach the server/);
});

test('reports page lists recent reports with safe text and links', async () => {
  const doc = new FakeDocument();
  const container = doc.body.appendChild(doc.createElement('div'));
  container.id = 'bugReports';
  const fetches = [];
  await reports.initBugsPage(doc, async (url) => {
    fetches.push(url);
    return jsonResponse(200, { success: true, bugs: [{ id: 7, title: '<img src=x onerror=alert(1)>', url: 'https://a.example/x', severity: 'low', created: '2026-10-01 00:00:00' }] });
  }, '');
  assert.deepEqual(fetches, ['/api/bugs']);
  assert.match(container.textContent, /#7 <img src=x onerror=alert\(1\)>/); // as text, not markup
  assert.ok(container.find((n) => n.tagName === 'A' && n.getAttribute('href') === '/pages/bugs.html?id=7'));
});

test('reports page shows one report for ?id=N and errors otherwise', async () => {
  const doc = new FakeDocument();
  const container = doc.body.appendChild(doc.createElement('div'));
  container.id = 'bugReports';
  const fetches = [];
  await reports.initBugsPage(doc, async (url) => {
    fetches.push(url);
    return jsonResponse(200, { success: true, bug: { id: 42, title: 'T', url: 'https://e.example', description: 'D', steps_to_reproduce: 'S' } });
  }, '?id=42');
  assert.deepEqual(fetches, ['/api/bugs?id=42']);
  assert.match(container.textContent, /#42 T/);
  assert.match(container.textContent, /Steps to reproduce/);

  await reports.initBugsPage(doc, async () => jsonResponse(404, { success: false, error: 'Bug report not found.' }), '?id=9');
  assert.equal(container.textContent, 'Bug report not found.');
});

test('report links only point at our own page', () => {
  assert.equal(reports.reportLink(5), '/pages/bugs.html?id=5');
  assert.equal(reports.reportLink('javascript:alert(1)'), null);
  assert.equal(reports.reportLink(undefined), null);
});
