# NixWeb 1.0.0 conformance checklist

App: ____________   Level claimed: ___   Date: ________   Tester: ____________   Device and iOS: ____________

Run `nixweb check APP --level N` first. It ticks the automated rules for you. The boxes below are for you to tick:
automated rules once the command passes them, manual rules once you have done them on a phone.

## Level 1: Installable

### Architecture
- [ ] **NW-ARC-001** MUST (automated) No build step, no framework, no package manager
- [ ] **NW-ARC-002** MUST (automated) One public folder, one server file beside it

### Network and hosting
- [ ] **NW-NET-001** MUST (automated) The server binds loopback by default and refuses anything else
- [ ] **NW-NET-002** MUST (automated) The listening socket is loopback only
- [ ] **NW-NET-003** MUST (automated) Nothing in the app starts tailscale funnel

### Server
- [ ] **NW-SRV-001** MUST (automated) Dotfiles, server source, repository and environment paths return 404
- [ ] **NW-SRV-002** MUST (automated) /ping answers fast, is never cached, and answers HEAD
- [ ] **NW-SRV-003** MUST (automated) Path traversal fails, including encoded forms
- [ ] **NW-SRV-004** MUST (automated) Correct MIME types
- [ ] **NW-SRV-005** MUST (automated) The server publishes public/ and nothing else, and never lists a directory

### Security and privacy
- [ ] **NW-SEC-006** MUST (automated) No third-party origins, no trackers
- [ ] **NW-SEC-007** MUST (automated) No code-injection sinks
- [ ] **NW-SEC-009** MUST (automated) No secrets in served files

### Installability
- [ ] **NW-INS-001** MUST (automated) A valid manifest is linked
- [ ] **NW-INS-002** MUST (automated) Required manifest members
- [ ] **NW-INS-003** MUST (automated) A stable id, and a start_url inside scope
- [ ] **NW-INS-004** MUST (automated) Complete, real, non-blank icons
- [ ] **NW-INS-005** MUST (automated) apple-touch-icon is declared, 180x180 and opaque
- [ ] **NW-INS-006** MUST (automated) The Apple and Chromium app meta tags
- [ ] **NW-INS-007** MUST (automated) Theme and background colours agree, and the first frame is not white

### Shell and layout
- [ ] **NW-SHL-001** MUST (automated) The viewport meta
- [ ] **NW-SHL-002** MUST (automated) Safe-area insets are added to real padding, on all four sides
- [ ] **NW-SHL-003** MUST (automated) The page never scrolls; lists scroll in their own box
- [ ] **NW-SHL-004** MUST (automated) The shell is sized with 100% or dvh, never 100vh
- [ ] **NW-SHL-005** MUST (automated) Form controls render at 16px or larger
- [ ] **NW-SHL-006** MUST (automated) touch-action: manipulation on controls, never on html or body

### iOS platform behaviour
- [ ] **NW-IOS-001** MUST (automated) Install state is detected three ways

### Offline and resilience
- [ ] **NW-OFF-001** MUST (automated) A service worker handles install, activate and fetch
- [ ] **NW-OFF-002** MUST (automated) Versioned caches; old ones deleted by prefix
- [ ] **NW-OFF-003** MUST (automated) Every precached URL exists

### Accessibility
- [ ] **NW-ACC-001** MUST (automated) Zoom is never disabled
- [ ] **NW-ACC-002** MUST (automated) Language, title, one h1 and a main landmark
- [ ] **NW-ACC-003** MUST (automated) Every control has a name and every image has alt

### Device verification
- [ ] **NW-DEV-001** MUST (manual) Installed on a real iPhone and opens as its own app
  - Device: Share, Add to Home Screen with Open as Web App on. The icon is your artwork, the app has its own App Switcher entry, and standalone detection reports true.

## Level 2: Dependable

### Architecture
- [ ] **NW-ARC-003** MUST (automated) Vendored third-party code is recorded

### Network and hosting
- [ ] **NW-NET-004** SHOULD (automated) The service comes back after a reboot
- [ ] **NW-NET-005** SHOULD (manual) Host and port are final before anyone installs; machine names carry nothing sensitive
  - Process: the README states the origin and the manifest id; a crt.sh search for the hostname shows nothing you mind being public.

