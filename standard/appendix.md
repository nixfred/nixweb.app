## Appendix A. Running the checker

```bash
nixweb check mytool                      # Level 2, the default
nixweb check mytool --level 3 --manual   # everything, and list what needs a person
nixweb check mytool --url https://HOST.TAILNET.ts.net:8731   # also test the HTTPS edge
nixweb check mytool --json               # for CI
nixweb standard --list --level 1         # the rules, without running anything
```

`nixweb check` starts the app's own `server.py` on a free loopback port, probes it, and stops it. It never touches the tailnet unless you pass `--url`. It needs only the Python standard library: it is written for Python 3.8 or newer and was tested on 3.14. The exit status is 0 with no failures and 1 with any. `--strict` also fails on recommendations and unverified rules. `--target URL` runs the runtime rules against a server that is already running, which is how an app with a server written in another language is checked.

The checker reads the app with a real HTML parser, not a text search, so a comment cannot satisfy a rule. It decodes the icon files and fails on one that is a single flat colour. It copies the app to a temporary folder, plants files that must never be served, and starts the server on the copy.

Tools outside the checker never change its result. Lighthouse gives performance and accessibility scores (its PWA category was removed in version 12, so it cannot score installability). axe or pa11y find a share of accessibility problems, and the Nu HTML Checker validates markup. Chrome DevTools, Application, Manifest shows installability errors. Playwright's WebKit build approximates Safari but is not Safari, and cannot reproduce Add to Home Screen. Remote debugging a real iPhone needs Safari Web Inspector on a Mac.

## Appendix B. Waivers

A rule that scans lines of code can be waived on one line with a comment on the same or the previous line:

    // nixweb-allow: NW-SEC-007 the sanitiser output is inserted here

Waivers exist for NW-NET-003, NW-SEC-006, NW-SEC-007, NW-IOS-002 and NW-OFF-011. A waiver without a reason is a defect. Every waiver is a SHOULD-style exception and belongs in `CONFORMANCE.md` too.

## Appendix C. Deliberately not required

- **HSTS.** It is keyed on the host name, covers every port, and is close to irreversible, so one experiment on another port can lock a host to HTTPS for a year. Tailscale does not add it. Leave it out unless you have decided.
- **Cross-Origin-Resource-Policy.** It can stop the operating system fetching the Home Screen icon, and that is not verified on a device. The template sends Cross-Origin-Opener-Policy only.
- **Splash screens.** iOS builds none from the manifest, and matching images per device are dozens of files. Paint the page background in the app's colour instead (NW-INS-007).
- **Manifest orientation, screenshots, shortcuts, display_override.** Chromium features. iOS ignores or does not document them. The layout must survive rotation anyway.
- **A Lighthouse PWA score.** The category no longer exists.
- **beforeinstallprompt.** iOS has no install prompt. The template shows instructions instead.
- **A login.** A tailnet-only app has none. The tailnet is the lock, and the Host and cross-site guards keep a web page in the phone's browser from using it.

## Appendix D. Things that used to be true

These claims circulate, and each was true once or is half true. Each was checked on 2026-10-11 against a primary source, which the rule that depends on it cites.

