# iPhone gotchas

Every one of these cost somebody an evening. The template handles them, but you need to know why,
because you will meet them again in an app you did not start from the template. Each point names the
rule in [STANDARD.md](../STANDARD.md) that checks it. Where a claim could not be confirmed from a
primary source it says so, and Appendix E of the standard lists what only a phone can answer.

## Installing

- **Add to Home Screen works from Safari, and since iOS 16.4 from Chrome, Edge, Firefox and
  others.** WebKit says a qualifying site opens as a standalone web app "no matter which browser
  added the website to the Home Screen". An earlier version of this page said the icon then opens
  inside that browser. That was wrong. Test in Safari first, because a third-party browser has to
  opt in to offering the option. (NW-DEV-001)
- **iOS 26 opens every site added to the Home Screen as a web app by default.** The person can switch
  "Open as Web App" off in the Add to Home Screen sheet, so tell them to leave it on. A manifest is
  no longer required, but keep it and the Apple meta tags: they still apply, and iOS 16.4 to 18 needs
  them. (NW-INS-006)
- **The icon.** A 180x180 opaque PNG in `apple-touch-icon` wins over the manifest icons, and iOS
  paints transparent pixels black. With no icon at all, iOS 16.4 and later draws a monogram, so the
  old story that it screenshots your page is outdated. A changed icon needs the app removed and added
  again (common practice, not verified). (NW-INS-004, NW-INS-005)
- **An installed app is bound to its origin: scheme, host and port.** Rename the machine or change
  the port and every installed copy becomes a different app. Decide first. (NW-NET-005)
- **`display: standalone`** is the one value that means the same everywhere. Fullscreen opens
  standalone and minimal-ui falls back to a browser shortcut. (NW-INS-002)

## Layout

- **`viewport-fit=cover`, or the safe-area insets are always zero.** The CSS looks right, the
  simulator looks right, and the phone clips the top row. (NW-SHL-001)
- **Add the inset to real padding**, never use it alone, and use all four sides. In landscape the
  left and right insets are not zero. (NW-SHL-002)
- **Size the shell with `height: 100%`**, not `100vh`. An installed app has no collapsing address
  bar, so 100% is stable. (NW-SHL-004)
- **Inputs render at 16px or larger**, or iOS zooms the page when one is focused and does not zoom
  back out. The fix is the size, not turning zoom off. (NW-SHL-005)
- **`user-scalable=no` does nothing on iPhone.** WebKit has ignored it since iOS 10. Elsewhere it
  blocks zoom and fails the accessibility audit. (NW-ACC-001)
- **The status bar.** The template uses `black`. `black-translucent` lets the header paint under the
  clock, but WebKit bug 301994 reports `env(safe-area-inset-top)` returning 0 under it on iOS 26.1
  and later, which puts the header under the time. Use it only after testing on the iOS you ship to.
  (NW-INS-008)
- **The keyboard shrinks the visual viewport and leaves the layout viewport alone.** If a screen has
  a text field, size it from `visualViewport`. `interactive-widget` is documented for Chrome on
  Android only. One developer reports an installed-app bug where the first keyboard open leaves the
  height permanently low; that is unverified on iOS 26. (NW-SHL-010)
- **Phone numbers.** Safari turns anything shaped like one into a call link. Switch it off with
  `format-detection`. (NW-SHL-009)

## Touch

- **Chrome is unselectable, content is selectable.** Without `user-select: none` on bars and
  buttons, every drag starts a text selection and a blue highlight chases your thumb. Put it on the
  whole body and people cannot copy their own data, and Look Up and translate stop working.
  (NW-SHL-007)
- **`touch-action: manipulation` on controls, never on `html` or `body`.** It drops the
  double-tap-zoom handling and keeps pan and pinch. One report from October 2025 says setting it on
  the root element stopped the keyboard appearing in an installed app (secondary, unverified).
  (NW-SHL-006)