### Server
- [ ] **NW-SRV-006** MUST (automated) Files without a content hash always revalidate
- [ ] **NW-SRV-007** MUST (automated) Errors and headers leak nothing
- [ ] **NW-SRV-008** SHOULD (automated) Conditional requests and compression
- [ ] **NW-SRV-009** SHOULD (automated) Byte ranges
- [ ] **NW-SRV-010** SHOULD (automated) Clean exit on SIGTERM
- [ ] **NW-SRV-011** MUST (automated) Request size and time are bounded

### Security and privacy
- [ ] **NW-SEC-001** MUST (automated) A strict Content-Security-Policy is sent as a header
- [ ] **NW-SEC-002** MUST (automated) Companion security headers on every response
- [ ] **NW-SEC-003** MUST (automated) Host header allowlist, against DNS rebinding
- [ ] **NW-SEC-004** MUST (automated) State-changing requests refuse cross-site origins
- [ ] **NW-SEC-005** MUST (automated) No CORS
- [ ] **NW-SEC-008** MUST (automated) No inline script, handlers or styles

### Installability
- [ ] **NW-INS-008** SHOULD (automated) The status bar style is a deliberate choice

### Shell and layout
- [ ] **NW-SHL-007** SHOULD (automated) Chrome is unselectable, content is selectable
- [ ] **NW-SHL-008** SHOULD (automated) Text size is locked against landscape inflation and the system font is used
- [ ] **NW-SHL-009** SHOULD (automated) Phone-number auto-linking is switched off
- [ ] **NW-SHL-010** SHOULD (automated) Text-entry screens follow the visual viewport

### iOS platform behaviour
- [ ] **NW-IOS-002** MUST (automated) No user-agent sniffing for the OS version
- [ ] **NW-IOS-003** MUST (automated) Lifecycle events, not unload
- [ ] **NW-IOS-004** MUST (automated) Platform APIs are feature-detected and degrade

### Offline and resilience
- [ ] **NW-OFF-004** MUST (automated) Only same-origin GET is cached, and /ping never
- [ ] **NW-OFF-005** MUST (automated) Only good responses are cached
- [ ] **NW-OFF-006** MUST (automated) The shell is the fallback for navigations only
- [ ] **NW-OFF-007** MUST (automated) Precaching reads past the HTTP cache
- [ ] **NW-OFF-008** MUST (automated) Registration sets updateViaCache to none
- [ ] **NW-OFF-009** SHOULD (automated) Updates are user-gated
- [ ] **NW-OFF-010** MUST (automated) Reachability is probed, not guessed
- [ ] **NW-OFF-011** MUST (automated) Every fetch has a timeout
- [ ] **NW-OFF-012** MUST (automated) Errors paint a screen, never a blank page
- [ ] **NW-OFF-013** SHOULD (automated) Runtime caching of API data is bounded and private-aware

### Data and storage
- [ ] **NW-DAT-001** MUST (automated) Offline writes queue in IndexedDB and replay from the open page
- [ ] **NW-DAT-002** MUST (automated) Every replayable write carries an idempotency key
- [ ] **NW-DAT-003** SHOULD (automated) Storage use is guarded and small
- [ ] **NW-DAT-004** MUST (manual) Device storage is rebuildable; first-run state never depends on Safari
  - Process: delete and re-add the icon on a test phone; nothing important is lost. Set a value in Safari, install, and confirm the app does not see it.

### Interface behaviour
- [ ] **NW-UIX-001** MUST (automated) Writes confirm, with specific wording
- [ ] **NW-UIX-002** MUST (manual) Every view has loading, empty, error and stale states
  - Device or browser: go offline, return an empty list, return a 500, and delay the answer 10 seconds; each shows its own state.
- [ ] **NW-UIX-003** MUST (manual) Every screen below the first has an in-app Back
  - Device: open a detail view; Back and the edge swipe agree and neither exits the app.
- [ ] **NW-UIX-004** SHOULD (automated) The running version is visible

