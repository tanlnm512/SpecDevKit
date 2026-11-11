---
description: Spec intake - /spec-intake <name> scouts + grills the idea into a validated intent.md before any docset exists
argument-hint: <new-spec-name>
skills: spec-intake
---

Run the spec-intake skill (auto-mounted) for this request: $ARGUMENTS

`/spec-intake <name>` is the intake verb of the suite's split form: given an
idea name, run the spec-intake skill —

- scaffold-lite `specs/<name>/intent.md` from the skill's own
  template (the one file intake writes; no docset skeleton),
- scout-probe the repo (facts first — never the user's job), baseline
  at HEAD,
- grill the frontier in rounds until empty (the non-answer rule hard
  stops; recommended answers are never adopted silently),
- gate: `scripts/check.py specs/<name> --intent-only` exits 0 — the
  green gate is the validation,
- name the next step: `/spec-author <name>` — docset authoring and
  execution are not this command's.
