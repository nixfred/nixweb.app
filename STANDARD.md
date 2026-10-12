# The NixWeb Standard for Home-Screen Web Apps

**Edition 1.0.0, 2026-10-11.** 105 rules in three levels. 87 are checked by a program and 18 need a person holding a phone.

## 1. What this is

This standard describes a phone app that is a plain web app: HTML, CSS and one JavaScript file, served by a small local server, put on a private network by `tailscale serve`, and added to the Home Screen of an iPhone. Android comes second. There is no Xcode, no App Store, no review and no build step.

It says what a correct one looks like, why each rule exists, and how to check it. Every rule has a stable ID, a requirement word, a reason and a test. A program, `nixweb check`, runs the tests a program can run, and a checklist covers the rest.

It exists because the failures are quiet. A page without `viewport-fit` looks right in a simulator and clips on the phone. A service worker that fails to install says nothing. A server that lists its own folder hands `.git` to everyone on the tailnet and nothing looks wrong. People copying an app do not see these, so the standard and the checker see them for them.

## 2. Who it is for

Anyone building this kind of app, including an AI coding agent working from a prompt. An agent should read `AGENTS.md` in the template, run `nixweb check`, and treat a failing MUST as a bug.

It is not a standard for public websites, for apps with accounts, or for apps that need the App Store. The no-login design is a decision about a private network (NW-NET-001 to NW-NET-003), and it stops being right the moment an app is published to the internet.

## 3. Conformance

- **Level 1, Installable.** It installs, it is not dangerous on the tailnet, and nothing basic is broken. Almost every rule is checked by the checker in seconds.
- **Level 2, Dependable.** It keeps working when things go wrong: host asleep, network gone, update mid-session, hostile page in the browser. Needs a running server and a few device checks.
- **Level 3, Exemplary.** It is proven. A person has run it on a real phone with assistive technology, the numbers are recorded, and a claim is published.

Levels are cumulative. Level 1 has 34 rules, Level 2 has 94 and Level 3 has 105.

An app conforms to Level N when every rule up to Level N is met, where:

- a **MUST** rule that fails is a failure;
- a **SHOULD** rule that is not met needs a written reason in `CONFORMANCE.md`;
- a **MAY** rule never affects conformance;
- a rule that does not apply (the app sends no writes, so the write rules do not apply) is recorded as not applicable, with the reason.

A claim names the edition and the level: "NixWeb 1.0, Level 2". A claim is self-attested unless a third party signs it. An automated pass is not a claim. `nixweb check` proves the rules a program can prove, and the rest need a person with a phone.

## 4. Requirement words

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY in this document are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174) when, and only when, they appear in all capitals.

## 5. Principles

The rules hang from nine principles.

1. It is a web page, not a store app. Nobody reviews it, so you own its correctness.
2. Loopback plus HTTPS. The app speaks plain HTTP to 127.0.0.1 and tailscale serve supplies HTTPS and the network boundary.
3. No build step. HTML, CSS and one JavaScript file that a client can read in an afternoon.
4. The page never scrolls; lists do.
5. Reads are free, writes confirm.
6. Fail honestly. Offline, unreachable and broken each say what is true.
7. The tailnet is the lock, not the only lock. There is no login, but the browser on the phone is still a way in.
8. Verify what you generate. A check that cannot fail is not a check.
9. Explain every quirk. A rule that exists for an iOS bug carries a WHY comment.

## 6. Reading a rule

Every rule has:

- **An ID**, like NW-SRV-005. IDs are permanent. They are never reused, renumbered or reordered, and they carry no level, because a rule can change level between editions. Cite a rule as `NixWeb 1.0 NW-SRV-005`.
- **A level and a keyword**, the keyword in capitals.
- **A test method.** A static rule reads the files, a runtime rule starts the app's own server and probes it, a device rule needs a phone, and a process rule needs a person's judgement.
- **A statement**, one testable sentence.
- **Why**, with the fact behind it and where it came from. Where a claim could not be confirmed from a primary source, the rule says so.
- **Test**, the exact way to check it.

## 7. Editions

The standard is versioned like software. A PATCH edition fixes wording and tests. A MINOR edition adds rules that cannot make a conforming app fail, and marks rules deprecated. A MAJOR edition may add new MUSTs, move a rule between levels or remove a rule. Each edition is tagged in git and never changed afterwards. `standard/rules.json` is the source: this document, the checklist and the checker are all built from it.

## Rule index

| ID | Level | Keyword | Test | Rule |
|---|---|---|---|---|
| NW-ARC-001 | 1 | MUST | auto | No build step, no framework, no package manager |
| NW-ARC-002 | 1 | MUST | auto | One public folder, one server file beside it |
| NW-ARC-003 | 2 | MUST | auto | Vendored third-party code is recorded |
| NW-NET-001 | 1 | MUST | auto | The server binds loopback by default and refuses anything else |
| NW-NET-002 | 1 | MUST | auto | The listening socket is loopback only |
| NW-NET-003 | 1 | MUST | auto | Nothing in the app starts tailscale funnel |
| NW-NET-004 | 2 | SHOULD | auto | The service comes back after a reboot |
| NW-NET-005 | 2 | SHOULD | manual | Host and port are final before anyone installs; machine names carry nothing sensitive |
| NW-NET-006 | 3 | SHOULD | manual | A grant narrows who can reach the app when the tailnet is shared |
| NW-NET-007 | 3 | SHOULD | auto | The tailnet HTTPS edge delivers what loopback does |
| NW-SRV-001 | 1 | MUST | auto | Dotfiles, server source, repository and environment paths return 404 |
| NW-SRV-002 | 1 | MUST | auto | /ping answers fast, is never cached, and answers HEAD |
| NW-SRV-003 | 1 | MUST | auto | Path traversal fails, including encoded forms |
| NW-SRV-004 | 1 | MUST | auto | Correct MIME types |
| NW-SRV-005 | 1 | MUST | auto | The server publishes public/ and nothing else, and never lists a directory |
| NW-SRV-006 | 2 | MUST | auto | Files without a content hash always revalidate |
| NW-SRV-007 | 2 | MUST | auto | Errors and headers leak nothing |
| NW-SRV-008 | 2 | SHOULD | auto | Conditional requests and compression |
| NW-SRV-009 | 2 | SHOULD | auto | Byte ranges |
| NW-SRV-010 | 2 | SHOULD | auto | Clean exit on SIGTERM |
| NW-SRV-011 | 2 | MUST | auto | Request size and time are bounded |
| NW-SEC-001 | 2 | MUST | auto | A strict Content-Security-Policy is sent as a header |
| NW-SEC-002 | 2 | MUST | auto | Companion security headers on every response |
| NW-SEC-003 | 2 | MUST | auto | Host header allowlist, against DNS rebinding |
| NW-SEC-004 | 2 | MUST | auto | State-changing requests refuse cross-site origins |
| NW-SEC-005 | 2 | MUST | auto | No CORS |
| NW-SEC-006 | 1 | MUST | auto | No third-party origins, no trackers |
| NW-SEC-007 | 1 | MUST | auto | No code-injection sinks |
| NW-SEC-008 | 2 | MUST | auto | No inline script, handlers or styles |
| NW-SEC-009 | 1 | MUST | auto | No secrets in served files |
| NW-INS-001 | 1 | MUST | auto | A valid manifest is linked |
| NW-INS-002 | 1 | MUST | auto | Required manifest members |
| NW-INS-003 | 1 | MUST | auto | A stable id, and a start_url inside scope |
| NW-INS-004 | 1 | MUST | auto | Complete, real, non-blank icons |
| NW-INS-005 | 1 | MUST | auto | apple-touch-icon is declared, 180x180 and opaque |
| NW-INS-006 | 1 | MUST | auto | The Apple and Chromium app meta tags |
| NW-INS-007 | 1 | MUST | auto | Theme and background colours agree, and the first frame is not white |
| NW-INS-008 | 2 | SHOULD | auto | The status bar style is a deliberate choice |
| NW-SHL-001 | 1 | MUST | auto | The viewport meta |
| NW-SHL-002 | 1 | MUST | auto | Safe-area insets are added to real padding, on all four sides |
| NW-SHL-003 | 1 | MUST | auto | The page never scrolls; lists scroll in their own box |
| NW-SHL-004 | 1 | MUST | auto | The shell is sized with 100% or dvh, never 100vh |
| NW-SHL-005 | 1 | MUST | auto | Form controls render at 16px or larger |
| NW-SHL-006 | 1 | MUST | auto | touch-action: manipulation on controls, never on html or body |
| NW-SHL-007 | 2 | SHOULD | auto | Chrome is unselectable, content is selectable |
| NW-SHL-008 | 2 | SHOULD | auto | Text size is locked against landscape inflation and the system font is used |
| NW-SHL-009 | 2 | SHOULD | auto | Phone-number auto-linking is switched off |
| NW-SHL-010 | 2 | SHOULD | auto | Text-entry screens follow the visual viewport |
| NW-IOS-001 | 1 | MUST | auto | Install state is detected three ways |
| NW-IOS-002 | 2 | MUST | auto | No user-agent sniffing for the OS version |
| NW-IOS-003 | 2 | MUST | auto | Lifecycle events, not unload |
| NW-IOS-004 | 2 | MUST | auto | Platform APIs are feature-detected and degrade |
| NW-OFF-001 | 1 | MUST | auto | A service worker handles install, activate and fetch |
| NW-OFF-002 | 1 | MUST | auto | Versioned caches; old ones deleted by prefix |
| NW-OFF-003 | 1 | MUST | auto | Every precached URL exists |
| NW-OFF-004 | 2 | MUST | auto | Only same-origin GET is cached, and /ping never |
| NW-OFF-005 | 2 | MUST | auto | Only good responses are cached |
| NW-OFF-006 | 2 | MUST | auto | The shell is the fallback for navigations only |
| NW-OFF-007 | 2 | MUST | auto | Precaching reads past the HTTP cache |
| NW-OFF-008 | 2 | MUST | auto | Registration sets updateViaCache to none |
| NW-OFF-009 | 2 | SHOULD | auto | Updates are user-gated |
| NW-OFF-010 | 2 | MUST | auto | Reachability is probed, not guessed |
| NW-OFF-011 | 2 | MUST | auto | Every fetch has a timeout |
| NW-OFF-012 | 2 | MUST | auto | Errors paint a screen, never a blank page |
| NW-OFF-013 | 2 | SHOULD | auto | Runtime caching of API data is bounded and private-aware |
| NW-DAT-001 | 2 | MUST | auto | Offline writes queue in IndexedDB and replay from the open page |
| NW-DAT-002 | 2 | MUST | auto | Every replayable write carries an idempotency key |
| NW-DAT-003 | 2 | SHOULD | auto | Storage use is guarded and small |
| NW-DAT-004 | 2 | MUST | manual | Device storage is rebuildable; first-run state never depends on Safari |
| NW-DAT-005 | 3 | SHOULD | manual | A conflict rule is written down before offline writes ship |
| NW-UIX-001 | 2 | MUST | auto | Writes confirm, with specific wording |
| NW-UIX-002 | 2 | MUST | manual | Every view has loading, empty, error and stale states |
| NW-UIX-003 | 2 | MUST | manual | Every screen below the first has an in-app Back |
| NW-UIX-004 | 2 | SHOULD | auto | The running version is visible |
| NW-ACC-001 | 1 | MUST | auto | Zoom is never disabled |
| NW-ACC-002 | 1 | MUST | auto | Language, title, one h1 and a main landmark |
| NW-ACC-003 | 1 | MUST | auto | Every control has a name and every image has alt |
| NW-ACC-004 | 2 | MUST | auto | A visible focus style |
| NW-ACC-005 | 2 | SHOULD | auto | Fixed bars never hide the focused control |
| NW-ACC-006 | 2 | MUST | auto | Status changes are announced |
| NW-ACC-007 | 2 | MUST | auto | Reduced motion is honoured |
| NW-ACC-008 | 2 | SHOULD | auto | The colour scheme is declared |
| NW-ACC-009 | 2 | MUST | auto | Navigation has a name and exposes the active item |
| NW-ACC-010 | 2 | MUST | auto | Declared text colours meet contrast |
| NW-ACC-011 | 2 | MUST | manual | Touch targets are at least 44px |
| NW-ACC-012 | 3 | MUST | manual | A VoiceOver walkthrough, with Larger Text and Reduce Motion |
| NW-ACC-013 | 3 | SHOULD | auto | Font sizes are relative, so Larger Text works |
| NW-PER-001 | 2 | SHOULD | auto | A small first-load budget |
| NW-PER-002 | 2 | SHOULD | auto | Scripts do not block rendering |
| NW-PER-003 | 2 | SHOULD | auto | System fonts, sized images |
| NW-PER-004 | 3 | MUST | manual | Core Web Vitals are measured on a real phone |
| NW-DOC-001 | 2 | MUST | auto | Every iOS-quirk CSS rule carries a WHY comment |
| NW-DOC-002 | 2 | SHOULD | auto | AGENTS.md tells an AI agent how to work in the app |
| NW-DOC-003 | 3 | MUST | auto | A conformance claim is published |
| NW-DOC-004 | 3 | MUST | auto | A real-device test is on record |
| NW-DOC-005 | 3 | SHOULD | auto | A change log is kept |
| NW-DEV-001 | 1 | MUST | manual | Installed on a real iPhone and opens as its own app |
| NW-DEV-002 | 2 | MUST | manual | Offline launch shows the app and says so honestly |
| NW-DEV-003 | 2 | MUST | manual | Safe areas and the keyboard work on a real phone |
| NW-DEV-004 | 2 | MUST | manual | The update flow works end to end |
| NW-DEV-005 | 2 | MUST | manual | External links are tested and recorded |
| NW-DEV-006 | 2 | MUST | manual | Permission prompts appear only after a tap |
| NW-DEV-007 | 2 | MUST | manual | Write flows are exercised |
| NW-DEV-008 | 3 | SHOULD | manual | Android Chrome install is checked when Android is claimed |
| NW-DEV-009 | 3 | MAY | manual | An idle-storage test |

