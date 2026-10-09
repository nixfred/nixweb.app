# nixweb.app

**Your own tools, on your phone, as home-screen apps. No Xcode, no developer account, no App Store, no review.**

A skeleton and a method for building iPhone (and Android) apps that are web apps, served off a machine
you already own: `gus`, `vic`, `fnix`, or a VPS (`red`, `blu`, `whi`), reached over Tailscale and
nowhere else.

---

## Where this came from

Daniel Lienemann, four weeks into building his own AI stack, mentioned in passing on 2026-10-08 that
his phone apps were "just web apps". Fred had never built an iPhone app because he assumed Xcode, a
signing certificate and App Store review stood in the way. They do not.

> **Fred:** "What you taught me tonight is making a web app, and it's indistinguishable. You're
> skipping 90% of the hard shit and going straight to the benefit."
>
> **Daniel:** "You just open it once in Safari, and then Share, Add to Home Screen, and that's all
> you have to do."

This repo is that conversation turned into something you can run.

---

## The whole idea in six lines

1. Your tool already serves HTTP on some port on one of your machines.
2. Keep it on `127.0.0.1` and put `tailscale serve` in front: HTTPS, tailnet only.
3. Add a `manifest.webmanifest`, a handful of Apple meta tags, and a real icon.
4. Open it in **Safari** on the phone. Share. **Add to Home Screen**.
5. It now has its own icon, its own window with no browser chrome, and its own slot in the app switcher.
6. Changing it is `git push` and a reload. No review, no version bump, no 30 percent.

---

## Quickstart

```bash
# 1. Make a new app from the template
~/Projects/nixweb.app/bin/nixweb new mytool

# 2. Serve it on the tailnet over HTTPS (python stays on 127.0.0.1)
~/Projects/nixweb.app/bin/nixweb serve mytool 8731

# 3. The command prints the exact URL to open on your phone, e.g.
#    https://gus.tail0940f.ts.net:8731
#    Open it in SAFARI, Share, Add to Home Screen.

# 4. Make it survive a reboot
~/Projects/nixweb.app/bin/nixweb install mytool 8731   # writes a systemd --user unit
```

---

## What the template already handles

These are the things that make a web page feel like a cheap web page instead of an app. Every one of
them is in `template/` already.

| Trap | What it looks like | Handled by |
|---|---|---|
| Text selects while you drag | Blue highlight everywhere, dragging breaks | `user-select: none` on chrome, kept **on** for content |
| Content under the notch | Top row unreadable on a modern iPhone | `viewport-fit=cover` + `env(safe-area-inset-*)` |
| The whole page bounces | Rubber-band scroll over the entire app | `overscroll-behavior: none`, page fixed, lists scroll |
| 300ms tap lag | Everything feels half a second behind | `touch-action: manipulation` |
| Default globe icon | Looks broken on the home screen | `apple-touch-icon` + manifest icons |
| Browser chrome visible | It is obviously a website | `display: standalone` |
| Dead tailnet shows a browser error | Looks like your app broke | service worker shell cache (needs HTTPS, so `nixweb serve` provides it) |
| "Can't reach home" on first run | Offline banner on a healthy app | `server.py` answers `/ping`; a bare static server 404s it |
| `.git` and `.env` readable | Whole history served to the tailnet | `server.py` 404s any dotfile path |
| Recording stops when the screen sleeps | Voice features silently fail | Wake Lock + documented fallback |

---

## Hosting, and when to move

| Host | What it is | Use it when |
|---|---|---|
| `gus` | Fred's desk machine (RTX 5070, Arch) | Anything that needs the GPU, or that you only use at home |
| `vic` | The mobile Arch laptop | Tools that should follow the laptop |
| `fnix` | MacBook Pro M4 Max | Anything that needs macOS: iMessage, Apple APIs, Xcode-adjacent work |
| `red` / `blu` / `whi` | Always-on VPS boxes | The moment you want the app up when your laptop is shut |

**Rule of thumb:** start on the machine that already has the data. Move to a VPS when "is my laptop
awake?" becomes the thing standing between you and your own tool.

Full detail: [docs/02-hosting.md](docs/02-hosting.md).

---

## The hard rule on exposure

**Tailscale only, until you decide otherwise on purpose.**

A home-screen web app has no login. Anyone holding your unlocked phone is already inside it. That is
fine on a private tailnet and it is not fine on the open internet. The app itself never listens
beyond `127.0.0.1`; only `tailscale serve` exposes it, and only to the tailnet.

`tailscale funnel` will put a service on the public internet with a real certificate in one command.
It is genuinely useful. It is also the exact moment your personal tool becomes an internet-facing
service that needs a login, a rate limit and a threat model. Treat it as a decision, never as a
convenience.

See [docs/04-https-and-tailscale.md](docs/04-https-and-tailscale.md).

---

## Layout

```
template/     the skeleton: index.html, manifest, service worker, CSS, JS, server.py
bin/nixweb    new / serve / install / icons / check
docs/         why, hosting, iPhone gotchas, HTTPS, offline
examples/     worked examples
IDEAS.md      ten apps worth building from projects that already exist
CLAUDE.md     rules for an AI working in this repo
```

---

## What a web app cannot do

Be honest about this up front, because finding out late is expensive.

- **No App Store listing.** Nobody discovers it. For a personal tool, a feature.
- **Push notifications** work on iOS 16.4+ **only once added to the home screen**, and are fiddly.
- **No Shortcuts intents, no widgets, no Live Activities, no share-sheet target.**
- **Background execution is limited.** It does not run when closed.
- **Audio capture stops when the screen sleeps.** Playback survives the lock screen. These are
  different things and the difference matters: see [docs/03-iphone-gotchas.md](docs/03-iphone-gotchas.md).
- **Install from Safari.** Since iOS 16.4 other browsers can Add to Home Screen too, but the icon then
  opens inside that browser. Safari is the reference path and the one to test.
- **Wake Lock does not work in an installed app on iOS 16.4 to 18.3.** It works from 18.4. Check the
  phone's iOS version before promising screen-on recording.

If you need any of the first four, you need a real app. For everything else, this is a better deal.
