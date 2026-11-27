#!/usr/bin/env python3
"""Build the home-screen version of "הקיטו שלי" into docs/my-keto/.

my-keto/app.html is the single source. It is a separate app from the tracker in index.html:
its own address (/keto-tracker/my-keto/), its own storage key and its own offline cache.
Run:  python3 my-keto/build.py
"""
import hashlib, json, math, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'docs', 'my-keto')
os.makedirs(OUT, exist_ok=True)

BG, SKIN, FLESH, PIT = '#f7f3ec', '#3f6b39', '#cfe3a2', '#8a5a34'


def pear(cx, cy, h, w, n=360):
    """Avocado outline: narrow at the top, round at the bottom."""
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        y = cy - h * math.cos(th)
        k = 0.62 + 0.38 * (1 - math.cos(th)) / 2
        x = cx + w * math.sin(th) * k
        pts.append((x, y))
    return pts


def icon(size, pad=0.0):
    n = 1024
    im = Image.new('RGB', (n, n), BG)
    d = ImageDraw.Draw(im)
    s = 1 - pad

    def u(p):
        return [((0.5 + (x - 0.5) * s) * n, (0.5 + (y - 0.5) * s) * n) for x, y in p]

    d.polygon(u(pear(0.5, 0.52, 0.38, 0.33)), fill=SKIN)
    d.polygon(u(pear(0.5, 0.535, 0.32, 0.275)), fill=FLESH)
    cx, cy, r = 0.5, 0.63, 0.125
    (x0, y0), (x1, y1) = u([(cx - r, cy - r), (cx + r, cy + r)])
    d.ellipse([x0, y0, x1, y1], fill=PIT)
    (x0, y0), (x1, y1) = u([(cx - 0.065, cy - 0.075), (cx - 0.02, cy - 0.03)])
    d.ellipse([x0, y0, x1, y1], fill='#a9764c')
    return im.resize((size, size), Image.LANCZOS)


icon(180).save(os.path.join(OUT, 'icon-180.png'))
icon(192).save(os.path.join(OUT, 'icon-192.png'))
icon(512).save(os.path.join(OUT, 'icon-512.png'))
icon(512, pad=0.2).save(os.path.join(OUT, 'icon-maskable-512.png'))

manifest = {
    'name': 'הקיטו שלי', 'short_name': 'הקיטו שלי', 'lang': 'he', 'dir': 'rtl',
    'start_url': './', 'scope': './', 'display': 'standalone', 'orientation': 'portrait',
    'background_color': BG, 'theme_color': BG,
    'icons': [
        {'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
        {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
        {'src': 'icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ],
}
json.dump(manifest, open(os.path.join(OUT, 'manifest.webmanifest'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)

src = open(os.path.join(HERE, 'app.html'), encoding='utf8').read()
assert '<!--SW-->' in src
page = src.replace('<!--SW-->', '''<script>
if('serviceWorker' in navigator){ window.addEventListener('load',function(){ navigator.serviceWorker.register('sw.js').catch(function(){}); }); }
</script>''')
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf8').write(page)

version = hashlib.sha1(page.encode('utf8')).hexdigest()[:10]
sw = '''/* Offline support. Pages come from the network when it answers within 3 seconds, otherwise from the cache. */
const CACHE = 'myketo-%s';
const SHELL = ['./', 'manifest.webmanifest', 'icon-180.png', 'icon-192.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  /* Only this app's old caches: another app on the same site keeps its own. */
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('myketo-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
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
      const cached = await caches.match(req, { ignoreSearch: true, cacheName: CACHE });
      const net = fetch(req).then(res => store(req, res));
      if (!cached) return net.catch(() => req.mode === 'navigate' ? caches.match('./', { cacheName: CACHE }) : Response.error());
      const timeout = new Promise(r => setTimeout(() => r(null), 3000));
      return (await Promise.race([net.catch(() => null), timeout])) || cached;
    })());
  } else if (/(^|\\.)fonts\\.(googleapis|gstatic)\\.com$/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(m => m || fetch(req).then(res => store(req, res))));
  }
});
''' % version
open(os.path.join(OUT, 'sw.js'), 'w', encoding='utf8').write(sw)
print('built docs/my-keto/ version', version)