## The rules

### Architecture (ARC)

#### NW-ARC-001: No build step, no framework, no package manager

`Level 1` `MUST` `static, automated`

The app MUST run as written. It MUST NOT need a bundler, transpiler, framework runtime or package manager to build or serve it, and its folder MUST NOT contain node_modules, a package.json that lists dependencies, a lockfile or a bundler config.

**Why.** An app that needs npm install is no longer something a client can read and change in an afternoon. This is the defining constraint of the standard. Vendored files are allowed because they are visible (NW-ARC-003).

**Test.** Static: no node_modules folder; no package.json with dependencies or devDependencies; none of package-lock.json, yarn.lock, pnpm-lock.yaml, bun.lock, bun.lockb, tsconfig.json, or a vite, webpack, rollup, parcel, esbuild, babel, postcss or tailwind config.

#### NW-ARC-002: One public folder, one server file beside it

`Level 1` `MUST` `static, automated`

The app MUST keep every file it publishes inside a public/ directory that contains index.html, and MUST have a server entry file (server.py, server.ts, server.js or server.mjs) beside public/, never inside it.

**Why.** Serving a directory that holds only what you mean to publish makes it impossible to leak .git, .env, notes or the server source through a missed denylist entry.

**Test.** Static: public/index.html exists; one server.* file exists in the app root; no server.* file exists inside public/.

#### NW-ARC-003: Vendored third-party code is recorded

`Level 2` `MUST` `static, automated`

If the app vendors third-party code (anything under public/vendor/ or public/lib/, or any *.min.js file), a VENDOR.md MUST list each file with its name, version, source URL and SHA-256.

**Why.** With no npm there is no lockfile to rot, so supply-chain risk concentrates in the few files you copied in. Pin and date them. The rule does not apply to an app that vendors nothing.

**Test.** Static: find vendored files; VENDOR.md exists and mentions each by file name. Compare sha256sum against the recorded hash.

**Sources.** https://owasp.org/www-project-application-security-verification-standard/

### Network and hosting (NET)

#### NW-NET-001: The server binds loopback by default and refuses anything else

`Level 1` `MUST` `static, automated`

The server MUST listen on 127.0.0.1 (or ::1) by default and MUST refuse to start on any other address unless an explicit, named override is set.

**Why.** tailscale serve is the one thing meant to reach the port. Binding 0.0.0.0 also publishes the app to the LAN and to coffee-shop wifi, and a loopback bind is what makes the Tailscale identity headers trustworthy.

**Test.** Static (server.py): the default bind is 127.0.0.1 and no default of 0.0.0.0, an empty string or :: appears. NW-NET-002 proves the real socket.

**Sources.** https://tailscale.com/kb/1242/tailscale-serve, https://tailscale.com/kb/1312/serve

#### NW-NET-002: The listening socket is loopback only

`Level 1` `MUST` `runtime, automated`

While it runs, the app's listening socket MUST be bound to 127.0.0.1 or ::1 and to no other address.

**Why.** A static read of the code can be wrong about what the process really did. The socket table is the truth.

**Test.** Runtime (Linux): the checker starts the server and reads /proc/net/tcp and /proc/net/tcp6. Elsewhere run ss -ltn or lsof -iTCP -sTCP:LISTEN by hand.

#### NW-NET-003: Nothing in the app starts tailscale funnel

`Level 1` `MUST` `static, automated`

No script, unit file or server code in the app MAY run tailscale funnel. Publishing to the public internet is a separate, written decision.

**Why.** Funnel puts the service on the open internet with a real certificate. A port is either served privately or funnelled and the most recent command wins, so one funnel command on a serve port silently flips it public. A no-login app on funnel is an internet-facing service with no authentication.

**Test.** Static: no 'tailscale funnel' in *.sh, *.service, *.py, *.js, *.mjs, *.ts, Makefile. By hand: tailscale funnel status shows nothing for this app.

**Fix.** If you really need the public internet: an app-level login, a rate limit, separate storage for other people's data, and a written decision in CONFORMANCE.md, before the command runs.

**Sources.** https://tailscale.com/kb/1223/funnel

#### NW-NET-004: The service comes back after a reboot

`Level 2` `SHOULD` `runtime, automated`

A long-lived app SHOULD run as a systemd user unit (nixweb install) with Restart=on-failure and linger enabled, never from nohup or an open terminal.

**Why.** nohup does not restart, logs nowhere useful and dies with the terminal. The tailnet mapping should live and die with the unit.

**Test.** Runtime (host): systemctl --user is-enabled nixweb-NAME.service; loginctl show-user USER -p Linger.

#### NW-NET-005: Host and port are final before anyone installs; machine names carry nothing sensitive

`Level 2` `SHOULD` `process, manual`

The app's tailnet hostname and HTTPS port SHOULD be chosen before it is installed on any phone and written in the README, and machine names SHOULD carry nothing sensitive.

**Why.** An installed app is bound to its origin (scheme, host, port). Renaming the machine or changing the port makes every installed icon a different app with different storage. Issuing an HTTPS certificate also writes the machine name to public Certificate Transparency logs, where anyone can search it.

**Test.** Process: the README states the origin and the manifest id; a crt.sh search for the hostname shows nothing you mind being public.

**Sources.** https://tailscale.com/kb/1153/enabling-https, https://developer.chrome.com/blog/pwa-manifest-id

#### NW-NET-006: A grant narrows who can reach the app when the tailnet is shared

`Level 3` `SHOULD` `process, manual`

If the tailnet has any user or device besides the owner, a grant limiting who can reach the app's port SHOULD be in place.

**Why.** Tailscale policy is deny by default but a personal tailnet often allows everything, and a shared-in device gets everything the node's identity can serve. A no-login app has no second lock.

**Test.** Process: in the admin console, Access controls, test access from a device that must be denied; tailscale ping and curl from it time out.

**Sources.** https://tailscale.com/kb/1324/grants

#### NW-NET-007: The tailnet HTTPS edge delivers what loopback does

`Level 3` `SHOULD` `runtime, automated`

Through its tailnet HTTPS URL the app SHOULD answer 200 with the same security headers it sends on loopback, and SHOULD still compress text.

**Why.** Verified 2026-10-11 on Tailscale 1.102.3: tailscale serve passes the original Host through, adds X-Forwarded-For, X-Forwarded-Host and X-Forwarded-Proto, replaces any client-supplied Tailscale-User-Login with the real one, and passes Content-Encoding and the app's headers through. It adds no HSTS of its own.

