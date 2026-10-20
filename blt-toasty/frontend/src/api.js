/**
 * BLT-Toasty Dashboard API Client
 *
 * Centralised HTTP layer with JWT Bearer auth, structured error handling,
 * and automatic token management via localStorage.
 *
 * Base URL defaults to the local Wrangler dev server (127.0.0.1:8787)
 * and can be overridden with the VITE_API_BASE_URL env variable.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// ── Token management ────────────────────────────────────────────────────────

const TOKEN_KEY = 'dashboard_token';

export function getToken() {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;

    // Fast client-side sanity check to prevent UI flash.
    // If it's obviously malformed or expired, discard it immediately.
    const payloadB64 = token.split('.')[1];
    if (!payloadB64) return null;

    const payloadStr = atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadStr);

    // If expiration time exists and is in the past, token is dead.
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      localStorage.removeItem(TOKEN_KEY);
      return null;
    }

    return token;
  } catch {
    // Fails to parse base64 or JSON -> malformed token.
    localStorage.removeItem(TOKEN_KEY);
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // SSR or restricted context — silently ignore
  }
}

export function clearToken() {
  setToken(null);
}

// ── Core fetch wrapper ──────────────────────────────────────────────────────

class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

/**
 * Authenticated JSON fetch. Attaches the JWT Bearer token from localStorage,
 * parses the JSON response, and throws a structured ApiError on failure.
 */
async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let body = null;
    try {
      body = await res.json();
    } catch {
      // non-JSON error body — ignore
    }

    // Signal auth failure globally so AuthGate can react without
    // coupling every page component to authentication logic.
    if (res.status === 401 || res.status === 403) {
      window.dispatchEvent(new CustomEvent('toasty:unauthorized'));
    }

    throw new ApiError(
      body?.error || `Request failed: ${res.status}`,
      res.status,
      body,
    );
  }

  return res.json();
}

// ── Endpoint functions ──────────────────────────────────────────────────────

/** GET /api/metrics — overview metric cards */
export const fetchMetrics = () => request('/api/metrics');

/** GET /api/activity — recent pipeline events */
export const fetchActivity = () => request('/api/activity');

/** GET /api/quarantine — failed / quarantined triage events */
export const fetchQuarantine = () => request('/api/quarantine');

/** GET /api/duplicates — duplicate candidate pairs */
export const fetchDuplicates = () => request('/api/duplicates');

/** GET /api/redactions — PII redaction audit log */
export const fetchRedactions = () => request('/api/redactions');

/** GET /health — unauthenticated health probe */
export const fetchHealth = () => request('/health');
