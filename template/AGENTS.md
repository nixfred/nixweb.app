# AGENTS.md

This is a NixWeb app: a phone app that is a plain web app, served over Tailscale and added to the
iPhone Home Screen. It follows the NixWeb Standard (STANDARD.md in the nixweb.app repository).
This file tells an AI coding agent how to work in it.

## Check your work

Run this before you say you are done, and paste the summary line into your reply.

    nixweb check .            # the automated rules, Level 2
    nixweb check . --manual   # also list the rules a person must test on a phone

A failing MUST is a bug in your change. Fix it, do not waive it. If a rule truly does not fit,
put `nixweb-allow: NW-XXX-000 reason` on that line and say why in your reply.

## Hard constraints

- No npm, no bundler, no framework, no build step. HTML, CSS and plain JavaScript only.
- Everything the app publishes lives in `public/`. Nothing else is served.
- `server.py` binds 127.0.0.1 only. Never bind 0.0.0.0. Never run `tailscale funnel`.
- No login on a tailnet-only app: the tailnet is the lock. Keep the Host and cross-site guards in
  `server.py` anyway, because a web page open in a browser on the tailnet can still send requests.
- No third-party scripts, fonts, analytics or CDN files.
- Build the DOM with `textContent`, never `innerHTML`.
- The page never scrolls. Lists scroll inside their own box.
- Every CSS rule that exists for an iOS quirk has a `WHY` comment. Keep them.
- Reads are free. Anything that sends, merges or deletes shows what it will do and waits for a tap.
- Bump `VERSION` in `public/sw.js` when you change a shell file.

## What needs a human

Add to Home Screen, safe areas, the keyboard, offline launch, VoiceOver and the update flow can only
be checked on a real iPhone. Say so. Do not claim Level 3 and do not fill in `device-test.md`.
