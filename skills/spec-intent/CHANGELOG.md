# Changelog — spec-intent

Release history. The skill begins life 2026-10-11 as the intake front
door of the split spec suite (spec-to-prod-split): repo scouting +
requirement grilling to a validated `specs/<name>/intent.md`, hard
stop — the docset is spec-shape's, execution spec-execute's.

## 0.1.0 — 2026-10-11

- Birth: `SKILL.md` playbook (scaffold-lite → scout → grill → gate →
  handoff), the `templates/intent.md` intake artifact (survey-shaped
  `**Baseline**:` header; Questions carry the grilling vocabulary),
  and the `spec-intent` router command.
- The bare name `spec` claims this skill (`commands/extra.txt` +
  `commands/spec.md` thin wrapper) — the monolith's intake verb
  moves here in the same change; its five lifecycle verbs follow it
  to spec-execute later in the split.
- First eval cases I1–I3 (`evals/cases.md`): raw idea to validated
  intent, the non-answer hard stop, the stale-baseline refusal.
- Engine surfaces (checker `--intent-only` profile, the intent node,
  `--span intent`) ship byte-identical in the shared core; this
  skill's span is `--span intent`.

Migration: none — new skill; the monolith retires in the same
release (FR-009). The skill installs by existing (its SKILL.md)
once the manifest surfaces regenerate; `/spec` now routes to
spec-intent's intake instead of the monolith's DEFINE entry.