**Test.** Runtime: nixweb check APP --url https://HOST:PORT requests / and checks the status and the security headers. Without --url this rule reports as not verified.

### Server (SRV)

#### NW-SRV-001: Dotfiles, server source, repository and environment paths return 404

`Level 1` `MUST` `runtime, automated`

The server MUST answer 404 for /.git/config, /.env, /.gitignore, /server.py and any path with a segment that starts with a dot.

**Why.** Every app is its own git repository and often holds a .env. A served .git is the whole history.

**Test.** Runtime: curl each path and require 404.

#### NW-SRV-002: /ping answers fast, is never cached, and answers HEAD

`Level 1` `MUST` `runtime, automated`

GET and HEAD /ping MUST return 200 quickly with Cache-Control: no-store.

**Why.** The app's reachability probe asks /ping. A bare static server 404s it, so a fresh app shows 'cannot reach home'. A cached 200 would report a dead host as alive.

**Test.** Runtime: GET and HEAD /ping return 200 and Cache-Control contains no-store.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching

#### NW-SRV-003: Path traversal fails, including encoded forms

`Level 1` `MUST` `runtime, automated`

Requests that try to climb out of the public directory MUST fail with a 4xx status: plain .., %2e%2e, double-encoded %252e%252e, an encoded slash, and a backslash.

**Why.** A server that decodes once and checks once is beaten by a path decoded twice or by a symlink. Resolve the real path, then require it stays inside the root.

**Test.** Runtime: curl --path-as-is with each form against a file known to exist one level up (server.py); require 4xx.

**Sources.** https://owasp.org/www-community/attacks/Path_Traversal

#### NW-SRV-004: Correct MIME types

`Level 1` `MUST` `runtime, automated`

The server MUST send application/manifest+json for the manifest, text/javascript for .js files including sw.js, text/css for .css and image/svg+xml for .svg, with charset=utf-8 on text types.

**Why.** A service worker or module script with the wrong type fails to register or load. RFC 9239 makes text/javascript the only recommended JavaScript type. An explicit table beats the OS mime database, which differs between Python versions.

**Test.** Runtime: curl -sI each file and compare Content-Type.

**Sources.** https://www.rfc-editor.org/rfc/rfc9239

#### NW-SRV-005: The server publishes public/ and nothing else, and never lists a directory

`Level 1` `MUST` `runtime, automated`

The server MUST publish only files inside public/ whose extension is on an allowlist, MUST NOT serve any file outside public/, and MUST answer 404, not a listing, for a directory without an index.html.

**Why.** A denylist (no dotfiles, no server.py) is a floor. Every other file in the folder, such as notes.md, app.db, server.py.bak or CLAUDE.md, stays readable by the whole tailnet. A dedicated directory plus an allowlist fails closed. Python's stock handler also lists directories and follows symlinks.

**Test.** Runtime on a temporary copy: the checker plants zz-nixweb-canary.txt in the app root, plus zz-nixweb-canary.db, server.py.bak and an empty directory in public/, starts the server on the copy, and requires 404 for all of them.

#### NW-SRV-006: Files without a content hash always revalidate

`Level 2` `MUST` `runtime, automated`

HTML, sw.js, the manifest and every file without a content hash in its name MUST be sent with Cache-Control: no-cache, no-store or max-age=0. Only content-hashed file names MAY be sent as immutable.

**Why.** With only Last-Modified and no Cache-Control a browser applies heuristic freshness, and cache.addAll() reads through the HTTP cache. A new service worker can then precache the old app.js and the update ships nothing. This was observed in the template before it was fixed.

**Test.** Runtime: curl -sI / /sw.js /manifest.webmanifest /app.js and read Cache-Control.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching

#### NW-SRV-007: Errors and headers leak nothing

`Level 2` `MUST` `runtime, automated`

No response header or error body MAY contain a language or library version, a file-system path or a stack trace, and a 404 body MUST be generic.

**Why.** Python's http.server announces 'SimpleHTTP/0.6 Python/3.x' in the Server header and echoes messages in its error pages. Detail belongs in the server log.

**Test.** Runtime: the Server header and a 404 body contain no 'Python', no path separator of the app folder, and no 'Traceback'.

#### NW-SRV-008: Conditional requests and compression

`Level 2` `SHOULD` `runtime, automated`

The server SHOULD send ETag or Last-Modified and answer a matching conditional GET with 304, and SHOULD gzip text responses when the client accepts it, with Vary: Accept-Encoding.

**Why.** With no-cache on everything (NW-SRV-006), 304 makes revalidation nearly free. Compression cuts the bytes a phone pulls through the tunnel. It was not documented whether tailscale serve compresses on its own, so the app does it.

**Test.** Runtime: a repeat GET with If-None-Match returns 304; a GET with Accept-Encoding: gzip on a text file returns Content-Encoding: gzip.

#### NW-SRV-009: Byte ranges

`Level 2` `SHOULD` `runtime, automated`

The server SHOULD honour a single Range request with 206 and Content-Range, and answer an unsatisfiable range with 416.

**Why.** Safari fetches audio and video with Range requests, and a server that answers 200 with the whole file is widely reported to stall or fail. Python's stock http.server ignores Range.

**Test.** Runtime: Range: bytes=0-9 on a file returns 206 with Content-Range; a range past the end returns 416.

#### NW-SRV-010: Clean exit on SIGTERM

`Level 2` `SHOULD` `runtime, automated`

The server SHOULD finish in-flight requests and exit with status 0 on SIGTERM.

**Why.** systemd stops a service with SIGTERM. Python's default kills the process mid-request, and a Ctrl-C handler alone does not cover it.

**Test.** Runtime: the checker sends SIGTERM to a server it started and requires exit status 0 within 3 seconds.

#### NW-SRV-011: Request size and time are bounded

`Level 2` `MUST` `runtime, automated`

The server MUST refuse a request body over a fixed limit (64 KiB for JSON) with 413 before reading it, and MUST set a socket timeout so one stuck client cannot hold a thread.

**Why.** ThreadingHTTPServer starts a thread per connection with no limits. A page open on a compromised device can flood a no-login endpoint.

**Test.** Runtime: a POST that declares Content-Length 99999999 gets 413 within 5 seconds.

### Security and privacy (SEC)

#### NW-SEC-001: A strict Content-Security-Policy is sent as a header

`Level 2` `MUST` `runtime, automated`

Every response MUST carry a Content-Security-Policy header that sets default-src 'self', does not allow 'unsafe-inline' or 'unsafe-eval' for scripts, and sets object-src 'none', base-uri and frame-ancestors.

**Why.** With no inline script and no other origin, a 'self'-only policy needs no nonces. frame-ancestors, sandbox and reporting do not work in a meta tag, so a meta CSP is not enough.

**Test.** Runtime: curl -sI and parse the policy. Optional: paste it into csp-evaluator.withgoogle.com.

**Sources.** https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html, https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP

#### NW-SEC-002: Companion security headers on every response

`Level 2` `MUST` `runtime, automated`

Every response, including 404s and /ping, MUST carry X-Content-Type-Options: nosniff, Referrer-Policy: no-referrer (or same-origin), and a Permissions-Policy that denies the features the app does not use.

**Why.** This is the OWASP Secure Headers baseline. An app that records audio must allow microphone=(self), so the default must match what the app uses. Cross-Origin-Opener-Policy: same-origin is also sent. Cross-Origin-Resource-Policy is deliberately left out of the template: it could stop the OS fetching the home-screen icon, and that is not verified on a device.

**Test.** Runtime: curl -sI on /, /ping and a missing path; each carries all three.

**Sources.** https://raw.githubusercontent.com/OWASP/www-project-secure-headers/master/ci/headers_add.json, https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Permissions-Policy

#### NW-SEC-003: Host header allowlist, against DNS rebinding

`Level 2` `MUST` `runtime, automated`

The server MUST answer 421 or 403 to a request whose Host is not one of its own names: localhost, 127.0.0.1, ::1, the machine's tailnet name and its tailnet addresses.

**Why.** A page on a hostile site can point its own DNS name at 127.0.0.1 and then talk to a loopback server using that name. Refusing unknown Host values ends the attack. Verified 2026-10-11 on Tailscale 1.102.3: tailscale serve passes the original Host through, so an exact allowlist works. This is the mitigation the MCP SDKs use for localhost servers. No OWASP primary page was found for it.

**Test.** Runtime: curl -H 'Host: evil.example' returns 421 or 403; Host: 127.0.0.1:PORT returns 200.

#### NW-SEC-004: State-changing requests refuse cross-site origins

`Level 2` `MUST` `runtime, automated`

POST, PUT, PATCH and DELETE MUST be refused with 403 when Sec-Fetch-Site is cross-site or same-site, or when Origin is present and does not match Host, including Origin: null. GET and HEAD MUST NOT change state. JSON endpoints SHOULD also require Content-Type: application/json.

**Why.** No login means no cookie to be missing: any page open in a browser on a tailnet device can send a request to your tailnet URL. OWASP names Fetch Metadata the primary defence. A request with neither header comes from curl or a script, not a browser page, and is allowed. Sec-Fetch-Site is sent by current browsers including Safari.

**Test.** Runtime: a POST with Sec-Fetch-Site: cross-site, one with Origin: https://evil.example and one with Origin: null each get 403; a POST with a matching Origin is not refused by the guard.

**Sources.** https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html, https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Site

#### NW-SEC-005: No CORS

`Level 2` `MUST` `runtime, automated`

The server MUST NOT send Access-Control-Allow-* headers, MUST NOT reflect Origin, and MUST answer OPTIONS with 405.

**Why.** Same-origin policy already blocks cross-origin reads. CORS only loosens it. CORS never protected writes: a simple cross-origin POST still executes (see NW-SEC-004).

**Test.** Runtime: OPTIONS with Origin: https://evil.example returns 405 and no Access-Control-Allow-Origin on any response.

**Sources.** https://web.dev/articles/cross-origin-resource-sharing

#### NW-SEC-006: No third-party origins, no trackers

`Level 1` `MUST` `static, automated`

The app MUST NOT load or contact any other origin (scripts, styles, fonts, images, analytics, telemetry, CDN assets, crash reporters), and MUST NOT include an analytics or tracking SDK.

