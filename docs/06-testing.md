# Testing and checking

Three layers. Each catches what the others cannot, and none of them replaces a phone in a hand.

## 1. `nixweb check`: seconds, nothing to install

```bash
nixweb check mytool                     # Level 2, the default
nixweb check mytool --level 3 --manual  # everything, and list what a person must do
nixweb check mytool --url https://HOST.TAILNET.ts.net:8731   # also test the HTTPS edge
nixweb check mytool --json              # for CI
```

It reads your files with a real HTML parser (so a comment cannot satisfy a rule), decodes your icon
files, copies the app to a temporary folder and plants files that must never be served, then starts
your own `server.py` on a free loopback port and probes it: path traversal, a spoofed Host, a
cross-site POST, caching headers, gzip, Range, SIGTERM. Python standard library only (written for 3.8 or newer, tested on 3.14). Exit status
is 0 with no failures and 1 with any.

It cannot judge how the app feels, see controls that JavaScript creates at run time, or know what
happens on a phone. **An automated pass is not a conformance claim.**

### Does the checker work?

```bash
python3 standard/selftest.py
```

The first `nixweb check` was a grep, and it passed a template that shipped `user-scalable=no`. The
self-test makes the checker prove itself. It breaks a copy of the template once for each automated
rule, in the one way that rule exists to catch, and requires the rule to notice. It also requires the
unbroken template to pass. A rule with no mutation fails the self-test, so a rule cannot be added
without a test that it can fail. Run it after any change to `standard/` or `template/`.

## 2. Optional tools

None of these change the checker's result. Use them when you want a second opinion.

| Tool | Good for | Limits |
|---|---|---|
| Lighthouse (CLI or DevTools) | Performance, accessibility, best practices, SEO | Its PWA category was removed in version 12 (2024), so it cannot score installability. Needs Node and Chrome. Scores are noisy. |
| axe-core or pa11y | WCAG problems in a running page | axe documents catching about 57 percent of WCAG issues automatically, on average. The rest need a person. |
| Nu HTML Checker (`vnu.jar`) | Markup validity | Validity only. Needs Java. |
| Chrome DevTools, Application | Manifest, installability errors, service worker state, cache contents | Chromium only |
| Playwright with WebKit | Layout in a WebKit engine on Linux | Playwright's own build, not Safari. Cannot do Add to Home Screen, standalone mode or iOS safe areas. Its docs say service workers are Chromium-only; that was not tested here. |
| Safari Web Inspector | The real thing, on a real phone | Needs a Mac. See below. |
| Xcode Simulator | Safari on a simulated phone | Mac only, and does not reproduce all of Add to Home Screen |

## 3. A real iPhone

Add to Home Screen, safe areas, the keyboard and offline launch can only be verified on a phone.
Install from the HTTPS tailnet URL, in Safari, with **Open as Web App** on, then work through these
and write the answers in `device-test.md` with the device, the iOS version and the date. The IDs are
the rules they prove.

1. **It installs and opens as its own app.** Own icon, own name, no browser bar. Log all three
   standalone tests. (NW-DEV-001)
2. **Offline launch.** Stop the host, force-quit the app, launch it. The shell should paint within
   about a second with cached data and a banner that names the host and the last contact. Repeat
   with Tailscale switched off on the phone. (NW-DEV-002)
3. **Safe areas and the keyboard.** Portrait and landscape: nothing under the notch, the Dynamic
   Island or the home indicator. Focus an input in the lower half, dismiss the keyboard three times.
   (NW-DEV-003)
4. **The update flow.** Install version 1, deploy version 2, background and reopen the app, tap the
   prompt: one reload, the version changes. (NW-DEV-004)
5. **An external link.** Tap one and write down whether it opens a sheet or leaves the app.
   (NW-DEV-005)
6. **Permissions.** No prompt until a control is tapped. (NW-DEV-006)
7. **Writes.** Confirmation wording, Undo, and an offline write that replays exactly once.
   (NW-DEV-007)
8. **States.** Loading, empty, error and stale each look different (NW-UIX-002), and every screen
   below the first has a Back control (NW-UIX-003).
9. **Touch targets** (NW-ACC-011), then **VoiceOver, Larger Text, Reduce Motion and Increase
   Contrast** on every screen (NW-ACC-012).

Remote debugging an iPhone needs Safari Web Inspector on a Mac: on the phone, Settings, Safari,
Advanced, Web Inspector; on the Mac, Safari, Settings, Advanced, Show features for web developers;
the phone then appears in the Develop menu. From Linux the practical route is a Mac you can reach
over the tailnet. `ios-webkit-debug-proxy` can reach the inspector from Linux, but it is fragile on current
iOS and the Chrome DevTools front end no longer speaks WebKit's protocol.

## Claiming a level

When the checks pass and the device test is done, fill in `CONFORMANCE.md` in the app:

```
Standard: NixWeb 1.0
Level: 2
Date: 2026-10-11
Tester: Fred
```

A claim reads "NixWeb 1.0, Level 2" and names an edition, because later editions can add rules. It is
self-attested unless someone else signs it. Level 3 also needs `device-test.md` filled in and a
`CHANGELOG.md`, and `nixweb check --level 3` checks that they are filled in, not that they are true.
