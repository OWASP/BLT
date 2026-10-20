import React from 'react';
import { ShieldOff } from 'lucide-react';

/**
 * Full-screen access denied screen shown when the dashboard detects
 * no token in localStorage or the backend returns 401/403.
 *
 * Intentionally stateless and prop-free: it exists only to inform,
 * not to offer a login flow (there is none — access is token-only).
 */
export default function AccessDenied() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-6 text-center">
      {/* Icon container — red tint matches the OWASP brand danger palette */}
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl border border-red-200 bg-red-50">
        <ShieldOff size={36} className="text-red-600" aria-hidden="true" />
      </div>

      <h1 className="text-2xl font-extrabold text-dark-base">Access Denied</h1>

      <p className="mt-3 max-w-sm text-sm leading-relaxed text-gray-500">
        You are not authorised to view the OWASP BLT-Toasty internal operations
        dashboard. A valid JWT token is required.
      </p>

      <p className="mt-6 text-xs text-gray-400">
        Contact your project lead to obtain an authorised token.
      </p>
    </div>
  );
}
