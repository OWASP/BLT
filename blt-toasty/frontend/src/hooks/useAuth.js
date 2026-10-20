import { useState, useEffect } from 'react';
import { getToken } from '../api';

/**
 * Returns whether the current session holds a valid-looking dashboard token.
 *
 * Two failure modes are handled:
 *  1. Token absent on mount  — user never set one.
 *  2. toasty:unauthorized event — backend rejected the token (expired / invalid).
 *
 * We deliberately do NOT decode or validate the JWT on the client side.
 * Client-side JWT validation is theatre: the real gate is the backend.
 * All we need to know is "does a token string exist, and did the backend
 * accept it?" — nothing more.
 */
export function useAuth() {
  // Presence check only — backend is the authority on validity.
  const [isAuthorized, setIsAuthorized] = useState(() => Boolean(getToken()));

  useEffect(() => {
    // If the backend returns 401/403, api.js fires this event.
    // We listen once per mount and lock the UI immediately.
    const handleUnauthorized = () => setIsAuthorized(false);
    window.addEventListener('toasty:unauthorized', handleUnauthorized);

    // Cleanup: remove listener when the component using this hook unmounts.
    return () => window.removeEventListener('toasty:unauthorized', handleUnauthorized);
  }, []); // Empty deps — listener is registered once, event-driven after that.

  return isAuthorized;
}
