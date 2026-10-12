/* nixweb.app template app.js. Rule IDs (NW-...) point at STANDARD.md in the nixweb.app repo.
   Jobs: show errors, register the service worker and offer updates, know whether the host is
   reachable, and handle the phone behaviours CSS cannot. */
'use strict';

var byId = function (id) { return document.getElementById(id); };
var netDot = byId('net'), netLabel = byId('netlabel'), banner = byId('offline');
var updateEl = byId('update'), fatalEl = byId('fatal'), versionEl = byId('version');

// ---------------------------------------------------------------------------
// 1. NW-OFF-012: an error paints a screen, never a blank page. Registered first so it also
//    covers startup. One card is enough, so a broken handler cannot loop.
// ---------------------------------------------------------------------------
function fatal(message) {
  if (!fatalEl || fatalEl.firstChild) return;
  var p = document.createElement('span');
  p.textContent = 'Something broke: ' + message;
  var b = document.createElement('button');
  b.type = 'button';
  b.textContent = 'Reload';
  b.addEventListener('click', function () { location.reload(); });
  fatalEl.appendChild(p);
  fatalEl.appendChild(b);
}
window.addEventListener('error', function (e) { fatal(e.message || 'script error'); });
window.addEventListener('unhandledrejection', function (e) {
  fatal(String((e.reason && e.reason.message) || e.reason || 'unhandled promise rejection'));
});

// ---------------------------------------------------------------------------
// 2. NW-DAT-003: storage can be blocked, full or evicted, so every access is guarded and
//    only small flags live here. Anything larger belongs in IndexedDB, anything precious
//    on the host.
// ---------------------------------------------------------------------------
var store = {
  get: function (k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
  set: function (k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* private mode or full: carry on */ } }
};

// ---------------------------------------------------------------------------
// 3. NW-OFF-011: every fetch has a timeout. A sleeping host over Tailscale often hangs instead
//    of refusing. A controller plus a timer, because AbortSignal.timeout pauses while a page
//    sits in the back-forward cache.
// ---------------------------------------------------------------------------
function nwFetch(url, opts, ms) {
  var ctl = new AbortController();
  var t = setTimeout(function () { ctl.abort(); }, ms || 5000);
  return fetch(url, Object.assign({}, opts, { signal: ctl.signal })).finally(function () { clearTimeout(t); });
}

// ---------------------------------------------------------------------------
// 4. NW-OFF-010: reachability is probed, never guessed. navigator.onLine says the radio is up;
//    it is true on a captive-portal wifi and when the tailnet is down. cache:'no-store' so a
//    cached 200 can never mask a dead host.
// ---------------------------------------------------------------------------
var lastOk = Number(store.get('nixweb.lastOk')) || 0;

function stamp(ms) {
  try { return new Intl.DateTimeFormat(undefined, { timeStyle: 'short' }).format(new Date(ms)); }
  catch (e) { return new Date(ms).toLocaleTimeString(); }
}

function ping() {
  return nwFetch('ping?t=' + Date.now(), { cache: 'no-store' }, 4000)
    .then(function (r) { return r.ok; })
    .catch(function () { return false; });
}

function setOnline(up) {
  if (netDot) netDot.classList.toggle('off', !up);
  if (netLabel) netLabel.textContent = up ? 'online' : 'unreachable';
  if (!banner) return;
  if (up) {
    lastOk = Date.now();
    store.set('nixweb.lastOk', String(lastOk));
    banner.textContent = '';
  } else {
    banner.textContent = "Can't reach " + (location.hostname || 'home') + '. Showing the last thing I knew' +
      (lastOk ? ' (last contact ' + stamp(lastOk) + ').' : '.');
  }
}

function checkNet() { return ping().then(setOnline); }
checkNet();
setInterval(checkNet, 20000);
// online and offline are only triggers to ask again, never answers.
window.addEventListener('online', checkNet);
window.addEventListener('offline', checkNet);

// ---------------------------------------------------------------------------
// 5. NW-IOS-003: lifecycle events, never unload. An installed iOS app is suspended and can be
//    killed in the background with no event at all, and a page restored from the back-forward
//    cache runs no script, so ask again on the way back.
// ---------------------------------------------------------------------------
var reg = null;
document.addEventListener('visibilitychange', function () {
  if (document.hidden) return; // nothing to save here; a real app saves on hidden and on pagehide
  checkNet();
  if (reg) reg.update().catch(function () { /* offline: try again next time */ });
  if (wakeLock === null && window.__nixwebRecording) keepAwake(true);
});
window.addEventListener('pageshow', function (e) { if (e.persisted) checkNet(); });

