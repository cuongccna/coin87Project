const CACHE_NAME = 'coin87-v1';
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/icon-192.png',
  '/globals.css'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 1. API Strategy: Stale-While-Revalidate (Conceptual for now, assuming /api path)
  // "Coin87 must feel reliable even when the network is not."
  // We serve cached content immediately, then update in background.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(event.request).then((cachedResponse) => {
          const fetchPromise = fetch(event.request)
            .then((networkResponse) => {
              cache.put(event.request, networkResponse.clone());
              return networkResponse;
            })
            .catch(() => {
              // Network failed. If we have no cache, we return nothing/error handled by UI.
              // Logic: The UI handles the empty state if fetch fails and no cache exists.
              // Just return undefined here to let the promise chain resolve.
              return cachedResponse; 
            });

          return cachedResponse || fetchPromise;
        });
      })
    );
    return;
  }

  // 2. Static Assets: Cache First
  // "Graceful degradation under poor connectivity"
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request).catch(() => {
        // Fallback or offline page can go here, but for now we just fail gracefully
        // as per "No error screens" rule (UI handles content).
        return new Response(null, { status: 404 });
      });
    })
  );
});
