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

## Making it survive a reboot

```bash
nixweb install mytool 8731          # writes ~/.config/systemd/user/nixweb-mytool.service
loginctl enable-linger $USER        # and keeps it running when you are logged out
journalctl --user -u nixweb-mytool -f
```

A user unit, not a system unit, because the app runs as you and reads your files. Never `nohup &`:
it does not restart, it does not log anywhere useful, and it dies with the terminal.

## Static versus dynamic

The template is static files, so `python3 -m http.server` is genuinely enough. The moment the app
needs to read a database or shell out, it needs a small backend: a single-file Python or Bun server
next to the static files, serving `/api/*`.

Keep the API surface tiny and read-only wherever you can. Every write endpoint is a thing a phone in
someone else's hand can do.
