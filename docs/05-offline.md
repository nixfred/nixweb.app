# Offline, and failing honestly

## The actual goal

Not "works fully offline". For a front end onto a machine at home, offline means the data is gone by
definition. The goal is narrower and more important:

**When the tailnet is unreachable, the user sees YOUR app with YOUR message, not Safari's error
page.** A browser error page makes people think your app is broken. A banner saying "can't reach
home, showing the last thing I knew, last contact 14:02" makes them think the network is down, which
is the truth. (NW-DEV-002)

This was tested in a real browser: with the server stopped and the app relaunched, it painted from
the service worker cache and said it could not reach the host.

## How the template does it

- The **service worker** precaches the shell (HTML, CSS, JS, icons) on first load with
  `cache: 'reload'`, so it can never store a stale copy from the browser's HTTP cache (NW-OFF-007).
  A cold start with no network paints your app instantly.
- A failed **navigation** falls back to the cached shell. A failed script, image or JSON request does
  not: HTML returned in place of `app.js` breaks parsing and hides the real error (NW-OFF-006).
- `/api/*` is **network first**, with a cache fallback that is marked `X-From-Cache`. Only good
  responses are cached (never a 4xx or 5xx), never one marked `no-store` or `private`, and no more
  than 50 entries (NW-OFF-005, NW-OFF-013).
- `/ping` is **never cached**, because a cached 200 would tell you a dead host is alive.
- **None of this runs over plain `http://`.** Browsers only register a service worker in a secure
  context, and `http://HOST.TAILNET.ts.net` is not one. That is why `nixweb serve` puts HTTPS in
  front: see [04](04-https-and-tailscale.md).

## Do not trust `navigator.onLine`

It tells you the radio is up. It says `true` on coffee-shop wifi you have not logged into, and `true`
when your tailnet is down. The only honest test is asking the host, with a timeout, because a host
that is asleep over Tailscale often hangs instead of refusing (NW-OFF-010, NW-OFF-011):

```js
function nwFetch(url, opts, ms) {
  var ctl = new AbortController();
  var t = setTimeout(function () { ctl.abort(); }, ms || 5000);
  return fetch(url, Object.assign({}, opts, { signal: ctl.signal })).finally(function () { clearTimeout(t); });
}
nwFetch('ping?t=' + Date.now(), { cache: 'no-store' }, 4000).then(r => r.ok).catch(() => false)
```

A controller and a timer, not `AbortSignal.timeout`, because that timer pauses while a page sits in
the back-forward cache. Re-check on `visibilitychange` and on `pageshow`, because phones freeze
background pages and your interval timer did not run while the app was away (NW-IOS-003).

## Updates

The browser installs a new service worker only when the bytes of `sw.js` change, so **bump `VERSION`
whenever a shell file changes.** Nothing else you edit alters `sw.js`, and the old worker will keep
serving the old `app.js` until you do (NW-OFF-002).

The template does not call `skipWaiting()` on install. A new worker waits, the page shows "Update
ready" with a button, and tapping it sends `SKIP_WAITING`, after which the page reloads once. That
is the safe default: `skipWaiting` lets a page that loaded under version 1 fetch version 2 resources
mid-session. The first install must not reload the page it just loaded, so the page remembers
whether it had a controller (NW-OFF-009).

The page also calls `registration.update()` whenever it becomes visible, because an installed iOS
app can stay resident for days and a check on navigation may not happen. The running version is shown
on screen, so "which version am I on?" has an answer (NW-UIX-004). This whole flow was tested in a
real browser. How soon an installed iOS 26 app sees a new worker is not documented; see
NW-DEV-004.

## When a write fails

Background Sync is not in Safari, so a service worker cannot flush a queue on iOS. If the app sends
writes, keep an outbox in IndexedDB, show each one as pending, and replay in order when the app opens,
becomes visible, comes back online or answers `/ping`. Every write carries an `Idempotency-Key` made
when the person acted and reused on each retry, and the server returns the stored answer for a
repeated key, because a write can succeed while its response is lost (NW-DAT-001, NW-DAT-002). Decide
the conflict rule before shipping: last write wins with a version check, or reject with 409 and show
the server copy (NW-DAT-005).

## Storage honesty

Everything on the device is a cache or a short outbox. Script-writable storage in a Safari tab is
cleared after 7 days without interaction. Installed apps are exempt, but treat that as a bonus.
The installed app does not share storage with Safari, so first-run state belongs on the host
(NW-DAT-004).
