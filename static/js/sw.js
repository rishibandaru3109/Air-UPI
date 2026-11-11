const CACHE_NAME = 'airupi-cache-v2';
const ASSETS = [
  '/',
  '/manifest.json',
  '/static/js/qrcode.min.js',
  '/static/js/jsQR.min.js',
  '/static/js/nacl-fast.min.js'
];

// Install: pre-cache core assets
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate: clean up old caches
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch: network-first for API, cache-first for static assets
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // Never cache API requests or service worker itself
  if (url.pathname.startsWith('/api/') || url.pathname === '/sw.js') {
    e.respondWith(fetch(e.request));
    return;
  }

  // Cache-first for everything else (static assets, HTML shell)
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((response) => {
        // Cache successful GET responses
        if (response.ok && e.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return response;
      });
    })
  );
});
