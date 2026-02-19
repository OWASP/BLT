// Service Worker - caches static assets, API responses, and HTML pages for faster loads.

const CACHE_VERSION = 'blt-leaf-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;
const CDN_CACHE = `${CACHE_VERSION}-cdn`;

// Static assets to precache on install
const PRECACHE_URLS = [
    '/',
    '/index.html',
    '/how-it-works.html',
    '/how-it-works.js',
    '/static/logo.png'
];

// CDN resources to cache on first fetch
const CDN_ORIGINS = [
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com'
];

// API paths to cache with stale-while-revalidate
const CACHEABLE_API_PATHS = [
    '/api/prs',
    '/api/repos',
    '/api/rate-limit',
    '/api/status'
];

// Max age for API cache entries  - 5 minutes
const API_CACHE_MAX_AGE = 5 * 60 * 1000;

// Install
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
            .catch((err) => {
                console.warn('[SW] Precache failed (non-fatal):', err);
                return self.skipWaiting();
            })
    );
});

// Activate
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key.startsWith('blt-leaf-') && key !== STATIC_CACHE && key !== API_CACHE && key !== CDN_CACHE)
                    .map((key) => caches.delete(key))
            )
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Only handle GET requests
    if (request.method !== 'GET') return;

    // CDN resources
    if (CDN_ORIGINS.some((origin) => request.url.startsWith(origin))) {
        event.respondWith(cacheFirst(request, CDN_CACHE));
        return;
    }

    // GitHub API - stale-while-revalidate with longer TTL
    if (request.url.includes('api.github.com')) {
        event.respondWith(staleWhileRevalidate(request, API_CACHE, 30 * 60 * 1000));
        return;
    }

    // Same origin requests only from here
    if (url.origin !== self.location.origin) return;

    // API endpoints - stale-while-revalidate
    if (CACHEABLE_API_PATHS.some((p) => url.pathname.startsWith(p))) {
        event.respondWith(staleWhileRevalidate(request, API_CACHE, API_CACHE_MAX_AGE));
        return;
    }

    // HTML pages
    if (request.headers.get('accept')?.includes('text/html') ||
        url.pathname === '/' ||
        url.pathname.endsWith('.html')) {
        event.respondWith(networkFirst(request, STATIC_CACHE));
        return;
    }

    // All other static assets
    event.respondWith(cacheFirst(request, STATIC_CACHE));
});

// Return cached response if available, otherwise fetch and cache
async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        // If both cache and network fail, return a basic offline response
        return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
    }
}

// Try network, fall back to cache. Always update cache on success
async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
    }
}

// Return cached response immediately - then update the cache in the background. If no cache or cache is stale - fetch from network.
async function staleWhileRevalidate(request, cacheName, maxAge) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);

    // Background revalidation
    const fetchAndCache = fetch(request)
        .then((response) => {
            if (response.ok) {
                // Clone and store with a timestamp header for age checking
                const headers = new Headers(response.headers);
                headers.set('sw-cache-time', Date.now().toString());
                const timedResponse = new Response(response.clone().body, {
                    status: response.status,
                    statusText: response.statusText,
                    headers
                });
                cache.put(request, timedResponse);
            }
            return response;
        })
        .catch(() => cached); // If network fails

    if (cached) {
        // Check if the cached entry is still fresh
        const cacheTime = parseInt(cached.headers.get('sw-cache-time') || '0', 10);
        const age = Date.now() - cacheTime;

        if (age < maxAge) {
            fetchAndCache.catch(() => {});
            return cached;
        }
    }

    // No cache or stale cache - wait for network
    return fetchAndCache;
}

// Message handler for cache invalidation
self.addEventListener('message', (event) => {
    if (event.data?.type === 'INVALIDATE_API_CACHE') {
        caches.open(API_CACHE).then((cache) => {
            cache.keys().then((keys) => {
                const path = event.data.path;
                keys.forEach((key) => {
                    const keyUrl = new URL(key.url);
                    if (!path || keyUrl.pathname.startsWith(path)) {
                        cache.delete(key);
                    }
                });
            });
        });
    }

    if (event.data?.type === 'CLEAR_ALL_CACHES') {
        caches.keys().then((keys) =>
            Promise.all(keys.map((key) => caches.delete(key)))
        );
    }
});
