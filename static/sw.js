const CACHE_NAME = 'modern-print-v2';
const ASSETS = [
  '/',
  '/admin/login',
  '/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  // Only intercept standard page asset reads, do not intercept form submissions
  if (e.request.method !== 'GET') return;

  e.respondWith(
    fetch(e.request).then((response) => {
      // Dynamic network caching update
      const resClone = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(e.request, resClone));
      return response;
    }).catch(() => {
      // Fallback asset loader if web connectivity is lost completely
      return caches.match(e.request);
    })
  );
});