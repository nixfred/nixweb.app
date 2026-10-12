# CLAUDE.md: nixweb.app

> Identity and global rules live in `~/.claude/CLAUDE.md` and the Larry Constitution.
> This file is only about this project.

## What this is

A skeleton, a method and a standard for building phone apps that are **web apps**, served off a
machine we already own and reached over Tailscale. Born 2026-10-08, when a friend told Fred that an
iPhone app is just a web page added to the home screen, and Fred realised he had been avoiding Xcode
for a year for no reason. On 2026-10-11 Fred asked for a standard, so other people can build
these correctly and be checked for it. That is `STANDARD.md`.

## Hard rules

1. **No build step. No framework. No npm.** The template is HTML, CSS and one JS file on purpose. The
   moment it needs a bundler it stops being something a client can copy and understand in an
   afternoon, which is the whole point. (NW-ARC-001)
2. **Tailscale only by default.** Nothing here binds to a public interface without an explicit,
   per-app decision. `tailscale funnel` is a decision, never a convenience. Apps listen on 127.0.0.1
   and `tailscale serve` fronts them with HTTPS (a secure context is what lets the service worker,
   Wake Lock and the mic work). Never bind 0.0.0.0. `tailscale serve --https=PORT` replaces whatever
   is on that port, so `nixweb` checks `tailscale serve status` first; keep it so.
3. **No login on a tailnet app.** Fred, 2026-10-10 and 2026-10-11: Tailscale is the security. Keep the
   Host and cross-site guards in `server.py` anyway.
4. **Every CSS rule that exists for an iOS quirk carries a `WHY` comment.** Someone will delete it
   otherwise. `NW-DOC-001` checks it.
5. **Verify what you generate.** `nixweb icons` counts the colours in the PNG it just wrote and fails
   on a blank tile. Hold new generators to the same standard.
6. **Reads are free; writes confirm.** Any app built from this template that can merge, send, start
   or delete shows what it is about to do and waits for a tap.
7. **Law 17 applies.** The page never scrolls. Lists scroll inside their own box.
8. **The template must pass its own standard.** After any change to `template/` or `standard/`, run
   `python3 standard/selftest.py` (about 35 seconds) and `bin/nixweb check template --level 3`. Only
   the three evidence rules (NW-DOC-003, -004, -005) may fail on the template.
9. **`standard/rules.json` is the source.** `STANDARD.md` and `standard/CHECKLIST.md` are generated
   by `bin/nixweb standard --rebuild`; never edit them by hand. Rule IDs are permanent: never reuse,
   renumber or reorder one. Every new automated rule needs a mutation in `standard/selftest.py`, and
   the self-test fails if it has none.
10. **Do not claim what a phone has not shown.** Nothing in this repo has been run on a physical
    iPhone. A claim that rests on a secondary source says so in the rule's Why and in Appendix E.
11. **No em-dashes.** Fred's law. `rules.json` is validated against them, and the generated documents
    are refused if they contain one.
12. **Keep people and machines out of tracked files.** No person's name, no real host name and no
    tailnet name in the README, the docs, IDEAS.md or this file. Use `HOST.TAILNET.ts.net` and generic
    words (desk machine, laptop, VPS). The repo is meant to go public one day.

## Layout

```
STANDARD.md   the standard: rules, reasons, tests (generated from standard/rules.json)
standard/     rules.json (the source), check.py (the checker), selftest.py, CHECKLIST.md,
              preamble.md and appendix.md (the prose around the generated rules)
template/     the skeleton: public/ (index.html, app.css, app.js, sw.js, manifest, icons),
              server.py, AGENTS.md, CONFORMANCE.md, device-test.md
bin/nixweb    new | icons | serve | install | check | standard | hosts
docs/         why, hosting, iPhone gotchas, HTTPS and Tailscale, offline, testing, security model
docs/img/     the README graphic (hero.svg is the source, hero.png is what the README shows)
IDEAS.md      ten apps worth building, all front ends onto existing projects
```

## Hosts

Any machine you own that runs Tailscale: a desk machine, a laptop, a Mac, an always-on VPS. Machine
names and the tailnet name stay out of this repo; write `HOST.TAILNET.ts.net` as the placeholder.
Start where the data is; move to a VPS when "is my laptop awake?" is the blocker.

## Testing

`nixweb check <app>` is a real checker: an HTML parser, PNG decoding, and a running server probed
with hostile requests. It proves the rules a program can prove. Real verification is still a phone
in a hand, and `device-test.md` is where that is recorded.

## Scripts and the safety check

Claude Code's built-in check blocks a whole command whose text contains `rm` with a variable path,
even inside a heredoc that only writes a script. `bin/nixweb` therefore never deletes: it writes a
`.new` file and moves it, and builds icons in a scratch folder before moving them into place. Keep it
that way.
