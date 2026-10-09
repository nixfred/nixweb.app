# iPhone gotchas

Every one of these cost somebody an evening. They are all handled in `template/`, but you need to
know *why*, because you will meet them again in an app you did not start from the template.

## Installing

- **Install from Safari, and test there.** Since iOS 16.4 other browsers can Add to Home Screen too,
  but the icon then opens inside that browser rather than as its own app. If someone says "it didn't
  work", ask which browser and which iOS version before anything else.
- **The icon must be a real file.** Without `apple-touch-icon` iOS screenshots your page and uses
  that. It looks broken and people lose faith in the whole idea immediately.
- **`display: standalone`** is what removes the browser chrome. Without it you shipped a bookmark.
- **Scope matters.** A link outside the manifest `scope` opens in Safari and kicks the user out of
  your app. Keep navigation inside, or open external links deliberately in a new tab.

## Layout

- **`viewport-fit=cover` or the safe-area insets are always zero.** This is the one that fools
  people: the CSS looks right, the simulator looks right, and the phone clips the top row.
- **Add the inset to real padding**, never use it alone. `padding-top: env(safe-area-inset-top)`
  gives a cramped header on a phone with no notch.
- **The bottom inset is 34px of unreachable screen** on a modern iPhone. A tab bar without it has a
  row of buttons under the home indicator.
- **44px minimum touch target.** Apple's number, and it is right.

## Touch

- **`user-select: none` on chrome is the single biggest "feels cheap" fix.** Without it every drag
  starts a text selection and a blue highlight chases your thumb. Re-enable it on content the user
  might legitimately want to copy.
- **`touch-action: manipulation`** removes the 300ms double-tap-to-zoom delay without killing pinch
  zoom for people who need it.
- **`overscroll-behavior: none` on the page, `contain` on the list.** Otherwise the whole app
  rubber-bands and the header detaches from the top of the screen.
- **`-webkit-overflow-scrolling: touch`** on the scrolling box for native momentum.
- **`-webkit-tap-highlight-color: transparent`** kills the grey flash on every tap.

## Audio and voice — read this before designing anything voice-first

Two different things that people conflate, and Daniel hit both:

| Event | Audio **capture** | Audio **playback** |
|---|---|---|
| Screen sleeps | **stops** | continues |
| Phone locks | stopped already | **continues** |
| App backgrounded | stops | continues briefly |

So: **a recording dies when the screen sleeps, and a podcast survives the lock screen.** If your app
records, request a Wake Lock (`navigator.wakeLock`) while recording. It is released automatically
when the app is backgrounded, so you must re-acquire on `visibilitychange`. That is by design, not a
bug. **Version matters:** Wake Lock works in a Safari tab from 16.4, but in an installed Home Screen
app it does not work from 16.4 to 18.3 and works from 18.4 (WebKit bug 254545). On an older phone,
tell the user plainly that recording stops when the screen sleeps.

Microphone capture has its own installed-app quirks. The permission prompt can come back on launch or
when the page navigates, so keep a single page and one live stream. Safari records MP4 with AAC, and
WebM with Opus only from 18.4, so choose the format with `MediaRecorder.isTypeSupported` and convert
on the server before transcription.

Some capabilities are only honoured once the app is **installed to the home screen** rather than
running in a Safari tab. If a voice feature works for you and not for a tester, ask whether they
installed it.

## Things a home-screen web app cannot do

No Shortcuts intents, no widgets, no Live Activities, no share-sheet target, no background
execution, no App Store listing. Push notifications work on iOS 16.4+ **only once installed**, and
are fiddly. If you need any of the first four, you need a real app.
