# Security model: the tailnet is the lock, and not the only lock

## The decision

A tailnet-only app has **no login**. Fred's rule, stated on 2026-10-10 and again on 2026-10-11:
Tailscale is the security. That is a decision about who can reach the port, and for a personal tool
it is right. This page is about what it covers and what it does not.

## Who can reach it

- Anyone signed in to your tailnet whose policy allows it, and any device shared in.
- Nobody else, **as long as** nothing runs `tailscale funnel` and nothing binds beyond loopback.

## The attacker you actually have

Not a stranger on the internet. Three realistic ones:

1. **A web page open in a browser on a tailnet device.** It can send requests to your tailnet URL
   from the person's own browser. It does this two ways: a cross-site request that carries no
   cookie because there is no login to forge, and DNS rebinding, where the page points its own name
   at `127.0.0.1` and talks to a loopback server.
2. **Another tailnet member, or a shared-in device,** that you did not mean to give access.
3. **A bug of your own:** a handler that trusts its input, or a page that renders pasted text as
   HTML.

## What the template does about each

| Guard | Rule | What it stops |
|---|---|---|
| Binds 127.0.0.1 and refuses anything else | NW-NET-001, -002 | The app being reachable from the LAN or from wifi |
| Serves only `public/`, only allowlisted file types, no listings | NW-SRV-005 | `.git`, `.env`, notes and the server source leaking |
| 404 for dotfiles; traversal fails in every encoding tried | NW-SRV-001, -003 | The same, through a crafted path |
| Answers only its own host names | NW-SEC-003 | DNS rebinding |
| Refuses writes marked cross-site, or from a foreign Origin | NW-SEC-004 | A web page forging a write |
| Sends no CORS headers; OPTIONS gets 405 | NW-SEC-005 | Loosening the browser's own protection |
| Caps request bodies, sets a socket timeout | NW-SRV-011 | A flood from a compromised page |
| Strict Content-Security-Policy and companion headers | NW-SEC-001, -002 | Injected script, framing, MIME sniffing |
| No third-party origins, no inline script | NW-SEC-006, -008 | Supply-chain leaks, and a CSP you can actually enforce |
| `textContent`, never `innerHTML`; no `eval` | NW-SEC-007 | Cross-site scripting from your own data |
| No secrets in served files | NW-SEC-009 | Everything on the tailnet reading your keys |
| Generic errors, no version in headers | NW-SRV-007 | Handing an attacker a map |

A write guard has one deliberate gap. A request that sends neither `Sec-Fetch-Site` nor `Origin`
comes from `curl` or a script, not from a browser page, and is allowed. Current browsers send one or
the other on a cross-site write.

## What not to do

- **Never `tailscale funnel` a no-login app.** A port is either served or funnelled and the most
  recent command wins, so one funnel command on a serve port silently makes it public. (NW-NET-003)
- **Never bind `0.0.0.0`.** It also publishes the app to the LAN, and it makes the Tailscale identity
  headers forgeable, because someone could reach the port directly. (NW-NET-001)
- **Do not trust `Tailscale-User-*` headers off loopback.** The template ignores them. If you use
  them, remember they are absent for tagged devices.
- **Do not put a secret in a host name.** The certificate writes the name to public logs.
  (NW-NET-005)
- **Do not add a third-party script "just for one thing".** Vendor it into `public/vendor/` and
  record it in `VENDOR.md`. (NW-SEC-006, NW-ARC-003)

## When you do need a login

The moment the app can be reached by anyone you did not put on the tailnet: a funnel, a shared
tailnet with people you do not fully trust, or data that is not yours. Then it needs a login you did
not write yourself, a rate limit, separate storage for other people's data, and a written decision in
`CONFORMANCE.md`. The standard's no-login stance ends there.
