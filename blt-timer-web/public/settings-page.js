import {
  api,
  logout,
  mountDashboardShell,
  showPageMessage,
  updateDashboardUser
} from './dashboard-shared.js';
import { populateTimezoneSelect } from './timezones.js';

const pageMarkup = `
  <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
    <section class="card p-6" aria-labelledby="profile-title"><p class="section-kicker">Profile</p><h2 id="profile-title" class="mt-1 text-xl font-semibold text-slate-950">Account details</h2><p class="mt-1 text-sm text-slate-500">Keep your public name and local timezone up to date.</p><form id="profile-form" class="mt-6 max-w-xl space-y-4"><div><label class="field-label" for="display-name">Display name</label><input id="display-name" class="field-input mt-1" maxlength="80" required /></div><div><label class="field-label" for="timezone">Timezone</label><select id="timezone" class="field-input mt-1" required></select><p class="mt-1 text-xs text-slate-500">Select your local IANA timezone.</p></div><div class="flex items-center gap-3"><button id="profile-submit" class="btn-primary" type="submit">Save settings</button><p id="profile-status" class="text-sm text-slate-500" role="status" aria-live="polite"></p></div></form></section>
    <aside class="card h-fit p-6"><p class="section-kicker">Data and privacy</p><h2 class="mt-1 text-xl font-semibold text-slate-950">You stay in control</h2><p class="mt-3 text-sm leading-6 text-slate-600">BLT Timer stores only your account, active session state in your browser, and work logs you choose to save. It does not collect keystrokes, screenshots, or activity monitoring data.</p><div class="mt-5 grid gap-2"><a class="btn-secondary" href="/api/export.json">Export JSON</a><a class="btn-secondary" href="/api/export.csv">Export CSV</a><button id="settings-logout-button" class="btn-danger" type="button">Log out</button></div></aside>
  </div>`;

const user = await mountDashboardShell('settings', {
  title: 'Settings',
  content: pageMarkup
});

if (user) {
  document.querySelector('#display-name').value = user.displayName || user.username || '';
  populateTimezoneSelect(
    document.querySelector('#timezone'),
    user.timezone || 'UTC'
  );
  document.querySelector('#settings-logout-button').addEventListener('click', logout);
  document.querySelector('#profile-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const submit = document.querySelector('#profile-submit');
    const status = document.querySelector('#profile-status');
    status.textContent = '';
    submit.disabled = true;
    try {
      const response = await api('/api/me', {
        method: 'PATCH',
        body: JSON.stringify({
          displayName: document.querySelector('#display-name').value.trim(),
          timezone: document.querySelector('#timezone').value
        })
      });
      updateDashboardUser(response.user);
      status.textContent = 'Settings saved.';
      showPageMessage('Settings saved.');
    } catch (error) {
      status.textContent = error.message || 'Could not save settings.';
      showPageMessage(status.textContent, { isError: true });
    } finally {
      submit.disabled = false;
    }
  });
}
