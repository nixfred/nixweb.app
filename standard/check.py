#!/usr/bin/env python3
"""nixweb standard checker. Python standard library only: no network, no build step.

  check.py APP [--level N] [--json] [--url URL] [--no-live] [--only ID,ID] [--strict] [--manual]
  check.py --list [--level N]
  check.py --standard            rebuild STANDARD.md and standard/CHECKLIST.md from rules.json

rules.json beside this file is the single source of truth. The standard document, the
checklist and this checker are all built from it, so they cannot drift apart.

A rule with a "check" name is run here. A rule with "check": null is MANUAL: it is counted
in every report and never silently passed, because only a person holding a real phone can
answer it. A failing MUST is a FAIL. A failing SHOULD or MAY is a WARN (a FAIL under --strict).

Exit status: 0 no failures, 1 something failed or could not be verified, 2 bad usage.
"""
import argparse
import gzip
import http.client
import json
import os
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RULES_FILE = os.path.join(HERE, "rules.json")

TTY = sys.stdout.isatty() and "NO_COLOR" not in os.environ
CY, GR, AM, RD, DIM, BD = "36", "32", "33", "31", "2", "1"


def paint(code, text):
    return "\x1b[%sm%s\x1b[0m" % (code, text) if TTY else text


PASS, FAIL, WARN, MANUAL, SKIPPED, NA = "pass", "fail", "warn", "manual", "skip", "n/a"
MARK = {PASS: ("✓", GR), FAIL: ("✗", RD), WARN: ("!", AM),
        MANUAL: ("○", DIM), SKIPPED: ("?", AM), NA: ("-", DIM)}
KEYWORDS = ("MUST", "SHOULD", "MAY")
METHODS = ("static", "runtime", "device", "process")


class Skip(Exception):
    """An automated rule that could not be run (no server to probe, tool missing)."""


CHECKS = {}


def check(fn):
    CHECKS[fn.__name__] = fn
    return fn


def ok(detail=""):
    return (PASS, detail)


def bad(detail):
    return (FAIL, detail)


def na(reason):
    return (NA, reason)


# ---------------------------------------------------------------------------
# The rules file
# ---------------------------------------------------------------------------
def load_spec():
    with open(RULES_FILE, encoding="utf-8") as f:
        spec = json.load(f)
    problems, seen = [], set()
    cats = spec.get("categories", {})
    for r in spec.get("rules", []):
        rid = r.get("id", "?")
        for k in ("id", "level", "keyword", "title", "statement", "why", "test", "method"):
            if k not in r:
                problems.append("%s: missing field %s" % (rid, k))
        if rid in seen:
            problems.append("%s: duplicate id" % rid)
        seen.add(rid)
        if not re.match(r"^NW-[A-Z]{3}-\d{3}$", rid):
            problems.append("%s: id must look like NW-XXX-000" % rid)
        elif rid.split("-")[1] not in cats:
            problems.append("%s: category not declared" % rid)
        if r.get("level") not in (1, 2, 3):
            problems.append("%s: level must be 1, 2 or 3" % rid)
        if r.get("keyword") not in KEYWORDS:
            problems.append("%s: keyword must be MUST, SHOULD or MAY" % rid)
        if r.get("method") not in METHODS:
            problems.append("%s: method must be one of %s" % (rid, ", ".join(METHODS)))
        if r.get("check") and r.get("method") in ("device", "process"):
            problems.append("%s: a device or process rule cannot be automated" % rid)
        if r.get("check") and r["check"] not in CHECKS:
            problems.append("%s: check %s has no implementation" % (rid, r["check"]))
        if r.get("method") == "static" and not r.get("check") and not r.get("manual_reason"):
            problems.append("%s: a static rule with no check needs manual_reason" % rid)
    if chr(0x2014) in json.dumps(spec, ensure_ascii=False):
        problems.append("rules.json contains an em-dash (U+2014); the standard never uses them")
    if problems:
        sys.stderr.write("rules.json is invalid:\n  " + "\n  ".join(problems) + "\n")
        sys.exit(2)
    return spec


def active(spec, level=3):
    return [r for r in spec["rules"] if r.get("status", "active") == "active" and r["level"] <= level]


# ---------------------------------------------------------------------------
# Reading the app under test
# ---------------------------------------------------------------------------
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr"}


class Page(HTMLParser):
    """Collects what the static rules need from index.html. A real parser, because a
    grep is satisfied by a comment or a string and a parser is not."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.tags, self.comments, self.stack, self.interactive, self.controls = [], [], [], [], []
        self.labels_for = set()
        self.title = ""
        self._in_title = False
        self.lang = None
        self.inline_scripts = 0
        self.inline_handlers = 0
        self.scripts = []
        self.in_noscript = set()
        self.present = False

    def handle_starttag(self, tag, attrs):
        a = dict((k, v if v is not None else "") for k, v in attrs)
        line = self.getpos()[0]
        self.tags.append((tag, a, line))
        if any(n["tag"] == "noscript" for n in self.stack):
            self.in_noscript.add(line)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self._in_title = True
        if tag == "label" and "for" in a:
            self.labels_for.add(a["for"])
        self.inline_handlers += len([k for k in a if k.startswith("on") and len(k) > 2])
        if tag == "script" and "src" not in a and a.get("type", "") not in (
                "application/json", "application/ld+json", "importmap"):
            self.inline_scripts += 1
        if tag == "script":
            self.scripts.append({"attrs": a, "in_head": any(n["tag"] == "head" for n in self.stack)})
        if tag in ("input", "select", "textarea"):
            self.controls.append({"tag": tag, "attrs": a, "line": line,
                                  "in_label": any(n["tag"] == "label" for n in self.stack)})
        if tag == "img":
            for n in self.stack:
                n["text"] += " " + a.get("alt", "")
        if tag not in VOID:
            self.stack.append({"tag": tag, "attrs": a, "text": "", "line": line})

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                node = self.stack[i]
                del self.stack[i:]
                if tag in ("button", "a"):
                    self.interactive.append(node)
                break

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        for n in self.stack:
            n["text"] += data

    def handle_comment(self, data):
        self.comments.append(data)

    def find(self, tag, **want):
        out = []
        for t, a, _ in self.tags:
            if t != tag:
                continue
            if all((k.replace("_", "-") in a) if v is True else (a.get(k.replace("_", "-")) == v)
                   for k, v in want.items()):
                out.append(a)
        return out

    def meta(self, name):
        for a in self.find("meta", name=name):
            return a.get("content", "")
        return None

    def links(self, rel):
        return [a for t, a, _ in self.tags if t == "link" and rel in a.get("rel", "").lower().split()]


def strip_css_comments(s):
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


class Ctx:
    def __init__(self, root):
        self.root = root
        self.live = None
        self.edge = None
        self.no_live = False
        self.live_error = "live checks were not run"
        self.pub = "public/" if os.path.isdir(os.path.join(root, "public")) else ""
        self._t, self._page, self._walk = {}, None, None

    def p(self, rel):
        return os.path.join(self.root, rel)

    def has(self, rel):
        return os.path.isfile(self.p(rel))

    def text(self, rel):
        if rel not in self._t:
            try:
                with open(self.p(rel), encoding="utf-8", errors="replace") as f:
                    self._t[rel] = f.read()
            except OSError:
                self._t[rel] = None
        return self._t[rel]

    @property
    def page(self):
        if self._page is None:
            self._page = Page()
            src = self.text(self.pub + "index.html")
            if src is not None:
                self._page.present = True
                self._page.feed(src)
                self._page.close()
        return self._page

    def walk(self):
        """Every file in the app, skipping dot-directories and node_modules."""
        if self._walk is None:
            out = []
            for d, dirs, files in os.walk(self.root):
                dirs[:] = [x for x in dirs if not x.startswith(".") and x != "node_modules"]
                for f in files:
                    out.append(os.path.relpath(os.path.join(d, f), self.root))
            self._walk = sorted(out)
        return self._walk

    def by_ext(self, *exts):
        return [f for f in self.walk() if f.lower().endswith(exts) and f.startswith(self.pub)]

    def css(self):
        return dict((f, self.text(f) or "") for f in self.by_ext(".css"))

    def js(self):
        return dict((f, self.text(f) or "") for f in self.by_ext(".js", ".mjs"))

    def resolve(self, href, base_rel=None):
        """A URL path used inside the app to a path relative to the app root, or None."""
        href = href.split("?")[0].split("#")[0]
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//", href):
            return None
        if href.startswith("/"):
            rel = os.path.join(self.pub, href.lstrip("/"))
        else:
            rel = os.path.join(os.path.dirname(base_rel) if base_rel else self.pub, href)
        rel = os.path.normpath(rel)
        return None if rel.startswith("..") else rel

    def manifest(self):
        """(data, rel_path, error). Follows <link rel=manifest>, else the conventional name."""
        href = None
        for a in self.page.links("manifest"):
            href = a.get("href")
        rel = self.resolve(href or "manifest.webmanifest")
        if rel is None:
            return None, str(href), "manifest href is an absolute URL or escapes the app folder"
        raw = self.text(rel)
        if raw is None:
            return None, rel, "no such file: %s" % rel
        try:
            return json.loads(raw), rel, None
        except ValueError as e:
            return None, rel, "not valid JSON: %s" % e

    def get(self, path, method="GET", headers=None, body=None):
        if self.live is None:
            raise Skip(self.live_error)
        return self.live.req(method, path, headers, body)


# ---------------------------------------------------------------------------
# A throwaway copy of the app's own server, so the runtime rules need nothing running
# ---------------------------------------------------------------------------
class Live:
    def __init__(self, root, url=None):
        self.root, self.url, self.proc = root, url, None
        self.scheme, self.host, self.port = "http", "127.0.0.1", None
        self.spawned = False

    def start(self):
        if self.url:
            u = urlsplit(self.url)
            self.scheme = u.scheme or "https"
            self.host = u.hostname
            self.port = u.port or (443 if self.scheme == "https" else 80)
            return None
        server = os.path.join(self.root, "server.py")
        if not os.path.isfile(server):
            return "no server.py in the app folder, and no --url given"
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.proc = subprocess.Popen([sys.executable, server, str(self.port)], cwd=self.root,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.spawned = True
        for _ in range(60):
            time.sleep(0.1)
            if self.proc.poll() is not None:
                return "server.py exited at once (run it by hand to see why)"
            try:
                self.req("GET", "/ping", timeout=1)
                return None
            except Skip:
                continue
        return "server.py never answered on 127.0.0.1:%d" % self.port

    def req(self, method, path, headers=None, body=None, timeout=5):
        if self.scheme == "https":
            conn = http.client.HTTPSConnection(self.host, self.port, timeout=timeout,
                                               context=ssl.create_default_context())
        else:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            data = resp.read(1 << 20)
            return resp.status, dict((k.lower(), v) for k, v in resp.getheaders()), data
        except (OSError, http.client.HTTPException) as e:
            raise Skip("could not reach %s:%s (%s)" % (self.host, self.port, e))
        finally:
            conn.close()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(3)
            except subprocess.TimeoutExpired:
                self.proc.kill()


# ---------------------------------------------------------------------------
# PNG reading, because the failure this project exists to prevent is an invisible icon
# ---------------------------------------------------------------------------
def png_info(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, idat, ihdr, trns = 8, [], None, False
    while pos + 8 <= len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif typ == b"IDAT":
            idat.append(body)
        elif typ == b"tRNS":
            trns = True
        elif typ == b"IEND":
            break
    if not ihdr:
        return None
    return {"w": ihdr[0], "h": ihdr[1], "depth": ihdr[2], "ctype": ihdr[3],
            "interlace": ihdr[6], "idat": b"".join(idat), "trns": trns}


def png_distinct_pixels(info, cap=2):
    """How many distinct pixels (stopping at cap), or None if this PNG layout is not handled."""
    if info["interlace"] or info["depth"] not in (8, 16):
        return None
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(info["ctype"])
    if ch is None or (info["ctype"] == 3 and info["depth"] != 8):
        return None
    bpp = ch * info["depth"] // 8
    stride = info["w"] * bpp
    try:
        raw = zlib.decompress(info["idat"])
    except zlib.error:
        return None
    prev, seen, pos = bytearray(stride), set(), 0
    for _ in range(info["h"]):
        if pos >= len(raw):
            return None
        f = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up = prev[i]
            if f == 1:
                line[i] = (line[i] + left) & 255
            elif f == 2:
                line[i] = (line[i] + up) & 255
            elif f == 3:
                line[i] = (line[i] + ((left + up) >> 1)) & 255
            elif f == 4:
                ul = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(up - ul), abs(left - ul), abs(left + up - 2 * ul)
                pr = left if (pa <= pb and pa <= pc) else (up if pb <= pc else ul)
                line[i] = (line[i] + pr) & 255
        for x in range(0, stride, bpp):
            seen.add(bytes(line[x:x + bpp]))
            if len(seen) >= cap:
                return len(seen)
        prev = line
    return len(seen)


# ===========================================================================
# THE CHECKS. One function per automatable rule, named by the rule's "check" field.
# Each takes the Ctx and returns ok(), bad(why), na(reason), or raises Skip(reason).
# A rule that does not apply says so (na) instead of passing silently.
# A justified exception in code carries a waiver comment on the same or the previous line:
#     nixweb-allow: NW-XXX-000 <reason>
# ===========================================================================
TEXT_EXT = (".html", ".css", ".js", ".mjs", ".json", ".webmanifest", ".svg", ".txt")


def keep_lines(m):
    return "\n" * m.group(0).count("\n")


def strip_c_comments(s):
    """JS comments removed, line numbers kept. // only counts as a comment when it does not
    follow a colon, so https://example survives."""
    s = re.sub(r"/\*.*?\*/", keep_lines, s, flags=re.S)
    return re.sub(r"(^|[^:\\'\"`])//[^\n]*", r"\1", s, flags=re.M)


