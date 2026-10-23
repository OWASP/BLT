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

function renderLogs() {
  const list = document.querySelector('#log-list');
  const empty = document.querySelector('#empty-logs');
  empty.classList.toggle('hidden', logs.length > 0);
  list.innerHTML = logs.map((log) => `
    <article class="log-card">
      <div class="flex flex-col justify-between gap-3 md:flex-row md:items-start"><div><h2 class="font-semibold text-slate-950">${escapeHtml(log.title)}</h2><p class="mt-1 text-sm text-slate-500">${escapeHtml(log.project || 'No project')} · ${escapeHtml(log.referenceUrl || 'No reference')}</p><p class="mt-2 text-sm leading-6 text-slate-600">${escapeHtml(log.notes || 'No notes added.')}</p></div><span class="duration-badge">${formatShort(log.durationSeconds)}</span></div>
      <div class="mt-4 flex flex-col justify-between gap-3 border-t border-slate-100 pt-3 text-xs font-medium text-slate-500 sm:flex-row sm:items-center"><span>${formatDateTime(log.startTime)} to ${formatDateTime(log.endTime)}</span><span class="flex gap-2"><button class="btn-secondary px-3 py-2 text-xs" type="button" data-action="edit-log" data-log-id="${escapeHtml(log.id)}">Edit</button><button class="btn-danger px-3 py-2 text-xs" type="button" data-action="delete-log" data-log-id="${escapeHtml(log.id)}">Delete</button></span></div>
    </article>`).join('');
}

async function loadLogs() {
  try {
    const data = await api('/api/logs?limit=10');
    logs = data.logs || [];
    renderLogs();
    document.querySelector('#page-message').classList.add('hidden');
  } catch (error) {
    showPageMessage(error.message || 'Could not load recent logs.', {
      isError: true,
      onRetry: () => loadLogs()
    });
  }
}

function selectedLog(id) {
  return logs.find((log) => log.id === id);
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

const pageMarkup = `
  <section class="card p-6" aria-labelledby="recent-logs-title">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><p class="section-kicker">Recent activity</p><h2 id="recent-logs-title" class="mt-1 text-xl font-semibold text-slate-950">Your latest work</h2><p class="mt-1 text-sm text-slate-500">Add, review, and update your most recent saved sessions.</p></div><button id="manual-log-button" class="btn-primary" type="button">+ Manual log</button></div>
    <div id="log-list" class="mt-5 grid gap-3"></div>
    <div id="empty-logs" class="mt-5 hidden rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center"><p class="text-sm font-semibold text-slate-950">No logs yet.</p><p class="mt-1 text-sm text-slate-500">Use Manual log to record work you completed away from the timer.</p><button id="empty-manual-log-button" class="btn-secondary mt-4" type="button">Add a manual log</button></div>
  </section>`;

const user = await mountDashboardShell('logs', {
  title: 'Recent logs',
  content: pageMarkup
});

if (user) {
  logModal = createLogModal({ onSave: saveLog, onDelete: deleteLog });
  const openManual = () => logModal.openForCreate();
  document.querySelector('#manual-log-button').addEventListener('click', openManual);
  document.querySelector('#empty-manual-log-button').addEventListener('click', openManual);
  document.querySelector('#log-list').addEventListener('click', (event) => {
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