**Why.** Every foreign origin leaks the user's address and referrer to a vendor, breaks offline use and defeats a 'self'-only CSP. The point of a tailnet app is that the data stays on the user's machines.

**Test.** Static: every absolute URL in HTML, CSS, JS, the manifest and sw.js is same-origin (comments excluded; the SVG namespace is allowed), and none of gtag, googletagmanager, google-analytics, plausible, mixpanel, segment, sentry, hotjar, posthog or sendBeacon appears.

**Fix.** Vendor the file into public/vendor/ and record it in VENDOR.md (NW-ARC-003).

#### NW-SEC-007: No code-injection sinks

`Level 1` `MUST` `static, automated`

The app MUST NOT use eval, new Function, document.write, string-argument setTimeout or setInterval, innerHTML, outerHTML or insertAdjacentHTML. Untrusted data MUST be inserted with textContent, createElement and setAttribute on non-executable attributes.

**Why.** OWASP's DOM XSS cheat sheet names textContent the safe sink. Data from your own notes is still untrusted: it can be pasted or synced from somewhere else.

**Test.** Static: scan the JavaScript for the sinks. A justified exception carries a waiver comment on the same or the previous line: nixweb-allow: NW-SEC-007 followed by the reason.

**Sources.** https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html

#### NW-SEC-008: No inline script, handlers or styles

`Level 2` `MUST` `static, automated`

index.html MUST NOT contain inline script bodies, on* event-handler attributes, inline style elements or style attributes, so the CSP can forbid them.

**Why.** Without this a strict CSP breaks the app, and the first fix people reach for is 'unsafe-inline'.

**Test.** Static: parse index.html; no script element without src, no on* attribute, no style element, no style attribute.

#### NW-SEC-009: No secrets in served files

`Level 1` `MUST` `static, automated`

Files in public/ MUST NOT contain API keys, tokens, passwords or private keys, and a .env file MUST NOT be tracked by git.

**Why.** Everything served is readable by every tailnet member and is cached on every device that opens the app.

**Test.** Static: scan public/ for private-key blocks, token shapes (sk-, ghp_, AKIA, xoxb-) and key, secret or password assignments to long string literals; git ls-files shows no .env.

### Installability (INS)

#### NW-INS-001: A valid manifest is linked

`Level 1` `MUST` `static, automated`

index.html MUST link a manifest with link rel=manifest, and the file MUST exist inside public/ and parse as JSON.

**Why.** Chromium reads the manifest from the page that is open, and Safari fetches it at page load since 15.4, so a broken link shows up early.

**Test.** Static: the link exists, the file exists, json.loads succeeds. Chrome DevTools, Application, Manifest shows no errors.

**Sources.** https://www.w3.org/TR/appmanifest/, https://web.dev/articles/add-manifest

#### NW-INS-002: Required manifest members

`Level 1` `MUST` `static, automated`

The manifest MUST declare name, short_name, start_url, display set to standalone, and icons, and MUST NOT set prefer_related_applications to true.

**Why.** Chromium's installability criteria need a name, start_url, display and 192 and 512 icons. Safari honours standalone; fullscreen opens standalone and minimal-ui degrades to a browser shortcut, so standalone is the one value that means the same everywhere. display_override is Chromium only.

**Test.** Static: read the members from the manifest.

**Sources.** https://web.dev/articles/install-criteria, https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable

#### NW-INS-003: A stable id, and a start_url inside scope

`Level 1` `MUST` `static, automated`

The manifest MUST set a stable id such as "/", start_url MUST sit inside scope, and scope MUST end with a slash. In-app navigation MUST stay inside it.

**Why.** Without an id, identity is derived from start_url and a later change makes a new app. WebKit documents id since 16.4. Scope matching is a same-origin string-prefix match, and a start_url outside the scope silently resets the scope to the default.

**Test.** Static: id is present; start_url and scope are relative or root-relative; scope ends with a slash. Chrome DevTools shows the computed App Id.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/id, https://developer.chrome.com/blog/pwa-manifest-id

#### NW-INS-004: Complete, real, non-blank icons

`Level 1` `MUST` `static, automated`

The manifest MUST list PNG icons at 192x192 and 512x512 with purpose any and a separate 512x512 PNG with purpose maskable. Every listed file MUST exist at its declared size, and no icon MAY be a single flat colour.

**Why.** Chromium needs 192 and 512. web.dev advises separate files because a maskable icon needs a full-bleed opaque background and a safe zone, while an any icon should not. An invisible icon, where a font did not render, is exactly the failure nixweb icons guards against.

**Test.** Static: the checker reads every PNG header and decodes the pixels. Paste the maskable icon into maskable.app to see the safe zone.

**Sources.** https://web.dev/articles/maskable-icon, https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Define_app_icons

#### NW-INS-005: apple-touch-icon is declared, 180x180 and opaque

`Level 1` `MUST` `static, automated`

index.html MUST link rel=apple-touch-icon to a 180x180 PNG with no alpha channel.

**Why.** Apple's tag takes precedence over manifest icons, and iOS paints transparent pixels black. Without one, iOS 16.4 and later draws a monogram. The old story that iOS screenshots your page is outdated.

**Test.** Static: the link exists; the file is a 180x180 PNG whose colour type has no alpha and no tRNS chunk.

**Sources.** https://webkit.org/blog/12445/new-webkit-features-in-safari-15-4/, https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/

#### NW-INS-006: The Apple and Chromium app meta tags

`Level 1` `MUST` `static, automated`

index.html MUST include apple-mobile-web-app-capable set to yes, apple-mobile-web-app-title, and mobile-web-app-capable set to yes.

**Why.** On iOS 16.4 to 18 a site without a standalone display or the capable tag was only a bookmark. iOS 26 opens every Home Screen site as a web app by default, but lets the user switch that off, so keep every signal. The tags cost nothing.

**Test.** Static: parse the head.

**Sources.** https://webkit.org/blog/17333/webkit-features-in-safari-26-0/, https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html

#### NW-INS-007: Theme and background colours agree, and the first frame is not white

`Level 1` `MUST` `static, automated`

The theme-color meta MUST equal the manifest theme_color, the manifest MUST set background_color, and html or body MUST paint a background colour so the launch frame is not white.

**Why.** web.dev says the meta tag should match theme_color. iOS does not build a splash from the manifest, so the first thing a dark app shows is whatever the page paints first.

**Test.** Static: compare the two colours; read the CSS for a background on html or body.

**Sources.** https://web.dev/articles/add-manifest

#### NW-INS-008: The status bar style is a deliberate choice

`Level 2` `SHOULD` `static, automated`

apple-mobile-web-app-status-bar-style SHOULD be set. black-translucent SHOULD be used only with a top-inset fallback (a max() of a fixed padding and env(safe-area-inset-top)) that has been verified on the shipping iOS release.

**Why.** WebKit bug 301994 reports iOS 26.1 and later with black-translucent and env(safe-area-inset-top) returning 0, which puts the header under the clock. The bug was reopened on 2026-08-04 after a reported fix. The template therefore ships black.

**Test.** Static: the meta is set; if it is black-translucent the CSS contains a max() around the top inset. Device: DEV-003.

**Sources.** https://bugs.webkit.org/show_bug.cgi?id=301994

### Shell and layout (SHL)

#### NW-SHL-001: The viewport meta

`Level 1` `MUST` `static, automated`

The viewport meta MUST be width=device-width, initial-scale=1, viewport-fit=cover.

**Why.** viewport-fit=cover is what makes env(safe-area-inset-*) non-zero. Without it the layout looks right in a simulator and clips on the phone. The zoom-limiting keys are covered by NW-ACC-001.

**Test.** Static: parse the meta content.

**Sources.** https://webkit.org/blog/7929/designing-websites-for-iphone-x/

#### NW-SHL-002: Safe-area insets are added to real padding, on all four sides

`Level 1` `MUST` `static, automated`

Fixed edge UI MUST add env(safe-area-inset-top), -right, -bottom and -left to real padding with calc() or max(), never use the inset alone.

**Why.** The insets are 0 on a phone without a notch, so an inset-only value gives a cramped header. In landscape the left and right insets become non-zero.

**Test.** Static: all four env() names appear and at least one sits inside calc() or max(). Device: rotate to landscape on a notched iPhone (DEV-003).

**Sources.** https://developer.mozilla.org/en-US/docs/Web/CSS/env

#### NW-SHL-003: The page never scrolls; lists scroll in their own box

`Level 1` `MUST` `static, automated`

html and body MUST have overflow hidden and overscroll-behavior none. Only lists scroll, each in its own box with overflow-y auto and overscroll-behavior contain.

**Why.** Law 17: a settings page that scrolls hides controls behind a gesture. overscroll-behavior needs iOS 16, so overflow hidden on the root is the part that works everywhere. Whether none removes all rubber-banding on iOS 26 is not confirmed by any source read.

**Test.** Static: the CSS rules exist. Device: drag on the header and on empty space; nothing moves.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/CSS/overscroll-behavior

#### NW-SHL-004: The shell is sized with 100% or dvh, never 100vh

`Level 1` `MUST` `static, automated`

The app shell MUST be sized with height 100% on html and body, or with dvh, and MUST NOT use 100vh.

**Why.** vh is the layout viewport and ignores browser chrome. In an installed app there is no collapsing bar, so 100% is the stable choice. dvh needs Safari 15.4.

**Test.** Static: no 100vh in any CSS file.

**Sources.** https://webkit.org/blog/12445/new-webkit-features-in-safari-15-4/

#### NW-SHL-005: Form controls render at 16px or larger

`Level 1` `MUST` `static, automated`

The CSS MUST set font-size of at least 16px on input, textarea and select.

**Why.** iOS Safari zooms in when a focused field has a computed font size under 16px, and does not zoom back out. The cure is the size, not disabling zoom. The threshold is consistent across secondary sources; no WebKit statement was found.

**Test.** Static: a rule for input, textarea and select with font-size of 16px or more (or 1rem at a 16px root). Device: tap each field; the page does not zoom.

#### NW-SHL-006: touch-action: manipulation on controls, never on html or body

`Level 1` `MUST` `static, automated`

The CSS MUST set touch-action: manipulation on buttons, tabs and links, and MUST NOT set it on html, body or *.

