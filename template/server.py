#!/usr/bin/env python3
"""nixweb.app template server.

Standard library only. No build step. Written for Python 3.8 or newer, tested on 3.14.

    python3 server.py [port] [--bind ADDR] [--public DIR]

The thin local server that `tailscale serve` fronts with HTTPS. It serves ONE directory,
public/, and nothing outside it, so a .git, a .env or this file cannot be published by
accident. Each block below carries the ID of the NixWeb Standard rule it implements
(STANDARD.md), so nobody deletes it as clutter. Add API routes with @route at the bottom of
the ROUTES section; the guards run before your handler does.
"""
import argparse
import gzip
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from email.utils import formatdate, parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
STARTED = time.time()
VERSION = "1"
LOOPBACK = ("127.0.0.1", "::1", "localhost")
MAX_BODY = 64 * 1024  # NW-SRV-011: refuse bigger request bodies before reading them

# NW-SRV-004: one explicit table, so a MIME type never depends on the Python version or the
# OS mime database. It doubles as the allowlist: a file with any other extension is a 404,
# even inside public/ (no .map, .py, .md, .db, .bak, .env).
TYPES = {
    ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".mjs": "text/javascript",
    ".json": "application/json", ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml", ".txt": "text/plain", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".avif": "image/avif",
    ".ico": "image/x-icon", ".woff2": "font/woff2", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".wav": "audio/wav", ".ogg": "audio/ogg", ".webm": "video/webm", ".mp4": "video/mp4",
}
TEXTUAL = {".html", ".css", ".js", ".mjs", ".json", ".webmanifest", ".svg", ".txt"}
HASHED = re.compile(r"[.\-][0-9a-f]{8,}\.[a-z0-9]+$")  # app.3fa9c2d1.js may be cached forever

