# Spec: dynamic-workflow

**Status**: done            <!-- approved 2026-09-20: the user's explicit
                                "viết spec và làm luôn" instruction in the
                                authoring session is the sign-off this gate
                                records; done 2026-09-20 — rulings report
                                (D-001…D-007) surfaced in-session and acked
                                by the user's commit-then-delete decision;
                                the as-built record lives in git history -->
**Created**: 2026-09-20
**Branch**: none — built in-place on main at the user's request (waived gate 5, D-004)

## What
The skill gains native dynamic-workflow runs on two harnesses: a generated
ZCode workflow script and a generated Claude Code workflow script, each
driving the existing frontier loop (compute the ready wave from doc state,
spawn it, recompute) through that harness's own workflow runtime, plus a
per-harness installer that puts the right dialect in the right place for
each coding agent.

## Why
Today the frontier loop runs only inside an orchestrator session: the
orchestrator reads `graph.py --state-json`, spawns waves by hand, and
re-runs everything on resume. Both major harnesses now ship script-driven
subagent orchestration (zcode dynamic workflows; Claude Code dynamic
workflows since mid-2026), which gives the loop a native surface — phase
graphs, rerun-as-command, resumable runs — without changing a single gate.
Without this, zcode and claude-code users pay the manual-orchestration tax
on every wave, and the skill's own "dynamic state-graph workflow" (ADR-010)
has no dynamic-workflow instantiation on any harness.

## Business value
Users of zcode and Claude Code run a spec's whole graph as one native
command (`spec-run <name>`) instead of hand-spawning every wave; maintainers
regenerate both dialects from one source of truth; other harnesses are
untouched (omp keeps its kernel recipe, Droid its mission mapping).

## User stories
### US1 — Run the graph natively (P1)
As a zcode or Claude Code user, I want to invoke the spec pipeline as a
native workflow command, so that waves spawn automatically with a progress
view and the run resumes from doc state after every human gate.

**Acceptance criteria** (each traces to an FR below):
- AC1: Given an approved spec with a ready wave, When I run the installed
  workflow with the spec name, Then every frontier agent payload is spawned
  as a subagent and the loop recomputes until a human gate.
- AC2: Given a state whose next step is a judgment gate (clarify,
  research-gate undetermined, before-audit, approve, closing-audit,
  tick-commit), When the workflow runs, Then it stops with an
  AWAITING HUMAN message naming the gate and what is needed, and never
  auto-satisfies the gate.

### US2 — Install per coding agent (P1)
As a user of either harness, I want one installer command per coding agent,
so that each harness gets its own dialect installed in its own workflow
root with a working skill_dir baked in.

**Acceptance criteria**:
- AC3: Given a synced skill, When I run the installer for a harness, Then
  that harness's workflow root holds the correct dialect with the resolved
  skill_dir baked in, and the other harness is untouched.
- AC4: Given a harness that is not installed (its home root absent), When
  the installer runs for it, Then it skips loudly and creates nothing.

### US3 — Maintain one source of truth (P2)
As a skill maintainer, I want both dialects generated from one definition,
so that the loop semantics cannot drift between harnesses and hand-edits
are caught mechanically.

**Acceptance criteria**:
- AC5: Given a hand-edited generated file, When the generator's --check
  runs, Then it reports drift and exits nonzero.

## Requirements
- **FR-001**: The system shall generate a ZCode dynamic-workflow dialect
  (`spec-run.dwf.ts`) that drives the frontier loop through the zcode
  workflow facade (typed `agent().ask()`, literal `phase()` names,
  `world.run` invocations of graph.py, a published markdown run summary),
  containing no `import`, `export`, or `declare` statement.
- **FR-002**: The system shall generate a Claude Code dynamic-workflow
  dialect (`spec-run.js`) that drives the same loop through Claude's
  primitives (`export const meta` first statement, `agent(prompt, {label,
  schema})`, `pipeline`, `phase`, `log`), containing no `import` statement
  and no direct filesystem or shell access in the script itself.
- **FR-003**: Both dialects shall mirror `graph.py --run` semantics exactly
  — state from `--state-json`; an AWAITING HUMAN stop at every judgment
  node (clarify, an undetermined research-gate, before-audit, approve, the
  closing-audit judgment, tick-commit); waves spawned from `--emit-spawns`
  payloads parsed from its output lines; and stops on a gate, workflow
  completion, a held state, the wave cap, or a wave that changed no doc
  state.
- **FR-004**: The system shall provide `tools/install-workflow.sh` that
  installs each dialect to its own harness root (zcode →
  `~/.zcode/workflows/` or `<repo>/.zcode/workflows/`; claude →
  `~/.claude/workflows/` or `<repo>/.claude/workflows/`), resolves and
  bakes the target's `skill_dir` into the installed copy, refuses foreign
  destination files via the repo's provenance-ledger discipline, and skips
  loudly (creating nothing) when a user-mode harness home is absent.
- **FR-005**: `tools/sync.sh` shall install and verify the workflow
  dialects for the zcode and claude roots it already manages, gated on
  each harness home existing.
- **FR-006**: Generated workflow files shall be committed regenerate-only
  artifacts with generator `--check` drift detection, and the tools suite
  shall cover generator determinism, per-dialect structural invariants,
  cross-dialect gate parity, and installer behavior (install, foreign
  refusal, drift detection, absent-home skip) under a fake HOME.
- **FR-007**: The skill documentation shall describe the dynamic-workflow
  surface — a SKILL.md run section, README harness-table and install
  entries, ADR-019, and a CHANGELOG entry — released as version 2.7.0 with
  the VERSION/SKILL.md frontmatter pair updated together.

## Scope
**In**: tools/workflow-defs.py (generator, both dialects as committed
artifacts under skills/spec-to-prod/workflows/), tools/install-workflow.sh
(zcode | claude | all; --user default / --project; --skill-dir override;
--check), the sync.sh install+verify wiring, docs (SKILL.md, README,
ADR-019, CHANGELOG, VERSION → 2.7.0), tools/tests/test_workflow_defs.py.
**Out (deferred)**: omp/Droid/Codex workflow dialects (omp keeps the
documented Python-kernel recipe; Droid keeps references/droid-modes.md;
Codex has no comparable runtime — ADR-019 records the criteria for adding
a dialect); per-role model tiering inside workflow runs (both facades lack
a per-spawn model knob today — session model for every role, same as the
existing zcode fallback spawn); running the workflow scripts on a spec
whose authoring (spec node) is still open — that stays a human-held step.

## Assumptions & risks
- Assumption: the zcode saved-workflow metadata block accepts
  `description` / `whenToUse` / `args` (documented fields only; the file
  name carries the workflow name) — chosen because the facade docs list
  exactly those three, and anything undocumented risks a loader error.
- Assumption: a Claude workflow agent may run `python3 …/graph.py` and read
  payload files from the repo root (subagents hold the session's tool
  permissions; the script itself needs no fs/shell by design).
- Risk: either runtime changes its facade (primitives renamed, meta shape)
  — mitigation: dialect invariants are unit-tested (FR-006) and each file
  carries a header naming its target runtime, so a harness change surfaces
  as a loud dialect edit + regenerate, not a silent break.
- Risk: baked `skill_dir` goes stale if the skill is later moved —
  mitigation: `--check` compares installed copies against the currently
  resolved skill_dir, so a re-run of the installer (or sync) repairs it.
