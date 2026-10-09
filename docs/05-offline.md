# Offline, and failing honestly

## The actual goal

Not "works fully offline". For a front end onto a machine at home, offline means the data is gone by
definition. The goal is narrower and more important:

**When the tailnet is unreachable, the user sees YOUR app with YOUR message, not Safari's error
page.** A browser error page makes people think your app is broken. A banner saying "can't reach
home, showing the last thing I knew" makes them think the network is down, which is the truth.

## How the template does it

- The **service worker** caches the shell (HTML, CSS, JS, icons) on first load. A cold start with no
  network paints your app instantly.
- `/api/*` is **network-first with a cache fallback**: fresh data when home is reachable, the last
  known answer when it is not.
- `/ping` is **never cached**, because a cached 200 would tell you a dead host is alive.

## Do not trust `navigator.onLine`

It tells you the radio is up. It says `true` on coffee-shop wifi you have not logged into, and
`true` when your tailnet is down. The only honest test is asking the host:

```js
fetch('ping?t=' + Date.now(), { cache: 'no-store' }).then(r => r.ok).catch(() => false)
```

Re-check on `visibilitychange`, because phones freeze background tabs aggressively and your interval
timer did not run while the app was away.

## Versioning

Bump `VERSION` in `sw.js` when the shell changes, or phones will serve the old one for a long time.
The template uses `skipWaiting()` plus `clients.claim()` so a reload picks up the new version instead
of waiting for every tab to close. That is the right trade for a personal tool and the wrong one for
a product with users mid-task.