# NW-SEC-001 and NW-SEC-002: sent on EVERY response, including 404s and /ping.
# CSP: no inline script, no eval, nothing from another origin (see NW-SEC-006, -007, -008).
# Permissions-Policy: deny what the app does not use. An app that records audio must change
# microphone=() to microphone=(self); one that uses the camera, camera=(self).
# Cross-Origin-Resource-Policy is deliberately NOT sent: it can block the OS fetching the
# home-screen icon, and that has not been verified on a device.
SECURITY_HEADERS = (
    ("Content-Security-Policy",
     "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
     "connect-src 'self'; font-src 'self'; manifest-src 'self'; worker-src 'self'; "
     "media-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'self'; "
     "frame-ancestors 'none'"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy",
     "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), hid=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
)


# ---------------------------------------------------------------------------------------
# NW-SEC-003: Host allowlist. The server only answers the names it is meant to be reached by.
# A DNS-rebinding page points its own name at 127.0.0.1 and then talks to this server with
# that name in the Host header; refusing unknown names ends the attack.
# ---------------------------------------------------------------------------------------
def host_only(value):
    v = (value or "").strip().lower()
    if v.startswith("["):
        end = v.find("]")
        return v[1:end] if end > 0 else ""
    return v.rsplit(":", 1)[0] if v.count(":") == 1 else v


class Hosts:
    def __init__(self):
        self.lock = threading.Lock()
        self.fixed = set(h.strip().lower() for h in os.environ.get("NIXWEB_HOSTS", "").split(",")
                         if h.strip())
        self.names = set(LOOPBACK)
        self.checked = 0.0
        self.refresh(force=True)

    def refresh(self, force=False):
        with self.lock:
            now = time.time()
            if not force and now - self.checked < 30:  # a flood of bad Hosts cannot spawn a flood of lookups
                return
            self.checked = now
        found = set()
        if not os.environ.get("NIXWEB_NO_TAILSCALE"):
            try:
                out = subprocess.run(["tailscale", "status", "--json"], capture_output=True, timeout=3)
                me = json.loads(out.stdout or b"{}").get("Self") or {}
                dns = (me.get("DNSName") or "").rstrip(".").lower()
                if dns:
                    found.add(dns)
                for ip in me.get("TailscaleIPs") or []:
                    found.add(str(ip).lower())
            except Exception:
                pass  # tailscaled not up yet (boot order): the next miss retries
        with self.lock:
            self.names = set(LOOPBACK) | self.fixed | found

    def allows(self, host):
        with self.lock:
            if host in self.names:
                return True
        self.refresh()
        with self.lock:
            return host in self.names


# ---------------------------------------------------------------------------------------
# API routes. Handlers take the parsed JSON body (or None) and return (status, jsonable).
#
#   @route("POST", "/api/note")
#   def add_note(obj):
#       return 201, {"id": 1}
#
# Writes arrive here only after the Host, cross-site, size and content-type guards in
# Handler.unsafe(), and a repeated Idempotency-Key replays the stored answer (NW-DAT-002).
# ---------------------------------------------------------------------------------------
ROUTES = {}
SEEN = OrderedDict()
WRITE_LOCK = threading.Lock()
GZ = {}


def route(method, path):
    def deco(fn):
        ROUTES[(method, path)] = fn
        return fn
    return deco


def accepts_gzip(header):
    h = header or ""
    return bool(re.search(r"\bgzip\b", h, re.I)) and not re.search(r"gzip\s*;\s*q=0(\.0*)?\s*(,|$)", h, re.I)


def etag_matches(header, etag):
    if header.strip() == "*":
        return True
    want = etag[2:] if etag.startswith("W/") else etag
    for part in header.split(","):
        p = part.strip()
        if (p[2:] if p.startswith("W/") else p) == want:
            return True
    return False


def parse_range(header, size):
    """None to ignore the header, 'bad' for 416, else (start, end). One range only."""
    m = re.match(r"^bytes=(\d*)-(\d*)$", header.strip())
    if not m or (m.group(1) == "" and m.group(2) == ""):
        return None
    a, b = m.groups()
    if a == "":
        n = int(b)
        if n == 0 or size == 0:
            return "bad"
        return max(0, size - n), size - 1
    start = int(a)
    end = min(int(b), size - 1) if b else size - 1
    if start >= size or start > end:
        return "bad"
    return start, end


class Handler(BaseHTTPRequestHandler):
    # NW-SRV-007: no Python version, no path, no traceback in anything a client can see.
    server_version = "nixweb"
    sys_version = ""
    error_message_format = "%(code)d %(message)s\n"
    error_content_type = "text/plain; charset=utf-8"
    protocol_version = "HTTP/1.0"  # one request per connection: no framing bugs to hide
    timeout = 30  # NW-SRV-011: a stuck client cannot hold a thread forever

    def version_string(self):
        return "nixweb"

    def send_response(self, code, message=None):
        self._code, self._sent = code, set()
        BaseHTTPRequestHandler.send_response(self, code, message)

    def send_header(self, keyword, value):
        self._sent.add(keyword.lower())
        BaseHTTPRequestHandler.send_header(self, keyword, value)

    def end_headers(self):
        for k, v in SECURITY_HEADERS:
            self.send_header(k, v)
        if self._code >= 400 and "cache-control" not in self._sent:
            self.send_header("Cache-Control", "no-store")
        BaseHTTPRequestHandler.end_headers(self)

    def log_message(self, fmt, *args):  # tokens in a query string never reach the log
        sys.stderr.write("%s %s\n" % (self.address_string(), re.sub(r"\?\S*", "?<redacted>", fmt % args)))

    # -- guards -----------------------------------------------------------------------
    def host_ok(self):
        h = host_only(self.headers.get("Host"))
        return bool(h) and self.server.hosts.allows(h)

    def same_origin(self):
        """NW-SEC-004. Browsers always send Sec-Fetch-Site or Origin on a cross-site write;
        curl and scripts send neither and are not the threat."""
        site = (self.headers.get("Sec-Fetch-Site") or "").lower()
        if site and site not in ("same-origin", "none"):
            return False
        origin = self.headers.get("Origin")
        if origin is not None:
            return urlsplit(origin).netloc.lower() == (self.headers.get("Host") or "").lower()
        return True

    def reject(self, code, message=None):
        self.close_connection = True
        self.send_error(code, message)

    # -- reads ------------------------------------------------------------------------
    def do_GET(self):
        self.read(False)

    def do_HEAD(self):
        self.read(True)

    def do_OPTIONS(self):  # NW-SEC-005: no CORS, so no preflight is ever answered
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def read(self, head):
        if not self.host_ok():
            return self.reject(421, "Misdirected Request")
        path = urlsplit(self.path).path
        if path == "/ping":  # NW-SRV-002: cheap, never cached, answers HEAD too
            return self.simple(200, b"ok\n", "text/plain; charset=utf-8", head)
        if path == "/health":
            body = json.dumps({"ok": True, "version": VERSION, "uptime": int(time.time() - STARTED)})
            return self.simple(200, body.encode(), "application/json", head)
        fn = ROUTES.get(("GET", path))
        if fn:
            return self.call(fn, None, None, head)
        self.static(path, head)

    def simple(self, code, body, ctype, head):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def call(self, fn, obj, key, head):
        try:
            with WRITE_LOCK:
                hit = SEEN.get((self.command, self.path, key)) if key else None
                if hit is None:
                    status, data = fn(obj)
                    hit = (status, json.dumps(data).encode())
                    if key:
                        SEEN[(self.command, self.path, key)] = hit
                        while len(SEEN) > 1000:
                            SEEN.popitem(last=False)
        except Exception as e:  # NW-SRV-007: the detail goes to the log, not the client
            sys.stderr.write("route error: %r\n" % (e,))
            return self.send_error(500, "Internal Error")
        self.send_response(hit[0])
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(hit[1])))
        self.send_header("Cache-Control", "private, no-cache")
        self.end_headers()
        if not head:
            self.wfile.write(hit[1])

    # -- static files -----------------------------------------------------------------
    def resolve(self, path):
        """URL path to a real file inside public/, else None. NW-SRV-001, -003, -005."""
        try:
            raw = unquote(path, errors="strict")
        except UnicodeDecodeError:
            return None
        if "\x00" in raw or "\\" in raw:
            return None
        parts = [p for p in raw.split("/") if p]
        if any(p.startswith(".") for p in parts):  # .., .git, .env, .gitignore
            return None
        rel = "/".join(parts)
        if raw.endswith("/") or not parts:  # a directory gets its index.html or a 404, never a listing
            rel = (rel + "/index.html") if rel else "index.html"
        root = self.server.public
        full = os.path.realpath(os.path.join(root, rel))  # symlinks are resolved, then checked
        if full != root and not full.startswith(root + os.sep):
            return None
        ext = os.path.splitext(full)[1].lower()
        if ext not in TYPES or not os.path.isfile(full):
            return None
        return full, ext

    def static(self, path, head):
        hit = self.resolve(path)
        if hit is None:
            return self.send_error(404, "Not Found")
        full, ext = hit
        st = os.stat(full)
        size, textual, rng = st.st_size, ext in TEXTUAL, self.headers.get("Range")
        gz = textual and size > 512 and not rng and accepts_gzip(self.headers.get("Accept-Encoding"))  # NW-SRV-008
        etag = 'W/"%x-%x%s"' % (size, st.st_mtime_ns, "-gz" if gz else "")
        lastmod = formatdate(st.st_mtime, usegmt=True)
        # NW-SRV-006: HTML, sw.js, the manifest and every un-hashed file revalidate on each use.
        # Without any Cache-Control a browser guesses a freshness from Last-Modified, and a new
        # service worker can precache the OLD app.js.
        cache = "public, max-age=31536000, immutable" if HASHED.search(full) else "no-cache"
        base = [("ETag", etag), ("Last-Modified", lastmod), ("Cache-Control", cache)]
        if textual:
            base.append(("Vary", "Accept-Encoding"))

        inm = self.headers.get("If-None-Match")  # NW-SRV-008
        fresh = False
        if inm is not None:
            fresh = etag_matches(inm, etag)
        elif self.headers.get("If-Modified-Since"):
            try:
                fresh = int(st.st_mtime) <= int(parsedate_to_datetime(self.headers["If-Modified-Since"]).timestamp())
            except (TypeError, ValueError):
                fresh = False
        if fresh:
            self.send_response(304)
            for k, v in base:
                self.send_header(k, v)
            return self.end_headers()

        start, end, code = 0, size - 1, 200
        if rng and rng.lower().startswith("bytes="):  # NW-SRV-009: Safari media needs 206
            ifr = self.headers.get("If-Range")
            if ifr is None or ifr.strip() in (etag, lastmod):
                r = parse_range(rng, size)
                if r == "bad":
                    self.send_response(416)
                    self.send_header("Content-Range", "bytes */%d" % size)
                    self.send_header("Content-Length", "0")
                    return self.end_headers()
                if r:
                    (start, end), code = r, 206
        self.send_response(code)
        self.send_header("Content-Type", TYPES[ext] + ("; charset=utf-8" if textual else ""))
        self.send_header("Accept-Ranges", "bytes")
        for k, v in base:
            self.send_header(k, v)
        if code == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        if gz:
            key = (full, st.st_mtime_ns, size)
            data = GZ.get(key)
            if data is None:
                with open(full, "rb") as f:
                    data = gzip.compress(f.read(), 6, mtime=0)
                if len(GZ) > 64:
                    GZ.clear()
                GZ[key] = data
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if not head:
                self.wfile.write(data)
            return
        length = max(0, end - start + 1)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if not head and length:
            with open(full, "rb") as f:
                f.seek(start)
                left = length
                while left > 0:
                    chunk = f.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)

    # -- writes -----------------------------------------------------------------------
    def unsafe(self):
        # NW-SEC-004 and NW-SRV-011: every guard runs BEFORE the body is read or a route is chosen.
        if not self.host_ok():
            return self.reject(421, "Misdirected Request")
        if not self.same_origin():
            return self.reject(403, "Cross-site request refused")
        if self.headers.get("Transfer-Encoding"):
            return self.reject(411, "Length Required")
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self.reject(400, "Bad Request")
        if n < 0:
            return self.reject(400, "Bad Request")
        if n > MAX_BODY:
            return self.reject(413, "Payload Too Large")
        fn = ROUTES.get((self.command, urlsplit(self.path).path))
        if fn is None:
            return self.reject(404, "Not Found")
        if n and (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            return self.reject(415, "Unsupported Media Type")  # JSON forces a CORS preflight on other origins
        body = self.rfile.read(n) if n else b""
        try:
            obj = json.loads(body) if body else None
        except ValueError:
            return self.reject(400, "Bad JSON")
        self.call(fn, obj, self.headers.get("Idempotency-Key"), False)

    do_POST = do_PUT = do_PATCH = do_DELETE = unsafe


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError, socket.timeout)):
            return  # a phone that locked mid-download is not an error
        ThreadingHTTPServer.handle_error(self, request, client_address)


