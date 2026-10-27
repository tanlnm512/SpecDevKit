# Changelog — spec-shape

Release history. The skill begins life 2026-10-11 as the authoring
middle phase of the split spec suite (spec-to-prod-split): gated intake
over a validated intent, the authoring waves to the approve handoff —
execution is spec-execute's, intake spec-intent's.

## Unreleased

- sync no longer deploys skills to `~/.zcode/skills/` (D-047): zcode
  discovers them through the `~/.agents` compatibility root it also
  scans — the native copy only duplicated every skill in its list.
- A delivered docset is historical: intent-baseline staleness becomes
  a visible SKIPPED note once task.md/spec.md records its
  `Delivered: commit @` line (D-046) — a green delivery no longer
  turns its own gate red (observed live in the 2026-10-27 eval pass).
- Engine test suites (`test_graph`, `test_check`, `test_specstate`)
  live here only (D-045).
- Each spec skill ships only its span's archetypes; this skill drops
  `builder.md`, and § Engineering rules have one builder carrier
  (D-044).
- Contract review at the approve stop: `reviewer-contract.md` is
  prepared when approve is READY (D-043); SKILL.md gains a generated
  spawn table, drift-checked against `graph.py`.
- Engineering rules move to the builder brief; briefs lose the retired
  spec-to-prod wording and gain the intent lens on the scout (D-042).
- spec-gen drafts spec.md from a green intent (D-041): the intake →
  shape handoff no longer exits 4; `verify RED` exits 1; `scaffold.sh
  --into-existing`; the node table's `{done}` cells render.

- `/spec-shape` → `/spec-gen` and the `/spec-to-prod` alias is
  removed early (D-006): eleven commands install; a skill may name
  no self-titled command. Migration: re-run `bash tools/sync.sh`.

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