### Accessibility
- [ ] **NW-ACC-004** MUST (automated) A visible focus style
- [ ] **NW-ACC-005** SHOULD (automated) Fixed bars never hide the focused control
- [ ] **NW-ACC-006** MUST (automated) Status changes are announced
- [ ] **NW-ACC-007** MUST (automated) Reduced motion is honoured
- [ ] **NW-ACC-008** SHOULD (automated) The colour scheme is declared
- [ ] **NW-ACC-009** MUST (automated) Navigation has a name and exposes the active item
- [ ] **NW-ACC-010** MUST (automated) Declared text colours meet contrast
- [ ] **NW-ACC-011** MUST (manual) Touch targets are at least 44px
  - Device or DevTools: measure each control; run axe, which has a target-size rule.

### Performance
- [ ] **NW-PER-001** SHOULD (automated) A small first-load budget
- [ ] **NW-PER-002** SHOULD (automated) Scripts do not block rendering
- [ ] **NW-PER-003** SHOULD (automated) System fonts, sized images

### Documentation and evidence
- [ ] **NW-DOC-001** MUST (automated) Every iOS-quirk CSS rule carries a WHY comment
- [ ] **NW-DOC-002** SHOULD (automated) AGENTS.md tells an AI agent how to work in the app

### Device verification
- [ ] **NW-DEV-002** MUST (manual) Offline launch shows the app and says so honestly
  - Device: stop the server, force-quit the app, launch it. Repeat with Tailscale switched off on the phone.
- [ ] **NW-DEV-003** MUST (manual) Safe areas and the keyboard work on a real phone
  - Device: rotate; focus an input in the lower half; dismiss the keyboard three times.
- [ ] **NW-DEV-004** MUST (manual) The update flow works end to end
  - Device: install version 1, deploy version 2, background and reopen the app, tap the prompt.
- [ ] **NW-DEV-005** MUST (manual) External links are tested and recorded
  - Device: tap an external link; note whether it opens a sheet with a Done button or leaves the app; app state must survive.
- [ ] **NW-DEV-006** MUST (manual) Permission prompts appear only after a tap
  - Device: fresh install shows no prompt until the control is tapped. Not applicable if the app uses none of them.
- [ ] **NW-DEV-007** MUST (manual) Write flows are exercised
  - Device: airplane mode, perform a write, restore the network, confirm exactly one result. Not applicable if the app sends no writes.

## Level 3: Exemplary

### Network and hosting
- [ ] **NW-NET-006** SHOULD (manual) A grant narrows who can reach the app when the tailnet is shared
  - Process: in the admin console, Access controls, test access from a device that must be denied; tailscale ping and curl from it time out.
- [ ] **NW-NET-007** SHOULD (automated) The tailnet HTTPS edge delivers what loopback does

### Data and storage
- [ ] **NW-DAT-005** SHOULD (manual) A conflict rule is written down before offline writes ship
  - Process: edit one record on two devices with one offline; on reconnect the offline one shows a conflict.

### Accessibility
- [ ] **NW-ACC-012** MUST (manual) A VoiceOver walkthrough, with Larger Text and Reduce Motion
  - Device: Settings, Accessibility. Swipe through every control; each has a name and role; operate each by double-tap; trigger an error and a toast; record in device-test.md.
- [ ] **NW-ACC-013** SHOULD (automated) Font sizes are relative, so Larger Text works

### Performance
- [ ] **NW-PER-004** MUST (manual) Core Web Vitals are measured on a real phone
  - Device: Chrome DevTools Performance with throttling; Safari Web Inspector timelines on the phone.

### Documentation and evidence
- [ ] **NW-DOC-003** MUST (automated) A conformance claim is published
- [ ] **NW-DOC-004** MUST (automated) A real-device test is on record
- [ ] **NW-DOC-005** SHOULD (automated) A change log is kept

### Device verification
- [ ] **NW-DEV-008** SHOULD (manual) Android Chrome install is checked when Android is claimed
  - Device: Chrome menu, Install app; DevTools, Application, Manifest shows no errors.
- [ ] **NW-DEV-009** MAY (manual) An idle-storage test
  - Device: leave an installed copy unused for 8 to 10 days on a spare phone, then open it offline.

