import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Generic async data-fetching hook.
 *
 * @param {() => Promise<T>} fetcher — API function that returns a promise.
 * @param {Object}  opts
 * @param {T}       opts.fallback     — value while loading or on error (defaults to null).
 * @param {boolean} opts.immediate    — fetch on mount (default true).
 * @param {number}  opts.pollMs       — if set, re-fetches at this interval.
 *
 * @returns {{ data: T, loading: boolean, error: Error|null, refetch: () => void }}
 */
export function useApi(fetcher, { fallback = null, immediate = true, pollMs = 0 } = {}) {
  const [data, setData] = useState(fallback);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      if (mountedRef.current) {
        setData(result);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetcher]);

  useEffect(() => {
    mountedRef.current = true;
    if (immediate) {
      execute();
    }
    return () => {
      mountedRef.current = false;
    };
  }, [execute, immediate]);

  // Optional polling
  useEffect(() => {
    if (!pollMs || pollMs <= 0) return;
    const id = setInterval(execute, pollMs);
    return () => clearInterval(id);
  }, [execute, pollMs]);

  return { data, loading, error, refetch: execute };
}
