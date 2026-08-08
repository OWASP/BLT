import {
  api,
  clearTimer,
  emptyTimer,
  formatDuration,
  formatShort,
  loadTimer,
  mountDashboardShell,
  saveTimer,
  showPageMessage
} from './dashboard-shared.js';
import { createLogModal } from './log-modal.js';

let timer = loadTimer();
let ticker = null;
let logModal = null;

function timerDetails() {
  return {
    title: document.querySelector('#task-title').value.trim(),
    project: document.querySelector('#project-name').value.trim(),
    referenceUrl: document.querySelector('#reference-url').value.trim()
  };
}

function hydrateTimerDetails() {
  document.querySelector('#task-title').value = timer.title || '';
  document.querySelector('#project-name').value = timer.project || '';
  document.querySelector('#reference-url').value = timer.referenceUrl || '';
}

function persistTimerDetails() {
  if (!timer.running) return;
  Object.assign(timer, timerDetails());
  saveTimer(timer);
}

function nowElapsed() {
  if (!timer.running) return 0;
  if (timer.paused) return timer.elapsedBeforePause || 0;
  return Math.floor((Date.now() - timer.startedAt) / 1000) + (timer.elapsedBeforePause || 0);
}

function updateTimerUi() {
  document.querySelector('#timer-display').textContent = formatDuration(nowElapsed());
  document.querySelector('#timer-state').textContent = !timer.running
    ? 'Ready to start'
    : timer.paused
      ? 'Paused'
      : 'Tracking now';
  document.querySelector('#start-button').disabled = timer.running;
  document.querySelector('#pause-button').disabled = !timer.running || timer.paused;
  document.querySelector('#pause-button').classList.toggle('hidden', timer.paused);
  document.querySelector('#resume-button').classList.toggle('hidden', !timer.paused);
  document.querySelector('#stop-button').disabled = !timer.running;
}

function tick() {
  window.clearInterval(ticker);
  ticker = window.setInterval(() => {
    updateTimerUi();
    saveTimer(timer);
  }, 1000);
  updateTimerUi();
}

function startTimer() {
  timer = {
    running: true,
    paused: false,
    startedAt: Date.now(),
    elapsedBeforePause: 0,
    pausedAt: null,
    ...timerDetails()
  };
  saveTimer(timer);
  tick();
  showPageMessage('Timer started. Your session continues while you browse other dashboard pages.');
}

function pauseTimer() {
  if (!timer.running || timer.paused) return;
  timer.elapsedBeforePause = nowElapsed();
  timer.paused = true;
  timer.pausedAt = Date.now();
  saveTimer(timer);
  updateTimerUi();
}

function resumeTimer() {
  if (!timer.running || !timer.paused) return;
  timer.paused = false;
  timer.startedAt = Date.now();
  timer.pausedAt = null;
  saveTimer(timer);
  tick();
}

function stopTimer() {
  if (!timer.running) return;
  const endTime = Date.now();
  const durationSeconds = nowElapsed();
  logModal.openForCreate({
    title: document.querySelector('#task-title').value.trim() || timer.title || 'Untitled BLT work',
    project: document.querySelector('#project-name').value.trim() || timer.project || '',
    referenceUrl: document.querySelector('#reference-url').value.trim() || timer.referenceUrl || '',
    startTime: endTime - durationSeconds * 1000,
    endTime
  });
}

async function loadStats() {
  try {
    const [today, week] = await Promise.all([
      api('/api/stats?range=today'),
      api('/api/stats?range=week')
    ]);
    document.querySelector('#today-total').textContent = formatShort(today.totalSeconds || 0);
    document.querySelector('#session-count').textContent = String(today.sessions || 0);
    document.querySelector('#week-total').textContent = formatShort(week.totalSeconds || 0);
  } catch (error) {
    showPageMessage(error.message || 'Could not load timer statistics.', {
      isError: true,
      onRetry: () => loadStats()
    });
  }
}

const pageMarkup = `
  <section class="grid gap-4 md:grid-cols-3" aria-label="Timer statistics">
    <article class="card p-5"><p class="stat-label">Today's focus time</p><p id="today-total" class="mt-2 text-3xl font-semibold tracking-tight text-slate-950">0m</p></article>
    <article class="card p-5"><p class="stat-label">Sessions</p><p id="session-count" class="mt-2 text-3xl font-semibold tracking-tight text-slate-950">0</p></article>
    <article class="card p-5"><p class="stat-label">This week</p><p id="week-total" class="mt-2 text-3xl font-semibold tracking-tight text-slate-950">0m</p></article>
  </section>
  <section class="card mt-5 p-6 md:p-8" aria-labelledby="timer-work-title">
    <div class="grid gap-6 lg:grid-cols-[1fr_260px] lg:items-center">
      <div>
        <label class="field-label" for="task-title">What are you working on?</label>
        <input id="task-title" class="mt-2 w-full border-0 border-b border-slate-200 bg-transparent px-0 py-3 text-2xl font-semibold tracking-tight text-slate-950 placeholder:text-slate-300 focus:border-red-600 focus:outline-none" placeholder="e.g. Fix timer save flow" />
        <div class="mt-4 grid gap-3 md:grid-cols-2"><input id="project-name" class="field-input" placeholder="Project, e.g. BLT Timer Web" aria-label="Project" /><input id="reference-url" class="field-input" placeholder="Reference, issue, URL" aria-label="Reference" /></div>
      </div>
      <div class="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-center"><p class="text-xs font-medium uppercase tracking-wide text-slate-500">Current timer</p><div id="timer-display" class="mt-3 font-mono text-5xl font-semibold tracking-tight text-slate-950">00:00:00</div><p id="timer-state" class="mt-2 text-sm text-slate-500">Ready to start</p></div>
    </div>
    <div class="mt-6 flex flex-col gap-3 sm:flex-row"><button id="start-button" class="btn-primary px-6 py-3 text-base" type="button">Start tracking</button><button id="pause-button" class="btn-secondary px-6 py-3 text-base" type="button">Pause</button><button id="resume-button" class="btn-secondary hidden px-6 py-3 text-base" type="button">Resume</button><button id="stop-button" class="btn-danger px-6 py-3 text-base" type="button">Stop &amp; save</button></div>
  </section>`;

const user = await mountDashboardShell('timer', {
  title: 'Track your work',
  content: pageMarkup
});

if (user) {
  logModal = createLogModal({
    async onSave(payload) {
      await api('/api/logs', { method: 'POST', body: JSON.stringify(payload) });
      clearTimer();
      timer = emptyTimer();
      window.clearInterval(ticker);
      updateTimerUi();
      showPageMessage('Work log saved.');
      await loadStats();
    },
    async onDelete() {}
  });
  document.querySelector('#start-button').addEventListener('click', startTimer);
  document.querySelector('#pause-button').addEventListener('click', pauseTimer);
  document.querySelector('#resume-button').addEventListener('click', resumeTimer);
  document.querySelector('#stop-button').addEventListener('click', stopTimer);
  document.querySelector('#task-title').addEventListener('input', persistTimerDetails);
  document.querySelector('#project-name').addEventListener('input', persistTimerDetails);
  document.querySelector('#reference-url').addEventListener('input', persistTimerDetails);
  hydrateTimerDetails();
  updateTimerUi();
  if (timer.running && !timer.paused) tick();
  loadStats();
}