- **`overscroll-behavior: none` on the page, `contain` on the list.** It needs iOS 16, so
  `overflow: hidden` on the root is the part that works everywhere. Whether `none` removes all
  rubber-banding on iOS 26 is not confirmed. (NW-SHL-003)
- **44px targets.** Apple's number. WCAG 2.2 sets a floor of 24px. (NW-ACC-011)
- **`-webkit-overflow-scrolling: touch` is obsolete.** The template no longer sets it.

## Knowing whether you are installed

- **Test three things.** An installed iOS app can report `display-mode: fullscreen` instead of
  `standalone` (WebKit bug 264218), and `navigator.standalone` is the old iOS-only flag. On iOS 26 a
  standalone app no longer implies a manifest. (NW-IOS-001)
- **Never parse the user agent for the iOS version.** Safari 26 reports a frozen one. Ask the person
  to read Settings, General, About. (NW-IOS-002)
- **There is no browser back button.** A screen below the first needs its own Back control.
  (NW-UIX-003)
- **External links.** Apple documents nothing here. Secondary sources say an out-of-scope link opens
  an in-app sheet, not Safari. Test it on your iOS and offer Copy link. (NW-DEV-005)

## Storage

- **The Home Screen app and Safari do not share storage.** Cookies, localStorage, IndexedDB and the
  service worker you set up in Safari do not exist in the installed app. WebKit calls this by design
  (bug 181849). Never do first-run setup in Safari. (NW-DAT-004)
- **Script-writable storage in a Safari tab is cleared after 7 days without interaction.** Installed
  Home Screen apps are exempt from that cap, and since Safari 17 an origin may use up to 60 percent
  of the disk. Treat it as a bonus and keep anything precious on the host. (NW-DAT-004)
- **What deleting and re-adding the icon does to storage is not documented.** Plan for it to be gone.

## Audio and voice: read this before designing anything voice-first

Two different things that people conflate. This table comes from one developer's field experience,
not from a primary source, so confirm it on your own phone:

| Event | Audio **capture** | Audio **playback** |
|---|---|---|
| Screen sleeps | **stops** | continues |
| Phone locks | stopped already | **continues** |
| App backgrounded | stops | continues briefly |

So a recording dies when the screen sleeps, and a podcast survives the lock screen. If your app
records, hold a Wake Lock (`navigator.wakeLock`) while recording. It is released whenever the app is
hidden, so re-acquire it on `visibilitychange`. **Version matters:** Wake Lock works in a Safari tab
from 16.4, but in an installed Home Screen app it did not work from 16.4 to 18.3 and works from 18.4
(WebKit bug 254545, fixed in the Safari 18.4 release notes). On an older phone, say plainly that
recording stops when the screen sleeps. (NW-IOS-004)

Pick the recorder format with `MediaRecorder.isTypeSupported`: MP4 with AAC always, WebM with Opus
only from 18.4. Convert on the server before transcription. Whether the microphone prompt comes back
on every launch of an installed app is not documented; do not promise either way.

## Notifications and other platform APIs

- **Web Push and badging work only in an installed app**, since iOS 16.4. The permission prompt must
  come from a tap, so put it behind a button. Declarative Web Push arrived in 18.4. (NW-DEV-006)
- **Not available in Safari on iPhone:** Background Sync, Web Bluetooth, WebUSB, Web Serial, WebHID,
  vibration, orientation lock. Give a fallback or drop the feature. A haptic can be had from a tap
  handler by clicking a hidden `input type=checkbox switch` (Safari 18), but that is a side effect of
  a form control, not an API, so never depend on it. (NW-IOS-004)
- **Manifest `shortcuts`, `screenshots` and `display_override`** are Chromium features.

## Things a home-screen web app cannot do

No Shortcuts intents, no widgets, no Live Activities, no share-sheet target, no App Store listing,
and no background execution: it does not run when closed.
