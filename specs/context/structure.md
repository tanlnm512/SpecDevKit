# Repo structure — SpecDevKit

**Baseline**: 0.1.0 @ 98fa893d4018592624c23f8fcf0b7e3855fe3989
First survey of this repo; re-surveys read this file first and re-survey
only the delta. All skills are self-contained by packaging — content used
by several skills is duplicated on purpose and pinned by tests
(`tools/tests/test_parity.py`); spec-design, spec-build, and spec-define
ship byte-identical copies of the shared engine scripts (see tech.md
conventions).

## area: skills — lifecycle commands

- `skills/spec-discover/` — pre-spec front door; three-lens panel over
  `contracts/panel.md`; output `brainstorms/<name>.md`.
- `skills/spec-define/` — intake; writes `specs/<name>/intent.md` only
  (one file, with the `**Type**` header set from the ask); references
  `references/grilling.md`.
- `skills/spec-design/` — authoring to the approve gate. Scripts:
  `scripts/scaffold.sh` (docset skeleton + INDEX registration),
  `scripts/check.py` (the mechanical gate, parity master for the docset
  discipline), `scripts/freeze.py` (approval freeze, parity master),
  `scripts/graph.py` (`--emit-spawns`/`--run`/`--next` — payload
  assembly + the workflow graph), `scripts/index.py` (the one writer of
  `specs/INDEX.md` lines), `scripts/contract.py` (SKILL.md node table),
  `scripts/specstate.py` (doc-state parser), `scripts/telemetry.py`.
  Templates in `templates/` (spec.md, spec-tiny.md, plan.md, tech-spec.md,
  task.md, test.md, survey.md, research.md, constitution.md). Lenses in
  `protocol/lenses.md`; briefs in `agents/`; ADRs in `decisions/`.
- `skills/spec-build/` — execution engine. Owns the runtime-only scripts
  `scripts/tick.py` (tick commits + `--park`), `scripts/audit.py` (proofs,
  dod gates, `regression`, `archived`), `scripts/archive.sh` + 
  `scripts/retro.py` (archive + retrospective), `scripts/migrate.py`
  (docset header migration), `scripts/gate.sh` + `gate_helpers.py`
  (repo checks runner, pinned copy used by audit's regression gate);
  carries byte-identical copies of the shared engine (check.py, freeze.py,
  graph.py, index.py, contract.py, specstate.py, telemetry.py). SKILL.md
  carries the delivery-pass (ship) and fix-round protocol prose.
- `skills/spec-ship/` — PR integration (`Shipped:` record, notes/ship.md).
- `skills/spec-release/` — release cutting; `scripts/release.py` (collect,
  changelog/release-notes rendering, `LEVEL_BY_TYPE`/`GROUP_BY_TYPE`),
  `scripts/skill-dir.sh`.
- `skills/spec-review/` — standalone review; `scripts/review_orchestrator.py`
  (the shared review oracle), `scripts/gate.sh` (mechanical gate).

## area: agent surface

- `skills/<name>/agents/*.md` — briefs; frontmatter-stripped body is the
  system prompt. Five suite archetypes (analyst, architect, tester,
  developer, auditor) byte-shared across the trio; outward phases add
  integrator (spec-ship) and release-manager (spec-release); spec-discover
  and spec-review carry their own panelists.
- Root `agents/` — generated views of the briefs (`tools/agent-defs.py`);
  regenerate-only.

## area: shared rules

- `rules/engineering-rules.md` — kit-wide engineering rules, canonical;
  injected into spec-build's developer/auditor briefs by
  `tools/kit-rules.py`.
- `GLOSSARY.md` — shared language, canonical-home routing.
- `specs/CONSTITUTION.md` — cross-spec non-negotiables, filled with the
  user at scaffold time.
- `specs/INDEX.md` — one line per spec, rendered by spec-design
  `scripts/index.py` only.

## area: specs (doc state)

- `specs/<name>/` — the doc-set: spec.md, plan.md, tech-spec.md, task.md,
  test.md, survey.md, research.md (+ intent.md intake, spawns/ payloads,
  notes/, approvals/ once frozen). `specs/context/` — cross-spec memory
  (this file, tech.md; `decisions.md` appears when archive.sh first rolls
  up a retro). `specs/archive/` — archived specs (created on first
  archive). `specs/BACKLOG.md` — parked work (created on first park).
- One live spec: `specs/loop-ready-docset/` (draft · feature · full).

## area: tools

- `tools/sync.sh` — the one install pipeline to harness roots
  (`--check` verifies); refreshes generated surfaces before install.
- `tools/agent-defs.py` — root `agents/` generation.
- `tools/plugin-manifest.py` — plugin.json/marketplace.json generation.
- `tools/kit-rules.py` — `§ Engineering rules` injection.
- `tools/drift-check.py` — generated-surface drift (contract, manifests,
  kit-rules, parity, diagrams, examples, personas).
- `tools/parity.py`, `tools/ownership.py`, `tools/evals.py`,
  `tools/grade.py` — test-time validators.
- `tools/tests/` — tooling suite (`run.sh`).

## area: entry points

- Skill commands: `/spec-discover`, `/spec-define`, `/spec-design`,
  `/spec-build`, `/spec-review`, `/spec-ship`, `/spec-release`
  (spec-build verbs: implement, audit, ship).
- Per-skill self-checks: `skills/<name>/tests/run.sh`;
  `python3 skills/spec-design/scripts/check.py <spec-dir> --repo <root>`.
- Repo gates: `tools/drift-check.py`, `bash tools/sync.sh --check`.
