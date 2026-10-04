# kit-level-up — design specification

> Handoff artifact of a spec-brainstorming run. Pre-spec by
> design: it records the chosen direction and the reasoning, not
> requirements. The next step is `/spec kit-level-up` with this doc
> as intent input; requirements shaping happens there, with the user.

**Status**: handoff-ready · **Date**: 2026-10-03 ·
**Direction**: blend — Minimalist baseline first, Visionary dogfood
loop second, Cynic scoping throughout

## Direction

The owner asked to "level up all skills, agents, workflows" along
three axes (fill the skill folder structure with value; apply
dynamic-workflow concepts to agents; mine GitHub best practices for
the workflows). The panel converged — all three lenses independently
named live executed evals as the missing substrate — and the owner
accepted the recommended blend with "yes": **run the already-written
evals live once (baseline), then institutionalize the dogfood loop,
then build each axis only where the baseline proves it dirty.**

- Selected: the three-phase blend. Phase 0 — execute evals E1–E4
  (spec-code-review) and the brainstorm cases live, zero new code;
  the results are the baseline every later claim is measured
  against. Phase 1 — make the loop routine: recorded transcripts
  in-repo and a minimal stdlib runner so re-running a case is one
  command. Phase 2 — the three axes build only where the baseline
  shows dirt, and every increment names the eval case it serves.
- Rationale (the orchestrator's recommendation, confirmed by the
  owner): all three lenses agreed nothing can currently show an
  upgrade made the skills *better* — E1–E4 have never run live
  (`skills/spec-code-review/observations/open-items.md` item 5) —
  so the axes would otherwise be vibes; the baseline is hours, not
  sprints; and the cairn→0.13.0 mining loop already proved one
  live run pays for itself.
- Rejected: **pure Cynic** (build nothing new) — daily use already
  proves the skills run; it strands the compounding loop and keeps
  "trust me" as the only evidence. **Visionary-first** (build the
  eval harness before one honest run) — risks its own watch
  condition: improvising to finish the first run, which collapses
  the self-proving thesis. **Axis-1-as-driver** (filling folder
  slots) — inventory, not value, until a baseline says which slot
  is load-bearing; the repo's own records mark some absences
  intentional.

## Problem Statement

- The owner levels the kit up in one-off pushes (today: mining the
  cairn fix-audit into 0.13.0) and cannot tell whether any upgrade
  made the skills better — the eval cases are written but have
  never executed live, so every improvement claim is untested.
- Current workaround: daily real use plus static test suites
  (mechanics covered, panel orchestration not) and occasional
  dogfood runs that leave no recorded artifact.
- Cost of the status quo: improvement effort is spent blind (the
  next axis might have no fuel), the shelved backlog (fix fan-out,
  per-repo config, incremental re-review) cannot be prioritized by
  evidence, and a consumer evaluating the kit sees claims without
  receipts.

## User Personas

### Persona 1 — the hands-off delegator

- Who: the kit's owner, running all three skills daily across
  zcode, Claude Code, omp and gemini; delegates wholesale
  ("làm hết") and wants recommendations, not options.
- Needs: one number that says whether a change helped, and bounded
  increments they can approve without reading diffs all day.
- Failed by: no baseline exists — upgrades land on trust; the open
  items list cannot be ranked by evidence.

### Persona 2 — the checkout consumer

- Who: someone installing the kit from a repository checkout onto
  their own machine harnesses.
- Needs: reason to trust that the skills do what SKILL.md claims
  before adopting them into their own delegation habits.
- Failed by: the repo ships tests and contracts but no recorded
  live-run evidence; peers (superpowers' drill harness, wshobson's
  plugin-eval) execute their skills and publish the results.

## Core MVP Features

1. Live baseline run — serves the hands-off delegator. Execute
   evals E1–E4 (`skills/spec-code-review/evals/cases.md`, seeded
   fixture in `examples/review-target/`) and the brainstorm cases
   once, live, and judge each against its written pass criteria.
2. One-command re-run — serves the hands-off delegator. A minimal
   stdlib-only runner (or documented command per case) so any case
   re-executes as one command; no new runtime dependencies.
3. Recorded-run surface — serves both personas. Every live run
   leaves a transcript/result in the repo (under each skill's
   `evals/` or `observations/`, benchmarks corpus later) so future
   changes ship with before/after receipts.
4. The scoping rule as kit process — serves the hands-off
   delegator. Every future kit increment names the eval case it
   serves; increments without one don't merge.

**Out of scope (day-one cut list)**: axis-2 build (workflow
concepts — artifacts-as-contracts, per-agent budgets, mechanical
independence — injected into agent briefs) until a live run shows
an orchestration failure a brief would fix; axis-3 workflow rewrite
(journal-then-replay durability, typed I/O contracts for the
dialect twins) until the baseline shows flakiness, cost blowouts or
unresumable runs; folder-filling as a driver of work; un-shelving
increment 2 (fix fan-out, batched verification, opt-in committer)
until a live run shows the fix loop drowning in findings; per-repo
config and PR comment-back stay parked (open items 2–4); release
surfaces (version-bump automation, validate CLI, changelog
machines) until after the loop exists.

## Potential Risk Mitigations

| Risk (from the panel) | Early warning | Mitigation or acceptance |
|---|---|---|
| Fatal assumption: "unfilled folder structure = missing value" drives the work | An increment merges scoped by folder structure rather than by the eval case it serves | Axis-1-as-driver rejected at selection; the scoping rule (MVP 4) blocks structure work with no served eval case |
| Axis 2 collides with C-03 (harness-neutral core): every application becomes another hand-maintained dialect twin, and re-unverifies fresh wins (0.13.0) | Orchestration-"concept" talk reappears before a baseline number exists | Axis 2 blocked until a live run shows an orchestration failure a brief would fix; then it enters as one increment with its own ADR |
| Hidden cost: every new surface charges permanent regenerate/drift/parity rent on one hands-off owner; the real backlog starves | Two consecutive surface merges with no recorded eval run between them | Bounded increments; receipts (MVP 3) make review cheap; the parked backlog re-enters only through the same scoping rule — accepted, not dropped |
| The self-proving thesis needs a live run to complete inside the skill's own contracts (Visionary's watch) | The first E1 attempt requires bending a skill rule to finish | See kill criteria — that failure downgrades the thesis to fixture-only evals and re-scopes the program |
| The whole cut assumes daily use ≠ validation (Minimalist's watch) | The owner disputes that assumption when the baseline is proposed | The baseline run itself tests it: if nothing measurable improves, the program still ends with the runner and receipts — accepted downside |
| Evidence-pack opinions imported from maintenance-mode upstreams (autogen) get pinned by drift-check | A stolen pattern enters the kit citing a maintenance-mode repo as its reason | Steals enter only through a dirt-showing baseline and carry their own ADR, not upstream's authority |

**Kill criteria**: (1) an eval case cannot complete on a real
repository inside the skill's own contracts without improvisation —
the self-proving thesis is dead; record the failure, fall back to
fixture-only evals, re-scope to the axes directly. (2) Two
consecutive increments merge without naming a served eval case —
stop the program; surface is outrunning evidence. (3) The baseline
comes back clean and later runs stay clean — the program ends
successfully having delivered baseline + runner + receipts; axes
1–3 had no fuel and that is the finding.

---

*Next step: `/spec kit-level-up` — treat this doc as intent input. The
commit is the user's.*