**Why.** manipulation removes the double-tap-zoom handling on the element and keeps pan and pinch. An October 2025 report found it on the root element stopped the keyboard appearing in an installed PWA. That report is secondary and unverified here, but the rule costs nothing.

**Test.** Static: the declaration exists and no root-level selector carries it.

#### NW-SHL-007: Chrome is unselectable, content is selectable

`Level 2` `SHOULD` `static, automated`

user-select: none SHOULD be set on buttons, bars and gesture surfaces only. It SHOULD NOT be set on html, body or *, so readable content stays selectable.

**Why.** Selectable text is needed for copy, Look Up, Speak Selection and translation. Dragging chrome starting a selection is the reason for the rule, so scope it to the chrome.

**Test.** Static: no root-level selector carries user-select: none. Device: long-press a data value; selection handles appear.

#### NW-SHL-008: Text size is locked against landscape inflation and the system font is used

`Level 2` `SHOULD` `static, automated`

html SHOULD set -webkit-text-size-adjust: 100%, and the font stack SHOULD start with system-ui or -apple-system.

**Why.** Safari inflates text in landscape without it. The system font renders in SF Pro and costs zero bytes.

**Test.** Static: both declarations exist.

#### NW-SHL-009: Phone-number auto-linking is switched off

`Level 2` `SHOULD` `static, automated`

index.html SHOULD set meta format-detection to telephone=no unless the app wants numbers dialled.

**Why.** By default Safari on iOS turns any string shaped like a phone number into a call link. Dashboards full of ids and timestamps get mangled.

**Test.** Static: the meta exists.

**Sources.** https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariHTMLRef/Articles/MetaTags.html

#### NW-SHL-010: Text-entry screens follow the visual viewport

`Level 2` `SHOULD` `static, automated`

If the app has text inputs it SHOULD size to window.visualViewport (resize and scroll events) so the focused field and its action stay reachable with the keyboard open, and SHOULD NOT depend on interactive-widget.

**Why.** On iOS the keyboard shrinks the visual viewport and leaves the layout viewport alone. interactive-widget is documented for Chrome on Android only. One developer reports an installed-app bug on iOS 17 and 18 where the first keyboard open leaves the height permanently low; that report is unverified on iOS 26.

**Test.** Static: if inputs exist, the JavaScript uses visualViewport. Device: DEV-003.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/CSS/Viewport_concepts

### iOS platform behaviour (IOS)

#### NW-IOS-001: Install state is detected three ways

`Level 1` `MUST` `static, automated`

If the app changes behaviour based on install state, it MUST test display-mode: standalone, display-mode: fullscreen and navigator.standalone.

**Why.** MDN's compatibility data records that an installed iOS web app reports display-mode: fullscreen, not standalone (WebKit bug 264218, open). navigator.standalone is iOS-only. On iOS 26 a standalone site no longer implies a manifest.

**Test.** Static: if the JavaScript mentions display-mode or navigator.standalone, all three tests are present. Device: log all three in the installed app.

**Sources.** https://bugs.webkit.org/show_bug.cgi?id=264218, https://developer.mozilla.org/en-US/docs/Web/CSS/@media/display-mode

#### NW-IOS-002: No user-agent sniffing for the OS version

`Level 2` `MUST` `static, automated`

The app MUST NOT parse navigator.userAgent to learn the iOS version. It MUST feature-detect instead.

**Why.** Safari 26 reports a frozen OS version in its user-agent string on iOS 26 and iPadOS 26. To learn a user's version, ask them to read Settings, General, About.

**Test.** Static: no userAgent parsing in the JavaScript.

**Sources.** https://developer.apple.com/tutorials/data/documentation/safari-release-notes/safari-26-release-notes.md

#### NW-IOS-003: Lifecycle events, not unload

`Level 2` `MUST` `static, automated`

The app MUST NOT use unload or beforeunload, MUST save on visibilitychange (hidden) and pagehide, and MUST re-check its state on visibilitychange (visible) and on pageshow when the page was restored from the back-forward cache.

**Why.** An installed iOS app is suspended and may be killed in the background with no event at all. Safari may restore a page from bfcache without running any script, so a timer that did not tick leaves a stale screen.

**Test.** Static: no unload or beforeunload listener; visibilitychange and pageshow listeners exist.

**Sources.** https://web.dev/articles/bfcache

#### NW-IOS-004: Platform APIs are feature-detected and degrade

`Level 2` `MUST` `static, automated`

The app MUST NOT rely on an API that Safari on iPhone lacks (navigator.vibrate, Web Bluetooth, WebUSB, Web Serial, WebHID, showOpenFilePicker, navigator.contacts, Background Sync) without a feature test and a fallback. A wake lock MUST be re-acquired on visibilitychange, and a MediaRecorder format MUST be chosen with isTypeSupported.

**Why.** MDN's compatibility data shows SyncManager unsupported in Safari on iOS. Wake Lock works in an installed Home Screen app only from iOS 18.4 (WebKit bug 254545). WebM in MediaRecorder arrived in 18.4. Web Push and badging work only in an installed app.

**Test.** Static: each risky API found has a matching 'in' or typeof test in the same file; wakeLock use is paired with a visibilitychange handler; MediaRecorder use is paired with isTypeSupported.

**Sources.** https://webkit.org/blog/16574/webkit-features-in-safari-18-4/, https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/

### Offline and resilience (OFF)

#### NW-OFF-001: A service worker handles install, activate and fetch

`Level 1` `MUST` `static, automated`

public/sw.js MUST exist, MUST be registered from the app's JavaScript behind a 'serviceWorker' in navigator test, and MUST handle install, activate and fetch.

**Why.** A tailnet host is often asleep. The service worker turns Safari's error page into your app with your message. Chromium no longer requires a service worker to install and Safari never did, but the offline shell needs one, and service workers need a secure context, which is why nixweb serve provides HTTPS.

**Test.** Static: the file exists, the registration is guarded, the three listeners exist. Device: DEV-002.

**Sources.** https://developer.chrome.com/blog/update-install-criteria, https://webkit.org/blog/17333/webkit-features-for-safari-26-0/

#### NW-OFF-002: Versioned caches; old ones deleted by prefix

`Level 1` `MUST` `static, automated`

Cache names MUST carry a version constant that changes with the shell, and activate MUST delete only this app's older caches, matched by a name prefix.

**Why.** Caches are shared by the whole origin and never expire by themselves. Deleting every cache that is not the current one wipes a sibling app on the same origin.

**Test.** Static: a version constant feeds the cache name; activate calls caches.delete behind a startsWith test.

**Sources.** https://web.dev/articles/offline-cookbook

#### NW-OFF-003: Every precached URL exists

`Level 1` `MUST` `static, automated`

Every URL in the precache list MUST resolve to a file in public/.

**Why.** cache.addAll rejects if any URL fails and the whole service worker install is discarded, which silently leaves the app with no offline shell. A template copied before nixweb icons has run is the usual way to hit it.

**Test.** Static: read the precache array and test each entry against public/.

#### NW-OFF-004: Only same-origin GET is cached, and /ping never

`Level 2` `MUST` `static, automated`

The fetch handler MUST pass non-GET requests, cross-origin requests and /ping straight to the network.

**Why.** A cached write is a lost write. Cross-origin responses are opaque and cannot be checked. A cached /ping would report a dead host as alive.

**Test.** Static: the handler tests the method, the origin and the /ping path before it touches the cache. Device: offline, a ping must reject.

**Sources.** https://web.dev/articles/offline-cookbook

#### NW-OFF-005: Only good responses are cached

`Level 2` `MUST` `static, automated`

Before cache.put the worker MUST check res.ok (or status 200) and a same-origin response type, MUST clone the response, and MUST pass the put to event.waitUntil.

**Why.** Cache.put stores any response, including 404, 500 and opaque ones. A cached 500 served as the last known answer looks like good data. Cache.add and addAll refuse non-2xx, put does not.

**Test.** Static: every cache.put is guarded by an ok test and is awaited through waitUntil.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/API/Cache/put

#### NW-OFF-006: The shell is the fallback for navigations only

`Level 2` `MUST` `static, automated`

When the network fails the worker MUST answer a navigation with the cached shell, and MUST NOT answer an image, script, style or JSON request with index.html.

**Why.** HTML returned for a failed app.js breaks parsing and hides the real error. A cached HTML page can then poison the cache under a script URL.

**Test.** Static: every fallback to index.html is gated by request.mode === 'navigate'.

**Sources.** https://web.dev/articles/offline-cookbook

#### NW-OFF-007: Precaching reads past the HTTP cache

`Level 2` `MUST` `static, automated`

The worker MUST precache with requests that use cache: 'reload', unless the server sends no-cache for every shell file (NW-SRV-006).

**Why.** cache.addAll goes through the HTTP cache. With heuristic freshness the new worker can store the old app.js and the update ships nothing.

**Test.** Static: the precache requests use cache: 'reload'; otherwise NW-SRV-006 passes at runtime.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching

#### NW-OFF-008: Registration sets updateViaCache to none

`Level 2` `MUST` `static, automated`

The page MUST register sw.js at a stable URL with updateViaCache: 'none'.

**Why.** The spec default is 'imports': the main script bypasses the HTTP cache but imported scripts may not. A stable URL keeps the update check working; an orphaned old URL cannot be reached again. The old advice to add a version query to sw.js is outdated.

**Test.** Static: the register call passes updateViaCache: 'none' and a constant 'sw.js' URL.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/updateViaCache, https://www.w3.org/TR/service-workers/

#### NW-OFF-009: Updates are user-gated

`Level 2` `SHOULD` `static, automated`

The worker SHOULD NOT call skipWaiting during install. It SHOULD wait for a SKIP_WAITING message, and the page SHOULD show 'update ready', reload once on controllerchange, and call registration.update() when it becomes visible.

**Why.** skipWaiting lets a page loaded under version 1 fetch version 2 resources mid-session. Update checks run on navigation, and an installed iOS app can stay resident for days (anecdotal, unverified), so ask for one when the app returns to the foreground.

**Test.** Static: skipWaiting sits in a message handler, not in install; the page has a controllerchange listener guarded against a second reload and a visibilitychange update call. Device: DEV-004.

**Sources.** https://web.dev/articles/service-worker-lifecycle

#### NW-OFF-010: Reachability is probed, not guessed

