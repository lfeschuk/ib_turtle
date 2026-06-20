const CACHE_NAME = 'chess-codex-cache-v2';
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  'https://img.icons8.com/ios-filled/512/000000/chess-board.png',
  'https://img.icons8.com/ios-filled/192/000000/chess-board.png'
];

// Install Event: cache precache assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: clean up old caches and take control
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Stale-While-Revalidate with dynamic caching
self.addEventListener('fetch', (event) => {
  // Only handle GET requests (skip API POST calls, etc.)
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.match(event.request).then((cachedResponse) => {
        const fetchPromise = fetch(event.request).then((networkResponse) => {
          // If response is valid, clone it and save to cache
          if (networkResponse.status === 200) {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        }).catch((err) => {
          console.debug('Network fetch failed, serving from cache if available', err);
        });

        // Return cached response instantly if available, otherwise wait for network
        return cachedResponse || fetchPromise;
      });
    })
  );
});
