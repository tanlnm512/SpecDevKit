---
description: Spec intake verb - /spec-idea <name> runs spec-intent: scout + grill the idea into a validated intent.md before any docset exists
argument-hint: <new-spec-name>
skills: spec-intent
---

Run the spec-intent skill (auto-mounted) for this request: $ARGUMENTS

`/spec-idea <name>` is the intake verb of the suite's split form: given an
idea name, run the spec-intent skill —

- scaffold-lite `specs/<name>/intent.md` from the skill's own
  template (the one file intake writes; no docset skeleton),
- scout-probe the repo (facts first — never the user's job), baseline
  at HEAD,
- grill the frontier in rounds until empty (the non-answer rule hard
  stops; recommended answers are never adopted silently),
- gate: `scripts/check.py specs/<name> --intent-only` exits 0, Status
  flips to validated,
- name the next step: `/spec-gen <name>` — docset authoring and
  execution are not this command's.