`Level 2` `MUST` `static, automated`

The app MUST decide whether the server is reachable with a fetch of /ping that uses cache: 'no-store' and a timeout, and MUST NOT gate behaviour on navigator.onLine alone.

**Why.** navigator.onLine says the radio is up. It is true on a captive-portal wifi and when the tailnet is down. MDN: do not disable features based on online status.

**Test.** Static: the JavaScript fetches ping with no-store and an abort signal.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/API/Navigator/onLine

#### NW-OFF-011: Every fetch has a timeout

`Level 2` `MUST` `static, automated`

Every fetch call MUST carry an AbortSignal, from AbortSignal.timeout or an AbortController with a timer, so a sleeping host cannot hang the screen.

**Why.** A host that is asleep over Tailscale often hangs instead of refusing, and fetch has no default timeout. AbortSignal.timeout works in Safari 16 and later, but its timer pauses while a page sits in the back-forward cache, so use a controller where wall time matters.

**Test.** Static: each fetch call has a signal option within its argument list. A justified exception carries nixweb-allow: NW-OFF-011 and a reason.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal/timeout_static

#### NW-OFF-012: Errors paint a screen, never a blank page

`Level 2` `MUST` `static, automated`

The app MUST register window error and unhandledrejection listeners that show a visible error with a Reload control, and index.html MUST contain a noscript message.

**Why.** An uncaught exception during startup leaves a white screen on iOS with no console. Promise rejections arrive on unhandledrejection, not on error.

**Test.** Static: both listeners exist and a noscript element exists. Device: throw an error on purpose and watch the error card.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/API/Window/unhandledrejection_event

#### NW-OFF-013: Runtime caching of API data is bounded and private-aware

`Level 2` `SHOULD` `static, automated`

If the worker caches API responses it SHOULD skip responses marked no-store or private, SHOULD cap the number of cached entries, and SHOULD mark answers served from cache.

**Why.** Cache Storage is origin-wide and persists on the device, so on a lost phone it is data at rest. A silent stale answer is a lie; mark it so the screen can say 'last known data'.

**Test.** Static: the API branch checks cache-control, trims the cache and sets a marker header. Not applicable if the worker caches no API data.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching

### Data and storage (DAT)

#### NW-DAT-001: Offline writes queue in IndexedDB and replay from the open page

`Level 2` `MUST` `static, automated`

If the app sends writes, a write that fails or happens offline MUST be stored in an IndexedDB outbox, shown as pending, and replayed when the app opens, becomes visible, comes back online or answers /ping. Background Sync MUST NOT be the only trigger.

**Why.** Background Sync is not in Safari or Firefox, so a service worker cannot flush the queue on iOS. The one dependable trigger on iOS is the app being open.

**Test.** Static: if any fetch uses POST, PUT, PATCH or DELETE, indexedDB is used. Not applicable otherwise. Device: DEV-007.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API, https://raw.githubusercontent.com/mdn/browser-compat-data/main/api/SyncManager.json

#### NW-DAT-002: Every replayable write carries an idempotency key

`Level 2` `MUST` `static, automated`

If the app sends writes, each one MUST carry an Idempotency-Key header made when the user acted (crypto.randomUUID), reused on every retry, and the server MUST return the stored answer for a repeated key.

**Why.** A write can succeed while the response is lost when the tunnel drops. A naive retry then duplicates it. The header is an IETF draft, not an RFC, so the server contract is yours to document.

**Test.** Static: writes set Idempotency-Key. Runtime: send the same keyed POST twice; one row changes and both answers match.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Idempotency-Key

#### NW-DAT-003: Storage use is guarded and small

`Level 2` `SHOULD` `static, automated`

localStorage and sessionStorage access SHOULD sit inside try and catch and SHOULD hold small flags only. Structured or large data belongs in IndexedDB.

**Why.** Storage can be blocked, full or evicted. localStorage is synchronous, so a large value read at startup blocks input.

**Test.** Static: every localStorage or sessionStorage use is inside a try block, and no JSON.stringify value is stored in localStorage.

#### NW-DAT-004: Device storage is rebuildable; first-run state never depends on Safari

`Level 2` `MUST` `process, manual`

Irreplaceable data MUST live on the host, and every byte on the device (Cache, IndexedDB, localStorage) MUST be treatable as a cache or a short outbox. Setup and first-run state MUST NOT depend on Safari, because the Home Screen app does not share storage with it.

**Why.** WebKit says the Home Screen app and Safari keep separate storage by design (bug 181849). Script-writable storage in a Safari tab is cleared after 7 days without interaction; installed apps are exempt from that cap, but treat that as a bonus, not a promise. Nothing was found on what deleting and re-adding the icon does.

**Test.** Process: delete and re-add the icon on a test phone; nothing important is lost. Set a value in Safari, install, and confirm the app does not see it.

**Sources.** https://webkit.org/tracking-prevention/, https://bugs.webkit.org/show_bug.cgi?id=181849, https://webkit.org/blog/14403/updates-to-storage-policy/

#### NW-DAT-005: A conflict rule is written down before offline writes ship

`Level 3` `SHOULD` `process, manual`

Each record type with offline writes SHOULD have one documented conflict rule: last write wins with a version check, or reject with 409 and show the server copy.

**Why.** Two devices can edit the same item while one is offline. An If-Match precondition turns a silent overwrite into a prompt, which matches the rule that writes confirm.

**Test.** Process: edit one record on two devices with one offline; on reconnect the offline one shows a conflict.

### Interface behaviour (UIX)

#### NW-UIX-001: Writes confirm, with specific wording

`Level 2` `MUST` `static, automated`

Before any send, merge, delete or outward-facing action the app MUST show a confirmation that names the object and the consequence, with outcome-labelled buttons and focus on the safe choice. A reversible action SHOULD offer Undo instead.

**Why.** Reads are free; writes confirm. Nielsen Norman Group: undo is the stronger safeguard, generic 'Are you sure?' dialogs train click-through, and the safe choice must not be the default Yes.

**Test.** Static: if the app sends writes, it uses a dialog element with showModal or a confirm call. Not applicable otherwise. Device: DEV-007.

**Sources.** https://www.nngroup.com/articles/confirmation-dialog/

#### NW-UIX-002: Every view has loading, empty, error and stale states

`Level 2` `MUST` `device, manual`

Every view MUST render an explicit loading state, an empty state, an error state with a Retry control, and a stale state that shows the age of cached data. A container MUST never be left empty.

**Why.** A blank list is indistinguishable from a bug. The honest-offline goal needs 'server unreachable, showing data from 14:02'.

**Test.** Device or browser: go offline, return an empty list, return a 500, and delay the answer 10 seconds; each shows its own state.

#### NW-UIX-003: Every screen below the first has an in-app Back

`Level 2` `MUST` `device, manual`

Every screen below the first MUST have a visible Back control in the app's own header, and any history.pushState use MUST match it.

**Why.** An installed iOS app has no browser back button. Whether an edge-swipe back gesture exists in installed apps on iOS 26 is not documented in any source read.

**Test.** Device: open a detail view; Back and the edge swipe agree and neither exits the app.

#### NW-UIX-004: The running version is visible

`Level 2` `SHOULD` `static, automated`

The app SHOULD show the shell version where a person can read it, and the worker SHOULD report the same string.

**Why.** iOS Home Screen apps are reported to keep old content after a deploy, and the fastest way to tell stale from fresh on a phone is a visible version. It also lets support say 'you should see v7'.

**Test.** Static: index.html has an element with id version, or the JavaScript writes one. Device: it equals the VERSION in sw.js.

### Accessibility (ACC)

#### NW-ACC-001: Zoom is never disabled

`Level 1` `MUST` `static, automated`

The viewport meta MUST NOT contain user-scalable=no, user-scalable=0, maximum-scale or minimum-scale.

**Why.** WCAG 1.4.4 requires text to resize to 200 percent. WebKit has ignored these keys since iOS 10, so on iPhone the tag does nothing and only fails the audit; elsewhere it blocks zoom. The input-zoom problem is solved by NW-SHL-005, not by this tag.

**Test.** Static: parse the viewport meta.

**Sources.** https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html, https://webkit.org/blog/7367/new-interaction-behaviors-in-ios-10/

#### NW-ACC-002: Language, title, one h1 and a main landmark

`Level 1` `MUST` `static, automated`

index.html MUST set the html lang attribute, a non-empty title, exactly one h1 and a main landmark.

**Why.** WCAG 3.1.1, 2.4.2 and 1.3.1. Screen readers choose a voice from lang, and landmarks let people skip to the content.

**Test.** Static: parse index.html.

**Sources.** https://www.w3.org/TR/WCAG22/

#### NW-ACC-003: Every control has a name and every image has alt

`Level 1` `MUST` `static, automated`

Every button, link, input, select and textarea MUST have an accessible name from text, aria-label, aria-labelledby or a label element, and every img MUST have an alt attribute.

**Why.** WCAG 4.1.2 and 1.1.1. A title attribute alone is not reliable on touch. Use native elements first: no ARIA is better than bad ARIA.

**Test.** Static: parse index.html. Dynamically created controls need the same care; verify them with axe or VoiceOver.

**Sources.** https://www.w3.org/WAI/ARIA/apg/practices/read-me-first/

#### NW-ACC-004: A visible focus style

`Level 2` `MUST` `static, automated`

The CSS MUST style :focus-visible with an outline of at least 2px that contrasts 3:1 with its surroundings, and MUST NOT remove outlines without replacing them.

**Why.** WCAG 2.4.7 and 1.4.11. A keyboard or switch user on an iPad or iPhone has no other cue.

**Test.** Static: a :focus-visible rule with an outline exists; no outline: none without one. Device: Tab through the app with a hardware keyboard.

**Sources.** https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html

#### NW-ACC-005: Fixed bars never hide the focused control

`Level 2` `SHOULD` `static, automated`

A scrolling region under a fixed header or tab bar SHOULD set scroll-padding equal to the bars' height.

**Why.** WCAG 2.4.11 (new in 2.2): a focused component must not be entirely hidden by a sticky bar.

**Test.** Static: scroll-padding or scroll-margin exists in the CSS.

#### NW-ACC-006: Status changes are announced

`Level 2` `MUST` `static, automated`

