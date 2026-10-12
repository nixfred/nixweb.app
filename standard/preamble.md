# {{TITLE}}

**Edition {{EDITION}}, {{DATE}}.** {{TOTAL}} rules in three levels. {{AUTO}} are checked by a program and {{MANUAL}} need a person holding a phone.

## 1. What this is

This standard describes a phone app that is a plain web app: HTML, CSS and one JavaScript file, served by a small local server, put on a private network by `tailscale serve`, and added to the Home Screen of an iPhone. Android comes second. There is no Xcode, no App Store, no review and no build step.

It says what a correct one looks like, why each rule exists, and how to check it. Every rule has a stable ID, a requirement word, a reason and a test. A program, `nixweb check`, runs the tests a program can run, and a checklist covers the rest.

It exists because the failures are quiet. A page without `viewport-fit` looks right in a simulator and clips on the phone. A service worker that fails to install says nothing. A server that lists its own folder hands `.git` to everyone on the tailnet and nothing looks wrong. People copying an app do not see these, so the standard and the checker see them for them.

## 2. Who it is for

Anyone building this kind of app, including an AI coding agent working from a prompt. An agent should read `AGENTS.md` in the template, run `nixweb check`, and treat a failing MUST as a bug.

It is not a standard for public websites, for apps with accounts, or for apps that need the App Store. The no-login design is a decision about a private network (NW-NET-001 to NW-NET-003), and it stops being right the moment an app is published to the internet.

## 3. Conformance

{{LEVELS}}

Levels are cumulative. Level 1 has {{C1}} rules, Level 2 has {{C2}} and Level 3 has {{C3}}.

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

{{PRINCIPLES}}

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
