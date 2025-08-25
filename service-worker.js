const CACHE_NAME = 'oathlink-ui-v1';
const ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.map(k => (k !== CACHE_NAME ? caches.delete(k) : null)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  const isAPI = /\/(compose|memory\/write|memory\/search|health|routes|openapi\.json)$/.test(url.pathname);
  if (isAPI) {
    e.respondWith(fetch(e.request).catch(() =>
      new Response(JSON.stringify({ ok:false, error:'offline', note:'API 請求無法離線' }),
        { headers:{'Content-Type':'application/json'} })
    ));
  } else {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});