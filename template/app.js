/* nixweb.app template app.js
   Three jobs: register the service worker, know whether we can reach home, and
   handle the phone behaviours that CSS cannot. */

// ---------------------------------------------------------------------------
// 1. Service worker. Without this, a dead tailnet shows Safari's error page and
//    the user thinks YOUR app is broken.
// ---------------------------------------------------------------------------
if ('serviceWorker' in navigator) {
  // Registered after load so it never competes with first paint.
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('sw.js').catch(function (e) {
      console.warn('[nixweb] service worker not registered:', e.message);
    });
  });
}

// ---------------------------------------------------------------------------
// 2. Reachability. navigator.onLine only tells you the RADIO is up. It says yes
//    on a coffee-shop wifi that has not let you past the captive portal, and yes
//    when your tailnet is down. So we actually ask the host.
// ---------------------------------------------------------------------------
var netDot = document.getElementById('net');
var banner = document.getElementById('offline');
var hostEl = document.getElementById('hostname');
if (hostEl) hostEl.textContent = location.hostname || 'home';

function ping() {
  // cache:'no-store' so a cached 200 never masks a dead host.
  return fetch('ping?t=' + Date.now(), { cache: 'no-store' })
    .then(function (r) { return r.ok; })
    .catch(function () { return false; });
}

function setOnline(up) {
  if (netDot) netDot.classList.toggle('off', !up);
  if (banner) banner.hidden = up;
}

function checkNet() { ping().then(setOnline); }
checkNet();
setInterval(checkNet, 20000);
window.addEventListener('online', checkNet);
window.addEventListener('offline', function () { setOnline(false); });
// Phones aggressively freeze background tabs; re-check the moment we come back.
document.addEventListener('visibilitychange', function () {
  if (!document.hidden) checkNet();
});

// ---------------------------------------------------------------------------
// 3. Are we installed, or still in a browser tab? Useful for telling the user
//    to install, and for anything that only works once installed (iOS push).
// ---------------------------------------------------------------------------
var standalone = window.matchMedia('(display-mode: standalone)').matches ||
                 window.navigator.standalone === true;
var modeEl = document.getElementById('mode');
if (modeEl) {
  modeEl.textContent = standalone
    ? 'Running as an installed app. No browser chrome.'
    : 'Running in a browser tab. Add to Home Screen to install.';
}
var servedEl = document.getElementById('served');
if (servedEl) servedEl.textContent = 'Served from ' + location.host;

// ---------------------------------------------------------------------------
// 4. Tabs. Kept trivially simple on purpose: the page never navigates, because a
//    navigation in an installed web app can kick you out to Safari if the target
//    is outside the manifest scope.
// ---------------------------------------------------------------------------
document.querySelectorAll('.tab').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('on'); });
    b.classList.add('on');
    // render(b.dataset.view)
  });
});

var refresh = document.getElementById('refresh');
if (refresh) refresh.addEventListener('click', function () { location.reload(); });

// ---------------------------------------------------------------------------
// 5. Wake Lock. REQUIRED READING if your app records audio.
//
//    Two different things people confuse:
//      - Screen SLEEPS   -> audio CAPTURE stops. Your recording is cut off.
//      - Phone LOCKS     -> audio PLAYBACK keeps going. Podcasts work fine.
//
//    Wake Lock keeps the screen awake so capture survives. It works in a Safari tab
//    from iOS 16.4, but in an INSTALLED home-screen app only from iOS 18.4 (it did
//    nothing on 16.4 to 18.3, WebKit bug 254545). It is released automatically when
//    you background the app, so you must re-acquire on visibilitychange. By design.
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
    // Refused when the tab is not visible, or on battery saver. Not fatal:
    // tell the user their recording may stop if the screen sleeps.
    console.warn('[nixweb] wake lock refused:', e.message);
  }
}
document.addEventListener('visibilitychange', function () {
  if (!document.hidden && wakeLock === null && window.__nixwebRecording) keepAwake(true);
});
window.nixweb = { keepAwake: keepAwake, ping: ping, standalone: standalone };
