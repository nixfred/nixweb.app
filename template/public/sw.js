/* nixweb.app service worker. Goal: when the tailnet host is unreachable, the person sees YOUR
   app with YOUR message, not Safari's error page. It is not a general offline database.
   Bump VERSION on every change to a shell file: the browser installs a new worker only when
   this file's bytes change (NW-OFF-002). */

const PREFIX = 'nixweb-';
const VERSION = '1';
const CACHE = PREFIX + VERSION;
const API = PREFIX + VERSION + '-api';
// The app shell: everything needed to paint a useful screen with no network. Every entry must
// exist, or the whole install is discarded (NW-OFF-003).
const SHELL = ['./', 'index.html', 'app.css', 'app.js', 'manifest.webmanifest',
               'icons/icon-180.png', 'icons/icon-192.png', 'icons/icon-512.png'];

self.addEventListener('install', (e) => {
  // cache: 'reload' reads past the HTTP cache. Without it addAll can store a stale copy of
  // app.js and the update ships nothing (NW-OFF-007). No skipWaiting here: the person decides
  // when to switch (NW-OFF-009).
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL.map((u) => new Request(u, { cache: 'reload' })))));
});

self.addEventListener('activate', (e) => {
  // Delete only OUR older caches, by prefix, so a sibling app on the same origin survives.
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith(PREFIX) && k !== CACHE && k !== API)
                                      .map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', (e) => {
  const d = e.data || {};
  if (d.type === 'SKIP_WAITING') self.skipWaiting();
  if (d.type === 'VERSION' && e.ports && e.ports[0]) e.ports[0].postMessage({ version: VERSION });
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;             // never cache writes
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;   // never cache other hosts
  if (url.pathname.endsWith('/ping')) return;   // the reachability probe must be real
  if (url.pathname.startsWith('/api/')) { e.respondWith(apiNetworkFirst(e)); return; }
  e.respondWith(shell(req));
});

// The shell: cache first. It changes rarely, and this is what makes a cold start instant.
async function shell(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req);
  if (hit) return hit;
  try {
    return await fetch(req);
  } catch (err) {
    // Only a NAVIGATION may fall back to the shell. HTML returned for a failed script or image
    // breaks parsing and hides the real error (NW-OFF-006).
    if (req.mode === 'navigate') {
      const index = await cache.match('index.html');
      if (index) return index;
    }
    return Response.error();
  }
}

// API data: network first, so fresh data wins whenever home is reachable. A cached answer is
// only a fallback, is marked as one, and never includes a 4xx or 5xx, a no-store or private
// response, or more than 50 entries (NW-OFF-005, NW-OFF-013).
async function apiNetworkFirst(e) {
  const req = e.request;
  const cache = await caches.open(API);
  try {
    const res = await fetch(req);
    const cc = res.headers.get('cache-control') || '';
    if (res.ok && res.type === 'basic' && !/no-store|private/i.test(cc)) {
      e.waitUntil(cache.put(req, res.clone()).then(() => trim(cache, 50)));
    }
    return res;
  } catch (err) {
    const hit = await cache.match(req);
    if (!hit) return Response.error();
    const h = new Headers(hit.headers);
    h.set('X-From-Cache', '1');
    return new Response(hit.body, { status: hit.status, statusText: hit.statusText, headers: h });
  }
}

async function trim(cache, max) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}
