# Factory Droid: spec mode & mission mode (the Droid adaptation)

Droid-specific guidance for running spec-to-prod under Droid's Spec
Mode and Mission Mode. Kept out of SKILL.md deliberately: every other
harness runs the main playbook unchanged, and only Droid splits a
session's capability by mode (Spec Mode is hard read-only) and splits
orchestration from workers (subagents cannot spawn subagents). Nothing
here changes the workflow graph, the doc state, or any gate — this file
maps Droid's session modes onto the same graph.

## What's installed (per tools/sync.sh)

- Role droids: `~/.factory/droids/spec-{surveyor,researcher,planner,
  tech,qa,task-breaker,implementer,reviewer}.md` — Task-tool
  `subagent_type` targets, `model: inherit` always, briefs verbatim.
- The skill: `~/.agents/skills/spec-to-prod/` (Droid's personal
  compatibility root) — SKILL.md playbook, scripts, templates.
- Lifecycle commands: `~/.factory/commands/{spec,plan,build,test,
  review,ship,spec-to-prod}.md` — installed only when `~/.factory`
  exists (never fabricated; loud skip otherwise).

## Model tiering: Task complexity, not frontmatter

Droid defs pin `model: inherit` by design — a guessed Factory model ID
is a DroidValidator load error waiting to happen, and D-012's
data-driven derivation has nothing Droid-shaped to derive. Cost tiers
ride the Task call's `complexity` argument, resolved by your
complexity-to-model routing in `/settings`. This is the Droid
equivalent of omp's `@smol` tiering (D-012/D-016):

| Role | `complexity` | Why |
|------|--------------|-----|
| spec-surveyor | `light` | cheap tier (D-016) |
| spec-researcher | `light` | cheap tier (D-016) |
| spec-task-breaker | `light` | cheap tier (D-016) |
| spec-implementer | `light` | cheap tier (D-016); fix rounds 4–5 escalate |
| spec-planner | (omit) | judgment authoring — session model |
| spec-tech | (omit) | judgment authoring — session model |
| spec-qa | (omit) | judgment authoring — session model |
| spec-reviewer | (omit) | adversarial judgment is the deliverable (D-012) |

The light tier mirrors the briefs' own `model:` frontmatter — the same
signal omp-defs.py reads. If your routing leaves `light` on Inherit,
the tiering is a no-op and every role runs on the session model.

## Spec Mode = the authoring phase, on paper only

Droid Spec Mode is hard read-only — no file writes, no commits, and
spawned subagents clamp to read-only and low-risk shell too. The
pipeline's first writes (scaffold.sh, spec.md) therefore cannot happen
in Spec Mode, and no wave can run there. The constraint lands on the
one phase that was always human-owned anyway (SKILL.md § Authoring the
spec: intent is human, never generated):

- In Spec Mode, derive the draft spec.md in-conversation (per
  `templates/spec.md`), run the clarify loop as plan-review rounds
  (batched frontier rounds of the draft's gaps — D-009's shape, minus
  the on-disk markers), and decide the researcher gate (run/skip) in
  the same conversation.
- The ExitSpecMode plan carries the full spec.md draft verbatim, the
  researcher-gate decision (real research.md content, or the byte-exact
  skip-marker line), and the execution outline.
- On approval, in Normal mode: `scripts/scaffold.sh <name>`, write the
  drafted spec.md exactly as approved, write research.md, then run the
  graph from the frontier (survey ∥ research, then plan ∥ tech ∥ qa,
  then tasks, verify, before-audit).
- The two approvals stay distinct. ExitSpecMode approves *authoring*;
  the pipeline's own approve gate (after the before-audit) still gates
  *execution*. Never let a Spec Mode approval write `Status: approved`.

## Mission Mode = the orchestrator session runs the graph

A mission worker is a subagent, and subagents cannot spawn subagents —
the Task tool is not available to them — so a worker cannot run a wave,
ever. Only the session holding Task can: the mission orchestrator.

- Feature = `specs/<name>`. During mission planning, fill
  `references/mission-brief.md` (features → specs, milestones →
  frontier bands) and author each spec via Spec Mode (section above).
- Milestones are frontier bands; `graph.py --state-json` is the
  milestone-progress oracle (done / READY / blocked per node).
- The orchestrator spawns role waves itself (SKILL.md § Spawn
  mechanics). Mission workers get no spec-to-prod feature work:
  a worker can read the playbook but cannot spawn the roles the
  playbook schedules — delegating a feature to one silently degrades
  it to playbook-less solo work.
- Human gates are mission pause points: clarify (in Spec Mode),
  research-gate, approve, closing-audit judgment, tick-commit. In an
  interactive Mission Control session, unblock by conversation. Under
  headless `droid exec --mission` the pipeline parks at the gate by
  design — doc state is the only state, so any later session resumes
  from the frontier losslessly.
- Mission validation: set `missionModelSettings.skipScrutiny` and
  `skipUserTesting` for spec-to-prod features. The closing audit + DoD
  scorecard already govern verification, and mission QA carries no FR
  traceability or TC pass conditions — running it on top double-pays
  for weaker evidence. Keeping them as an outer check is the
  orchestrator's judgment call, not a default.
- Parallel execute across specs is fine (disjoint `specs/<name>/`
  dirs, disjoint files); each spec's own fix-round frontier stays
  inside its own graph.