def strip_html_comments(s):
    return re.sub(r"<!--.*?-->", keep_lines, s, flags=re.S)


def app_js(ctx, include_sw=False):
    out = {}
    for rel, txt in ctx.js().items():
        if "/vendor/" in "/" + rel or rel.lower().endswith(".min.js"):
            continue
        if not include_sw and os.path.basename(rel) == "sw.js":
            continue
        out[rel] = txt
    return out


def js_text(ctx, include_sw=False):
    return "\n".join(strip_c_comments(t) for t in app_js(ctx, include_sw).values())


def sw_text(ctx):
    t = ctx.text(ctx.pub + "sw.js")
    return None if t is None else strip_c_comments(t)


def css_text(ctx):
    return "\n".join(strip_css_comments(t) for t in ctx.css().values())


def waived(raw_lines, i, rid):
    for j in (i, i - 1):
        if 0 <= j < len(raw_lines) and "nixweb-allow" in raw_lines[j] and rid in raw_lines[j]:
            return True
    return False


def js_hits(ctx, rid, pattern, flags=0, include_sw=False):
    rx, hits = re.compile(pattern, flags), []
    for rel, raw in app_js(ctx, include_sw).items():
        raw_lines = raw.split("\n")
        for i, line in enumerate(strip_c_comments(raw).split("\n")):
            if rx.search(line) and not waived(raw_lines, i, rid):
                hits.append("%s:%d" % (rel, i + 1))
    return hits


def sends_writes(ctx):
    return bool(re.search(r"method\s*:\s*['\"](POST|PUT|PATCH|DELETE)['\"]", js_text(ctx), re.I))


def css_rules(ctx):
    rules = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css_text(ctx)):
        decls = {}
        for prop, val in re.findall(r"([-\w]+)\s*:\s*([^;]+?)\s*(?:;|$)", body):
            decls[prop.lower()] = val.strip()
        rules.append(([s.strip() for s in sel.split(",") if s.strip()], decls))
    return rules


def css_vars(rules):
    out = {}
    for sels, d in rules:
        if any(s in (":root", "html") for s in sels):
            for k, v in d.items():
                if k.startswith("--"):
                    out[k] = v
    return out


def css_color(v, vars_, depth=0):
    v = (v or "").strip().lower()
    if depth > 6:
        return None
    m = re.match(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)$", v)
    if m:
        if m.group(1) in vars_:
            return css_color(vars_[m.group(1)], vars_, depth + 1)
        return css_color(m.group(2), vars_, depth + 1) if m.group(2) else None
    if v.startswith("#"):
        h = v[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            if h[6:] != "ff":
                return None
            h = h[:6]
        if len(h) == 6:
            try:
                return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                return None
    m = re.match(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)\s*(?:[,/]\s*([\d.]+%?))?\s*\)$", v)
    if m:
        if m.group(4) and float(m.group(4).rstrip("%")) < (100 if m.group(4).endswith("%") else 1):
            return None
        return tuple(int(m.group(i)) for i in (1, 2, 3))
    return {"white": (255, 255, 255), "black": (0, 0, 0)}.get(v)


def luminance(rgb):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def shell_urls(ctx):
    sw = sw_text(ctx)
    if sw is None:
        return None
    m = re.search(r"(?:const|let|var)\s+(?:SHELL|PRECACHE|PRECACHE_URLS|ASSETS|APP_SHELL)\s*=\s*\[(.*?)\]", sw, re.S)
    if not m:
        return None
    return re.findall(r"['\"]([^'\"]*)['\"]", m.group(1))


def md_field(text, name):
    m = re.search(r"^[ \t>*_-]*\**%s\**[ \t]*:[ \t]*\**[ \t]*(.*?)[ \t]*$" % re.escape(name), text or "", flags=re.I | re.M)
    if not m:
        return None
    v = m.group(1).strip().strip("*_ ")
    if not v or re.match(r"^[_.\-\s<>\[\]]*$", v) or re.search(r"\b(todo|fill in|tbd|your name|yyyy)\b", v, re.I):
        return None
    return v


# ------------------------------- ARC ---------------------------------------
@check
def arc_no_build(ctx):
    problems = []
    if os.path.isdir(ctx.p("node_modules")):
        problems.append("node_modules/ exists")
    pj = ctx.text("package.json")
    if pj is not None:
        try:
            d = json.loads(pj)
            if d.get("dependencies") or d.get("devDependencies"):
                problems.append("package.json lists dependencies")
        except ValueError:
            problems.append("package.json is not valid JSON")
    names = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb", "tsconfig.json")
    cfg = re.compile(r"^(vite|webpack|rollup|parcel|esbuild|babel|postcss|tailwind|snowpack|gulpfile|gruntfile)\b|^\.babelrc", re.I)
    for f in sorted(os.listdir(ctx.root)):
        if f in names or cfg.search(f):
            problems.append("%s present" % f)
    return bad("; ".join(problems)) if problems else ok()


@check
def arc_public_dir(ctx):
    if not os.path.isfile(ctx.p("public/index.html")):
        return bad("public/index.html is missing")
    if not [f for f in os.listdir(ctx.root) if re.match(r"^server\.(py|ts|js|mjs)$", f)]:
        return bad("no server.py, server.ts, server.js or server.mjs beside public/")
    inside = [f for f in os.listdir(ctx.p("public")) if f.startswith("server.")]
    if inside:
        return bad("server file inside public/: " + ", ".join(inside))
    return ok()


@check
def arc_vendor_record(ctx):
    vendored = [f for f in ctx.walk()
                if (f.startswith(ctx.pub) and re.search(r"(^|/)(vendor|lib)/", f)) or f.lower().endswith(".min.js")]
    if not vendored:
        return na("nothing is vendored")
    rec = ctx.text("VENDOR.md")
    if rec is None:
        return bad("vendored files (%s) but no VENDOR.md" % ", ".join(vendored[:3]))
    missing = [f for f in vendored if os.path.basename(f) not in rec]
    return bad("not listed in VENDOR.md: " + ", ".join(missing[:5])) if missing else ok()


# ------------------------------- NET ---------------------------------------
@check
def net_loopback_default(ctx):
    src = ctx.text("server.py")
    if src is None:
        if any(os.path.isfile(ctx.p("server." + e)) for e in ("ts", "js", "mjs")):
            raise Skip("not a Python server: NW-NET-002 checks the socket at runtime")
        return bad("no server.py")
    code = strip_c_comments(src.replace("#", "//"))  # good enough: drop Python comments before scanning
    m = re.search(r"add_argument\(\s*[\"']--bind[\"'][^)]*default\s*=\s*[\"']([^\"']*)[\"']", src)
    if not m:
        return bad("cannot find a --bind default in server.py; the default must be 127.0.0.1")
    if m.group(1) not in ("127.0.0.1", "::1", "localhost"):
        return bad("the default bind is %r, not loopback" % m.group(1))
    if re.search(r"[\"']0\.0\.0\.0[\"']", code):
        return bad("a 0.0.0.0 literal appears in server.py")
    if "ALLOW_PUBLIC_BIND" not in src and "refus" not in src:
        return bad("server.py does not refuse a non-loopback --bind")
    return ok()


