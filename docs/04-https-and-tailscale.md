# HTTPS, Tailscale, and the line you should not cross by accident

## Why nixweb serves HTTPS even inside the tailnet

Not for encryption. WireGuard already encrypts every packet between your phone and the host, so a
TLS layer adds no protection against anyone who is not already on your tailnet.

The reason is the **secure context**. Browsers hide a set of APIs from any page that was not loaded
over HTTPS (or from `localhost`), and `http://gus.tail0940f.ts.net` is neither:

| Needs a secure context | Over plain http:// |
|---|---|
| Service worker (the offline shell) | `navigator.serviceWorker` is undefined. Nothing registers and nothing complains. |
| Wake Lock (keeps the screen on while recording) | refused |
| Microphone capture (`getUserMedia`) | refused |
| Web push | unavailable |

So on plain HTTP the app looks fine and quietly loses its offline cache, and any voice-first idea
(see Idea Box in [IDEAS.md](../IDEAS.md)) cannot work at all.

## How it is wired

```
phone ──HTTPS──> tailscaled  gus.tail0940f.ts.net:8731 ──HTTP──> 127.0.0.1:8731  server.py
```

- `server.py` listens on **127.0.0.1 only** and refuses to start on anything else (NW-NET-001). The
  port does not exist on the LAN or on coffee-shop wifi. Only tailscaled can reach it, and it only
  answers the tailnet.
- `nixweb serve` runs `tailscale serve --bg --https=PORT http://127.0.0.1:PORT` and takes the
  mapping down again on Ctrl-C. `nixweb install` ties the mapping to the systemd unit, so
  `systemctl --user disable --now nixweb-NAME` removes it too.
- The app port and the HTTPS port are the same number.

`127.0.0.1` cannot be reached by your phone. Localhost means *this machine*, and your phone is not
this machine. That is fine here: the phone talks to tailscaled, and tailscaled talks to localhost.
It is also the most common "why can't I see it" when someone skips `tailscale serve`.

## What tailscale serve does to a request

Checked on 2026-10-11 on gus, Tailscale 1.102.3, with a throwaway server that echoed the headers it
received through a real `https://gus.tail0940f.ts.net:PORT` mapping:

| What the app sees | Value |
|---|---|
| `Host` | The name the phone used, with the port. **Preserved.** |
| `X-Forwarded-For`, `-Host`, `-Proto` | Added by serve |
| `Tailscale-User-Login`, `-Name`, `-Profile-Pic` | Added by serve: the person on the other end |
| A `Tailscale-User-Login` the client sent | **Replaced** by the real one |
| The app's own `Content-Encoding`, CSP, `Cache-Control` | Passed through unchanged |
| `Strict-Transport-Security` | Not added |

What follows from that:

- An exact Host allowlist works, so the server uses one (NW-SEC-003). It reads its own tailnet name
  and addresses from `tailscale status --json`.
- The identity headers can be trusted **only because the app binds loopback**. Anyone who could reach
  the port directly could send their own. They are absent for tagged devices, and never sent over
  Funnel. The template ignores them: a tailnet-only app has no login.
- Whether serve compresses an uncompressed response was not tested, so the app does its own gzip
  (NW-SRV-008).

## Ports

Tailscale's documentation lists no restricted range for serving to the tailnet. The 443, 8443 and
10000 list that many guides repeat is the **Funnel** list. But `tailscale serve --https=PORT <target>`
**replaces** whatever already answers on that port, and a host often has several services doing
exactly this. `nixweb` reads `tailscale serve status --json` first and refuses a port that is already
mapped to something else. Look yourself with `tailscale serve status`.

## Certificates

tailscaled gets a real Let's Encrypt certificate for `<host>.tail0940f.ts.net` on the first request
(a few seconds), renews it (they last 90 days), and the browser trusts it with no warning. HTTPS has
to be enabled for the tailnet in the admin console first; `tailscale cert <host>` fails with a link
if it is not. Let's Encrypt rate limits can block new requests for up to 34 hours, so do not delete
and reissue repeatedly.

**The hostname becomes public.** Certificates are written to public Certificate Transparency logs,
so `gus.tail0940f.ts.net` can be found by anyone who searches for it. The app behind it cannot be
reached from outside the tailnet, and the log holds the host name only, not an app path. But the
*name* is not secret. Name machines neutrally before turning HTTPS on, and consider the tailnet-name
randomisation in the admin console. (NW-NET-005)

## Your host and port are the app's identity

An installed app is bound to scheme, host and port. Rename the machine or change `--https=PORT` and
every installed icon becomes a different app, with different storage. Pick both once, and write them
in the app's README next to the manifest `id`.

## Who can reach it

Tailscale's policy is deny by default, but a personal tailnet often allows everything, and a
shared-in device gets whatever the node's identity can serve. With any second person or device on the
tailnet, add a grant that limits who can reach the app's port. A no-login app has no second lock.
(NW-NET-006)

## The line

```bash
tailscale serve   # inside the tailnet, with HTTPS
tailscale funnel  # ON THE PUBLIC INTERNET, with a real certificate
```

`funnel` is one word and it changes what your tool is. A port is either served privately or
funnelled, and the most recent command wins, so one `tailscale funnel` on a serve port silently makes
it public. The moment it runs, a personal app with no login is reachable by anyone who finds the
hostname. Funnel traffic carries no identity headers.

**Before funnelling anything, it needs:** a login you did not write yourself, a rate limit, separate
storage for your data and other people's, and a written reason. Daniel's public tunnel with five
testers is the live example: his personal data and the testers' data must not share a database.

Treat `funnel` the way you treat `rm -rf`. Not forbidden, just never casual. No script in an app
may start it (NW-NET-003).

## What server.py refuses to serve

Every app is its own git repo, so the folder it lives in contains `.git` (the whole history) and
probably a `.env`. The server serves one subfolder, `public/`, and only files whose extension is on
an allowlist, so none of that can be published by a missed denylist entry (NW-SRV-005). It still
answers 404 for any path with a segment that starts with a dot, and for traversal in every encoding
it was tested with (NW-SRV-001, NW-SRV-003).
