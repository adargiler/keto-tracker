/* Offline support. Pages come from the network when it answers within 3 seconds, otherwise from the cache. */
const CACHE = 'keto-97df295a98';
const SHELL = ['./', 'manifest.webmanifest', 'icon-180.png', 'icon-192.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  /* Only this app's old caches: the separate app in my-keto/ on the same site keeps its own. */
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('keto-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
function store(req, res) {
  if (res && (res.ok || res.type === 'opaque')) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
  return res;
}
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    e.respondWith((async () => {
      const cached = await caches.match(req, { ignoreSearch: true });
      const net = fetch(req).then(res => store(req, res));
      if (!cached) return net.catch(() => req.mode === 'navigate' ? caches.match('./') : Response.error());
      const timeout = new Promise(r => setTimeout(() => r(null), 3000));
      return (await Promise.race([net.catch(() => null), timeout])) || cached;
    })());
  } else if (/(^|\.)fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(m => m || fetch(req).then(res => store(req, res))));
  }
});
