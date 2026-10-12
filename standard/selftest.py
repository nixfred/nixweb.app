#!/usr/bin/env python3
"""Self-test for the NixWeb checker. Python standard library only.

A checker that cannot fail is worse than none. The first `nixweb check` was a grep, and it passed a
template that shipped user-scalable=no. This test makes the checker prove itself:

  1. The pristine template passes every automated rule, except the three that need evidence a
     template cannot have (a conformance claim, a device record, a change log) and the two that
     need a host unit or a tailnet.
  2. For every automated rule, a copy of the template is broken in the one way that rule exists
     to catch, and the rule must say so.

    python3 standard/selftest.py [--only NW-XXX-000]

Every automated rule must have a mutation below or an entry in EXCLUDED with a reason, so a rule
cannot be added without a test that it can fail.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TEMPLATE = os.path.join(REPO, "template")
CHECK = os.path.join(HERE, "check.py")


def make_png(w, h, rgb=(11, 16, 24), alpha=False):
    px = bytes(rgb) + (b"\xff" if alpha else b"")
    raw = b"".join(b"\x00" + px * w for _ in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6 if alpha else 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def R(path, old, new):
    def op(d):
        p = os.path.join(d, path)
        s = open(p, encoding="utf-8").read()
        if old not in s:
            raise SystemExit("selftest is out of date: %r not found in %s" % (old[:60], path))
        open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
    return op


def Rx(path, pattern, repl, flags=0):
    def op(d):
        p = os.path.join(d, path)
        s = open(p, encoding="utf-8").read()
        new, n = re.subn(pattern, repl, s, count=1, flags=flags)
        if not n:
            raise SystemExit("selftest is out of date: /%s/ not found in %s" % (pattern[:60], path))
        open(p, "w", encoding="utf-8").write(new)
    return op


def A(path, text):
    def op(d):
        with open(os.path.join(d, path), "a", encoding="utf-8") as f:
            f.write(text)
    return op


def W(path, data):
    def op(d):
        p = os.path.join(d, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    return op


def X(path):
    def op(d):
        os.remove(os.path.join(d, path))
    return op


# Relaxing the server so it serves anything under the app, including dotfiles and .py files.
OPEN_SERVER = [
    Rx("server.py", r'if any\(p\.startswith\("\."\) for p in parts\):[^\n]*\n\s+return None', "pass"),
    R("server.py", "if ext not in TYPES or not os.path.isfile(full):", "if not os.path.isfile(full):"),
    R("server.py", 'self.send_header("Content-Type", TYPES[ext] + ("; charset=utf-8" if textual else ""))',
      'self.send_header("Content-Type", TYPES.get(ext, "text/plain"))'),
]
WRITES = [A("public/app.js", "\nnwFetch('/api/x', { method: 'POST' });\n")]
MANY_PX = "\n" + "".join(".a%d{font-size:%dpx}" % (i, 10 + i) for i in range(30)) + "\n"
GOOD_CLAIM = "# Claim\nStandard: NixWeb 1.0\nLevel: 2\nDate: 2026-10-11\nTester: Fred\n"
GOOD_DEVICE = "# Device test\nDevice: iPhone 16\niOS: 26.0\nDate: 2026-10-11\nTester: Fred\n"

# rule id -> (what we break, operations, expected status or None for the rule's own failure status)
M = {
 "NW-ARC-001": ("a package.json that lists dependencies", [W("package.json", '{"dependencies":{"left-pad":"1.0.0"}}')]),
 "NW-ARC-002": ("public/index.html is missing", [X("public/index.html")]),
 "NW-ARC-003": ("vendored code with no VENDOR.md", [W("public/vendor/lib.js", "var x = 1;\n")]),
 "NW-NET-001": ("the default bind becomes 0.0.0.0", [R("server.py", 'ap.add_argument("--bind", default="127.0.0.1")', 'ap.add_argument("--bind", default="0.0.0.0")')]),
 "NW-NET-002": ("the server really listens on 0.0.0.0", [
     R("server.py", 'ap.add_argument("--bind", default="127.0.0.1")', 'ap.add_argument("--bind", default="0.0.0.0")'),
     R("server.py", 'if a.bind not in LOOPBACK and os.environ.get("NIXWEB_ALLOW_PUBLIC_BIND") != "1":', "if False:")]),
 "NW-NET-003": ("a deploy script that runs tailscale funnel", [W("deploy.sh", "tailscale funnel 8731\n")]),
 "NW-SRV-001": ("the server serves a .env file", OPEN_SERVER + [W("public/.env", "SECRET=1\n")]),
 "NW-SRV-002": ("/ping is gone", [R("server.py", 'if path == "/ping":', 'if path == "/pingx":')]),
 "NW-SRV-003": ("traversal is allowed", OPEN_SERVER + [
     Rx("server.py", r"if full != root and not full\.startswith\(root \+ os\.sep\):\s*\n\s*return None", "pass")]),
 "NW-SRV-004": ("the manifest is sent as application/json", [R("server.py", '".webmanifest": "application/manifest+json"', '".webmanifest": "application/json"')]),
 "NW-SRV-005": ("the server publishes the whole app folder", [R("server.py", "public = os.path.realpath(a.public)", "public = os.path.realpath(HERE)")]),
 "NW-SRV-006": ("shell files get max-age=3600", [R("server.py", 'if HASHED.search(full) else "no-cache"', 'if HASHED.search(full) else "public, max-age=3600"')]),
 "NW-SRV-007": ("the Server header names Python", [R("server.py", 'return "nixweb"', 'return "SimpleHTTP/0.6 Python/3.14"')]),
 "NW-SRV-008": ("gzip is switched off", [Rx("server.py", r"gz = textual and size > 512[^\n]*", "gz = False")]),
 "NW-SRV-009": ("Range is ignored", [R("server.py", 'if rng and rng.lower().startswith("bytes="):', "if False:")]),
 "NW-SRV-010": ("SIGTERM is not handled", [R("server.py", "signal.signal(signal.SIGTERM, stop)", "pass")]),
 "NW-SRV-011": ("the body cap is removed", [R("server.py", "if n > MAX_BODY:", "if False:")]),
 "NW-SEC-001": ("the CSP allows anything", [R("server.py", "default-src 'self'; script-src 'self';", "default-src *; script-src 'self' 'unsafe-inline';")]),
 "NW-SEC-002": ("nosniff is no longer sent", [Rx("server.py", r'\("X-Content-Type-Options", "nosniff"\),', "")]),
 "NW-SEC-003": ("every Host is accepted", [R("server.py", "return bool(h) and self.server.hosts.allows(h)", "return True")]),
 "NW-SEC-004": ("cross-site writes are accepted", [R("server.py", "if not self.same_origin():", "if False:")]),
 "NW-SEC-005": ("OPTIONS is answered with 204", [R("server.py", 'self.send_response(405)\n        self.send_header("Allow", "GET, HEAD")', 'self.send_response(204)\n        self.send_header("Allow", "GET, HEAD")')]),
 "NW-SEC-006": ("a Google Fonts stylesheet", [R("public/index.html", '<link rel="stylesheet" href="app.css">', '<link rel="stylesheet" href="app.css">\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">')]),
 "NW-SEC-007": ("document.body.innerHTML is assigned", [A("public/app.js", "\ndocument.body.innerHTML = 'x';\n")]),
 "NW-SEC-008": ("an inline script", [R("public/index.html", "<noscript>", "<script>var a = 1;</script>\n<noscript>")]),
 "NW-SEC-009": ("an API key in app.js", [A("public/app.js", '\nvar apiKey = "sk-abcdefghijklmnopqrstuvwxyz123456";\n')]),
 "NW-INS-001": ("the manifest link is removed", [Rx("public/index.html", r'<link rel="manifest"[^>]*>\n', "")]),
 "NW-INS-002": ("display is browser", [R("public/manifest.webmanifest", '"display": "standalone"', '"display": "browser"')]),
 "NW-INS-003": ("the manifest id is removed", [R("public/manifest.webmanifest", '"id": "/",\n  ', "")]),
 "NW-INS-004": ("the 512 icon is one flat colour", [W("public/icons/icon-512.png", make_png(512, 512))]),
 "NW-INS-005": ("the apple-touch-icon has an alpha channel", [W("public/icons/icon-180.png", make_png(180, 180, alpha=True))]),
 "NW-INS-006": ("apple-mobile-web-app-capable is removed", [R("public/index.html", '<meta name="apple-mobile-web-app-capable" content="yes">', "")]),
 "NW-INS-007": ("theme-color no longer matches the manifest", [R("public/index.html", '<meta name="theme-color" content="#0b1018">', '<meta name="theme-color" content="#ffffff">')]),
 "NW-INS-008": ("black-translucent with no top-inset fallback", [R("public/index.html", 'name="apple-mobile-web-app-status-bar-style" content="black"', 'name="apple-mobile-web-app-status-bar-style" content="black-translucent"')]),
 "NW-SHL-001": ("viewport-fit=cover is removed", [R("public/index.html", "initial-scale=1, viewport-fit=cover", "initial-scale=1")]),
 "NW-SHL-002": ("the bottom inset is not used", [Rx("public/app.css", r"\s*--bottom:env\(safe-area-inset-bottom, 0px\);", "")]),
 "NW-SHL-003": ("html and body can scroll", [R("public/app.css", "  overflow:hidden;\n  overscroll-behavior:none;", "  overscroll-behavior:none;")]),
 "NW-SHL-004": ("a rule uses 100vh", [A("public/app.css", "\n.x{height:100vh}\n")]),
 "NW-SHL-005": ("inputs render at 14px", [R("public/app.css", "font-size:max(16px,1rem)", "font-size:14px")]),
 "NW-SHL-006": ("touch-action on html", [A("public/app.css", "\nhtml{touch-action:manipulation}\n")]),
 "NW-SHL-007": ("user-select none on body", [A("public/app.css", "\nbody{user-select:none}\n")]),
 "NW-SHL-008": ("text-size-adjust is removed", [R("public/app.css", "-webkit-text-size-adjust:100%;", "")]),
 "NW-SHL-009": ("format-detection is removed", [R("public/index.html", '<meta name="format-detection" content="telephone=no">', "")]),
 "NW-SHL-010": ("an input and no visualViewport", [R("public/index.html", '<main class="scroll" id="main">', '<main class="scroll" id="main"><input id="q" aria-label="q">')]),
 "NW-IOS-001": ("display-mode: fullscreen is not tested", [Rx("public/app.js", r"window\.matchMedia\('\(display-mode: fullscreen\)'\)\.matches \|\|\s*", "")]),
 "NW-IOS-002": ("the user agent is parsed", [A("public/app.js", "\nvar ua = navigator.userAgent;\n")]),
 "NW-IOS-003": ("an unload listener", [A("public/app.js", "\nwindow.addEventListener('unload', function () {});\n")]),
 "NW-IOS-004": ("navigator.vibrate with no test", [A("public/app.js", "\nnavigator.vibrate(10);\n")]),
 "NW-OFF-001": ("sw.js is missing", [X("public/sw.js")]),
 "NW-OFF-002": ("old caches are deleted without a prefix test", [Rx("public/sw.js", r"k\.startsWith\(PREFIX\) && ", "")]),
 "NW-OFF-003": ("a precached file does not exist", [R("public/sw.js", "'icons/icon-512.png']", "'icons/icon-512.png', 'icons/missing.png']")]),
 "NW-OFF-004": ("the same-origin guard is removed", [R("public/sw.js", "if (url.origin !== location.origin) return;   // never cache other hosts", "")]),
 "NW-OFF-005": ("errors are cached", [R("public/sw.js", "if (res.ok && res.type === 'basic' &&", "if (res.type === 'basic' &&")]),
 "NW-OFF-006": ("any failed request gets index.html", [R("public/sw.js", "if (req.mode === 'navigate') {", "if (true) {")]),
 "NW-OFF-007": ("no cache: reload and the server sends max-age", [
     R("public/sw.js", "new Request(u, { cache: 'reload' })", "u"),
     R("server.py", 'if HASHED.search(full) else "no-cache"', 'if HASHED.search(full) else "public, max-age=3600"')]),
 "NW-OFF-008": ("updateViaCache is not none", [R("public/app.js", "{ updateViaCache: 'none' }", "{}")]),
 "NW-OFF-009": ("the worker no longer waits for SKIP_WAITING", [R("public/sw.js", "if (d.type === 'SKIP_WAITING') self.skipWaiting();", "")]),
 "NW-OFF-010": ("the probe may be cached", [R("public/app.js", "{ cache: 'no-store' }", "{ cache: 'default' }")]),
 "NW-OFF-011": ("a fetch with no signal", [A("public/app.js", "\nfetch('x');\n")]),
 "NW-OFF-012": ("the noscript message is removed", [Rx("public/index.html", r"<noscript>.*?</noscript>\n", "", re.S)]),
 "NW-OFF-013": ("private responses are cached", [R("public/sw.js", "/no-store|private/i.test(cc)", "/zzz/i.test(cc)")]),
 "NW-DAT-001": ("writes with no IndexedDB outbox", WRITES),
 "NW-DAT-002": ("writes with no idempotency key", WRITES),
 "NW-DAT-003": ("JSON stored in localStorage outside try", [A("public/app.js", "\nlocalStorage.setItem('k', JSON.stringify({}));\n")]),
 "NW-UIX-001": ("writes with no confirmation", WRITES),
 "NW-UIX-004": ("no version element", [R("public/index.html", '<span id="version">unknown</span>', "unknown")]),
 "NW-ACC-001": ("user-scalable=no", [R("public/index.html", 'viewport-fit=cover">', 'viewport-fit=cover, user-scalable=no">')]),
 "NW-ACC-002": ("html has no lang", [R("public/index.html", '<html lang="en">', "<html>")]),
 "NW-ACC-003": ("a button with no name", [R("public/index.html", '<main class="scroll" id="main">', '<main class="scroll" id="main"><button type="button"></button>')]),
 "NW-ACC-004": ("the focus style is removed", [Rx("public/app.css", r":focus-visible\{[^}]*\}\n", "")]),
 "NW-ACC-005": ("scroll-padding is removed", [R("public/app.css", "scroll-padding-block:1rem;", "")]),
 "NW-ACC-006": ("the offline banner is not a live region", [R("public/index.html", '<div class="banner" id="offline" role="status"></div>', '<div class="banner" id="offline"></div>')]),
 "NW-ACC-007": ("a transition with no reduced-motion rule", [A("public/app.css", "\n.x{transition:opacity .2s}\n")]),
 "NW-ACC-008": ("no color-scheme meta", [R("public/index.html", '<meta name="color-scheme" content="dark">', "")]),
 "NW-ACC-009": ("the nav has no name", [R("public/index.html", '<nav class="tabs" aria-label="Sections">', '<nav class="tabs">')]),
 "NW-ACC-010": ("grey text on near-black", [R("public/app.css", "--txt:#d3dde8;", "--txt:#222222;")]),
 "NW-ACC-013": ("fixed px font sizes", [A("public/app.css", MANY_PX)]),
 "NW-PER-001": ("a 200 KB script", [A("public/app.js", "\n/* " + "x" * 200000 + " */\n")]),
 "NW-PER-002": ("a render-blocking script", [R("public/index.html", '<script src="app.js" defer></script>', '<script src="app.js"></script>')]),
 "NW-PER-003": ("an image with no size", [R("public/index.html", '<main class="scroll" id="main">', '<main class="scroll" id="main"><img src="icons/icon-180.png" alt="x">')]),
 "NW-DOC-001": ("a WHY comment is removed", [R("public/app.css", "/* WHY: iOS flashes a grey box on every tap. Our own :active styles replace it. */", "")]),
 "NW-DOC-002": ("AGENTS.md is missing", [X("AGENTS.md")]),
}
# Evidence rules: the pristine template must fail them, and a filled-in file must pass them.
EVIDENCE = {
 "NW-DOC-003": ("a filled-in claim", [W("CONFORMANCE.md", GOOD_CLAIM)]),
 "NW-DOC-004": ("a filled-in device record", [W("device-test.md", GOOD_DEVICE)]),
 "NW-DOC-005": ("a change log with an entry", [W("CHANGELOG.md", "# Changes\n2026-10-11 first release, version 1\n")]),
}
EXCLUDED = {
 "NW-NET-004": "needs a systemd user unit on the host running the test",
 "NW-NET-007": "needs a live tailnet URL; run it with nixweb check APP --url",
}
EXPECTED_AT_BASELINE = {"NW-DOC-003": "fail", "NW-DOC-004": "fail", "NW-DOC-005": "warn",
                        "NW-NET-004": "skip", "NW-NET-007": "skip"}


def fresh_copy():
    tmp = tempfile.mkdtemp(prefix="nwselftest-")
    dst = os.path.join(tmp, "app")
    shutil.copytree(TEMPLATE, dst, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    return tmp, dst


def run_check(app, rule_id=None, live=True):
    cmd = [sys.executable, CHECK, app, "--level", "3", "--json"]
    if rule_id:
        cmd += ["--only", rule_id]
    if not live:
        cmd += ["--no-live"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(out.stdout)["results"]
    except ValueError:
        raise SystemExit("the checker did not return JSON:\n%s\n%s" % (out.stdout[-400:], out.stderr[-400:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()
    spec = json.load(open(os.path.join(HERE, "rules.json"), encoding="utf-8"))
    rules = dict((r["id"], r) for r in spec["rules"])
    auto = [i for i, r in rules.items() if r.get("check")]
    problems = []
    t0 = time.time()

    missing = [i for i in auto if i not in M and i not in EVIDENCE and i not in EXCLUDED]
    if missing:
        problems.append("automated rules with no mutation: " + ", ".join(missing))
    stale = [i for i in list(M) + list(EVIDENCE) if i not in rules]
    if stale:
        problems.append("mutations for rules that no longer exist: " + ", ".join(stale))

    print("Baseline: the pristine template")
    tmp, app = fresh_copy()
    try:
        base = dict((r["id"], r["status"]) for r in run_check(app))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for i in auto:
        want = EXPECTED_AT_BASELINE.get(i)
        got = base.get(i)
        if want is not None:
            if got != want:
                problems.append("baseline %s: expected %s, got %s" % (i, want, got))
        elif got not in ("pass", "n/a"):
            problems.append("baseline %s: the template itself gets %s" % (i, got))
    print("  %d automated rules, %d pass or n/a on the template" % (len(auto), len([i for i in auto if base.get(i) in ("pass", "n/a")])))

    print("No-live: nothing may be started when --no-live is given")
    tmp, app = fresh_copy()
    try:
        for rid in ("NW-SRV-005", "NW-SRV-010", "NW-NET-002"):
            got = run_check(app, rid, live=False)[0]["status"]
            print("  %s %s -> %s" % ("ok  " if got == "skip" else "FAIL", rid, got))
            if got != "skip":
                problems.append("%s must be skipped under --no-live, got %s" % (rid, got))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("Mutations: break the template once per rule")
    todo = [(i, M[i]) for i in M] + [(i, EVIDENCE[i]) for i in EVIDENCE]
    if args.only:
        todo = [(i, m) for i, m in todo if i == args.only]
    for rid, (what, ops) in todo:
        if rid not in rules:
            continue
        tmp, app = fresh_copy()
        try:
            for op in ops:
                op(app)
            positive = rid in EVIDENCE
            live = rules[rid]["method"] != "static" or bool(rules[rid].get("live"))
            got = run_check(app, rid, live=live)[0]["status"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        want = ("pass",) if positive else (("fail",) if rules[rid]["keyword"] == "MUST" else ("warn", "fail"))
        flag = "ok  " if got in want else "FAIL"
        print("  %s %s  %s -> %s" % (flag, rid, what, got))
        if got not in want:
            problems.append("%s: %s should give %s, got %s" % (rid, what, "/".join(want), got))
    for rid, why in sorted(EXCLUDED.items()):
        print("  --   %s  not mutation-tested: %s" % (rid, why))

    print()
    if problems:
        print("SELFTEST FAILED (%d problem(s), %.0f s):" % (len(problems), time.time() - t0))
        for p in problems:
            print("  - " + p)
        return 1
    print("selftest passed in %.0f s: %d automated rules, %d broken on purpose and caught, %d need a host or a tailnet." % (
        time.time() - t0, len(auto), len(M) + len(EVIDENCE), len(EXCLUDED)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