def listening_on(port):
    found = []
    for fn in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(fn) as f:
                rows = f.read().splitlines()[1:]
        except OSError:
            continue
        for row in rows:
            cols = row.split()
            if len(cols) > 3 and cols[3] == "0A":
                ip, prt = cols[1].split(":")
                if int(prt, 16) == port:
                    found.append((fn.rsplit("/", 1)[1], ip))
    return found


@check
def net_listen_loopback_only(ctx):
    if ctx.live is None:
        raise Skip(ctx.live_error)
    if not ctx.live.spawned:
        raise Skip("needs a server the checker started itself (do not pass --target)")
    if not os.path.exists("/proc/net/tcp"):
        raise Skip("no /proc/net/tcp on this OS; run lsof -iTCP -sTCP:LISTEN by hand")
    rows = listening_on(ctx.live.port)
    if not rows:
        return bad("no listening socket found for port %d" % ctx.live.port)
    wrong = []
    for table, ip in rows:
        loop = ip.endswith("7F") if table == "tcp" else (ip == "00000000000000000000000001000000" or ip.endswith("0100007F"))
        if not loop:
            wrong.append("%s %s" % (table, ip))
    return bad("listening on a non-loopback address: " + ", ".join(wrong)) if wrong else ok()


@check
def net_no_funnel(ctx):
    rx = re.compile(r"tailscale\s+funnel", re.I)
    hits = []
    for f in ctx.walk():
        base = os.path.basename(f)
        if not (f.endswith((".sh", ".service", ".timer", ".py", ".js", ".mjs", ".ts", ".yml", ".yaml")) or base in ("Makefile", "justfile")):
            continue
        raw = (ctx.text(f) or "").split("\n")
        for i, line in enumerate(raw):
            if rx.search(line) and not waived(raw, i, "NW-NET-003"):
                hits.append("%s:%d" % (f, i + 1))
    return bad("tailscale funnel appears in " + ", ".join(hits[:5])) if hits else ok()


@check
def net_systemd_unit(ctx):
    if not shutil.which("systemctl"):
        raise Skip("no systemctl on this OS")
    name = "nixweb-%s.service" % os.path.basename(ctx.root.rstrip("/"))
    unit = os.path.expanduser("~/.config/systemd/user/" + name)
    if not os.path.isfile(unit):
        raise Skip("no %s on this host (run nixweb install if the app should survive a reboot)" % name)
    r = subprocess.run(["systemctl", "--user", "is-enabled", name], capture_output=True, text=True)
    return ok() if r.stdout.strip() == "enabled" else bad("%s exists but is %s" % (name, r.stdout.strip() or "not enabled"))


@check
def net_edge(ctx):
    if ctx.edge is None:
        raise Skip("pass --url https://HOST:PORT to check the tailnet edge")
    st, h, _ = ctx.edge.req("GET", "/")
    if st != 200:
        return bad("GET / through the edge returned %d" % st)
    missing = [k for k in ("content-security-policy", "x-content-type-options", "referrer-policy") if k not in h]
    return bad("headers missing at the edge: " + ", ".join(missing)) if missing else ok()


# ------------------------------- SRV ---------------------------------------
HASHED = re.compile(r"[.\-][0-9a-f]{8,}\.[a-z0-9]+$")


def served_paths(ctx, *exts):
    return ["/" + f[len(ctx.pub):] for f in ctx.by_ext(*exts)]


@check
def srv_hides_secrets(ctx):
    leaks = []
    for p in ("/.git/config", "/.env", "/.gitignore", "/.DS_Store", "/server.py"):
        st = ctx.get(p)[0]
        if st != 404:
            leaks.append("%s -> %d" % (p, st))
    return bad("should be 404: " + ", ".join(leaks)) if leaks else ok()


@check
def srv_ping(ctx):
    t0 = time.time()
    st, h, _ = ctx.get("/ping")
    took = time.time() - t0
    if st != 200:
        return bad("GET /ping returned %d" % st)
    if "no-store" not in h.get("cache-control", ""):
        return bad("GET /ping has no Cache-Control: no-store")
    if ctx.get("/ping", "HEAD")[0] != 200:
        return bad("HEAD /ping did not return 200")
    return bad("/ping took %.1f s" % took) if took > 1.5 else ok()


@check
def srv_traversal(ctx):
    leaks = []
    for p in ("/../server.py", "/%2e%2e/server.py", "/%252e%252e/server.py", "/..%2fserver.py",
              "/%2e%2e%2fserver.py", "/..%5cserver.py", "/....//server.py", "/%2e%2e/%2e%2e/etc/passwd"):
        st = ctx.get(p)[0]
        if not 400 <= st < 500:
            leaks.append("%s -> %d" % (p, st))
    return bad("traversal not refused: " + ", ".join(leaks)) if leaks else ok()


@check
def srv_mime(ctx):
    want = {".webmanifest": "application/manifest+json", ".js": "text/javascript", ".mjs": "text/javascript",
            ".css": "text/css", ".svg": "image/svg+xml", ".html": "text/html"}
    problems = []
    for p in served_paths(ctx, *want.keys())[:14]:
        st, h, _ = ctx.get(p)
        ct = h.get("content-type", "").lower()
        ext = os.path.splitext(p)[1]
        if st != 200 or not ct.startswith(want[ext]):
            problems.append("%s is %s (%d)" % (p, ct or "untyped", st))
        elif "charset=utf-8" not in ct and ext != ".svg":
            problems.append("%s has no charset=utf-8" % p)
    return bad("; ".join(problems)) if problems else ok()