1. *Other iOS browsers open the Home Screen icon inside themselves.* WebKit says a qualifying site opens as a standalone web app no matter which browser added it, from iOS 16.4. Earlier editions of this project said the opposite.
2. *Without apple-touch-icon iOS screenshots your page.* Manifest icons have been used since iOS 15.4, and since 16.4 iOS draws a monogram.
3. *user-scalable=no stops zoom on iPhone.* WebKit has ignored it since iOS 10.
4. *Wake Lock does not work in an installed iOS app.* It did not from 16.4 to 18.3. It does from 18.4.
5. *An iPhone app needs a manifest and a service worker.* On iOS 26 every site added to the Home Screen opens as a web app, and the user can turn that off.
6. *tailscale serve only allows ports 443, 8443 and 10000.* Those are the Funnel ports. The Serve documentation lists no range.
7. *A private tailnet needs no CSRF protection.* The attacker is a web page open in a browser on the tailnet.
8. *Safari deletes all PWA data after 7 days.* That is script-writable storage in a browser tab. Installed Home Screen apps are exempt.
9. *Background Sync works everywhere.* It is not in Safari.
10. *display-mode: standalone is true in an installed iOS app.* The compatibility data records fullscreen instead (WebKit bug 264218).
11. *Parse the user agent for the iOS version.* Safari 26 reports a frozen version.
12. *black-translucent reliably draws under the status bar.* It regressed on iOS 26.1 (WebKit bug 301994, reopened 2026-08-04).
13. *iOS limits storage to 50 MB.* Since Safari 17 an origin may use up to 60 percent of the disk.
14. *sw.js needs a version query to avoid the HTTP cache.* The spec default fetches the main script past it. The real risks are imported scripts and precaching other files (NW-OFF-007).
15. *HTTPS inside a tailnet is for encryption.* WireGuard already encrypts. It is for the secure context that service workers, Wake Lock, the microphone and push require.
16. *Tailnet host names are private.* Issuing a certificate writes the name to public Certificate Transparency logs.

## Appendix E. Open questions

These could not be confirmed from a primary source in this edition and need a device. They are flagged in the rules that depend on them.

- How soon an installed iOS 26 app picks up a new service worker, and what real eviction looks like for an installed app.
- Whether Cross-Origin-Resource-Policy blocks the icon fetch (so it is omitted).
- Whether a font-size under 16px is exactly what triggers input zoom, from WebKit rather than from secondary sources.
- Whether `font: -apple-system-body` makes installed apps follow Larger Text.
- What an external link does in an installed app: an in-app sheet, as secondary sources say, or Safari.
- Whether the microphone permission prompts again on each launch of an installed app.
- Whether an edge-swipe back gesture exists in installed apps on iOS 26.
- What iOS 26.x does with the theme-color meta in an installed app.
- Whether touch-action on the root element stops the keyboard appearing (one secondary report).
- Whether tailscale serve compresses an uncompressed response. It passes a compressed one through unchanged.
- The 44 point figure in Apple's Human Interface Guidelines, whose page did not load for the researcher.

## Appendix F. How this edition was verified

- **Sources.** Each rule's Why cites the primary source it rests on and flags what only a secondary source supported. Researched on 2026-10-11 against the WebKit blog and Apple release notes, MDN, W3C, web.dev, OWASP and Tailscale's documentation.
- **The tailnet edge.** Checked on Tailscale 1.102.3 with a throwaway server that echoed its request headers: serve preserves Host, adds X-Forwarded-For, X-Forwarded-Host and X-Forwarded-Proto, and replaces a spoofed Tailscale-User-Login with the real one.
- **The template meets its own standard.** `nixweb check` on the template finds no failures at Level 2. At Level 3 it fails only the three rules that need evidence a template cannot have: a conformance claim, a device record and a change log.
- **The checker can fail.** `standard/selftest.py` breaks a copy of the template once for each automated rule, except the two that need a host unit or a tailnet, and requires the rule to notice. It passes. The first version of `nixweb check` was a grep that passed a template shipping `user-scalable=no`, which is why this test exists. Run it after any change to the rules or the template.
- **A real browser.** The template was loaded in Chromium under its own Content-Security-Policy with no unexpected errors. The service worker installed and cached the shell, a deployed new version produced the update prompt and switched on a tap, and with the server stopped the app launched from cache and said it could not reach the host.
- **Not verified.** Nothing here has been run on a physical iPhone, on Android, or under `nixweb install`. Appendix E lists what only a phone can answer.

## Appendix G. Edition history

- **{{EDITION}}** ({{DATE}}). First edition. {{TOTAL}} rules: {{L1}} at Level 1, {{L2}} added at Level 2, {{L3}} added at Level 3.