def main():
    ap = argparse.ArgumentParser(description="nixweb template server")
    ap.add_argument("port", nargs="?", type=int, default=8731)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--public", default=os.path.join(HERE, "public"))
    a = ap.parse_args()
    # NW-NET-001: loopback only. tailscale serve is the one thing allowed to reach this port.
    if a.bind not in LOOPBACK and os.environ.get("NIXWEB_ALLOW_PUBLIC_BIND") != "1":
        sys.exit("nixweb: refusing to bind %s. tailscale serve fronts this server, and any other "
                 "address also exposes it to the LAN. Set NIXWEB_ALLOW_PUBLIC_BIND=1 only if you mean it." % a.bind)
    public = os.path.realpath(a.public)
    if not os.path.isdir(public):
        sys.exit("nixweb: no public directory at %s" % public)
    if ":" in a.bind:
        Server.address_family = socket.AF_INET6
    srv = Server((a.bind, a.port), Handler)
    srv.public, srv.hosts = public, Hosts()
    # NW-SRV-010: systemd stops a service with SIGTERM; finish in-flight requests, exit 0.
    stop = lambda *_: threading.Thread(target=srv.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print("nixweb: serving %s on http://%s:%d (hosts: %s)" % (
        public, a.bind, a.port, ", ".join(sorted(srv.hosts.names))), file=sys.stderr, flush=True)
    srv.serve_forever()
    srv.server_close()


if __name__ == "__main__":
    main()