@check
def srv_public_only(ctx):
    if ctx.no_live:
        raise Skip(ctx.live_error)
    if not os.path.isfile(ctx.p("server.py")):
        raise Skip("no server.py to start on a copy")
    tmp = tempfile.mkdtemp(prefix="nwcheck-")
    try:
        dst = os.path.join(tmp, "app")
        shutil.copytree(ctx.root, dst, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
        pub = "public" if os.path.isdir(os.path.join(dst, "public")) else "."
        with open(os.path.join(dst, "zz-nixweb-canary.txt"), "w") as f:
            f.write("canary")
        with open(os.path.join(dst, pub, "zz-nixweb-canary.db"), "w") as f:
            f.write("canary")
        with open(os.path.join(dst, pub, "server.py.bak"), "w") as f:
            f.write("canary")
        os.makedirs(os.path.join(dst, pub, "zz-empty-dir"), exist_ok=True)
        live = Live(dst)
        err = live.start()
        if err:
            raise Skip(err)
        try:
            leaks = []
            for p in ("/zz-nixweb-canary.txt", "/zz-nixweb-canary.db", "/server.py.bak", "/zz-empty-dir/"):
                if live.req("GET", p)[0] == 200:
                    leaks.append(p)
            return bad("served although it should not be: " + ", ".join(leaks)) if leaks else ok()
        finally:
            live.stop()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@check
def srv_cache_control(ctx):
    paths = ["/"] + [p for p in served_paths(ctx, ".html", ".js", ".mjs", ".css", ".webmanifest")
                     if not HASHED.search(p)]
    problems = []
    for p in paths[:14]:
        cc = ctx.get(p)[1].get("cache-control", "")
        if not re.search(r"no-cache|no-store|max-age=0", cc):
            problems.append("%s has Cache-Control %r" % (p, cc))
    return bad("; ".join(problems)) if problems else ok()


@check
def srv_no_leaks(ctx):
    problems = []
    for p in ("/", "/zz-missing-nixweb"):
        st, h, body = ctx.get(p)
        server = h.get("server", "")
        if re.search(r"python|simplehttp|werkzeug|\d+\.\d+", server, re.I):
            problems.append("Server header %r names a version" % server)
        text = body.decode("utf-8", "replace")
        if st == 404 and re.search(r"traceback|python|/home/|/usr/|/tmp/|error response", text, re.I):
            problems.append("404 body leaks detail")
    return bad("; ".join(problems)) if problems else ok()


@check
def srv_delivery(ctx):
    cands = [(os.path.getsize(ctx.p(f)), f) for f in ctx.by_ext(".css", ".js", ".html", ".json") if os.path.getsize(ctx.p(f)) > 600]
    if not cands:
        return na("no text file over 600 bytes to test with")
    path = "/" + sorted(cands)[0][1][len(ctx.pub):]
    st, h, plain = ctx.get(path)
    problems = []
    if "etag" in h:
        c = ctx.get(path, headers={"If-None-Match": h["etag"]})[0]
    elif "last-modified" in h:
        c = ctx.get(path, headers={"If-Modified-Since": h["last-modified"]})[0]
    else:
        c = None
        problems.append("no ETag or Last-Modified on %s" % path)
    if c is not None and c != 304:
        problems.append("conditional GET returned %d, not 304" % c)
    st2, h2, gz = ctx.get(path, headers={"Accept-Encoding": "gzip"})
    if h2.get("content-encoding") != "gzip":
        problems.append("%s is not gzipped when the client accepts gzip" % path)
    else:
        try:
            if gzip.decompress(gz) != plain:
                problems.append("gzipped body differs from the plain body")
        except (OSError, EOFError):
            problems.append("gzipped body does not decompress")
        if "accept-encoding" not in h2.get("vary", "").lower():
            problems.append("no Vary: Accept-Encoding on a gzipped response")
    return bad("; ".join(problems)) if problems else ok()


@check
def srv_range(ctx):
    cands = [f for f in ctx.by_ext(".js", ".css", ".html", ".png") if os.path.getsize(ctx.p(f)) > 64]
    if not cands:
        return na("no file over 64 bytes to test with")
    path = "/" + cands[0][len(ctx.pub):]
    st, h, body = ctx.get(path, headers={"Range": "bytes=0-9"})
    if st != 206 or not h.get("content-range", "").startswith("bytes 0-9/") or len(body) != 10:
        return bad("Range: bytes=0-9 on %s gave %d (want 206 with 10 bytes and Content-Range)" % (path, st))
    st = ctx.get(path, headers={"Range": "bytes=999999999-"})[0]
    return ok() if st == 416 else bad("an unsatisfiable range gave %d, not 416" % st)


@check
def srv_sigterm(ctx):
    if ctx.no_live:
        raise Skip(ctx.live_error)
    if not os.path.isfile(ctx.p("server.py")):
        raise Skip("no server.py to start")
    live = Live(ctx.root)
    err = live.start()
    if err:
        raise Skip(err)
    live.proc.terminate()
    try:
        rc = live.proc.wait(3)
    except subprocess.TimeoutExpired:
        live.proc.kill()
        return bad("still running 3 seconds after SIGTERM")
    return ok() if rc == 0 else bad("exit status %s on SIGTERM (want 0)" % rc)


@check
def srv_body_cap(ctx):
    if ctx.live is None:
        raise Skip(ctx.live_error)
    conn = http.client.HTTPConnection(ctx.live.host, ctx.live.port, timeout=5)
    try:
        conn.request("POST", "/api/nixweb-check", body=b"{",
                     headers={"Content-Type": "application/json", "Content-Length": "99999999"})
        st = conn.getresponse().status
    except socket.timeout:
        return bad("the server waited for a 99999999 byte body instead of refusing it")
    except (OSError, http.client.HTTPException) as e:
        raise Skip("could not run the oversize test (%s)" % e)
    finally:
        conn.close()
    return ok() if st == 413 else bad("an oversize body got %d, not 413" % st)


# ------------------------------- SEC ---------------------------------------
def parse_csp(v):
    d = {}
    for part in v.split(";"):
        bits = part.strip().split()
        if bits:
            d[bits[0].lower()] = bits[1:]
    return d


@check
def sec_csp(ctx):
    v = ctx.get("/")[1].get("content-security-policy")
    if not v:
        return bad("no Content-Security-Policy header")
    d = parse_csp(v)
    problems = []
    if "'self'" not in d.get("default-src", []) and "'none'" not in d.get("default-src", []):
        problems.append("default-src is not 'self'")
    script = d.get("script-src", d.get("default-src", []))
    for bad_tok in ("'unsafe-inline'", "'unsafe-eval'", "*"):
        if bad_tok in script:
            problems.append("script-src allows %s" % bad_tok)
    if d.get("object-src") != ["'none'"]:
        problems.append("object-src is not 'none'")
    for k in ("base-uri", "frame-ancestors"):
        if k not in d:
            problems.append("no %s" % k)
    return bad("; ".join(problems)) if problems else ok()


@check
def sec_headers(ctx):
    problems = []
    for p in ("/", "/ping", "/zz-missing-nixweb"):
        h = ctx.get(p)[1]
        if h.get("x-content-type-options", "").lower() != "nosniff":
            problems.append("%s: no X-Content-Type-Options: nosniff" % p)
        if h.get("referrer-policy", "").lower() not in ("no-referrer", "same-origin"):
            problems.append("%s: Referrer-Policy is not no-referrer or same-origin" % p)
        if not h.get("permissions-policy"):
            problems.append("%s: no Permissions-Policy" % p)
    return bad("; ".join(problems)) if problems else ok()


@check
def sec_host_allowlist(ctx):
    st = ctx.get("/", headers={"Host": "evil.example"})[0]
    if st not in (421, 403, 400):
        return bad("Host: evil.example got %d, want 421 or 403" % st)
    own = "127.0.0.1:%d" % ctx.live.port
    st = ctx.get("/", headers={"Host": own})[0]
    return ok() if st == 200 else bad("the server's own name %s got %d" % (own, st))


@check
def sec_csrf(ctx):
    if ctx.live is None:
        raise Skip(ctx.live_error)
    port = ctx.live.port
    base = {"Content-Type": "application/json"}
    path = "/api/nixweb-check"

    def post(extra):
        h = dict(base)
        h.update(extra)
        return ctx.get(path, "POST", h, b"{}")[0]

    problems = []
    for label, extra in (("Sec-Fetch-Site: cross-site", {"Sec-Fetch-Site": "cross-site"}),
                         ("Sec-Fetch-Site: same-site", {"Sec-Fetch-Site": "same-site"}),
                         ("Origin: https://evil.example", {"Origin": "https://evil.example"}),
                         ("Origin: null", {"Origin": "null"})):
        st = post(extra)
        if st != 403:
            problems.append("%s got %d, want 403" % (label, st))
    st = post({"Sec-Fetch-Site": "same-origin", "Origin": "http://127.0.0.1:%d" % port})
    if st in (403, 421):
        problems.append("a same-origin write was refused with %d" % st)
    return bad("; ".join(problems)) if problems else ok()


@check
def sec_no_cors(ctx):
    st, h, _ = ctx.get("/", "OPTIONS", {"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    problems = []
    if st != 405:
        problems.append("OPTIONS got %d, want 405" % st)
    if "access-control-allow-origin" in h:
        problems.append("OPTIONS reply carries Access-Control-Allow-Origin")
    if "access-control-allow-origin" in ctx.get("/", headers={"Origin": "https://evil.example"})[1]:
        problems.append("GET reply carries Access-Control-Allow-Origin")
    return bad("; ".join(problems)) if problems else ok()


TRACKERS = re.compile(r"gtag\(|googletagmanager|google-analytics|plausible\.|mixpanel|segment\.(com|io)|"
                      r"sentry|hotjar|posthog|sendBeacon|fullstory|amplitude\.", re.I)


@check
def sec_no_third_party(ctx):
    hits = []
    for f in ctx.walk():
        if not f.startswith(ctx.pub) or not f.lower().endswith((".html", ".css", ".js", ".mjs", ".webmanifest", ".json", ".svg")):
            continue
        if f.lower().endswith(".min.js") or "/vendor/" in "/" + f:
            continue
        raw = ctx.text(f) or ""
        text = strip_html_comments(raw) if f.endswith(".html") else (raw if f.endswith((".json", ".webmanifest", ".svg")) else strip_c_comments(raw))
        raw_lines = raw.split("\n")
        for i, line in enumerate(text.split("\n")):
            if waived(raw_lines, i, "NW-SEC-006"):
                continue
            for u in re.findall(r"https?://[^\s\"'<>)\\]+", line):
                host = urlsplit(u).hostname or ""
                if host in ("localhost", "127.0.0.1") or u.startswith(("http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink")):
                    continue
                hits.append("%s:%d %s" % (f, i + 1, u[:60]))
            if re.search(r"(src|href)\s*=\s*[\"']//", line):
                hits.append("%s:%d protocol-relative URL" % (f, i + 1))
            if f.endswith((".js", ".mjs", ".html")) and TRACKERS.search(line):
                hits.append("%s:%d analytics or tracking code" % (f, i + 1))
    return bad("; ".join(hits[:5])) if hits else ok()


@check
def sec_no_sinks(ctx):
    pat = (r"\beval\s*\(|new\s+Function\s*\(|document\.write(ln)?\s*\(|\b(setTimeout|setInterval)\s*\(\s*[\"'`]"
           r"|\.(innerHTML|outerHTML)\b|insertAdjacentHTML\s*\(")
    hits = js_hits(ctx, "NW-SEC-007", pat, include_sw=True)
    return bad("code-injection sink at " + ", ".join(hits[:6])) if hits else ok()


@check
def sec_no_inline(ctx):
    pg = ctx.page
    if not pg.present:
        return bad("public/index.html is missing")
    problems = []
    if pg.inline_scripts:
        problems.append("%d inline script(s)" % pg.inline_scripts)
    if pg.inline_handlers:
        problems.append("%d inline on* handler(s)" % pg.inline_handlers)
    styles = len([1 for t, a, _ in pg.tags if t == "style"]) + len([1 for t, a, _ in pg.tags if "style" in a])
    if styles:
        problems.append("%d inline style element(s) or attribute(s)" % styles)
    return bad(", ".join(problems)) if problems else ok()


SECRET_PATTERNS = [r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\b(sk|pk)-[A-Za-z0-9]{20,}", r"\bghp_[A-Za-z0-9]{20,}",
                   r"\bgithub_pat_[A-Za-z0-9_]{20,}", r"\bAKIA[0-9A-Z]{16}\b", r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
                   r"(api[_-]?key|secret|passw(or)?d|token)[\"']?\s*[:=]\s*[\"'][^\"']{12,}[\"']"]


@check
def sec_no_secrets(ctx):
    hits = []
    for f in ctx.walk():
        if not f.startswith(ctx.pub) or not f.lower().endswith(TEXT_EXT):
            continue
        raw = ctx.text(f) or ""
        text = strip_c_comments(raw) if f.endswith((".js", ".mjs", ".css")) else raw
        for rx in SECRET_PATTERNS:
            if re.search(rx, text, re.I):
                hits.append(f)
                break
    if os.path.isdir(ctx.p(".git")) and shutil.which("git"):
        r = subprocess.run(["git", "-C", ctx.root, "ls-files"], capture_output=True, text=True)
        for f in r.stdout.split("\n"):
            b = os.path.basename(f)
            if b == ".env" or (b.startswith(".env.") and b not in (".env.example", ".env.sample")):
                hits.append("%s is tracked by git" % f)
    return bad("looks like a secret: " + ", ".join(hits[:5])) if hits else ok()


# ------------------------------- INS ---------------------------------------
@check
def ins_manifest_linked(ctx):
    if not ctx.page.present:
        return bad("public/index.html is missing")
    if not ctx.page.links("manifest"):
        return bad("no link rel=manifest in index.html")
    _, rel, err = ctx.manifest()
    return bad(err) if err else ok()


@check
def ins_manifest_members(ctx):
    data, rel, err = ctx.manifest()
    if err:
        return bad(err)
    problems = ["missing %s" % k for k in ("name", "short_name", "start_url") if not str(data.get(k, "")).strip()]
    if data.get("display") != "standalone":
        problems.append("display is %r, want 'standalone'" % data.get("display"))
    if not data.get("icons"):
        problems.append("no icons")
    if data.get("prefer_related_applications") is True:
        problems.append("prefer_related_applications is true")
    return bad("; ".join(problems)) if problems else ok()


@check
def ins_manifest_id_scope(ctx):
    data, rel, err = ctx.manifest()
    if err:
        return bad(err)
    problems = []
    if not str(data.get("id", "")).strip():
        problems.append("no id")
    scope, start = data.get("scope"), data.get("start_url")
    if not scope or not start:
        problems.append("scope and start_url are both required")
    else:
        murl = urljoin("https://app.invalid/", rel[len(ctx.pub):] if rel.startswith(ctx.pub) else rel)
        s_abs, st_abs = urljoin(murl, scope), urljoin(murl, start)
        if not s_abs.endswith("/"):
            problems.append("scope does not end with a slash")
        if not st_abs.startswith(s_abs):
            problems.append("start_url is outside scope")
    return bad("; ".join(problems)) if problems else ok()


def parse_sizes(s):
    return [tuple(int(x) for x in t.lower().split("x")) for t in str(s or "").split() if re.match(r"^\d+x\d+$", t.lower())]


@check
def ins_icons(ctx):
    data, rel, err = ctx.manifest()
    if err:
        return bad(err)
    problems, have = [], {"192": False, "512": False, "mask": False}
    for ic in data.get("icons") or []:
        src = str(ic.get("src", ""))
        purposes = str(ic.get("purpose", "any")).split()
        sizes = parse_sizes(ic.get("sizes"))
        path = ctx.resolve(src, rel)
        if path is None or not os.path.isfile(ctx.p(path)):
            problems.append("%s does not exist" % src)
            continue
        info = png_info(ctx.p(path))
        if info is None:
            problems.append("%s is not a readable PNG" % src)
            continue
        if sizes and (info["w"], info["h"]) != sizes[0]:
            problems.append("%s is %dx%d but the manifest says %dx%d" % ((src, info["w"], info["h"]) + sizes[0]))
        px = png_distinct_pixels(info)
        if px is not None and px < 2:
            problems.append("%s is a single flat colour" % src)
        if "maskable" in purposes and "any" in purposes:
            problems.append("%s mixes any and maskable; use two files" % src)
        if (info["w"], info["h"]) == (192, 192) and "any" in purposes:
            have["192"] = True
        if (info["w"], info["h"]) == (512, 512) and "any" in purposes:
            have["512"] = True
        if (info["w"], info["h"]) == (512, 512) and "maskable" in purposes and "any" not in purposes:
            have["mask"] = True
    for k, label in (("192", "192x192 any"), ("512", "512x512 any"), ("mask", "512x512 maskable")):
        if not have[k]:
            problems.append("no %s PNG icon" % label)
    return bad("; ".join(problems)) if problems else ok()


@check
def ins_apple_icon(ctx):
    links = ctx.page.links("apple-touch-icon")
    if not links:
        return bad("no link rel=apple-touch-icon")
    path = ctx.resolve(links[0].get("href", ""))
    if path is None or not os.path.isfile(ctx.p(path)):
        return bad("the apple-touch-icon file does not exist")
    info = png_info(ctx.p(path))
    if info is None:
        return bad("the apple-touch-icon is not a readable PNG")
    problems = []
    if (info["w"], info["h"]) != (180, 180):
        problems.append("it is %dx%d, want 180x180" % (info["w"], info["h"]))
    if info["ctype"] in (4, 6) or info["trns"]:
        problems.append("it has an alpha channel (iOS paints transparency black)")
    return bad("; ".join(problems)) if problems else ok()


@check
def ins_apple_meta(ctx):
    pg = ctx.page
    problems = []
    if (pg.meta("apple-mobile-web-app-capable") or "").lower() != "yes":
        problems.append("apple-mobile-web-app-capable is not yes")
    if not (pg.meta("apple-mobile-web-app-title") or "").strip():
        problems.append("no apple-mobile-web-app-title")
    if (pg.meta("mobile-web-app-capable") or "").lower() != "yes":
        problems.append("mobile-web-app-capable is not yes")
    return bad("; ".join(problems)) if problems else ok()


@check
def ins_colors(ctx):
    data, rel, err = ctx.manifest()
    if err:
        return bad(err)
    problems = []
    meta = (ctx.page.meta("theme-color") or "").strip().lower()
    theme = str(data.get("theme_color", "")).strip().lower()
    if not meta:
        problems.append("no theme-color meta")
    elif meta != theme:
        problems.append("theme-color %s differs from manifest theme_color %s" % (meta, theme or "(none)"))
    if not str(data.get("background_color", "")).strip():
        problems.append("no manifest background_color")
    rules = css_rules(ctx)
    painted = [v for sels, d in rules if any(s in ("html", "body") for s in sels)
               for k, v in d.items() if k in ("background", "background-color")]
    if not painted:
        problems.append("html or body paints no background (the launch frame is white)")
    return bad("; ".join(problems)) if problems else ok()


@check
def ins_status_bar(ctx):
    v = (ctx.page.meta("apple-mobile-web-app-status-bar-style") or "").lower()
    if not v:
        return bad("apple-mobile-web-app-status-bar-style is not set")
    if v == "black-translucent" and not re.search(r"max\([^;{}]*(safe-area-inset-top|var\(--top\))", css_text(ctx)):
        return bad("black-translucent without a max() fallback around the top inset (WebKit bug 301994)")
    return ok()


# ------------------------------- SHL ---------------------------------------
@check
def shl_viewport(ctx):
    v = ctx.page.meta("viewport")
    if v is None:
        return bad("no viewport meta")
    toks = dict(t.strip().split("=", 1) for t in v.split(",") if "=" in t)
    problems = []
    if toks.get("width") != "device-width":
        problems.append("width is not device-width")
    if toks.get("initial-scale") != "1":
        problems.append("initial-scale is not 1")
    if toks.get("viewport-fit") != "cover":
        problems.append("viewport-fit is not cover")
    return bad("; ".join(problems)) if problems else ok()


@check
def shl_safe_area(ctx):
    css = css_text(ctx)
    for side in ("top", "right", "bottom", "left"):
        if not re.search(r"env\(\s*safe-area-inset-%s\b" % side, css):
            return bad("env(safe-area-inset-%s) is not used" % side)
    props = [k for sels, d in css_rules(ctx) for k, v in d.items() if k.startswith("--") and "safe-area-inset" in v]
    for m in re.finditer(r"(calc|max)\(([^;{}]*)\)", css):
        body = m.group(2)
        if "env(safe-area-inset" in body or any("var(%s" % p in body for p in props):
            return ok()
    return bad("no calc() or max() adds an inset to real padding; an inset used alone cramps a phone without a notch")


@check
def shl_scroll_model(ctx):
    rules = css_rules(ctx)
    root = {}
    for sels, d in rules:
        if any(s in ("html", "body") for s in sels):
            root.update(d)
    problems = []
    if "hidden" not in (root.get("overflow") or root.get("overflow-y") or "").lower():
        problems.append("html and body do not set overflow: hidden")
    if (root.get("overscroll-behavior") or root.get("overscroll-behavior-y") or "").lower() != "none":
        problems.append("html and body do not set overscroll-behavior: none")
    if not any((d.get("overflow-y") or d.get("overflow") or "").lower() in ("auto", "scroll")
               and (d.get("overscroll-behavior") or "").lower() == "contain" for sels, d in rules):
        problems.append("no list box with overflow-y: auto and overscroll-behavior: contain")
    return bad("; ".join(problems)) if problems else ok()


@check
def shl_no_100vh(ctx):
    return bad("100vh found in the CSS") if re.search(r"\b100vh\b", css_text(ctx)) else ok()


@check
def shl_input_font(ctx):
    for sels, d in css_rules(ctx):
        if any(re.match(r"^(input|textarea|select)\b", s) for s in sels) and "font-size" in d:
            v = d["font-size"].lower()
            nums = [float(x) for x in re.findall(r"([\d.]+)px", v)] + [float(x) * 16 for x in re.findall(r"([\d.]+)rem", v)]
            if nums and max(nums) >= 16:
                return ok()
    return bad("no rule gives input, textarea and select a font-size of at least 16px")


@check
def shl_touch_action(ctx):
    rules = css_rules(ctx)
    if not any(d.get("touch-action", "").lower() == "manipulation" for _, d in rules):
        return bad("no touch-action: manipulation on any control")
    for sels, d in rules:
        if "touch-action" in d and any(s in ("html", "body", "*", ":root") for s in sels):
            return bad("touch-action is set on %s" % ", ".join(sels))
    return ok()


@check
def shl_selection(ctx):
    for sels, d in css_rules(ctx):
        for k in ("user-select", "-webkit-user-select"):
            if d.get(k, "").lower() == "none" and any(s in ("html", "body", "*", ":root", ".app", "main") for s in sels):
                return bad("user-select: none on %s makes all content unselectable" % ", ".join(sels))
    return ok()


@check
def shl_text_size(ctx):
    rules = css_rules(ctx)
    problems = []
    if not any(d.get("-webkit-text-size-adjust", d.get("text-size-adjust", "")).replace(" ", "") == "100%" for _, d in rules):
        problems.append("no -webkit-text-size-adjust: 100%")
    fams = [v for sels, d in rules if any(s in ("html", "body") for s in sels) for k, v in d.items() if k == "font-family"]
    if not fams or not re.match(r"^\s*(system-ui|-apple-system)", fams[-1]):
        problems.append("the font stack does not start with system-ui or -apple-system")
    return bad("; ".join(problems)) if problems else ok()


@check
def shl_format_detection(ctx):
    return ok() if "telephone=no" in (ctx.page.meta("format-detection") or "").replace(" ", "") else bad("no meta format-detection telephone=no")


@check
def shl_keyboard(ctx):
    js = js_text(ctx)
    has_inputs = bool(ctx.page.controls) or bool(re.search(r"createElement\(\s*['\"](input|textarea)['\"]", js))
    if not has_inputs:
        return na("the app has no text inputs")
    return ok() if "visualViewport" in js else bad("the app has inputs but never reads window.visualViewport")


# ------------------------------- IOS ---------------------------------------
@check
def ios_standalone(ctx):
    js = js_text(ctx)
    if not re.search(r"display-mode|navigator\.standalone", js):
        return na("the app does not branch on install state")
    miss = [label for label, rx in (("display-mode: standalone", r"display-mode:\s*standalone"),
                                    ("display-mode: fullscreen", r"display-mode:\s*fullscreen"),
                                    ("navigator.standalone", r"navigator\.standalone")) if not re.search(rx, js)]
    return bad("install state is not tested with: " + ", ".join(miss)) if miss else ok()


@check
def ios_no_ua(ctx):
    hits = js_hits(ctx, "NW-IOS-002", r"navigator\.(userAgent|appVersion)\b", include_sw=True)
    return bad("user-agent parsing at " + ", ".join(hits[:5])) if hits else ok()


@check
def ios_lifecycle(ctx):
    js = js_text(ctx)
    problems = []
    if re.search(r"['\"](unload|beforeunload)['\"]", js):
        problems.append("uses unload or beforeunload")
    if "visibilitychange" not in js:
        problems.append("no visibilitychange listener")
    if "pageshow" not in js or "persisted" not in js:
        problems.append("no pageshow handler that reads event.persisted")
    return bad("; ".join(problems)) if problems else ok()


RISKY_APIS = [
    ("navigator.vibrate", r"navigator\.vibrate\s*\(", r"['\"]vibrate['\"]\s+in\s+navigator|navigator\.vibrate\s*&&|typeof\s+navigator\.vibrate"),
    ("Web Bluetooth", r"navigator\.bluetooth\b", r"['\"]bluetooth['\"]\s+in\s+navigator|navigator\.bluetooth\s*&&|typeof\s+navigator\.bluetooth"),
    ("WebUSB", r"navigator\.usb\b", r"['\"]usb['\"]\s+in\s+navigator|navigator\.usb\s*&&|typeof\s+navigator\.usb"),
    ("Web Serial", r"navigator\.serial\b", r"['\"]serial['\"]\s+in\s+navigator|navigator\.serial\s*&&|typeof\s+navigator\.serial"),
    ("WebHID", r"navigator\.hid\b", r"['\"]hid['\"]\s+in\s+navigator|navigator\.hid\s*&&|typeof\s+navigator\.hid"),
    ("File System Access", r"\bshow(Open|Save)FilePicker\b|\bshowDirectoryPicker\b", r"['\"]show(Open|Save)FilePicker['\"]\s+in\s+window|window\.show(Open|Save)FilePicker\s*&&|typeof\s+window\.show"),
    ("Contact Picker", r"navigator\.contacts\b", r"['\"]contacts['\"]\s+in\s+navigator|navigator\.contacts\s*&&"),
    ("Background Sync", r"\.sync\s*\.\s*register\s*\(|periodicSync", r"['\"](sync|periodicSync)['\"]\s+in\s+|SyncManager"),
]


@check
def ios_feature_detect(ctx):
    js = js_text(ctx, include_sw=True)
    problems = []
    for label, use, guard in RISKY_APIS:
        if re.search(use, js) and not re.search(guard, js):
            problems.append("%s is used without a feature test" % label)
    if "wakeLock" in js and not (re.search(r"['\"]wakeLock['\"]\s+in\s+navigator", js) and "visibilitychange" in js):
        problems.append("wakeLock needs an 'in navigator' test and re-acquire on visibilitychange")
    if "new MediaRecorder" in js and "isTypeSupported" not in js:
        problems.append("MediaRecorder without isTypeSupported")
    return bad("; ".join(problems)) if problems else ok()


# ------------------------------- OFF ---------------------------------------
@check
def off_sw_present(ctx):
    sw = sw_text(ctx)
    if sw is None:
        return bad("%ssw.js does not exist" % ctx.pub)
    js = js_text(ctx)
    problems = []
    if not re.search(r"serviceWorker\s*\.\s*register\s*\(", js):
        problems.append("nothing registers the service worker")
    if not re.search(r"['\"]serviceWorker['\"]\s+in\s+navigator", js):
        problems.append("the registration is not guarded by 'serviceWorker' in navigator")
    for ev in ("install", "activate", "fetch"):
        if not re.search(r"addEventListener\(\s*['\"]%s['\"]" % ev, sw):
            problems.append("no %s handler" % ev)
    return bad("; ".join(problems)) if problems else ok()


@check
def off_cache_names(ctx):
    sw = sw_text(ctx)
    if sw is None:
        return bad("no sw.js")
    problems = []
    if not re.search(r"(const|let|var)\s+VERSION\b", sw):
        problems.append("no VERSION constant")
    deletes = [m.start() for m in re.finditer(r"caches\.delete", sw)]
    if not deletes:
        problems.append("activate never deletes old caches")
    elif not any(re.search(r"\.startsWith\(", sw[max(0, d - 400):d]) for d in deletes):
        problems.append("old caches are deleted without a name-prefix test, which would wipe a sibling app")
    return bad("; ".join(problems)) if problems else ok()


@check
def off_shell_exists(ctx):
    urls = shell_urls(ctx)
    if urls is None:
        return na("no precache array found in sw.js")
    missing = []
    for u in urls:
        path = ctx.resolve(u if u not in ("", "./", "/") else "index.html")
        if path is None or not os.path.isfile(ctx.p(path)):
            missing.append(u)
    return bad("precached but missing: " + ", ".join(missing)) if missing else ok()


@check
def off_guards(ctx):
    sw = sw_text(ctx)
    if sw is None:
        return bad("no sw.js")
    problems = []
    if not re.search(r"\.method\s*[!=]==?\s*['\"]GET['\"]", sw):
        problems.append("no GET-only guard")
    if not re.search(r"\.origin\s*[!=]==?\s*(self\.)?location\.origin", sw):
        problems.append("no same-origin guard")
    if "/ping" not in sw:
        problems.append("/ping is not excluded from caching")
    return bad("; ".join(problems)) if problems else ok()


@check
def off_ok_only(ctx):
    sw = sw_text(ctx)
    if sw is None:
        return bad("no sw.js")
    puts = [m.start() for m in re.finditer(r"\.put\(", sw)]
    if not puts:
        return na("the worker never writes to the cache after install")
    problems = []
    for pos in puts:
        before = sw[max(0, pos - 400):pos]
        if not re.search(r"\.ok\b|status\s*===?\s*200", before):
            problems.append("a cache.put is not guarded by an ok test")
    if "waitUntil" not in sw:
        problems.append("cache.put is not passed to event.waitUntil")
    if ".clone()" not in sw:
        problems.append("the response is not cloned before caching")
    return bad("; ".join(sorted(set(problems)))) if problems else ok()


@check
def off_nav_fallback(ctx):
    sw = sw_text(ctx)
    if sw is None:
        return bad("no sw.js")
    falls = [m.start() for m in re.finditer(r"match\(\s*['\"](\./|/|index\.html)['\"]", sw)]
    if not falls:
        return na("the worker has no shell fallback")
    for pos in falls:
        if not re.search(r"mode\s*===?\s*['\"]navigate['\"]", sw[max(0, pos - 400):pos]):
            return bad("a fallback to the shell is not gated by request.mode === 'navigate'")
    return ok()


@check
def off_precache_fresh(ctx):
    sw = sw_text(ctx)
    if sw is None:
        return bad("no sw.js")
    if re.search(r"cache\s*:\s*['\"]reload['\"]", sw):
        return ok()
    if ctx.live is None:
        raise Skip("no cache: 'reload' in sw.js and no server to prove NW-SRV-006")
    return ok() if srv_cache_control(ctx)[0] == PASS else bad("neither cache: 'reload' in sw.js nor no-cache from the server")


@check
def off_update_via_cache(ctx):
    js = js_text(ctx)
    m = re.search(r"serviceWorker\s*\.\s*register\s*\(\s*(['\"])([^'\"]+)\1\s*(?:,\s*\{([^}]*)\})?", js)
    if not m:
        return bad("no serviceWorker.register call with a literal URL")
    problems = []
    if not re.match(r"^/?sw\.js$", m.group(2)):
        problems.append("the worker URL %r is not a stable sw.js" % m.group(2))
    if not re.search(r"updateViaCache\s*:\s*['\"]none['\"]", m.group(3) or ""):
        problems.append("register() does not pass updateViaCache: 'none'")
    return bad("; ".join(problems)) if problems else ok()


@check
def off_update_flow(ctx):
    sw, js = sw_text(ctx) or "", js_text(ctx)
    problems = []
    m = re.search(r"addEventListener\(\s*['\"]install['\"].*?(?=addEventListener\(|$)", sw, re.S)
    if m and "skipWaiting" in m.group(0):
        problems.append("the worker calls skipWaiting during install")
    if "SKIP_WAITING" not in sw:
        problems.append("the worker does not wait for a SKIP_WAITING message")
    if "controllerchange" not in js:
        problems.append("the page has no controllerchange listener")
    if not re.search(r"visibilitychange[\s\S]{0,500}\.update\s*\(", js):
        problems.append("the page does not call registration.update() when it becomes visible")
    return bad("; ".join(problems)) if problems else ok()


@check
def off_probe(ctx):
    js = js_text(ctx)
    problems = []
    if "ping" not in js:
        problems.append("the app never asks /ping")
    if not re.search(r"cache\s*:\s*['\"]no-store['\"]", js):
        problems.append("the probe does not use cache: 'no-store'")
    if not re.search(r"AbortController|AbortSignal", js):
        problems.append("the probe has no timeout")
    return bad("; ".join(problems)) if problems else ok()


@check
def off_fetch_timeout(ctx):
    rx = re.compile(r"\bfetch\s*\(")
    hits = []
    for rel, raw in app_js(ctx).items():
        raw_lines, text = raw.split("\n"), strip_c_comments(raw)
        for m in rx.finditer(text):
            line = text.count("\n", 0, m.start())
            if "signal" not in text[m.start():m.start() + 240] and not waived(raw_lines, line, "NW-OFF-011"):
                hits.append("%s:%d" % (rel, line + 1))
    return bad("fetch without a signal at " + ", ".join(hits[:6])) if hits else ok()


@check
def off_error_boundary(ctx):
    js, problems = js_text(ctx), []
    for ev in ("error", "unhandledrejection"):
        if not re.search(r"addEventListener\(\s*['\"]%s['\"]" % ev, js):
            problems.append("no window %s listener" % ev)
    if not any(t == "noscript" for t, _, _ in ctx.page.tags):
        problems.append("no noscript message")
    return bad("; ".join(problems)) if problems else ok()


@check
def off_api_policy(ctx):
    sw = sw_text(ctx)
    if sw is None or "/api/" not in sw or ".put(" not in sw:
        return na("the worker caches no API data")
    problems = []
    if not re.search(r"no-store|private", sw):
        problems.append("does not skip no-store or private responses")
    if ".keys()" not in sw:
        problems.append("does not cap the number of cached entries")
    if not re.search(r"X-From-Cache|x-from-cache|stale", sw):
        problems.append("does not mark answers served from cache")
    return bad("; ".join(problems)) if problems else ok()


# ------------------------------- DAT ---------------------------------------
@check
def dat_outbox(ctx):
    if not sends_writes(ctx):
        return na("the app sends no writes")
    return ok() if "indexedDB" in js_text(ctx) else bad("the app sends writes but never uses indexedDB for an outbox")


@check
def dat_idempotency(ctx):
    if not sends_writes(ctx):
        return na("the app sends no writes")
    return ok() if "Idempotency-Key" in js_text(ctx) else bad("writes do not send an Idempotency-Key")


@check
def dat_storage(ctx):
    problems = []
    used = False
    for rel, raw in app_js(ctx).items():
        text = strip_c_comments(raw)
        for m in re.finditer(r"\b(localStorage|sessionStorage)\b", text):
            used = True
            if not re.search(r"\btry\s*\{", text[max(0, m.start() - 300):m.start()]):
                problems.append("%s:%d storage access outside try" % (rel, text.count("\n", 0, m.start()) + 1))
        if re.search(r"setItem\([^)]*JSON\.stringify", text):
            problems.append("%s stores JSON in localStorage" % rel)
    if not used:
        return na("the app does not use localStorage or sessionStorage")
    return bad("; ".join(problems[:5])) if problems else ok()


# ------------------------------- UIX ---------------------------------------
@check
def uix_confirm(ctx):
    if not sends_writes(ctx):
        return na("the app sends no writes")
    return ok() if re.search(r"showModal\s*\(|\bconfirm\s*\(", js_text(ctx)) else bad("the app sends writes but has no confirmation dialog")


@check
def uix_version(ctx):
    pg = ctx.page
    return ok() if any(a.get("id") == "version" for _, a, _ in pg.tags) else bad("no element with id=version in index.html")


# ------------------------------- ACC ---------------------------------------
@check
def acc_zoom(ctx):
    v = (ctx.page.meta("viewport") or "").lower().replace(" ", "")
    hits = [k for k in ("user-scalable=no", "user-scalable=0", "maximum-scale", "minimum-scale") if k in v]
    return bad("viewport contains " + ", ".join(hits)) if hits else ok()


@check
def acc_basics(ctx):
    pg, problems = ctx.page, []
    if not pg.present:
        return bad("public/index.html is missing")
    if not (pg.lang or "").strip():
        problems.append("no html lang")
    if not pg.title.strip():
        problems.append("empty title")
    h1 = len([1 for t, _, _ in pg.tags if t == "h1"])
    if h1 != 1:
        problems.append("%d h1 elements (want 1)" % h1)
    if not any(t == "main" or a.get("role") == "main" for t, a, _ in pg.tags):
        problems.append("no main landmark")
    return bad("; ".join(problems)) if problems else ok()


@check
def acc_names(ctx):
    pg, problems = ctx.page, []
    if not pg.present:
        return bad("public/index.html is missing")
    for n in pg.interactive:
        a = n["attrs"]
        if n["tag"] == "a" and "href" not in a:
            continue
        if not ((n["text"] or "").strip() or a.get("aria-label", "").strip() or a.get("aria-labelledby", "").strip()):
            problems.append("%s at line %d has no accessible name" % (n["tag"], n["line"]))
    for c in pg.controls:
        a = c["attrs"]
        if c["tag"] == "input" and a.get("type", "text").lower() in ("hidden", "submit", "button", "reset", "image"):
            continue
        if not (a.get("aria-label") or a.get("aria-labelledby") or c["in_label"] or a.get("id") in pg.labels_for):
            problems.append("%s at line %d has no label" % (c["tag"], c["line"]))
    for tag, a, line in pg.tags:
        if tag == "img" and "alt" not in a:
            problems.append("img at line %d has no alt" % line)
    return bad("; ".join(problems[:6])) if problems else ok()


@check
def acc_focus(ctx):
    css = css_text(ctx)
    if not re.search(r":focus-visible[^{]*\{[^}]*outline", css):
        return bad("no :focus-visible rule with an outline")
    return ok()


@check
def acc_scroll_padding(ctx):
    return ok() if re.search(r"scroll-(padding|margin)", css_text(ctx)) else bad("no scroll-padding or scroll-margin")


@check
def acc_live(ctx):
    pg, problems, found = ctx.page, [], 0
    for tag, a, line in pg.tags:
        if line in pg.in_noscript:
            continue
        if re.search(r"banner|toast|alert|snackbar|notice|offline|fatal", (a.get("id", "") + " " + a.get("class", "")).lower()):
            found += 1
            if a.get("role") not in ("status", "alert", "log") and "aria-live" not in a:
                problems.append("%s at line %d is not a live region" % (a.get("id") or a.get("class"), line))
    if not found:
        return na("no banner or toast elements")
    return bad("; ".join(problems)) if problems else ok()


@check
def acc_motion(ctx):
    css = css_text(ctx)
    if not re.search(r"\banimation(-name)?\s*:|\btransition\s*:|@keyframes", css):
        return na("the CSS animates nothing")
    return ok() if "prefers-reduced-motion" in css else bad("the CSS animates but has no prefers-reduced-motion rule")


@check
def acc_scheme(ctx):
    css, problems = css_text(ctx), []
    if not ctx.page.meta("color-scheme"):
        problems.append("no color-scheme meta")
    if not re.search(r"color-scheme\s*:", css):
        problems.append("no color-scheme in the CSS")
    if re.search(r"prefers-color-scheme[^{]*\{\s*\}", css):
        problems.append("an empty prefers-color-scheme block")
    return bad("; ".join(problems)) if problems else ok()


@check
def acc_nav_state(ctx):
    pg = ctx.page
    navs = [a for t, a, _ in pg.tags if t == "nav"]
    if not navs:
        return na("no nav landmark")
    problems = []
    if not all(a.get("aria-label") or a.get("aria-labelledby") for a in navs):
        problems.append("a nav has no aria-label")
    if not re.search(r"aria-(current|selected|pressed)", js_text(ctx) + " " + " ".join(k for _, a, _ in pg.tags for k in a)):
        problems.append("nothing exposes the active item with aria-current, aria-selected or aria-pressed")
    return bad("; ".join(problems)) if problems else ok()


@check
def acc_contrast(ctx):
    rules = css_rules(ctx)
    vars_ = css_vars(rules)
    bad_pairs, checked = [], 0
    for sels, d in rules:
        fg = css_color(d.get("color"), vars_) if "color" in d else None
        bgv = d.get("background-color") or d.get("background")
        bg = None
        if bgv and "gradient" not in bgv and "url(" not in bgv:
            m = re.search(r"var\([^)]*\)|#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)", bgv)
            bg = css_color(m.group(0), vars_) if m else css_color(bgv, vars_)
        if fg and bg:
            checked += 1
            r = contrast(fg, bg)
            if r < 4.5:
                bad_pairs.append("%s %.1f:1" % (", ".join(sels)[:30], r))
    if not checked:
        return na("no rule declares both a text colour and a background")
    return bad("below 4.5:1: " + "; ".join(bad_pairs)) if bad_pairs else ok()


@check
def acc_relative(ctx):
    css = css_text(ctx)
    css = re.sub(r"(max|min|clamp)\([^;{}]*\)", "", css)
    sizes = re.findall(r"font-size\s*:\s*([^;}]+)", css)
    if not sizes:
        return na("no font-size declarations")
    rel = len([s for s in sizes if re.search(r"rem|em|%", s)])
    return ok() if rel * 10 >= len(sizes) * 7 else bad("only %d of %d font sizes are relative (rem, em or %%)" % (rel, len(sizes)))


# ------------------------------- PER ---------------------------------------
@check
def per_budget(ctx):
    files = ctx.by_ext(".html", ".css", ".js", ".mjs")
    total = sum(os.path.getsize(ctx.p(f)) for f in files)
    js = sum(os.path.getsize(ctx.p(f)) for f in ctx.by_ext(".js", ".mjs"))
    problems = []
    if total > 170 * 1024:
        problems.append("HTML, CSS and JS total %d KB (budget 170)" % (total // 1024))
    if js > 100 * 1024:
        problems.append("JavaScript totals %d KB (budget 100)" % (js // 1024))
    urls = shell_urls(ctx)
    if urls and len(urls) > 12:
        problems.append("%d precached files (budget 12)" % len(urls))
    return bad("; ".join(problems)) if problems else ok()


@check
def per_script_loading(ctx):
    problems = []
    for s in ctx.page.scripts:
        a = s["attrs"]
        if "src" in a and s["in_head"] and not ("defer" in a or "async" in a or a.get("type") == "module"):
            problems.append("script %s in head blocks rendering (add defer)" % a.get("src"))
    return bad("; ".join(problems)) if problems else ok()


@check
def per_assets(ctx):
    css, problems = css_text(ctx), []
    for block in re.findall(r"@font-face\s*\{([^}]*)\}", css):
        if re.search(r"https?://", block):
            problems.append("@font-face loads a font from another origin")
        if "font-display" not in block:
            problems.append("@font-face has no font-display")
    for tag, a, line in ctx.page.tags:
        if tag == "img" and not ("width" in a and "height" in a):
            problems.append("img at line %d has no width and height" % line)
    return bad("; ".join(problems)) if problems else ok()


# ------------------------------- DOC ---------------------------------------
QUIRKS = re.compile(r"env\(\s*safe-area|overscroll-behavior|touch-action|user-select|text-size-adjust|"
                    r"tap-highlight-color|overflow-scrolling|touch-callout")


@check
def doc_why(ctx):
    missing = []
    for rel in ctx.by_ext(".css"):
        raw = ctx.text(rel) or ""
        ends = [raw.count("\n", 0, m.end()) for m in re.finditer(r"/\*.*?\*/", raw, flags=re.S) if "WHY" in m.group(0)]
        stripped = re.sub(r"/\*.*?\*/", keep_lines, raw, flags=re.S).split("\n")
        for i, line in enumerate(stripped):
            if QUIRKS.search(line) and not any(e <= i and i - e <= 4 for e in ends):
                missing.append("%s:%d" % (rel, i + 1))
    return bad("no WHY comment above " + ", ".join(missing[:6])) if missing else ok()


@check
def doc_agents(ctx):
    t = ctx.text("AGENTS.md")
    if t is None:
        return bad("no AGENTS.md")
    return ok() if "nixweb check" in t else bad("AGENTS.md does not mention nixweb check")


@check
def doc_claim(ctx):
    t = ctx.text("CONFORMANCE.md")
    if t is None:
        return bad("no CONFORMANCE.md")
    miss = [k for k in ("Standard", "Level", "Date", "Tester") if md_field(t, k) is None]
    return bad("CONFORMANCE.md has no value for: " + ", ".join(miss)) if miss else ok()


@check
def doc_device_record(ctx):
    t = ctx.text("device-test.md")
    if t is None:
        return bad("no device-test.md")
    miss = [k for k in ("Device", "iOS", "Date", "Tester") if md_field(t, k) is None]
    if md_field(t, "iOS") and not re.match(r"^\d+(\.\d+)*", md_field(t, "iOS")):
        miss.append("iOS (a version number)")
    if md_field(t, "Date") and not re.match(r"^\d{4}-\d{2}-\d{2}", md_field(t, "Date")):
        miss.append("Date (YYYY-MM-DD)")
    return bad("device-test.md has no usable value for: " + ", ".join(miss)) if miss else ok()


@check
def doc_changelog(ctx):
    for name in ("CHANGELOG.md", "CHANGE.log", "CHANGES.md"):
        t = ctx.text(name)
        if t and len(t.strip()) > 10:
            return ok()
    return bad("no CHANGELOG.md or CHANGE.log with entries")


# ===========================================================================
# Running, reporting, and building the documents from rules.json
# ===========================================================================
def make_result(rule, status, detail):
    return {"id": rule["id"], "level": rule["level"], "keyword": rule["keyword"], "title": rule["title"],
            "method": rule["method"], "status": status, "detail": detail, "why": rule["why"],
            "fix": rule.get("fix", ""), "test": rule["test"]}


def run_checks(app, spec, level, only, no_live, target, edge_url):
    rules = active(spec, level)
    if only:
        wanted = set(x.strip() for x in only.split(","))
        rules = [r for r in rules if r["id"] in wanted]
    ctx = Ctx(app)
    ctx.no_live = no_live
    live = None
    needs = any(r.get("check") and (r["method"] == "runtime" or r.get("live")) for r in rules)
    if no_live:
        ctx.live_error = "live checks were switched off with --no-live"
    elif needs:
        live = Live(app, target)
        err = live.start()
        if err:
            ctx.live_error, live = err, None
        else:
            ctx.live = live
    if edge_url:
        edge = Live(app, edge_url)
        edge.start()
        ctx.edge = edge
    results = []
    try:
        for r in rules:
            if not r.get("check"):
                results.append(make_result(r, MANUAL, ""))
                continue
            try:
                status, detail = CHECKS[r["check"]](ctx)
            except Skip as e:
                status, detail = SKIPPED, str(e)
            except Exception as e:  # a crashing check is a failure of the checker, said loudly
                status, detail = FAIL, "the checker crashed: %r" % (e,)
            if status == FAIL and r["keyword"] != "MUST":
                status = WARN
            results.append(make_result(r, status, detail))
    finally:
        if live:
            live.stop()
    return results


def tally(results, level):
    t = dict((s, 0) for s in (PASS, FAIL, WARN, SKIPPED, NA, MANUAL))
    for r in results:
        if r["level"] == level:
            t[r["status"]] += 1
    t["total"] = sum(t.values())
    return t


def print_report(args, spec, app, results):
    print(paint(BD, "nixweb check") + "  %s   %s %s   target Level %d (%s)" % (
        os.path.basename(app.rstrip("/")), spec["standard"], spec["edition"], args.level,
        spec["levels"][str(args.level)]["name"]))
    print()
    for lv in range(1, args.level + 1):
        rows = [r for r in results if r["level"] == lv]
        t = tally(results, lv)
        print(paint(BD, "Level %d  %s" % (lv, spec["levels"][str(lv)]["name"])) +
              paint(DIM, "   %d rules: %d pass, %d fail, %d warn, %d not verified, %d not applicable, %d need a person" % (
                  t["total"], t[PASS], t[FAIL], t[WARN], t[SKIPPED], t[NA], t[MANUAL])))
        for r in rows:
            show = args.verbose or r["status"] in (FAIL, WARN, SKIPPED) or (args.manual and r["status"] == MANUAL)
            if not show:
                continue
            sym, col = MARK[r["status"]]
            print("  %s %s %-6s %s" % (paint(col, sym), r["id"], r["keyword"], r["title"]))
            if r["detail"] and r["status"] in (FAIL, WARN, SKIPPED, NA):
                print(paint(DIM, "      " + r["detail"]))
            if r["status"] in (FAIL, WARN):
                print(paint(DIM, "      why: " + r["why"]))
                if r["fix"]:
                    print(paint(DIM, "      fix: " + r["fix"]))
            if r["status"] == MANUAL:
                print(paint(DIM, "      test: " + r["test"]))
        print()


def verdict(args, results):
    fails = [r for r in results if r["status"] == FAIL]
    warns = [r for r in results if r["status"] == WARN]
    skips = [r for r in results if r["status"] == SKIPPED]
    manual = [r for r in results if r["status"] == MANUAL]
    code = 1 if fails or (args.strict and (warns or skips)) else 0
    if fails:
        line = paint(RD, "NOT CONFORMANT to Level %d: %d automated rule(s) failed." % (args.level, len(fails)))
    else:
        line = paint(GR, "No automated failures for Level %d." % args.level)
        if skips:
            line += paint(AM, " %d rule(s) could not be verified." % len(skips))
        if warns:
            line += paint(AM, " %d recommendation(s) not met." % len(warns))
    extra = ""
    if manual:
        extra = ("  %d rule(s) need a person with a phone: see standard/CHECKLIST.md, or run again with --manual. "
                 "An automated pass is not a conformance claim." % len(manual))
    return code, line + extra


def cmd_list(spec, level):
    for r in active(spec, level):
        print("%s  L%d  %-6s %-8s %-6s %s" % (r["id"], r["level"], r["keyword"], r["method"],
                                               "auto" if r.get("check") else "manual", r["title"]))


def counts(spec):
    rules = active(spec, 3)
    per = {1: 0, 2: 0, 3: 0}
    for r in rules:
        per[r["level"]] += 1
    return rules, per, sum(1 for r in rules if r.get("check"))


def render_rule(r):
    how = r["method"] + (", automated" if r.get("check") else ", manual")
    out = ["#### %s: %s" % (r["id"], r["title"]), "", "`Level %d` `%s` `%s`" % (r["level"], r["keyword"], how), "",
           r["statement"], "", "**Why.** " + r["why"], "", "**Test.** " + r["test"]]
    if r.get("fix"):
        out += ["", "**Fix.** " + r["fix"]]
    if r.get("refs"):
        out += ["", "**Sources.** " + ", ".join(r["refs"])]
    return "\n".join(out) + "\n"


def build_documents(spec):
    rules, per, auto = counts(spec)
    cum = (per[1], per[1] + per[2], per[1] + per[2] + per[3])
    subs = {"{{TITLE}}": spec["title"], "{{EDITION}}": spec["edition"], "{{DATE}}": spec["date"],
            "{{TOTAL}}": str(len(rules)), "{{AUTO}}": str(auto), "{{MANUAL}}": str(len(rules) - auto),
            "{{L1}}": str(per[1]), "{{L2}}": str(per[2]), "{{L3}}": str(per[3]),
            "{{C1}}": str(cum[0]), "{{C2}}": str(cum[1]), "{{C3}}": str(cum[2]),
            "{{PRINCIPLES}}": "\n".join("%d. %s" % (i + 1, p) for i, p in enumerate(spec["principles"])),
            "{{LEVELS}}": "\n".join("- **Level %s, %s.** %s" % (k, v["name"], v["blurb"]) for k, v in sorted(spec["levels"].items()))}
    order = list(spec["categories"])

    def read(name):
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            text = f.read()
        for k, v in subs.items():
            text = text.replace(k, v)
        return text

    idx = ["| ID | Level | Keyword | Test | Rule |", "|---|---|---|---|---|"]
    body = []
    for cat in order:
        rs = sorted([r for r in rules if r["id"].split("-")[1] == cat], key=lambda r: r["id"])
        if not rs:
            continue
        body.append("### %s (%s)\n" % (spec["categories"][cat], cat))
        for r in rs:
            idx.append("| %s | %d | %s | %s | %s |" % (r["id"], r["level"], r["keyword"], "auto" if r.get("check") else "manual", r["title"]))
            body.append(render_rule(r))
    standard = "\n".join([read("preamble.md").rstrip(), "", "## Rule index", ""] + idx +
                         ["", "## The rules", ""] + body + ["", read("appendix.md").rstrip(), ""])

    chk = ["# %s %s conformance checklist" % (spec["standard"], spec["edition"]), "",
           "App: ____________   Level claimed: ___   Date: ________   Tester: ____________   Device and iOS: ____________", "",
           "Run `nixweb check APP --level N` first. It ticks the automated rules for you. The boxes below are for you to tick:",
           "automated rules once the command passes them, manual rules once you have done them on a phone.", ""]
    for lv in (1, 2, 3):
        chk += ["## Level %d: %s" % (lv, spec["levels"][str(lv)]["name"]), ""]
        for cat in order:
            rs = sorted([r for r in rules if r["level"] == lv and r["id"].split("-")[1] == cat], key=lambda r: r["id"])
            if not rs:
                continue
            chk.append("### %s" % spec["categories"][cat])
            for r in rs:
                chk.append("- [ ] **%s** %s (%s) %s" % (r["id"], r["keyword"], "automated" if r.get("check") else "manual", r["title"]))
                if not r.get("check"):
                    chk.append("  - %s" % r["test"])
            chk.append("")
    return standard, "\n".join(chk) + "\n"


def cmd_standard(spec):
    standard, checklist = build_documents(spec)
    with open(os.path.join(REPO, "STANDARD.md"), "w", encoding="utf-8") as f:
        f.write(standard)
    with open(os.path.join(HERE, "CHECKLIST.md"), "w", encoding="utf-8") as f:
        f.write(checklist)
    if chr(0x2014) in standard or chr(0x2014) in checklist:
        sys.stderr.write("the generated documents contain an em-dash; fix the source text\n")
        return 1
    print("wrote %s and %s" % (os.path.join(REPO, "STANDARD.md"), os.path.join(HERE, "CHECKLIST.md")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nixweb check", description="Check an app against the NixWeb Standard.")
    ap.add_argument("app", nargs="?", help="the app folder (the one that holds public/ and server.py)")
    ap.add_argument("--level", type=int, choices=(1, 2, 3), default=2, help="highest level to check (default 2)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--url", help="the tailnet URL, to check the HTTPS edge (NW-NET-007)")
    ap.add_argument("--target", help="run the runtime checks against an already-running server instead of starting server.py")
    ap.add_argument("--no-live", action="store_true", help="skip every rule that needs a running server")
    ap.add_argument("--only", help="comma-separated rule IDs")
    ap.add_argument("--strict", action="store_true", help="warnings and unverified rules also fail the run")
    ap.add_argument("--manual", action="store_true", help="also print the rules that need a person")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every rule, not just the ones that need attention")
    ap.add_argument("--list", action="store_true", help="list the rules and exit")
    ap.add_argument("--standard", action="store_true", help="rebuild STANDARD.md and standard/CHECKLIST.md")
    args = ap.parse_args(argv)
    spec = load_spec()
    if args.list:
        cmd_list(spec, args.level if "--level" in (argv or sys.argv) else 3)
        return 0
    if args.standard:
        return cmd_standard(spec)
    if not args.app or not os.path.isdir(args.app):
        ap.error("give the app folder, for example: nixweb check ~/Projects/mytool")
    app = os.path.abspath(args.app)
    results = run_checks(app, spec, args.level, args.only, args.no_live, args.target, args.url)
    code, line = verdict(args, results)
    if args.json:
        print(json.dumps({"standard": spec["standard"], "edition": spec["edition"], "app": app, "level": args.level,
                          "results": results, "exit": code}, indent=1))
        return code
    print_report(args, spec, app, results)
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
