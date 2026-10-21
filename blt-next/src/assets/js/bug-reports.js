/**
 * Bug reports: sends the Report Bug form to /api/bugs and shows the real result, and
 * renders the recent-reports list and a single report on pages/bugs.html.
 *
 * Everything from the server is put on the page with textContent, never innerHTML.
 * Loaded as a classic script in the browser; also require()-able for node tests.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.BLTBugReports = api;
    if (typeof document !== 'undefined') {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => api.init(document, root.fetch.bind(root)));
      } else {
        api.init(document, root.fetch.bind(root));
      }
    }
  }
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const ENDPOINT = '/api/bugs';
  const LIMITS = { title: 200, url: 200, description: 5000, steps: 5000 };
  const LABELS = { title: 'Bug title', url: 'Affected URL', description: 'Description', steps: 'Steps to reproduce' };
  const SEVERITIES = ['critical', 'high', 'medium', 'low', 'info'];
  const TYPES = ['security', 'functional', 'ui', 'performance', 'other'];
  const TYPE_LABELS = { security: 'Security', functional: 'Functional', ui: 'UI / UX', performance: 'Performance', other: 'Other' };
  const FIELD_IDS = { title: 'bugTitle', url: 'bugUrl', severity: 'bugSeverity', type: 'bugType', description: 'bugDescription', steps: 'bugSteps' };

  /** Same checks as the Worker, so most mistakes are caught before a round trip. */
  function validate(fields) {
    for (const name of ['title', 'url', 'description', 'steps']) {
      const value = String(fields[name] || '').trim();
      if (!value && name !== 'steps') return { field: name, message: `${LABELS[name]} is required.` };
      if (value.length > LIMITS[name]) return { field: name, message: `${LABELS[name]} must be ${LIMITS[name]} characters or fewer.` };
    }
    const url = String(fields.url).trim();
    if (!/^https?:\/\/[^\s/?#]+[^\s]*$/i.test(url)) {
      return { field: 'url', message: 'Affected URL must be a full http:// or https:// address.' };
    }
    if (!SEVERITIES.includes(fields.severity)) return { field: 'severity', message: 'Choose a severity.' };
    if (!TYPES.includes(fields.type)) return { field: 'type', message: 'Choose a bug type.' };
    return null;
  }

  /** The message to show for a failed request. */
  function describeFailure(status, body) {
    if (body && typeof body.error === 'string' && body.error) return body.error;
    if (status === 429) return 'Too many reports right now. Please wait a minute and try again.';
    if (status >= 500 || status === 0) return 'The report could not be saved. Please try again later.';
    return 'The report could not be sent. Please check the form and try again.';
  }

  /** POST the fields; resolves to { ok, status, body } and never throws. */
  async function sendReport(fields, fetchImpl) {
    let response;
    try {
      response = await fetchImpl(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
        body: new URLSearchParams(fields).toString(),
        credentials: 'same-origin',
      });
    } catch (err) {
      return { ok: false, status: 0, body: { error: "Couldn't reach the server. Check your connection and try again." } };
    }
    let body = null;
    try {
      body = await response.json();
    } catch (err) {
      body = null;
    }
    const ok = response.ok && !!(body && body.success);
    return { ok, status: response.status, body };
  }

  function el(doc, tag, className, text) {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  /** A safe link target: only our own /pages/bugs.html?id=N links. */
  function reportLink(id) {
    return Number.isInteger(id) ? `/pages/bugs.html?id=${id}` : null;
  }

  function successPanel(doc, body) {
    const panel = el(doc, 'div', 'p-8 rounded-lg border border-green-300 bg-green-50 dark:bg-green-900/20 dark:border-green-800 text-center');
    panel.setAttribute('role', 'status');
    panel.id = 'bugReportResult';
    const id = body && Number.isInteger(body.id) ? body.id : null;
    panel.appendChild(el(doc, 'h2', 'text-xl font-bold text-green-800 dark:text-green-300 mb-2', id ? `Report #${id} submitted` : 'Report submitted'));
    panel.appendChild(el(doc, 'p', 'text-sm text-green-900 dark:text-green-200', 'Thank you for helping make the web safer. Your report has been saved.'));
    const actions = el(doc, 'div', 'mt-5 flex justify-center gap-3');
    const link = reportLink(id);
    if (link) {
      const view = el(doc, 'a', 'px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-md hover:bg-red-700', 'View your report');
      view.setAttribute('href', link);
      actions.appendChild(view);
    }
    const again = el(doc, 'a', 'px-4 py-2 text-sm font-medium text-red-600 border border-red-600 rounded-md', 'Report another bug');
    again.setAttribute('href', '/pages/report-bug.html');
    actions.appendChild(again);
    panel.appendChild(actions);
    return panel;
  }

  function readForm(form) {
    const data = {};
    for (const [key, value] of new FormData(form).entries()) {
      if (typeof value === 'string') data[key] = value;
    }
    return data;
  }

  function showError(doc, message, field) {
    const box = doc.getElementById('custom-error-box');
    const text = doc.getElementById('custom-error-text');
    if (text) text.textContent = message;
    if (box) box.classList.remove('hidden');
    const input = field && FIELD_IDS[field] ? doc.getElementById(FIELD_IDS[field]) : null;
    if (input) {
      input.setAttribute('aria-invalid', 'true');
      if (typeof input.focus === 'function') input.focus();
    }
  }

  function clearError(doc) {
    const box = doc.getElementById('custom-error-box');
    if (box) box.classList.add('hidden');
    for (const id of Object.values(FIELD_IDS)) {
      const input = doc.getElementById(id);
      if (input) input.removeAttribute('aria-invalid');
    }
  }

  /** Wire the Report Bug form. */
  function initForm(doc, fetchImpl) {
    const form = doc.getElementById('bugReportForm');
    if (!form) return;
    const button = doc.getElementById('bugSubmit');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      clearError(doc);
      const fields = readForm(form);
      const problem = validate(fields);
      if (problem) {
        showError(doc, problem.message, problem.field);
        return;
      }
      if (button) {
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
      }
      const result = await sendReport(fields, fetchImpl);
      if (button) {
        button.disabled = false;
        button.removeAttribute('aria-busy');
      }
      if (result.ok) {
        form.replaceWith(successPanel(doc, result.body));
      } else {
        showError(doc, describeFailure(result.status, result.body), result.body && result.body.field);
      }
    });
  }

  function formatDate(value) {
    if (!value) return '';
    const date = new Date(String(value).replace(' ', 'T') + (/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? '' : 'Z'));
    return isNaN(date.getTime()) ? String(value) : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function hostOf(url) {
    try {
      return new URL(url).host;
    } catch (err) {
      return String(url || '');
    }
  }

  function badges(doc, bug) {
    const row = el(doc, 'div', 'flex flex-wrap gap-2 text-[11px] font-semibold');
    if (bug.severity) row.appendChild(el(doc, 'span', 'px-2 py-0.5 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300', bug.severity));
    if (bug.bug_type) row.appendChild(el(doc, 'span', 'px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200', TYPE_LABELS[bug.bug_type] || bug.bug_type));
    if (bug.status) row.appendChild(el(doc, 'span', 'px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300', bug.status));
    return row;
  }

  /** Recent reports as a list of links. */
  function renderList(doc, container, bugs) {
    container.textContent = '';
    if (!bugs.length) {
      container.appendChild(el(doc, 'p', 'text-sm text-gray-500 dark:text-gray-400', 'No reports yet.'));
      return;
    }
    const list = el(doc, 'ul', 'divide-y divide-[#E5E5E5] dark:divide-gray-800 border border-[#E5E5E5] dark:border-gray-800 rounded-lg');
    for (const bug of bugs) {
      const item = el(doc, 'li', 'p-4');
      const link = el(doc, 'a', 'font-semibold text-gray-900 dark:text-gray-100 hover:text-red-600', `#${bug.id} ${bug.title || hostOf(bug.url)}`);
      const href = reportLink(bug.id);
      if (href) link.setAttribute('href', href);
      item.appendChild(link);
      item.appendChild(el(doc, 'p', 'text-xs text-gray-500 dark:text-gray-400 mt-1', `${hostOf(bug.url)} · ${formatDate(bug.created)}`));
      item.appendChild(badges(doc, bug));
      list.appendChild(item);
    }
    container.appendChild(list);
  }

  /** One report. */
  function renderBug(doc, container, bug) {
    container.textContent = '';
    container.appendChild(el(doc, 'h2', 'text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2', `#${bug.id} ${bug.title || hostOf(bug.url)}`));
    container.appendChild(badges(doc, bug));
    const meta = el(doc, 'p', 'text-sm text-gray-500 dark:text-gray-400 mt-3', `Reported ${formatDate(bug.created)} · Affected URL: `);
    meta.appendChild(el(doc, 'code', 'break-all', bug.url || ''));
    container.appendChild(meta);
    container.appendChild(el(doc, 'h3', 'text-sm font-semibold mt-6 mb-1', 'Description'));
    container.appendChild(el(doc, 'p', 'text-sm whitespace-pre-wrap break-words', bug.description || ''));
    if (bug.steps_to_reproduce) {
      container.appendChild(el(doc, 'h3', 'text-sm font-semibold mt-6 mb-1', 'Steps to reproduce'));
      container.appendChild(el(doc, 'p', 'text-sm whitespace-pre-wrap break-words', bug.steps_to_reproduce));
    }
  }

  async function loadJson(url, fetchImpl) {
    try {
      const response = await fetchImpl(url, { headers: { Accept: 'application/json' } });
      const body = await response.json().catch(() => null);
      return { ok: response.ok && !!(body && body.success), status: response.status, body };
    } catch (err) {
      return { ok: false, status: 0, body: null };
    }
  }

  /** Fill pages/bugs.html: one report when ?id=N is given, else the recent list. */
  async function initBugsPage(doc, fetchImpl, search) {
    const container = doc.getElementById('bugReports');
    if (!container) return;
    const id = new URLSearchParams(search || '').get('id');
    if (id && /^\d{1,12}$/.test(id)) {
      const result = await loadJson(`${ENDPOINT}?id=${id}`, fetchImpl);
      if (result.ok) renderBug(doc, container, result.body.bug);
      else container.textContent = describeFailure(result.status, result.body);
      return;
    }
    const result = await loadJson(ENDPOINT, fetchImpl);
    if (result.ok) renderList(doc, container, result.body.bugs || []);
    else container.textContent = describeFailure(result.status, result.body);
  }

  function init(doc, fetchImpl) {
    initForm(doc, fetchImpl);
    const search = doc.defaultView && doc.defaultView.location ? doc.defaultView.location.search : '';
    initBugsPage(doc, fetchImpl, search);
  }

  return { validate, describeFailure, sendReport, successPanel, renderList, renderBug, initForm, initBugsPage, init, reportLink };
});
