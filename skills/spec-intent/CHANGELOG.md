# Changelog — spec-intent

Release history. The skill begins life 2026-10-11 as the intake front
door of the split spec suite (spec-to-prod-split): repo scouting +
requirement grilling to a validated `specs/<name>/intent.md`, hard
stop — the docset is spec-shape's, execution spec-execute's.

## Unreleased

- The mini-spec example ships its green `intent.md` — the package's
  own-type artifact, gated by `check.py --intent-only` (staleness
  SKIPPED: the example's baseline commit is not a repo ancestor).

- A delivered docset is historical: the staleness refusal becomes a
  SKIPPED note once the docset records `Delivered: commit @`
  (spec-shape D-046, shipped in this skill's engine replica).
- The scout brief states its package scope: a package ships only its
  span's lens sections (D-044) — lens names the brief mentions that
  this package does not carry are never spawned.

- Grilling gains a failure-patterns scan — nine draft phrasings
  (vague verbs, missing acceptance criteria, assumed prior
  knowledge, vague aesthetics, no boundary) and the frontier
  question each becomes; facts behind a row stay the runner's
  job. Serves eval case I1. Adapted from nidhinjs/prompt-master
  (reviewed 2026-10-24).

- Replica engine suites removed; spec-shape owns them (spec-shape
  D-045).
- `agents/` ships the scout alone — the only archetype the intent
  span spawns (D-020).
- D-019: grilling rounds ride the harness's structured question
  tool where one exists — options as the choices, ➡️ first,
  split-never-truncate across the tool's per-call cap; the printed
  ❓ round stays the universal form and D-018's non-answer hard
  stop is unchanged.
- `/spec` → `/spec-idea` (D-003): the intake command renames; the
  skill name, scripts, and flow are unchanged. Migration: re-run
  `bash tools/sync.sh` — the stale prune removes the old `spec.md`
  from every root.

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
