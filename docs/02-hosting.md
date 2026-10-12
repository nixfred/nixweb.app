# Where to serve it

| Host | What it is | Serve here when |
|---|---|---|
| `gus` | Desk machine, RTX 5070 12GB, Arch | The app needs the GPU (local transcription, classification), or the data already lives here, or you only use it at home |
| `vic` | Mobile Arch laptop | The tool should follow the laptop, and you accept it is down when the lid is shut |
| `fnix` | MacBook Pro M4 Max | You need macOS: iMessage, Apple APIs, anything the Blip bridge touches |
| `red` / `blu` / `whi` | Always-on VPS | It must be up when every laptop is shut. `whi` also holds the fleet secrets vault |

Tailnet suffix: `tail0940f.ts.net`. So gus is `gus.tail0940f.ts.net`.

## The honest decision

**Start where the data already is.** A front end that has to reach across the tailnet to read a
database is slower, more fragile and harder to debug than one sitting next to it.

**Move to a VPS at exactly one trigger:** when "is my laptop awake?" is the thing standing between
you and your own tool. Not before. A VPS adds a machine to patch, a bill, and a second place for
secrets to live.

## Choose the host and port once

An installed app is bound to its origin: scheme, host and port. Rename the machine or change the
HTTPS port and every installed icon becomes a different app, with different storage and no way to
update the old one. Pick the final host and port before anyone installs, and write the origin and
the manifest `id` in the app's README (NW-NET-005). Moving to a VPS later means installing again on
every phone.

## Making it survive a reboot

```bash
nixweb install mytool 8731          # writes ~/.config/systemd/user/nixweb-mytool.service
loginctl enable-linger $USER        # and keeps it running when you are logged out
journalctl --user -u nixweb-mytool -f
```

A user unit, not a system unit, because the app runs as you and reads your files. Never `nohup &`:
it does not restart, it does not log anywhere useful, and it dies with the terminal. The tailnet
mapping lives and dies with the unit (NW-NET-004).

## What server.py does

`template/server.py` is standard-library Python and serves one folder, `public/`, and nothing
outside it. A `.git`, a `.env`, your notes and the server source cannot be published by a missed
denylist entry (NW-SRV-005). It also:

- binds `127.0.0.1` and refuses any other address (NW-NET-001);
- answers `/ping` and `/health`, never cached (NW-SRV-002);
- sends a strict Content-Security-Policy and the companion headers on every response, even a 404
  (NW-SEC-001, NW-SEC-002);
- answers only its own host names, which ends DNS rebinding (NW-SEC-003);
- refuses cross-site writes (NW-SEC-004) and oversize bodies (NW-SRV-011);
- makes every un-hashed file revalidate, and speaks 304, gzip and Range (NW-SRV-006, -008, -009);
- exits cleanly on SIGTERM, so systemd stops it without cutting a request in half (NW-SRV-010).

Why each one matters is in [07-security-model.md](07-security-model.md).

## Static versus dynamic

When the app needs data, add routes to `server.py` instead of a second server:

```python
@route("GET", "/api/notes")
def list_notes(_):
    return 200, {"notes": read_notes()}
```

A handler gets the parsed JSON body (or `None`) and returns `(status, object)`. Writes reach it only
after the Host, cross-site, size and content-type guards, and a repeated `Idempotency-Key` replays
the stored answer, which is what makes an offline retry safe (NW-DAT-002).

Keep the API surface tiny and read-only wherever you can. Every write endpoint is a thing a phone in
someone else's hand can do, and every write confirms on screen first (NW-UIX-001).

A server in another language is fine. Keep `public/`, put the same guards in front, and check it
while it runs with `nixweb check APP --target http://127.0.0.1:PORT`.
