/* nixweb.app service worker.
   Goal: when the tailnet is unreachable, the user sees YOUR app with YOUR message,
   not Safari's error page. It is NOT a general offline database. */

const VERSION = 'nixweb-v1';
// The app shell: everything needed to paint a useful screen with no network.
const SHELL = ['./', 'index.html', 'app.css', 'app.js', 'manifest.webmanifest', 'icons/icon-180.png'];

self.addEventListener('install', (e) => {
  // skipWaiting so a reload picks up the new version instead of waiting for every
  // tab to close. On a personal tool that is what you want.
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;             // never cache writes
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;   // never cache other hosts
  if (url.pathname.endsWith('/ping')) return;   // the reachability probe must be real

  // API calls: network first, so you always get fresh data when home is reachable,
  // and the last known answer when it is not.
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(VERSION).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Shell: cache first. It changes rarely and this is what makes a cold start instant.
  e.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).catch(() => caches.match('index.html')))
  );
});