// ---------------------------------------------------------------------------
// 6. Service worker and NW-OFF-009 user-gated updates. A new worker waits; the person taps;
//    the page reloads once. The first install must not reload the page it just loaded.
// ---------------------------------------------------------------------------
var hadController = !!(navigator.serviceWorker && navigator.serviceWorker.controller);
var reloading = false;

function offerUpdate(worker) {
  if (!updateEl) return;
  updateEl.textContent = '';
  var s = document.createElement('span');
  s.textContent = 'Update ready.';
  var b = document.createElement('button');
  b.type = 'button';
  b.textContent = 'Reload to update';
  b.addEventListener('click', function () { worker.postMessage({ type: 'SKIP_WAITING' }); });
  updateEl.appendChild(s);
  updateEl.appendChild(b);
}

// NW-UIX-004: show the running version. The worker owns it, so ask the worker.
function askVersion() {
  navigator.serviceWorker.ready.then(function (r) {
    if (!r.active || !versionEl) return;
    var ch = new MessageChannel();
    ch.port1.onmessage = function (e) { versionEl.textContent = e.data.version; };
    r.active.postMessage({ type: 'VERSION' }, [ch.port2]);
  });
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    // NW-OFF-008: a stable URL and updateViaCache none, so the worker script is always re-fetched.
    navigator.serviceWorker.register('sw.js', { updateViaCache: 'none' }).then(function (r) {
      reg = r;
      if (r.waiting && navigator.serviceWorker.controller) offerUpdate(r.waiting);
      r.addEventListener('updatefound', function () {
        var w = r.installing;
        if (!w) return;
        w.addEventListener('statechange', function () {
          if (w.state === 'installed' && navigator.serviceWorker.controller) offerUpdate(w);
        });
      });
      askVersion();
    }).catch(function (e) { console.warn('[nixweb] service worker not registered:', e.message); });
  });
  navigator.serviceWorker.addEventListener('controllerchange', function () {
    if (!hadController) { hadController = true; return; }
    if (reloading) return;
    reloading = true;
    location.reload();
  });
}

// ---------------------------------------------------------------------------
// 7. NW-IOS-001: installed or still in a tab? An installed iOS app can report display-mode
//    fullscreen instead of standalone (WebKit bug 264218), and navigator.standalone is the
//    old iOS-only flag, so test all three. On iOS 26 standalone no longer implies a manifest.
// ---------------------------------------------------------------------------
var standalone = window.matchMedia('(display-mode: standalone)').matches ||
                 window.matchMedia('(display-mode: fullscreen)').matches ||
                 window.navigator.standalone === true;
var modeEl = byId('mode');
if (modeEl) {
  modeEl.textContent = standalone
    ? 'Running as an installed app. No browser chrome.'
    : 'Running in a browser tab. Add to Home Screen to install.';
}
var servedEl = byId('served');
if (servedEl) servedEl.textContent = 'Served from ' + location.host;

// ---------------------------------------------------------------------------
// 8. Tabs. Kept trivially simple: the page never navigates, so nothing can leave the manifest
//    scope. aria-current tells a screen reader which one is active (NW-ACC-009). When a view
//    really changes, also move focus to its heading and update document.title.
// ---------------------------------------------------------------------------
document.querySelectorAll('.tab').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab').forEach(function (x) {
      x.classList.remove('on');
      x.removeAttribute('aria-current');
    });
    b.classList.add('on');
    b.setAttribute('aria-current', 'page');
  });
});

var refresh = byId('refresh');
if (refresh) refresh.addEventListener('click', function () { location.reload(); });

// ---------------------------------------------------------------------------
// 9. Wake Lock. Optional: read this if the app records audio. A sleeping screen stops audio
//    CAPTURE; playback survives the lock screen. A Safari tab can hold a wake lock from iOS
//    16.4, an installed app only from iOS 18.4 (WebKit bug 254545). It is released whenever
//    the app is hidden, so it is re-acquired on visibilitychange above. NW-IOS-004.
// ---------------------------------------------------------------------------
var wakeLock = null;
async function keepAwake(on) {
  try {
    if (on && 'wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release', function () { wakeLock = null; });
    } else if (wakeLock) {
      await wakeLock.release();
      wakeLock = null;
    }
  } catch (e) {
    // Refused when the page is hidden or on low power. Not fatal: tell the person that
    // recording may stop when the screen sleeps.
    console.warn('[nixweb] wake lock refused:', e.message);
  }
}
window.nixweb = { keepAwake: keepAwake, ping: ping, fetch: nwFetch, standalone: standalone };
