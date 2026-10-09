#!/usr/bin/env python3
"""nixweb.app template server.

Static files plus the one thing a bare `python3 -m http.server` cannot do: answer /ping.
Standard library only, no build step.

    python3 server.py [port] [--bind ADDR]

It listens on 127.0.0.1 by default. That is deliberate: `nixweb serve` puts `tailscale serve`
in front of it, which adds HTTPS and exposes it to the tailnet and nowhere else. Binding
0.0.0.0 would also expose it to whatever wifi the laptop is sitting on.
"""
import argparse
import functools
import io
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = unquote(urlsplit(self.path).path)

        # WHY: app.js asks /ping to find out whether home is reachable. A bare static
        # server 404s it, and the app then shows "can't reach home" on its very first run.
        # no-store because a cached 200 would tell the user a dead host is alive.
        if path == "/ping":
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return io.BytesIO(body)

        # WHY: every app is its own git repo, so the directory being served contains .git
        # (full history) and probably a .env. A segment starting with "." covers both and
        # also ".." traversal. server.py hides itself so a later /api/ handler is not
        # published by accident.
        parts = [p for p in path.split("/") if p]
        if any(p.startswith(".") for p in parts) or parts[-1:] == ["server.py"]:
            self.send_error(404)
            return None

        return super().send_head()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("port", nargs="?", type=int, default=8731)
    ap.add_argument("--bind", default="127.0.0.1")
    a = ap.parse_args()
    handler = functools.partial(Handler, directory=HERE)
    srv = ThreadingHTTPServer((a.bind, a.port), handler)
    print(f"nixweb: serving {HERE} on http://{a.bind}:{a.port}", file=sys.stderr, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
