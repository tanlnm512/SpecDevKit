# Changelog — spec-shape

Release history. The skill begins life 2026-10-11 as the authoring
middle phase of the split spec suite (spec-to-prod-split): gated intake
over a validated intent, the authoring waves to the approve handoff —
execution is spec-execute's, intake spec-intent's.

## 0.1.0 — 2026-10-11

- Birth: `SKILL.md` playbook (`graph.py --span shape` — intake gate,
  survey, plan ∥ tech ∥ qa, tasks, verify, hard stop at approve),
  the `spec-shape` router command, and the docset `templates/`.
- The thin `/spec-to-prod` one-release alias router lives here
  (`commands/extra.txt` claims the bare name; D-006) mapping verbs to
  the three successors — the monolith's full router is deleted in the
  same change.
- The authoring cases (E1–E3-class) move here from the monolith's
  `evals/cases.md`, naming spec-shape.
- Engine surfaces (the shared core, the `--span shape` intake gate)
  ship byte-identical from the master at this skill's `scripts/`.

Migration: none — new skill; the monolith retires in the same
release (FR-009). The skill installs by existing (its SKILL.md)
once the manifest surfaces regenerate; `/spec-to-prod` now routes
through this skill's thin alias, and the authoring verbs answer
here instead of the monolith.
