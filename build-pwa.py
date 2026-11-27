#!/usr/bin/env python3
"""Build the home-screen (installable) version of the tracker into docs/.

index.html is the single source (it is also what gets published as the Claude artifact).
Run:  python3 build-pwa.py
"""
import hashlib, json, os, re
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'docs')
os.makedirs(OUT, exist_ok=True)

src = open(os.path.join(HERE, 'index.html'), encoding='utf8').read()
cut = src.index('<div id="app"')
head_part, body_part = src[:cut], src[cut:]
head_part = head_part.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')

BG, YOLK, INK = '#131110', '#f0b23e', '#291b02'

def icon(size, pad=0.0):
    """Egg yolk with a barbell across it. pad shrinks the art for maskable icons."""
    n = 1024
    im = Image.new('RGB', (n, n), BG)
    d = ImageDraw.Draw(im)
    def u(v):
        return (0.5 + (v - 0.5) * (1 - pad)) * n
    def box(x0, y0, x1, y1, fill, r=0.0):
        d.rounded_rectangle([u(x0), u(y0), u(x1), u(y1)], radius=r * n * (1 - pad), fill=fill)
    d.ellipse([u(0.13), u(0.13), u(0.87), u(0.87)], fill=YOLK)
    box(0.20, 0.475, 0.80, 0.525, INK, 0.02)
    for x0, x1, h in ((0.295, 0.375, 0.19), (0.625, 0.705, 0.19), (0.225, 0.28, 0.12), (0.72, 0.775, 0.12)):
        box(x0, 0.5 - h, x1, 0.5 + h, INK, 0.025)
    return im.resize((size, size), Image.LANCZOS)

icon(180).save(os.path.join(OUT, 'icon-180.png'))
icon(192).save(os.path.join(OUT, 'icon-192.png'))
icon(512).save(os.path.join(OUT, 'icon-512.png'))
icon(512, pad=0.2).save(os.path.join(OUT, 'icon-maskable-512.png'))

manifest = {
    'name': 'יומן קיטו וכוח', 'short_name': 'קיטו וכוח', 'lang': 'he', 'dir': 'rtl',
    'start_url': './', 'scope': './', 'display': 'standalone', 'orientation': 'portrait',
    'background_color': BG, 'theme_color': BG,
    'icons': [
        {'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
        {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
        {'src': 'icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ],
}
json.dump(manifest, open(os.path.join(OUT, 'manifest.webmanifest'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)

page = '''<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="קיטו וכוח">
<meta name="theme-color" content="#131110">
<meta name="robots" content="noindex,nofollow">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" type="image/png" href="icon-192.png">
<style>body{margin:0;padding-top:env(safe-area-inset-top,0px)}[hidden]{display:none!important}</style>
''' + head_part + '''</head>
<body>
''' + body_part + '''
<script>
if('serviceWorker' in navigator){ window.addEventListener('load',function(){ navigator.serviceWorker.register('sw.js').catch(function(){}); }); }
</script>
</body>
</html>
'''
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf8').write(page)

version = hashlib.sha1(page.encode('utf8')).hexdigest()[:10]
sw = '''/* Offline support. Pages come from the network when it answers within 3 seconds, otherwise from the cache. */
const CACHE = 'keto-%s';
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
  } else if (/(^|\\.)fonts\\.(googleapis|gstatic)\\.com$/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(m => m || fetch(req).then(res => store(req, res))));
  }
});
''' % version
open(os.path.join(OUT, 'sw.js'), 'w', encoding='utf8').write(sw)
open(os.path.join(OUT, '.nojekyll'), 'w').close()
print('built docs/ version', version)
