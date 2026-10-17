import { detectTimezone } from './timezones.js';

const loginTab = document.getElementById('login-tab');
const registerTab = document.getElementById('register-tab');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const authMessage = document.getElementById('auth-message');

function showMessage(message, isError = false) {
  authMessage.textContent = message;
  authMessage.classList.remove('hidden');
  authMessage.classList.toggle('border-red-200', isError);
  authMessage.classList.toggle('bg-red-50', isError);
  authMessage.classList.toggle('text-red-700', isError);
}

function setLoading(form, loading) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = loading;
  button.textContent = loading ? 'Please wait…' : button.dataset.label;
}

function showTab(tab) {
  const loginActive = tab === 'login';
  loginForm.classList.toggle('hidden', !loginActive);
  registerForm.classList.toggle('hidden', loginActive);
  loginTab.classList.toggle('bg-white', loginActive);
  loginTab.classList.toggle('shadow-sm', loginActive);
  loginTab.classList.toggle('text-slate-950', loginActive);
  loginTab.classList.toggle('text-slate-500', !loginActive);
  registerTab.classList.toggle('bg-white', !loginActive);
  registerTab.classList.toggle('shadow-sm', !loginActive);
  registerTab.classList.toggle('text-slate-950', !loginActive);
  registerTab.classList.toggle('text-slate-500', loginActive);
  authMessage.classList.add('hidden');
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

loginForm.querySelector('button[type="submit"]').dataset.label = 'Sign in';
registerForm.querySelector('button[type="submit"]').dataset.label = 'Create account';

loginTab.addEventListener('click', () => showTab('login'));
registerTab.addEventListener('click', () => showTab('register'));

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  setLoading(loginForm, true);
  try {
    await postJson('/api/auth/login', {
      login: document.getElementById('login-identifier').value.trim(),
      password: document.getElementById('login-password').value
    });
    window.location.href = '/dashboard';
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setLoading(loginForm, false);
  }
});

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  setLoading(registerForm, true);
  try {
    await postJson('/api/auth/register', {
      username: document.getElementById('register-username').value.trim(),
      email: document.getElementById('register-email').value.trim(),
      password: document.getElementById('register-password').value,
      timezone: detectTimezone()
    });
    window.location.href = '/dashboard';
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setLoading(registerForm, false);
  }
});
