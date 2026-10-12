# Ten web apps worth building

Every one of these is a **phone front end onto something that already exists** on a desk machine, a
laptop, a Mac or a VPS. None of them needs a new backend. That is the point: the hard part is already built and sitting
on a machine you own, and the only thing missing is a way to reach it from the sofa, the car or a
coffee shop.

Ranked by how much the phone actually adds. An app that is better at the desk does not belong here.

---

## 1. Burn Bar Pocket
**Source:** `~/Projects/burnbar` (Omarchy plugin, already computes all of this)

Banked, on-pace and time-to-reset across Claude, Codex, Grok and Kimi, on one screen.

**Why the phone:** the single most useful number Fred owns is "how hard can I burn right now", and
today it only exists on a desktop bar. The decision it drives (start the big job, or wait for the
reset) usually gets made away from the desk.

**Serve from:** the machine the plugin runs on. **Hardest bit:** the quota readers are already there; the work is one JSON
endpoint and a layout that reads at a glance in sunlight.
**Phone-only win:** a Home Screen icon that is red when you are behind pace.

---

## 2. herdr Remote
**Source:** `~/Projects/herdr` (0.9 fleet, `herdr --machine <label>` already works cross-host)

The attention queue: which agent sessions on which hosts are waiting on a human, sorted by who has
been blocked longest. Tap one, read the last 40 lines, send a prompt back.

**Why the phone:** this is the killer one. Agents block on a question and then idle for an hour
because nobody is at the keyboard. Unblocking from a phone turns dead time into throughput.

**Serve from:** the machine you work at (it can already reach the others over SSH).
**Hardest bit:** sending a prompt is a write. Confirm before send, and never auto-approve.
**Phone-only win:** answer `AskUserQuestion` prompts from anywhere.

---

## 3. Orca Deck
**Source:** Orca worktrees in `~/Projects/<repo>/fm-*`, plus `gh`

Every open PR and worktree across the fleet, with its CI state, and a merge button that refuses a
failing check.

**Why the phone:** reviewing a diff on a phone is miserable, but *deciding* on a PR you already
reviewed is a ten-second job that currently waits until you are back at a desk.

**Serve from:** the machine that holds the worktrees. **Hardest bit:** an irreversible action behind a thumb. Require the PR to be
green and show the SHA you are merging, exactly as the builder/reviewer loop already does.

---

## 4. Larry Live
**Source:** `~/.claude/bin` Larry Live on :7788, already has a `/fleet` band

Fleet health: which hosts are up, which services are running, what each Larry is doing right now.

**Why the phone:** it is already a web page. This is the cheapest win on the list, an afternoon at
most, and it is the thing you want when something feels wrong and you are not home.

**Serve from:** it already serves. Add the manifest and the icon and it is done.
**Hardest bit:** nothing. Start here if you want to learn the pattern on something real.

---

## 5. Lamplight Remote
**Source:** `~/Projects/lamplight` (single-machine; the Govee lamps are the physical Larry)

Scenes, per-theme playlists, brightness, and the Larry presence colour, from the phone.

**Why the phone:** you adjust lights while standing up, not while sitting at the machine that
controls them. Right now the only control surface is the desk you just walked away from.

**Serve from:** the machine that owns the lights. **Hardest bit:** the bars must never flash, which is a
standing rule; the phone must not become a way around it.

---

## 6. Sonomarchy Remote
**Source:** `~/Projects/sonomarchy` + the pa-dlna Sonos outputs

Pick an output, pick a source, volume, now-playing. A remote for the thing that is already piping
audio to Sonos.

**Why the phone:** this is literally what phones are for, and the existing control lives in a bar
widget on one machine.

**Serve from:** the machine that pipes the audio. **Hardest bit:** the stacked-attenuation trap (silent but playing) should be
visible on the phone, not something you diagnose at the desk afterwards.

---

## 7. Idea Box
**Source:** nothing yet. This is the one to build from scratch.

Hold a button, talk. It transcribes locally, splits one rambling voice dump into separate numbered
items, works out which project each belongs to, flags overlap with something you already logged,
and files each one into the right repo's notes.

**Why the phone:** ideas arrive in the car and in bed. One person who built this reported going to
sleep earlier, because the thought was safely out of their head.

**Serve from:** a machine with a GPU (local Whisper plus GPU classification: this should cost nothing per use).
**Hardest bit:** the classifier. Start with "ask me which project" and only automate once it is
boringly right.

---

## 8. Test Drive Console
**Source:** `~/VMs/test-drive` (`test-drive list|new|push|check|shot`)

The VM lab from the phone: what is running, start a check, and look at the screenshot it took.

**Why the phone:** `shot` produces a PNG you are supposed to actually look at. Looking at a picture
is the one thing a phone is strictly better at than a terminal.

**Serve from:** the machine that runs the VMs. **Hardest bit:** the global lock. The app must show "queued behind another
session" honestly rather than appearing hung, which is the same mistake the CLI already warns about.

---

## 9. Pulse Pocket
**Source:** `~/Projects/pulse` + NVML, the disk/power/RAM plugins

Vitals for your machines: GPU, temps, NVMe health, battery, zram, the iGPU idle draw.

**Why the phone:** you want this exactly when you are *not* at the machine, because the machine is
doing something long and you are wondering whether to worry.

**Serve from:** the desk machine, polling the laptop over the tailnet.
**Hardest bit:** NVMe SMART needs root. Expose one tiny read-only endpoint rather than giving the
web app a sudo path.

---

## 10. Ladder Companion
**Source:** `~/Projects/ladder.nixfred.com` + its D1 database

The consultant's view, not the client's: where every client stands, what is owed to them, what they
owe, and the next session, with a box to log a win the moment it happens.

**Why the phone:** wins and promises happen on calls and in texts, away from the desk, and get lost
because logging them means opening a laptop. A client telling you something is the moment to record
it.

**Serve from:** a VPS, because this one should be up when the laptops are shut.
**Hardest bit:** it writes to the live client database. Draft-then-confirm, never straight-to-write,
and the same Law 18 instinct that keeps email in drafts.

---

## The three rules for picking the next one

1. **The phone must add something the desk cannot.** Mobility, a camera, a thumb, or being away.
   If it is just "the same thing, smaller", skip it.
2. **The backend must already exist.** These are front ends. The moment you are writing a new
   service, you have left this list.
3. **Reads are free, writes need a confirm.** Every app above that can change something real
   (merge, send, start) shows what it is about to do and waits.