A banner or toast that appears without receiving focus MUST sit in an element with role status, role alert or aria-live, present in the markup before its text changes.

**Why.** WCAG 4.1.3. A live region that is inserted or unhidden together with its content is often not announced, so keep the container present and change its text.

**Test.** Static: every element that looks like a banner or toast has a live role. Device: VoiceOver on, switch the host off; the message is spoken without moving focus.

**Sources.** https://www.w3.org/TR/WCAG22/

#### NW-ACC-007: Reduced motion is honoured

`Level 2` `MUST` `static, automated`

If the CSS animates or transitions anything, it MUST also contain a prefers-reduced-motion rule that removes the non-essential motion.

**Why.** Large scaling and panning can trigger vestibular disorders. The query is Baseline widely available.

**Test.** Static: if animation or transition appears, a prefers-reduced-motion media query exists. Not applicable otherwise.

**Sources.** https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion

#### NW-ACC-008: The colour scheme is declared

`Level 2` `SHOULD` `static, automated`

The app SHOULD declare color-scheme in a meta tag and in CSS, and SHOULD ship a palette for every scheme it declares.

**Why.** Native controls and scrollbars follow color-scheme. An empty light-mode stub that declares nothing leaves form controls mismatched.

**Test.** Static: both declarations exist, and if light is declared a prefers-color-scheme rule has content.

**Sources.** https://webkit.org/blog/15865/webkit-features-in-safari-18-0/

#### NW-ACC-009: Navigation has a name and exposes the active item

`Level 2` `MUST` `static, automated`

A nav landmark MUST have an aria-label, and the active tab or view MUST be exposed with aria-current, aria-selected or aria-pressed, not by colour alone.

**Why.** WCAG 1.4.1 and 4.1.2. A tab bar where the active state is only a colour class is invisible to a screen reader.

**Test.** Static: nav has aria-label; the markup or the JavaScript sets aria-current, aria-selected or aria-pressed.

#### NW-ACC-010: Declared text colours meet contrast

`Level 2` `MUST` `static, automated`

Every CSS rule that sets both a text colour and a background MUST give a contrast ratio of at least 4.5:1 (3:1 for text of 24px, or 18.66px bold, and larger).

**Why.** WCAG 1.4.3. The checker only sees pairs declared in the same rule, so axe on the running app (NW-ACC-011) covers the rest.

**Test.** Static: resolve colours and custom properties, compute the WCAG ratio.

**Sources.** https://www.w3.org/TR/WCAG22/

#### NW-ACC-011: Touch targets are at least 44px

`Level 2` `MUST` `device, manual`

Every tappable control MUST be at least 44x44 CSS px including padding, with 8px between neighbours, and never below the WCAG 2.2 floor of 24x24 px.

**Why.** Apple's figure is 44 points (secondary sources agree; the HIG page did not load for the researcher). WCAG 2.5.8 sets 24px with exceptions. Design to the larger number, audit to the smaller.

**Test.** Device or DevTools: measure each control; run axe, which has a target-size rule.

**Sources.** https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html

#### NW-ACC-012: A VoiceOver walkthrough, with Larger Text and Reduce Motion

`Level 3` `MUST` `device, manual`

Before a Level 3 claim, a person MUST walk through every screen with VoiceOver on an iPhone with the app installed, with Larger Text at its maximum, Reduce Motion on and Increase Contrast on, and record the result.

**Why.** Automated tools find only a minority of WCAG problems. Live regions and focus behave differently per platform.

**Test.** Device: Settings, Accessibility. Swipe through every control; each has a name and role; operate each by double-tap; trigger an error and a toast; record in device-test.md.

#### NW-ACC-013: Font sizes are relative, so Larger Text works

`Level 3` `SHOULD` `static, automated`

Font sizes SHOULD be in rem or em, with the root following the system text size, instead of fixed px values.

**Why.** Fixed px sizes ignore the reader's text-size setting. The font: -apple-system-body mechanism for Dynamic Type is from memory and unverified in installed apps, so test it on a device.

**Test.** Static: most font-size declarations are not px.

### Performance (PER)

#### NW-PER-001: A small first-load budget

`Level 2` `SHOULD` `static, automated`

The shell (HTML, CSS and JavaScript together) SHOULD stay under 170 KB uncompressed, JavaScript under 100 KB, and the precache list at 12 files or fewer.

**Why.** web.dev's budget is 170 KB compressed for the critical path and a time to interactive of 5 seconds on baseline phones. The 100 KB and 12-file figures are this standard's recommendation, not a published number. A no-build app should sit far below.

**Test.** Static: sum the sizes of the HTML, CSS and JS files in public/.

**Sources.** https://web.dev/articles/performance-budgets-101

#### NW-PER-002: Scripts do not block rendering

`Level 2` `SHOULD` `static, automated`

Scripts SHOULD load with defer or type=module, or sit at the end of body, and index.html SHOULD NOT preload anything except a late-discovered main image.

**Why.** Render-blocking scripts delay the first paint. Preloading everything dilutes priority.

**Test.** Static: every script element has defer or type=module, or follows the main content.

**Sources.** https://web.dev/articles/optimize-lcp

#### NW-PER-003: System fonts, sized images

`Level 2` `SHOULD` `static, automated`

The app SHOULD use the system font stack. A custom face SHOULD be a self-hosted WOFF2 with font-display, and every img SHOULD have width and height.

**Why.** A web font is a render and layout-shift risk and one more file the service worker must precache. Reserved image space prevents layout shift.

**Test.** Static: no @font-face from another origin; each @font-face has font-display; each img has width and height.

#### NW-PER-004: Core Web Vitals are measured on a real phone

`Level 3` `MUST` `device, manual`

Before a Level 3 claim the app MUST be measured on a real phone and meet LCP of 2.5 s or less, INP of 200 ms or less and CLS of 0.1 or less, and the numbers MUST be recorded.

**Why.** These are the current good thresholds at the 75th percentile. LCP and CLS are Chromium APIs, so measure in Chrome DevTools with 4x CPU throttling and judge feel in Safari.

**Test.** Device: Chrome DevTools Performance with throttling; Safari Web Inspector timelines on the phone.

**Sources.** https://web.dev/articles/vitals, https://web.dev/articles/inp

### Documentation and evidence (DOC)

#### NW-DOC-001: Every iOS-quirk CSS rule carries a WHY comment

`Level 2` `MUST` `static, automated`

Every CSS declaration that exists for a platform quirk (safe-area insets, overscroll-behavior, touch-action, user-select, text-size-adjust, tap-highlight, overflow-scrolling) MUST have a comment containing WHY on the same line or in the preceding four lines.

**Why.** Someone will delete an unexplained rule, and then wonder six months later why dragging highlights text.

**Test.** Static: for each such declaration, look back four lines for a comment with WHY.

#### NW-DOC-002: AGENTS.md tells an AI agent how to work in the app

`Level 2` `SHOULD` `static, automated`

The app SHOULD have an AGENTS.md that states the conformance level, the check command, the hard constraints, and what needs a human.

**Why.** agents.md is a plain Markdown format read by many coding agents. A short file beats an agent guessing the rules.

**Test.** Static: AGENTS.md exists and mentions nixweb check.

**Sources.** https://agents.md

#### NW-DOC-003: A conformance claim is published

`Level 3` `MUST` `static, automated`

A Level 3 app MUST contain a CONFORMANCE.md that names the standard and edition, the level, the date, the tester, the rules marked not applicable with a reason, and any exceptions.

**Why.** A claim is only worth something if it names an edition and can be re-checked. Claims are self-attested unless a third party signs.

**Test.** Static: CONFORMANCE.md has non-empty Standard, Level, Date and Tester lines.

#### NW-DOC-004: A real-device test is on record

`Level 3` `MUST` `static, automated`

A Level 3 app MUST contain a device-test.md with the device model, the iOS version, the date, the tester and a result for each device rule.

**Why.** Add to Home Screen, safe areas, the keyboard and offline launch can only be verified on a phone. Remote debugging needs a Mac (Safari Web Inspector); from Linux, a fleet Mac is the practical inspector host.

**Test.** Static: device-test.md has non-empty iOS, Device, Date and Tester lines.

**Sources.** https://webkit.org/web-inspector/enabling-web-inspector/

#### NW-DOC-005: A change log is kept

`Level 3` `SHOULD` `static, automated`

The app SHOULD keep a CHANGELOG.md or CHANGE.log with a dated line for each release.

**Why.** It answers 'what did I ship and when' and ties a deployed VERSION to a change.

**Test.** Static: the file exists and is not empty.

### Device verification (DEV)

#### NW-DEV-001: Installed on a real iPhone and opens as its own app

`Level 1` `MUST` `device, manual`

The app MUST be added to the Home Screen of a real iPhone and open standalone, with its own icon, its own name and no browser bar.

**Why.** Nothing else proves the install path. WebKit states a qualifying site opens as a standalone web app no matter which browser added it (iOS 16.4 and later), and on iOS 26 the user can turn Open as Web App off in the Add to Home Screen sheet. Test from Safari first.

**Test.** Device: Share, Add to Home Screen with Open as Web App on. The icon is your artwork, the app has its own App Switcher entry, and standalone detection reports true.

**Sources.** https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/, https://webkit.org/blog/17333/webkit-features-for-safari-26-0/

#### NW-DEV-002: Offline launch shows the app and says so honestly

`Level 2` `MUST` `device, manual`

With the host stopped and the app force-quit, launching it MUST paint the shell within about a second, show cached data, and show a banner that says the server is unreachable with the time of the last good contact and a Retry control.

**Why.** This is the product promise: your app with your message, not Safari's error page.

**Test.** Device: stop the server, force-quit the app, launch it. Repeat with Tailscale switched off on the phone.

#### NW-DEV-003: Safe areas and the keyboard work on a real phone

`Level 2` `MUST` `device, manual`

On a notched iPhone, in portrait and landscape, the header and tab bar MUST clear the notch, the Dynamic Island and the home indicator, and a focused input MUST stay visible with the keyboard open and the layout MUST recover when it closes.

**Why.** The simulator can look right while the phone clips the top row. The status-bar and keyboard behaviour on iOS 26 has open WebKit bugs.

**Test.** Device: rotate; focus an input in the lower half; dismiss the keyboard three times.

#### NW-DEV-004: The update flow works end to end

