const CACHE_NAME = 'airupi-cache-v1';
const ASSETS = [
  '/',
  '/static/js/qrcode.min.js',
  '/static/js/jsQR.min.js',
  '/static/js/nacl-fast.min.js'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});