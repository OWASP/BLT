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
    return localStorage.getItem(TOKEN_KEY);
  } catch {
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