`Level 2` `MUST` `device, manual`

With the app installed and open, deploying a new version MUST produce an update prompt, one reload on acceptance, and a changed version string.

**Why.** iOS update timing for installed apps is unverified in the sources read, so only a device test can say.

**Test.** Device: install version 1, deploy version 2, background and reopen the app, tap the prompt.

#### NW-DEV-005: External links are tested and recorded

`Level 2` `MUST` `device, manual`

The result of tapping an external link in the installed app MUST be recorded for the target iOS version, and the app MUST offer a Copy link action for anything that has to reach Safari.

**Why.** Secondary sources say out-of-scope links open in an in-app sheet, not Safari. The earlier docs said Safari. No primary source was found, so test it.

**Test.** Device: tap an external link; note whether it opens a sheet with a Done button or leaves the app; app state must survive.

#### NW-DEV-006: Permission prompts appear only after a tap

`Level 2` `MUST` `device, manual`

If the app uses notifications, the microphone, the camera or location, the system prompt MUST appear only after the user taps an explicit control, and the app MUST explain when a feature needs the Home Screen install.

**Why.** WebKit requires a user gesture for the notification prompt, and Web Push and badging work only in an installed app. A prompt on load wastes the one chance.

**Test.** Device: fresh install shows no prompt until the control is tapped. Not applicable if the app uses none of them.

**Sources.** https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/

#### NW-DEV-007: Write flows are exercised

`Level 2` `MUST` `device, manual`

If the app sends writes, each MUST be tried on a phone: the confirmation wording, Undo, and an offline write that replays once after reconnecting without duplicating.

**Why.** Confirm and replay logic only fails under real network loss.

**Test.** Device: airplane mode, perform a write, restore the network, confirm exactly one result. Not applicable if the app sends no writes.

#### NW-DEV-008: Android Chrome install is checked when Android is claimed

`Level 3` `SHOULD` `device, manual`

If the app claims Android support, it SHOULD be installed from Chrome on a real Android phone and checked in the DevTools Application panel with no installability errors.

**Why.** Chromium's installability and maskable-icon rules differ from Safari's. Lighthouse no longer scores PWAs, so use the DevTools Manifest panel.

**Test.** Device: Chrome menu, Install app; DevTools, Application, Manifest shows no errors.

#### NW-DEV-009: An idle-storage test

`Level 3` `MAY` `device, manual`

A Level 3 app MAY record what an installed copy keeps after 8 to 10 days unused.

**Why.** No 2026 source was found on real iOS eviction for installed apps. WebKit says Home Screen apps are exempt from the 7-day cap, and a test is the only evidence.

**Test.** Device: leave an installed copy unused for 8 to 10 days on a spare phone, then open it offline.


## Appendix A. Running the checker

```bash
nixweb check mytool                      # Level 2, the default
nixweb check mytool --level 3 --manual   # everything, and list what needs a person
nixweb check mytool --url https://HOST.TAILNET.ts.net:8731   # also test the HTTPS edge
nixweb check mytool --json               # for CI
nixweb standard --list --level 1         # the rules, without running anything
```

`nixweb check` starts the app's own `server.py` on a free loopback port, probes it, and stops it. It never touches the tailnet unless you pass `--url`. It needs only the Python standard library: it is written for Python 3.8 or newer and was tested on 3.14. The exit status is 0 with no failures and 1 with any. `--strict` also fails on recommendations and unverified rules. `--target URL` runs the runtime rules against a server that is already running, which is how an app with a server written in another language is checked.

The checker reads the app with a real HTML parser, not a text search, so a comment cannot satisfy a rule. It decodes the icon files and fails on one that is a single flat colour. It copies the app to a temporary folder, plants files that must never be served, and starts the server on the copy.

Tools outside the checker never change its result. Lighthouse gives performance and accessibility scores (its PWA category was removed in version 12, so it cannot score installability). axe or pa11y find a share of accessibility problems, and the Nu HTML Checker validates markup. Chrome DevTools, Application, Manifest shows installability errors. Playwright's WebKit build approximates Safari but is not Safari, and cannot reproduce Add to Home Screen. Remote debugging a real iPhone needs Safari Web Inspector on a Mac.

## Appendix B. Waivers

A rule that scans lines of code can be waived on one line with a comment on the same or the previous line:

    // nixweb-allow: NW-SEC-007 the sanitiser output is inserted here

Waivers exist for NW-NET-003, NW-SEC-006, NW-SEC-007, NW-IOS-002 and NW-OFF-011. A waiver without a reason is a defect. Every waiver is a SHOULD-style exception and belongs in `CONFORMANCE.md` too.

## Appendix C. Deliberately not required

- **HSTS.** It is keyed on the host name, covers every port, and is close to irreversible, so one experiment on another port can lock a host to HTTPS for a year. Tailscale does not add it. Leave it out unless you have decided.
- **Cross-Origin-Resource-Policy.** It can stop the operating system fetching the Home Screen icon, and that is not verified on a device. The template sends Cross-Origin-Opener-Policy only.
- **Splash screens.** iOS builds none from the manifest, and matching images per device are dozens of files. Paint the page background in the app's colour instead (NW-INS-007).
- **Manifest orientation, screenshots, shortcuts, display_override.** Chromium features. iOS ignores or does not document them. The layout must survive rotation anyway.
- **A Lighthouse PWA score.** The category no longer exists.
- **beforeinstallprompt.** iOS has no install prompt. The template shows instructions instead.
- **A login.** A tailnet-only app has none. The tailnet is the lock, and the Host and cross-site guards keep a web page in the phone's browser from using it.

## Appendix D. Things that used to be true

These claims circulate, and each was true once or is half true. Each was checked on 2026-10-11 against a primary source, which the rule that depends on it cites.

1. *Other iOS browsers open the Home Screen icon inside themselves.* WebKit says a qualifying site opens as a standalone web app no matter which browser added it, from iOS 16.4. Earlier editions of this project said the opposite.
2. *Without apple-touch-icon iOS screenshots your page.* Manifest icons have been used since iOS 15.4, and since 16.4 iOS draws a monogram.
3. *user-scalable=no stops zoom on iPhone.* WebKit has ignored it since iOS 10.
4. *Wake Lock does not work in an installed iOS app.* It did not from 16.4 to 18.3. It does from 18.4.
5. *An iPhone app needs a manifest and a service worker.* On iOS 26 every site added to the Home Screen opens as a web app, and the user can turn that off.
6. *tailscale serve only allows ports 443, 8443 and 10000.* Those are the Funnel ports. The Serve documentation lists no range.
7. *A private tailnet needs no CSRF protection.* The attacker is a web page open in a browser on the tailnet.
8. *Safari deletes all PWA data after 7 days.* That is script-writable storage in a browser tab. Installed Home Screen apps are exempt.
9. *Background Sync works everywhere.* It is not in Safari.
10. *display-mode: standalone is true in an installed iOS app.* The compatibility data records fullscreen instead (WebKit bug 264218).
11. *Parse the user agent for the iOS version.* Safari 26 reports a frozen version.
12. *black-translucent reliably draws under the status bar.* It regressed on iOS 26.1 (WebKit bug 301994, reopened 2026-08-04).
13. *iOS limits storage to 50 MB.* Since Safari 17 an origin may use up to 60 percent of the disk.
14. *sw.js needs a version query to avoid the HTTP cache.* The spec default fetches the main script past it. The real risks are imported scripts and precaching other files (NW-OFF-007).
15. *HTTPS inside a tailnet is for encryption.* WireGuard already encrypts. It is for the secure context that service workers, Wake Lock, the microphone and push require.
16. *Tailnet host names are private.* Issuing a certificate writes the name to public Certificate Transparency logs.

## Appendix E. Open questions

These could not be confirmed from a primary source in this edition and need a device. They are flagged in the rules that depend on them.

- How soon an installed iOS 26 app picks up a new service worker, and what real eviction looks like for an installed app.
- Whether Cross-Origin-Resource-Policy blocks the icon fetch (so it is omitted).
- Whether a font-size under 16px is exactly what triggers input zoom, from WebKit rather than from secondary sources.
- Whether `font: -apple-system-body` makes installed apps follow Larger Text.
- What an external link does in an installed app: an in-app sheet, as secondary sources say, or Safari.
- Whether the microphone permission prompts again on each launch of an installed app.
- Whether an edge-swipe back gesture exists in installed apps on iOS 26.
- What iOS 26.x does with the theme-color meta in an installed app.
- Whether touch-action on the root element stops the keyboard appearing (one secondary report).
- Whether tailscale serve compresses an uncompressed response. It passes a compressed one through unchanged.
- The 44 point figure in Apple's Human Interface Guidelines, whose page did not load for the researcher.

## Appendix F. How this edition was verified

- **Sources.** Each rule's Why cites the primary source it rests on and flags what only a secondary source supported. Researched on 2026-10-11 against the WebKit blog and Apple release notes, MDN, W3C, web.dev, OWASP and Tailscale's documentation.
- **The tailnet edge.** Checked on Tailscale 1.102.3 with a throwaway server that echoed its request headers: serve preserves Host, adds X-Forwarded-For, X-Forwarded-Host and X-Forwarded-Proto, and replaces a spoofed Tailscale-User-Login with the real one.
- **The template meets its own standard.** `nixweb check` on the template finds no failures at Level 2. At Level 3 it fails only the three rules that need evidence a template cannot have: a conformance claim, a device record and a change log.
- **The checker can fail.** `standard/selftest.py` breaks a copy of the template once for each automated rule, except the two that need a host unit or a tailnet, and requires the rule to notice. It passes. The first version of `nixweb check` was a grep that passed a template shipping `user-scalable=no`, which is why this test exists. Run it after any change to the rules or the template.
- **A real browser.** The template was loaded in Chromium under its own Content-Security-Policy with no unexpected errors. The service worker installed and cached the shell, a deployed new version produced the update prompt and switched on a tap, and with the server stopped the app launched from cache and said it could not reach the host.
- **Not verified.** Nothing here has been run on a physical iPhone, on Android, or under `nixweb install`. Appendix E lists what only a phone can answer.

## Appendix G. Edition history

- **1.0.0** (2026-10-11). First edition. 105 rules: 34 at Level 1, 60 added at Level 2, 11 added at Level 3.
