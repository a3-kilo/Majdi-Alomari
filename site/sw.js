const CACHE = 'majdi-academic-v15-routing';
const CORE = [
  './',
  './research/',
  './publications/',
  './profile/',
  './assets/site.css',
  './assets/site.js',
  './assets/favicon.svg',
  './assets/majdi-portrait-original.jpg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(CORE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys
        .filter(key => key.startsWith('majdi-') && key !== CACHE)
        .map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (!url.pathname.startsWith(new URL('./', self.registration.scope).pathname)) return;

  // Always look for updated pages, CSS and JS first, so a new deployment
  // cannot be held back by older cached navigation code.
  if (request.mode === 'navigate' || /\.(?:js|css)$/.test(url.pathname)) {
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          event.waitUntil(caches.open(CACHE).then(cache => cache.put(request, copy)));
        }
        return response;
      }).catch(async () => {
        const old = await caches.match(request);
        if (old) return old;
        if (request.mode === 'navigate') {
          const home = await caches.match(new URL('./', self.registration.scope));
          if (home) return home;
        }
        return Response.error();
      })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(cache => cache.put(request, copy)));
      }
      return response;
    }))
  );
});
