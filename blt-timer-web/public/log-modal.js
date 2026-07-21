import { formatDateTime, toDateTimeLocalValue } from './dashboard-shared.js';

function payloadFromForm(overlay) {
  const title = overlay.querySelector('#log-modal-title-input').value.trim();
  const startTime = new Date(overlay.querySelector('#log-modal-start').value).getTime();
  const endTime = new Date(overlay.querySelector('#log-modal-end').value).getTime();

  if (!title) throw new Error('Title is required.');
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || endTime <= startTime) {
    throw new Error('End time must be later than start time.');
  }

  return {
    title,
    notes: overlay.querySelector('#log-modal-notes').value.trim(),
    project: overlay.querySelector('#log-modal-project').value.trim(),
    referenceUrl: overlay.querySelector('#log-modal-reference').value.trim(),
    source: 'web',
    startTime,
    endTime,
    durationSeconds: Math.floor((endTime - startTime) / 1000)
  };
}

export function createLogModal({ onSave, onDelete }) {
  let currentLog = null;
  const overlay = document.createElement('div');
  overlay.className = 'log-modal-overlay';
  overlay.innerHTML = `
    <section class="log-modal-panel" role="dialog" aria-modal="true" aria-labelledby="log-modal-title">
      <header class="flex items-start justify-between gap-4 border-b border-slate-100 p-5"><div><p class="section-kicker">Work log</p><h2 id="log-modal-title" class="mt-1 text-xl font-semibold text-slate-950">Save work log</h2><p id="log-modal-description" class="mt-1 text-sm text-slate-500">Record the work you completed.</p></div><button id="log-modal-close" class="btn-secondary px-3 py-2 text-xs" type="button">Close</button></header>
      <form id="log-modal-form" class="space-y-4 p-5">
        <div><label class="field-label" for="log-modal-title-input">Title</label><input id="log-modal-title-input" class="field-input mt-1" required /></div>
        <div><label class="field-label" for="log-modal-notes">Notes</label><textarea id="log-modal-notes" class="field-input mt-1 min-h-24" placeholder="What did you work on?"></textarea></div>
        <div class="grid gap-3 md:grid-cols-2"><div><label class="field-label" for="log-modal-project">Project</label><input id="log-modal-project" class="field-input mt-1" /></div><div><label class="field-label" for="log-modal-reference">Reference</label><input id="log-modal-reference" class="field-input mt-1" placeholder="Issue or URL" /></div></div>
        <div class="grid gap-3 md:grid-cols-2"><div><label class="field-label" for="log-modal-start">Start time</label><input id="log-modal-start" class="field-input mt-1" type="datetime-local" required /></div><div><label class="field-label" for="log-modal-end">End time</label><input id="log-modal-end" class="field-input mt-1" type="datetime-local" required /></div></div>
        <p id="log-modal-error" class="form-error" role="alert"></p>
        <footer class="flex flex-wrap justify-between gap-3 border-t border-slate-100 pt-5"><button id="log-modal-delete" class="btn-danger hidden" type="button">Delete log</button><span></span><div class="flex gap-3"><button id="log-modal-cancel" class="btn-secondary" type="button">Cancel</button><button id="log-modal-save" class="btn-primary" type="submit">Save work log</button></div></footer>
      </form>
    </section>`;
  document.body.append(overlay);

  const close = () => {
    overlay.classList.remove('active');
    currentLog = null;
  };
  const error = overlay.querySelector('#log-modal-error');
  const saveButton = overlay.querySelector('#log-modal-save');
  const deleteButton = overlay.querySelector('#log-modal-delete');

  function fill(log) {
    overlay.querySelector('#log-modal-title-input').value = log.title || '';
    overlay.querySelector('#log-modal-notes').value = log.notes || '';
    overlay.querySelector('#log-modal-project').value = log.project || '';
    overlay.querySelector('#log-modal-reference').value = log.referenceUrl || '';
    overlay.querySelector('#log-modal-start').value = toDateTimeLocalValue(log.startTime);
    overlay.querySelector('#log-modal-end').value = toDateTimeLocalValue(log.endTime);
  }

  function open(log, isEdit) {
    currentLog = isEdit ? log : null;
    fill(log);
    error.textContent = '';
    overlay.querySelector('#log-modal-title').textContent = isEdit ? 'Edit work log' : 'Save work log';
    overlay.querySelector('#log-modal-description').textContent = isEdit
      ? `Update the details for the session from ${formatDateTime(log.startTime)}.`
      : 'Record the work you completed.';
    saveButton.textContent = isEdit ? 'Update work log' : 'Save work log';
    deleteButton.classList.toggle('hidden', !isEdit);
    overlay.classList.add('active');
    window.setTimeout(() => overlay.querySelector('#log-modal-title-input').focus(), 0);
  }

  overlay.querySelector('#log-modal-close').addEventListener('click', close);
  overlay.querySelector('#log-modal-cancel').addEventListener('click', close);
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) close();
  });
  overlay.querySelector('#log-modal-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const payload = payloadFromForm(overlay);
      saveButton.disabled = true;
      await onSave(payload, currentLog);
      close();
    } catch (saveError) {
      error.textContent = saveError.message || 'Could not save this work log.';
    } finally {
      saveButton.disabled = false;
    }
  });
  deleteButton.addEventListener('click', async () => {
    if (!currentLog || !window.confirm('Delete this work log? This cannot be undone.')) return;
    try {
      deleteButton.disabled = true;
      await onDelete(currentLog.id);
      close();
    } catch (deleteError) {
      error.textContent = deleteError.message || 'Could not delete this work log.';
    } finally {
      deleteButton.disabled = false;
    }
  });

  return {
    openForCreate(initialValues = {}) {
      const endTime = initialValues.endTime || Date.now();
      open({
        title: initialValues.title || '',
        notes: initialValues.notes || '',
        project: initialValues.project || '',
        referenceUrl: initialValues.referenceUrl || '',
        startTime: initialValues.startTime || endTime - 30 * 60 * 1000,
        endTime
      }, false);
    },
    openForEdit(log) {
      open(log, true);
    },
    close,
    destroy() {
      overlay.remove();
    }
  };
}
