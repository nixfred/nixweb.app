# HTTPS, Tailscale, and the line you should not cross by accident

## Why plain HTTP is fine here

Inside a tailnet, every connection is already end-to-end encrypted by WireGuard. Putting TLS inside
that gets you a second encryption layer, a certificate to manage, and no additional protection
against anyone who is not already on your tailnet.

**On the open internet it is the opposite**: plain HTTP means anyone between the phone and the host
reads everything, including whatever token your app is using. There is no middle position.

So the rule is simple: **HTTP on the tailnet, HTTPS everywhere else, and never confuse which one you
are on.** If you cannot say out loud which it is, stop.

## Binding

```bash
python3 -m http.server 8731 --bind 0.0.0.0     # every interface, including untrusted wifi
python3 -m http.server 8731 --bind 100.75.37.107  # the tailnet address only
```

`0.0.0.0` is fine on a desktop behind a router. **On a laptop that sits on coffee-shop wifi, bind the
tailnet address only** — otherwise everyone on that network can reach your tool. `nixweb serve` uses
`0.0.0.0` for convenience; change it for anything you carry.

`127.0.0.1` cannot be reached by your phone. Localhost means *this machine*, and your phone is not
this machine. This is the most common "why can't I see it" and it is worth teaching rather than
just fixing.

## Real certificates on the tailnet

If you want HTTPS without exposing anything:

```bash
tailscale cert gus.tail0940f.ts.net     # real cert, valid name, never leaves the tailnet
```

Then terminate TLS with Caddy or your own server. Worth doing when a browser API you need is
secure-context-only.

## The line

```bash
tailscale serve   # inside the tailnet, with HTTPS
tailscale funnel  # ON THE PUBLIC INTERNET, with a real certificate
```

`funnel` is one word and it changes what your tool is. The moment it runs, a personal app with no
login is reachable by anyone who finds the hostname.

**Before funnelling anything, it needs:** a login you did not write yourself, a rate limit, separate
storage for your data and other people's, and a reason. Daniel's public tunnel with five testers is
the live example: his personal data and the testers' data must not share a database.

Treat `funnel` the way you treat `rm -rf`. Not forbidden, just never casual.
