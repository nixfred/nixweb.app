# CLAUDE.md — nixweb.app

> Identity and global rules live in `~/.claude/CLAUDE.md` and the Larry Constitution.
> This file is only about this project.

## What this is

A skeleton and a method for building phone apps that are **web apps**, served off a machine we
already own and reached over Tailscale. Born 2026-10-08, when Daniel Lienemann told Fred that an
iPhone app is just a web page added to the home screen, and Fred realised he had been avoiding
Xcode for a year for no reason.

## Hard rules

1. **No build step. No framework. No npm.** The template is HTML, CSS and one JS file on purpose.
   The moment it needs a bundler it stops being something a client can copy and understand in an
   afternoon, which is the whole point.
2. **Tailscale only by default.** Nothing here binds to a public interface without an explicit,
   per-app decision. `tailscale funnel` is a decision, never a convenience. Apps listen on
   127.0.0.1 and `tailscale serve` fronts them with HTTPS (a secure context is what lets the
   service worker, Wake Lock and the mic work). Never bind 0.0.0.0. `tailscale serve --https=PORT`
   replaces whatever is on that port, so `nixweb` checks `tailscale serve status` first; keep it so.
3. **Every CSS rule that exists for an iOS quirk carries a `WHY` comment.** Someone will delete it
   otherwise, and then wonder six months later why dragging highlights text.
4. **Verify what you generate.** `nixweb icons` counts the colours in the PNG it just wrote and
   fails loudly on a blank tile, because an invisible icon is the exact failure this project exists
   to prevent. Hold new generators to the same standard.
5. **Reads are free; writes confirm.** Any app built from this template that can merge, send, start
   or delete shows what it is about to do and waits for a tap.
6. **Law 17 applies.** The page never scrolls. Lists scroll inside their own box.

## Layout

```
template/     the skeleton (index.html, app.css, app.js, sw.js, manifest, server.py)
bin/nixweb    new | icons | serve | install | check | hosts
docs/         why, hosting, iPhone gotchas, HTTPS/Tailscale, offline
IDEAS.md      ten apps worth building, all front ends onto existing projects
examples/     worked examples
```

## Hosts

gus (desk, RTX 5070), vic (mobile laptop), fnix (MacBook Pro M4 Max), and the VPS boxes red, blu,
whi. Tailnet suffix `tail0940f.ts.net`. Start where the data is; move to a VPS when "is my laptop
awake?" is the blocker.

## Testing

`nixweb check <app>` audits for the known traps. It is a grep, not a browser, so it proves the rule
is present rather than that the app feels right. Real verification is a phone in a hand.
