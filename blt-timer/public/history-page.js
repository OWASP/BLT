import {
  api,
  escapeHtml,
  formatDateTime,
  formatShort,
  mountDashboardShell,
  showPageMessage
} from './dashboard-shared.js';
import { createLogModal } from './log-modal.js';

let logs = [];
let logModal = null;
let searchTimeout = null;

function rangeStartMs(rangeName) {
  const now = new Date();
  if (rangeName === 'today') return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (rangeName === 'week') return Date.now() - 7 * 24 * 60 * 60 * 1000;
  if (rangeName === 'month') return Date.now() - 30 * 24 * 60 * 60 * 1000;
  return null;
}

function buildLogQueryParams() {
  const params = new URLSearchParams({ limit: '100' });
  const start = rangeStartMs(document.querySelector('#range-filter').value);
  const query = document.querySelector('#search-input').value.trim();
  if (start !== null) params.set('start', String(start));
  if (query) params.set('q', query);
  return params;
}

function renderLogs() {
  const body = document.querySelector('#history-table');
  const empty = document.querySelector('#history-empty');
  empty.classList.toggle('hidden', logs.length > 0);
  body.innerHTML = logs.map((log) => `
    <tr>
      <td class="px-4 py-4 font-medium text-slate-950">${escapeHtml(log.title)}</td>
      <td class="px-4 py-4 text-slate-600">${escapeHtml(log.project || 'No project')}</td>
      <td class="px-4 py-4 text-slate-500">${formatDateTime(log.startTime)}</td>
      <td class="px-4 py-4 font-medium text-slate-950">${formatShort(log.durationSeconds)}</td>
      <td class="px-4 py-4"><div class="flex gap-2"><button class="btn-secondary px-3 py-2 text-xs" type="button" data-action="edit-log" data-log-id="${escapeHtml(log.id)}">Edit</button><button class="btn-danger px-3 py-2 text-xs" type="button" data-action="delete-log" data-log-id="${escapeHtml(log.id)}">Delete</button></div></td>
    </tr>`).join('');
}

async function loadLogs() {
  try {
    const data = await api(`/api/logs?${buildLogQueryParams().toString()}`);
    logs = data.logs || [];
    renderLogs();
    document.querySelector('#page-message').classList.add('hidden');
  } catch (error) {
    showPageMessage(error.message || 'Could not load work history.', {
      isError: true,
      onRetry: () => loadLogs()
    });
  }
}

async function saveLog(payload, existingLog) {
  if (existingLog) {
    await api(`/api/logs/${encodeURIComponent(existingLog.id)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  } else {
    await api('/api/logs', { method: 'POST', body: JSON.stringify(payload) });
  }
  await loadLogs();
  showPageMessage(existingLog ? 'Work log updated.' : 'Work log saved.');
}

async function deleteLog(id) {
  await api(`/api/logs/${encodeURIComponent(id)}`, { method: 'DELETE', body: '{}' });
  await loadLogs();
  showPageMessage('Work log deleted.');
}

function selectedLog(id) {
  return logs.find((log) => log.id === id);
}

function debounceLoadLogs() {
  window.clearTimeout(searchTimeout);
  searchTimeout = window.setTimeout(() => loadLogs(), 250);
}

const pageMarkup = `
  <section class="card p-6" aria-labelledby="history-title">
    <div class="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><p class="section-kicker">History</p><h2 id="history-title" class="mt-1 text-xl font-semibold text-slate-950">Search and export work logs</h2><p class="mt-1 text-sm text-slate-500">Find a saved session, update it, or download your history.</p></div><div class="flex flex-wrap gap-2"><a class="btn-secondary" href="/api/export.json">Export JSON</a><a class="btn-primary" href="/api/export.csv">Export CSV</a></div></div>
    <div class="mt-5 grid gap-2 lg:grid-cols-[10rem_minmax(0,1fr)_auto]"><select id="range-filter" class="field-input" aria-label="Filter logs by date range"><option value="today">Today</option><option value="week" selected>This week</option><option value="month">This month</option><option value="all">All logs</option></select><input id="search-input" class="field-input" placeholder="Search title or notes" aria-label="Search work logs" /><button id="refresh-logs-button" class="btn-secondary" type="button">Refresh</button></div>
    <div class="history-table-wrap mt-5"><table class="min-w-full text-left text-sm"><thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th class="px-4 py-3">Title</th><th class="px-4 py-3">Project</th><th class="px-4 py-3">Started</th><th class="px-4 py-3">Duration</th><th class="px-4 py-3">Actions</th></tr></thead><tbody id="history-table" class="divide-y divide-slate-100 bg-white"></tbody></table></div>
    <div id="history-empty" class="mt-5 hidden rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center"><p class="text-sm font-semibold text-slate-950">No work logs match this view.</p><p class="mt-1 text-sm text-slate-500">Adjust the filters or create a manual log from Recent logs.</p></div>
  </section>`;

const user = await mountDashboardShell('history', {
  title: 'Work history',
  content: pageMarkup
});

if (user) {
  logModal = createLogModal({ onSave: saveLog, onDelete: deleteLog });
  document.querySelector('#range-filter').addEventListener('change', loadLogs);
  document.querySelector('#search-input').addEventListener('input', debounceLoadLogs);
  document.querySelector('#refresh-logs-button').addEventListener('click', loadLogs);
  document.querySelector('#history-table').addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const log = selectedLog(button.dataset.logId);
    if (!log) return;
    if (button.dataset.action === 'edit-log') logModal.openForEdit(log);
    if (button.dataset.action === 'delete-log' && window.confirm('Delete this work log? This cannot be undone.')) {
      deleteLog(log.id).catch((error) => showPageMessage(error.message, { isError: true }));
    }
  });
  loadLogs();
}
