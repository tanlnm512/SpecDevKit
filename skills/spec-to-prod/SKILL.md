---
name: spec-to-prod
description: >-
  Language-agnostic multi-agent pipeline for spec-driven development: orchestrates role sub-agents
  in parallel waves to produce grounded contract files under specs/<name>/ — spec.md, plan.md,
  task.md (the status holder), tech-spec.md, test.md — plus survey.md and research.md as evidence,
  all verified by scripts/check.py. Use when the user asks to run the multi-agent spec pipeline,
  spec out a bugfix (same pipeline with the references/bugfix.md deltas — "spec this bug", "turn
  the login crash into a spec"), spawn or re-run a specific spec role agent ("re-survey the auth
  spec", "refresh the tech spec", "rebuild the task list"), scaffold specs/ for a project, or
  execute an approved task.md through
  implementer agents. Recognise its specs on disk by tech-spec.md + survey.md and the singular
  task.md / test.md names. Invoked as /spec-to-prod <verb> <spec-name>, or as
  the native /spec-run workflow ("run the auth spec pipeline", "continue the
  spec").
metadata:
  owner: platform-core
  version: "2.7.3"
---

# Spec-to-Prod (spec-driven development)

Orchestrate role-specific sub-agents to produce an execution-ready, grounded
doc set per feature. You (the main session) are the **orchestrator**: you own
the spec's intent and the coordination; the agents own depth in their lane.

```text
specs/<name>/
├── spec.md        # WHAT & WHY — business, user stories, FR-###/AC  (orchestrator + user)
├── survey.md      # code-state ground truth — evidence/status/verify  (surveyor)
├── research.md    # external references + options                    (researcher)
├── plan.md        # milestones, dependencies, parallelization map    (planner)
├── tech-spec.md   # architecture, diagram, impact, decisions         (tech)
├── task.md        # phased checkboxes — the ONLY status holder       (task-breaker)
└── test.md        # TC-### business test cases traced to FRs         (qa)
```

The 5 contract files are the deliverable; survey.md/research.md are inputs
that stay for provenance. Traceability chain `FR → T → TC` must be greppable
— `scripts/check.py` enforces it. The full contract — file ownership,
status lifecycle, spawn-payload rules — is canonical in
`contracts/docset.md`.

## Workflow graph (nodes, edges, frontier)

Scheduling is a **dynamic state graph**, not a numbered ladder (ADR-010).
The doc state under `specs/<name>/` is the only state: every node's signal
is derived from it, mechanically, by `scripts/graph.py`. You remain the
judgment layer — gate decisions, brief quality, rulings — never a stage
counter.

```text
spec → clarify? → research-gate? → (research) → survey → plan ∥ tech ∥ qa
     → tasks → verify → before-audit → approve (HUMAN) → execute
     (per-task frontier, fix-round loops ≤5) → closing-audit → tick-commit
     → archive

loop edges:  clarify · fix-round (≤5/task) · re-brief · converge (survey staleness)
```

- **Nodes** — one per role agent (survey, research, plan, tech, qa, tasks,
  execute) plus orchestrator/mechanical nodes (spec, clarify, research-gate,
  verify, before-audit, approve, closing-audit, tick-commit, archive).
  Every node has one mechanical done-signal, read from doc state.
- **Data edges** — a node is *ready* exactly when all of its inputs are
  done; *done* nodes are never re-run (except through a loop edge).
- **Conditional & loop edges** — the researcher gate (below), fix rounds
  (`(fix <n>/5)` per task), re-briefs (orchestrator-driven, on a gap
  digest), converge (survey staleness → survey re-run → `audit.py
  converge` → appended tasks re-enter execute), and the clarify loop (open
  `NEEDS CLARIFICATION` markers hold the frontier until resolved).
- **Frontier** — every node that is ready and not done.

**The scheduling rule**: run the ready frontier as one wave, recompute,
repeat — every agent node in the wave spawned in a single message, so
they run concurrently. Waves, not stages: the frontier may hold one node
or four, and its shape comes from doc state, not from a fixed sequence. The
authoring wave (plan ∥ tech ∥ qa) works because each agent writes a
different file from the same inputs; qa deliberately never reads
tech-spec.md or plan.md (tests from requirements, blind to implementation).
The surveyor self-checks its own survey.md (`check.py --survey-only`)
before returning its digest — a fabricated citation fails there, in the
survey node, not three nodes and three documents later at the closing
audit.

Node states use one vocabulary everywhere (report, `--state-json`, this
doc): `done` · `READY` · `blocked(<reason>)` · `gate:undetermined` ·
`SKIPPED`.

| Node | Ready when | Done when |
|------|------------|-----------|
| `spec` | always (entry) | spec.md filled; no open `NEEDS CLARIFICATION` markers |
| `clarify` | open markers exist | markers resolved (removed/answered in spec.md) |
| `research-gate` | spec done | research.md exists — real content → ran, skip marker → skipped |
| `research` | gate resolved `run` | research.md non-marker, non-empty |
| `survey` | spec done | survey.md filled AND `check.py --survey-only` exits 0 |
| `plan` | spec + survey done | plan.md filled |
| `tech` | spec + survey done AND research resolved (either form) | tech-spec.md filled |
| `qa` | spec + survey done (never reads plan/tech — parallel-safe) | test.md filled |
| `tasks` | plan + tech + survey done | task.md filled |
| `verify` | plan, tech, qa, tasks, survey all done | `check.py <spec-dir>` exits 0 |
| `before-audit` | verify done | `Before-audit: passed @ <sha-or-dash>` recorded in task.md |
| `approve` (HUMAN) | before-audit done | spec.md `Status: approved` (or later) |
| `execute` | approved + before-audit recorded | every task entry ticked `[x]` or struck `~~` |
| `closing-audit` | execute done — 0 todo (digests orchestrator-confirmed) | `audit.py dod` DoD scorecard's mechanical gates pass |
| `tick-commit` | closing-audit done | tasks ticked + burndown consistent; commit step SKIPPED-noted in non-git repos |
| `archive` | tick-commit done AND spec `Status: done` | dir moved to `specs/archive/<date>-<name>/`, INDEX repointed |

The per-task frontier inside `execute`: a task is runnable when it is
`- [ ]`, its `(after T###)` dependencies are all ticked or struck, it is
not at the fix-round cap `(fix 5/5)`, and its intended files are disjoint
from its wave-mates' (the planner's parallelization map, per task). Tasks
at the cap are surfaced for adjudication, never auto-retried.

> **Orientation (non-normative).** The historical Stage 0–4 ladder —
> author the spec · survey ∥ research · plan ∥ tech ∥ qa · task breakdown ·
> verify + before-audit — survives only as the *typical topological order*
> of the graph above: the order a fresh spec's waves usually land in.
> Nothing schedules by stage number. The frontier is the only scheduler,
> and the loop edges (clarify, fix rounds, converge) can send work back
> upstream at any time.

### The researcher gate (a judgment node the graph never decides)

`research-gate` is ready as soon as `spec.md` is done — and its decision
is yours alone. graph.py reports it `gate:undetermined` until research.md
exists, and every auto-trigger pauses there; no tooling ever decides run
or skip. The researcher costs a full spawn (≈15× a solo pass, same as any
agent) — that cost is only justified when there's real uncertainty to
resolve. After deriving research questions from the spec's open technical
choices:

- **≥1 real open question** (a genuine unknown — which library, which
  algorithm, which protocol version): resolve the gate as **run** — the
  researcher joins the analysis wave alongside the surveyor.
- **Zero real open questions** (the approach is already obvious — most
  bugfixes, most single-known-pattern internal changes): resolve as
   **skip**: write research.md containing the line `not applicable — no
   open questions at Stage 0` — exactly that bare line (the detector
   matches the stripped line byte-exact, em dash included; a prefixed
   `research.md:` form reads as real content and the gate resolves "run")
   — in place of the template yourself, so every frontier
  computation can tell "skipped on purpose" apart from "forgotten." The
  analysis wave becomes a solo surveyor spawn.

Manufacturing questions to justify the spawn is the failure mode this gate
exists to prevent.

### graph.py (the mechanical truth you schedule from)

`python3 scripts/graph.py <spec-dir>` reads doc state alone and prints the
workflow graph's live picture — per-node state and reason, the frontier
wave, loop-edge status, the lifecycle `Status:`, task counts, and a git
line (git-derived signals degrade loudly: `SKIPPED (not a git repo)`,
never a silent false result). Modes:

- **Report** (default) — the picture above; work the frontier it prints.
- **`--state-json`** — the same state, machine-readable: nodes with
  state+reason, edges, frontier, loops, counts, git. The oracle for tests
  and validators.
- **`--mermaid`** — the live state graph rendered (solid = data edges,
  dotted = conditional/loop edges).
- **`--explain NODE`** — why one node sits in its current state, plus its
  ready/done conditions; for `execute`, the per-task frontier.
- **`--emit-spawns`** — writes one self-contained spawn payload per
  frontier agent node to `specs/<name>/spawns/wave-<N>/<role>.md`
  (`--wave-dir` overrides the directory): header (spec_dir / repo /
  resolved skill_dir) + the input payload filled from doc state (FR list,
  the task entry verbatim + TC acceptance commands, research questions) +
  the frontmatter-stripped brief body byte-verbatim +
  `_shared-protocol.md` verbatim — **the reviewer is the one exempt role**
  (its brief states it needs no `_shared-protocol.md`). While the
  research-gate is undetermined it also prepares `researcher.md` (spec
  digest + FR list + questions): the instrument of a `run` decision — the
  gate itself is still never decided by tooling, and `--run` still pauses
  before any wave. Wave numbers are state-derived: 1 = analysis (survey ∥
  research), 2 = plan ∥ tech ∥ qa, 3 = tasks, 4+ = execute batches.
  `spawns/` is a derived, regenerate-only artifact dir — safe to delete,
  never read by check.py, never status.
- **`--repair NODE`** — with `--emit-spawns`: also emit one agent node's
  payload when it is not in the frontier — the single-agent repair-run
  instrument (§ Run modes' table). `--repair survey` on a stale baseline
  carries the `DELTA RE-SURVEY` block (§ **Converge**): the converge
  re-survey merged, not rebuilt. Never part of `--run` — a repair run is
  orchestrator-driven by definition.
- **`--run`** — the auto-trigger loop: compute the frontier; **pause with
  `AWAITING HUMAN: <node>: <what is needed>`** at every judgment node;
  run the mechanical verify node (check.py) directly; emit payloads for
  the ready agent wave; invoke `--runner` per payload (a command template
  with `{prompt_file}` `{role}` `{spec_dir}` `{skill_dir}` substituted;
  the default `print` runner echoes the invocation — equivalent to
  `--dry-run` with payloads written); recompute and repeat until a gate,
  workflow completion, `--max-waves`, or a wave that changed nothing.
  **Human gates are never auto-satisfied**: clarify, approve, an
  undetermined research-gate, the closing-audit judgment (including
  rulings), and tick-commit always pause. before-audit pauses the same way
  (same `AWAITING HUMAN:` prefix): it is the orchestrator's six-gate
  judgment, which no script can perform. `--run` itself mutates no doc
  state — only the runner's own effects move the workflow.

## Effort scaling (parallel by default — scale down only with a reason)

Parallel spawning is the DEFAULT at every size; running serial/inline is
the exception that needs justification.

- **Default — small and medium** (≤3 FRs, one area): the graph runs the
  same waves as large — analysis (surveyor ∥ researcher, if the gate above
  says there's real uncertainty), then plan ∥ tech ∥ qa, then
  task-breaker. Depth per agent shrinks (fewer items each), but the wave
  shape holds.
- **Large** (multi-area, gated, research-heavy): the full graph, full
  depth.
- **Inline exception** — the orchestrator works a node itself ONLY when
  the work is a single file with zero unknowns (e.g. one grep-verifiable
  survey item, one-file task execution). Cost honesty: multi-agent ≈15× a
  solo pass — accepted because correctness and wall-clock beat token
  spend; a user's "go cheap/inline" is the override, not the default.

## Spawn mechanics (how to launch a role agent)

1. **Resolve `skill_dir` once per session, before the first spawn.** Check,
   in priority order: omp-native roots first — project
   `.omp/skills/spec-to-prod/`, then `~/.omp/agent/skills/spec-to-prod/`
   — then a project-level `.claude/skills/spec-to-prod/`,
   `.zcode/skills/spec-to-prod/`, or `.agents/skills/spec-to-prod/`, then
   the same three roots under `~` — use whichever exists first
   (`scripts/skill-dir.sh` prints it; in omp, a `/skill:spec-to-prod`
   invocation names its skill directory in the injected prompt — prefer
   that when present). Carry this resolved absolute path in every spawn
   payload below; agent defs and briefs never hardcode one, since the
   same skill can live at a different root on a different machine or
   install, and only the orchestrator's own session can reliably tell
   which root is actually active.
2. **Preferred where the harness supports custom agent types**: spawn with
   `subagent_type: spec-<role>` — one file per role, `agents/spec-*.md`:
   harness frontmatter (tools, readonly, model) on top of the full brief
   body. Install copies where the harness reads agent defs
   (`~/.claude/agents/` on Claude Code). The frontmatter mechanically
   enforces what used to be prose only (e.g. the reviewer physically
   cannot write; no agent can spawn another) — a guarantee that holds only
   where the harness honors agent-def frontmatter; elsewhere the same
   rules ride in the fallback prompt below, enforced by instruction alone.
   omp, opencode, droid, and agy get generated dialects of the same
   briefs (`~/.omp/agent/agents/` and `~/.config/opencode/agents/` and
   `~/.factory/droids/` regenerated by sync; Antigravity reads the
   committed repo-root `agents/` personas); zcode has no agent defs
   and always uses the fallback below.
   Include `skill_dir: <resolved path>` in the prompt — the body points to
   `_shared-protocol.md` relative to that, never a path baked into the
   file itself.
3. **Fallback** (defs not installed, or spawning a generic agent type):
   read `<skill_dir>/agents/spec-<role>.md` and strip its frontmatter —
   the body IS the
   system prompt — and build a self-contained prompt: `<body contents> +
   <skill_dir>/agents/_shared-protocol.md (verbatim — the reviewer is the
   one exempt role: its brief states it needs no `_shared-protocol.md`) +
   input payload (see the body's "Input payload")`. `graph.py
   --emit-spawns` builds exactly this payload from doc state — prefer its
   output as-is (mechanical, byte-verbatim), or use it as the reference
   recipe when you must hand-build one.
4. Either way, spawn the whole wave in one message. On asynchronous
   harnesses the `Agent` call returns an `agentId` immediately and each
   digest arrives as its agent finishes; on synchronous harnesses the same
   single-message batch returns every digest at once — the wave shape is
   identical either way, only when you read the digests differs. Spawns
   are also fresh: no conversation context carries over, so the payload
   must name the spec dir and quote the FR list / research questions. For
   agents producing code or scripts, include the **acceptance-test
   commands** in the payload — agents correct even the orchestrator's own
   mistakes when the tests are in the prompt.
5. Agents **write their artifact to disk** and return only a short digest —
   never pipe file content through the conversation (telephone game). Later
   nodes read the artifacts, not the digests. Each brief defines its exact
   `digest:` shape — make decisions from those fields, not from prose.
6. If an agent reports a gap (e.g. tech needs a citation survey.md lacks),
  re-brief the responsible agent — don't let one agent edit another's file.

## Running under omp (native execution)

Everything above is harness-neutral; omp (Oh My Pi) additionally exposes
primitives worth using directly once `skill_dir` resolves to one of the
`.omp/` roots (§ Spawn mechanics step 1) — this section is the omp-specific
instantiation of that generic prose, not a new set of rules.

- **The wave IS the `task` tool's `tasks[]` array.** One call, one array
  entry per frontier agent, `agent: spec-<role>` (Role table) — this is
  literally step 4's "spawn the whole wave in one message." Put what every
  entry shares (spec dir path, resolved `skill_dir`, repo root) in the
  batch's `context` field once instead of repeating it inside each task's
  own prompt text; each entry's `task` field then carries only what's
  unique to that role (its Input payload — FR list, the task entry
  verbatim, research questions).
- **`outputSchema` mechanically enforces a brief's `digest:` shape** — the
  fields stay exactly what the brief defines (contracts/docset.md's return
  contract is unchanged); the schema is enforcement, not a new contract. A
  harness without schema support runs the identical prose digest
  unaffected. This is the direct fix for anti-pattern #2 (telephone-game
  drift from a malformed digest) wherever the harness offers it.
- **Results auto-deliver — don't poll.** A `task` call returns immediately;
  each digest lands as its agent finishes (step 4's "asynchronous
  harnesses" case, concretely). Keep working the rest of the wave's
  bookkeeping and read digests as they arrive; reach for `hub`'s wait only
  when genuinely blocked with nothing else queued.
- **No peer channel, harness-enforced, not just stated**: the generated omp
  agent defs (`tools/omp-defs.py`) grant no `hub` tool to any `spec-*`
  role, so § Independent spawns' "no peer-to-peer messaging" holds
  structurally under omp, the same shape as the reviewer's read-only
  guarantee.
- **Role tiering rides the generated defs.** Four of the eight roles run
  omp's `@smol` cheap tier — surveyor, researcher, task-breaker,
  implementer (D-012 + D-016) — derived mechanically from each brief's
  own `model:` frontmatter by `tools/omp-defs.py`; reviewer, planner,
  tech, and qa inherit the session model. The implementer's cheap tier
  is what its fix-round ladder's "capability tier up" (rounds 4–5)
  escalates *from* — and the tier-up target is the **default tier**, not
  "a generic agent": omp's `task` model role (what the `task` tool's
  generic subagents resolve through) is itself commonly a fast-tier
  alias — on the reference config it equals `@smol`, making a generic
  spawn a lateral move, not an escalation. The omp-native tier-up is the
  orchestrator working the re-brief inline (its session model is the
  default tier), or an explicit default-tier spawn where the harness
  allows per-spawn model choice.
- **Recompute the frontier in-process, not one subprocess per call.**
  `graph.py`/`check.py`/`audit.py` (over `specstate.py`) are plain
  stdlib-only modules — `check.py`/`audit.py`'s `main(argv=None)` accepts
  args directly (defaulting to `sys.argv` for the CLI path, unchanged).
  The frontier loop's actual hot path is "run the wave, recompute, repeat"
  — a real multi-phase spec pays a fresh `python3 scripts/graph.py` call,
  interpreter start and all, on every single recompute otherwise. Inside
  omp's persistent eval kernel, import once per session and call directly
  for every later recompute:

  ```python
  import sys, importlib.util
  for name in ("specstate", "check", "audit", "graph"):
      spec = importlib.util.spec_from_file_location(
          name, f"{skill_dir}/scripts/{name}.py")
      mod = importlib.util.module_from_spec(spec)
      sys.modules[name] = mod
      spec.loader.exec_module(mod)
  import specstate, check, audit, graph  # cache hits — binds the names
  graph.main(["specs/<name>", "--state-json"])  # or no flag for the report
  ```

  `graph.py`'s own internal probes (survey/verify/closing-audit) keep
  shelling out to check.py/audit.py via `subprocess` regardless — that
  isolates their prints/argv from graph.py's own process, deliberately,
  and stays untouched; this recipe optimizes the orchestrator's own
  repeated top-level calls, the ones the recompute loop actually pays for.
- **`xd://lsp`/`ast_edit` are orchestrator-session devices, not
  automatically a spawned subagent's.** Verified empirically, not
  assumed: a `spec-surveyor` spawned via the `task` tool reports
  `Mounted devices: .` (empty) even though its frontmatter grants
  `write` — device mounting is a separate mechanism from the base tool
  allowlist, and a default spawn gets none. Where the orchestrator's own
  session does have them mounted (as this one does), they're useful for
  its own inline work (§ Effort scaling's single-file exception, or
  spot-checking a citation before re-briefing) — but the
  surveyor/implementer briefs deliberately don't tell the *subagent* to
  reach for them, since a spawned one can't. If a future harness build
  mounts these for task-spawned roles, re-verify with the same probe
  (spawn one, try `write path=xd://lsp`) before trusting the claim
  again — anything less is "inherited numbers laundered as evidence"
  (anti-pattern 9) about tool capability instead of a count.

## Running under Factory Droid (spec & mission modes)

Droid-only adaptation, kept out of this playbook on purpose: Spec Mode
is the authoring phase on paper (subagents clamp read-only), Mission
Mode runs only from an orchestrator session (subagents cannot spawn
subagents), and cost tiers ride the Task `complexity` argument. The
mapping lives in `references/droid-modes.md`; the mission-planning
skeleton is `references/mission-brief.md`. The graph, gates, and doc
state are unchanged.

## Dynamic workflow runs (zcode · claude code)

Where the harness has a script-driven workflow runtime, the frontier
loop has a native instantiation: the generated `spec-run` workflow
(ADR-019) computes the ready wave from doc state, spawns it as
subagents, recomputes, and stops `AWAITING HUMAN` at every judgment
gate — the same loop, gates, and resume contract as this playbook; the
workflow is `graph.py --run`'s runner seam made native, and it decides
nothing the orchestrator wouldn't.

- **Installed per harness** — `~/.zcode/workflows/spec-run.dwf.ts`
  (zcode: run via the harness's workflow surface with
  `{"spec": "<name>"}`) and `~/.claude/workflows/spec-run.js`
  (claude code: `/spec-run` with the spec in args).
  `tools/install-workflow.sh zcode|claude|all` installs one or both
  (`--project` for `<repo>/.<harness>/workflows/`); `tools/sync.sh`
  installs and verifies both where the harness home exists. Each
  installed copy carries its root's own `skill_dir` baked in; a runtime
  `skill_dir` arg overrides it.
- **Sources** — `skills/spec-to-prod/workflows/` are committed
  regenerate-only artifacts of `tools/workflow-defs.py` (its templates
  are the single representation; `--check` catches hand-edits). Never
  edit the generated files; edit the generator and regenerate.
- **Run semantics** — state comes only from `graph.py --state-json`,
  waves from `--emit-spawns` payloads (each subagent reads its payload
  file and writes its artifact to disk); the run stops at a gate
  (clarify · undetermined research-gate · before-audit · approve ·
  closing-audit · tick-commit), on completion, on a held frontier, at
  the wave cap (default 12), or on a no-change wave — answer the gate,
  rerun, and the loop resumes from doc state. The zcode dialect
  publishes a markdown run summary; the claude dialect logs the same
  report. A wave that changed no doc state gets exactly one re-brief
  round for its failed payloads (failure digest verbatim in the retry
  ask; D-020) — rounds 2+ are yours.
- **Cost & unattended levers** (D-020) — staged tiering on zcode:
  launch the analysis waves (survey/research — cheap-tier roles per
  D-016) with the workflow run's subagent-model override on a cheap
  model, and the execute waves at the default; per-role tiering is not
  possible on either facade. Scheduled / off-peak runs: wrap the
  workflow with the harness's scheduler (cron / off-peak queue) — only
  spans with no gate ahead (post-approve) are safe to run unattended;
  the run parks at the closing-audit ack by design. On Claude Code,
  pre-approve the probe's `python3 …/graph.py` command in the project's
  permission rules so mid-wave permission prompts don't stall the run.
- **Limit** — per-role cost tiers do not ride into workflow runs (the
  facades expose no per-spawn model knob); every spawned role runs the
  run's model — per-run tier choice exists on zcode (see the cost
  levers above), per-role does not. The authoring half (spec node +
  clarify loop) stays with you and the user — a workflow run on an
  unauthored spec reports `held` and names why.

## Independent spawns (no cross-agent coordination)

Agents in a wave run fully independently. There is no shared manifest, no
sync log, and no peer-to-peer messaging between them — nothing under
`specs/<name>/` exists for that purpose, and agents are given no
peer-messaging capability with a wave-mate (harness-enforced where agent
defs apply, payload-enforced otherwise). Each agent gets everything it
needs in its own spawn payload (per the brief's "Input payload") and
reports back only its digest; the orchestrator is the only point where
information from one agent can reach another.

If an agent hits something that would affect a wave-mate — a file that
doesn't exist, a premise that's false, a citation another agent's file is
missing — it says so in its own digest (per its brief's "Guardrails"/
"Done when"), never by editing another agent's file or trying to reach it
directly. The orchestrator reads every digest once the wave finishes and
re-briefs whoever needs it (§ Spawn mechanics, step 6).

## Role table

| Agent | File | subagent_type | Type | Readiness (node) | Produces | Loads skill |
|-------|------|---------------|------|------------------|----------|-------------|
| surveyor | `agents/spec-surveyor.md` | `spec-surveyor` | Explore | spec done → survey | survey.md (+ specs/context/ first run) | — (workspace graph/code-intel tool if present) |
| researcher | `agents/spec-researcher.md` | `spec-researcher` | Explore | research-gate resolved `run` → research | research.md | paper-fetch / semanticscholar (if apt) |
| planner | `agents/spec-planner.md` | `spec-planner` | GP | spec + survey done → plan | plan.md | — (workspace graph/code-intel tool if present) |
| tech | `agents/spec-tech.md` | `spec-tech` | GP | spec + survey done AND research resolved (either form) → tech | tech-spec.md | mermaid cheatsheet (vendored) · creating-mermaid-diagrams for image export only |
| qa | `agents/spec-qa.md` | `spec-qa` | GP | spec + survey done → qa (never reads plan/tech) | test.md | web-gui-tester (UI specs), agent-native-design (agent CLIs) |
| task-breaker | `agents/spec-task-breaker.md` | `spec-task-breaker` | GP | plan + tech + survey done → tasks | task.md | — |
| implementer | `agents/spec-implementer.md` | `spec-implementer` | GP | approved + before-audit recorded → execute, per-task frontier | code/tests only | repo's own conventions |
| reviewer | `agents/spec-reviewer.md` | `spec-reviewer` | Explore | never a frontier node — the orchestrator's optional adversarial call during verification | nothing — findings only | — |

defs and briefs are the same file: `agents/spec-*.md` = frontmatter + brief body; install
them where the harness reads agent defs (`~/.claude/agents/` on Claude
Code). Harnesses without user-installable agent types (e.g. ZCode)
use the fallback spawn — same briefs, rules carried in the prompt
(§ Spawn mechanics).

## Lifecycle commands (the addyosmani surface)

Six thin command files — `commands/{spec,plan,build,test,review,ship}.md`
in this package, installed flat into the harness command roots alongside
the router — expose the development lifecycle popularized by
addyosmani/agent-skills. Each delegates into the graph at a node; no new
machinery, contract unchanged:

```text
  DEFINE          PLAN           BUILD          VERIFY         REVIEW          SHIP
 ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐
 │ Idea │ ───▶ │ Spec │ ───▶ │ Code │ ───▶ │ Test │ ───▶ │  QA  │ ───▶ │  Go  │
 │Refine│      │  PRD │      │ Impl │      │Debug │      │ Gate │      │ Live │
 └──────┘      └──────┘      └──────┘      └──────┘      └──────┘      └──────┘
  /spec          /plan          /build        /test         /review       /ship
```

| Command | Graph landing |
|---------|---------------|
| `/spec <name>` | DEFINE — the spec node + clarify loop (the `scaffold` verb; `bugfix` deltas when it's a bug) |
| `/plan <spec>` | PLAN — run waves from current doc state through verify + before-audit to the approve gate |
| `/build <spec> [T###]` | BUILD — the execute node (the `implement` verb): implementer waves, no ticks, no commits |
| `/test <spec>` | VERIFY — closing-audit steps 9–10: `audit.py proofs --run` + regression gate; requires execute done |
| `/review <spec>` | REVIEW — closing-audit steps 7–8 + the DoD scorecard: scope diff, cleanliness sweep |
| `/ship <spec>` | SHIP — the tick-commit node: the ONE commit, rulings ack, `Status: done`, archive on request |

Namespace split, one surface apart: the bare lifecycle commands are
graph-spanning runs; the `/spec-to-prod <verb>` router keeps its own
verb space — there `plan`/`tech`/`qa` still mean single-agent authoring
repair runs and `review` still means the docs reviewer (ADR-013).
`/test`, `/review`, and `/ship` are three portions of the ONE closing
audit, never three audits: a failure in any portion is a fix round, and
the audit re-runs whole from step 7 (§ Execution mode); `/ship` refuses
unless the other two are green. Deliberately NOT adopted from that
surface: per-task commits and per-task verification.

"Prod" means production-READY, not deployed (ADR-014): the graph's
terminal path is execute → closing-audit → tick-commit → archive — what
leaves the pipeline is a verified, single-commit changeset in the local
repo. Push, PR, deploy, and publish are out-of-workspace side effects
the rulings rule already stop-and-asks; they stay human/CI actions, and
there is deliberately no release node in the graph.

## Run modes (the full workflow is not the only way)

Invoked as `/spec-to-prod <verb> <spec-name>` (the `~/.agents/commands/
spec-to-prod.md` router), via the six bare lifecycle commands (§
Lifecycle commands), or naturally ("re-survey the auth spec"). Three
ways to run, chosen by the user's ask or the state of the graph:

**Full workflow** — default for a new large spec: compute the frontier,
run the ready wave, recompute, repeat until the graph completes
(archive).

**Single-agent runs** — when one artifact needs refresh or repair, run just
that node's agent (same brief, same payload rules — plus: the current docs are now
*inputs* to read first, IDs are never renumbered, and `check.py` runs after):

| User says / situation | Run |
|---|---|
| "re-survey <spec>", baseline drifted, or before adding scope | surveyor |
| new open technical questions emerged | researcher |
| milestones reorder (gate fired, scope added, dependency changed) | planner |
| a decision changed; divergence needs a D-### + rewritten section | tech |
| new FRs appended and need TCs | qa |
| check.py traceability/burndown failures | task-breaker |
| survey staleness fires (check 8, or resuming) — see **Converge** below | surveyor, then `audit.py converge` |

**Converge** — the mechanical answer to "the codebase drifted past the
spec after merge/rebase." Re-run the surveyor in place (single-agent
repair run, above) against current HEAD — **delta-scoped**: emit the
payload with `scripts/graph.py <spec-dir> --emit-spawns --repair survey`
and it carries a `DELTA RE-SURVEY` block (the code files git says
changed since the survey's baseline commit — the specs tree excluded,
since a docs-only commit can't invalidate a code citation; a citation in
an unchanged file
cannot have moved), so the surveyor merges into the existing survey.md
instead of rebuilding — re-grepping only items whose evidence cites a
changed file, keeping untouched items byte-identical, refreshing the
Baseline header — instead of paying a second full survey. (First
surveys, fresh baselines, and non-git repos get the plain full-survey
payload; a git that cannot scope the delta degrades to an explicit
"re-survey in full" line, never a silent empty delta.) Then run
`scripts/audit.py
converge <spec-dir> --repo <path>` (`--repo` defaults to the spec dir's
grandparent) — it diffs the freshly-written
survey.md against its last committed version and prints each item id
that is new (`NEW GAP`) or regressed (`DONE → PARTIAL/TODO`,
`REGRESSED`) since that baseline. Append one task per line it prints
(next free T-ID via `check.py --next-ids`, cite the FR each evidences)
instead of letting the drift sit unnoticed until a downstream doc's
citation goes stale. Items it doesn't list (unchanged or improved) need
nothing. (In a non-git repo this edge reports `SKIPPED (not a git repo)`
— there is no committed baseline to diff against.)

**Execution mode** — spawning agents to *do* the tasks (below).

## Execution mode (agents doing the tasks — the execute node)

Work task.md inline or via **implementer agents** — one task per spawn.
Audits happen exactly twice for the whole plan — never per task, never per
phase, never per resumed session: the **before-audit runs once, when the
execution frontier first becomes eligible** (verify done — § Verification),
before any task is ever spawned; the user's approval (§ Verification) then
opens the execute node. The **closing audit runs once, after every task in
task.md across every phase has been implemented**. Between those two
points, implementers just implement — no per-task gate, no per-phase
audit, no tick, no commit. **Nothing is ticked or committed until every
task in the plan is done and the closing audit passes.**

### Implementation (no gating, no per-phase audit)

Coordinated waves (parallel is the default), spanning however many phases
task.md has:

1. **Wave-first**: at each round of the execute node, ALL runnable tasks —
   `- [ ]`, dependencies ticked/struck, not at the fix cap — that are not
   dependency-chained go out as **one wave — implementers spawned in a
   single message** so they run concurrently. Only tasks that consume
   another task's output (or share its files) run serially, chained after
   it. `[P]` marking (task-breaker) exists to make the chains visible; the
   absence of a chain means parallel. `graph.py --explain execute` prints
   this per-task frontier, with file-overlap notes for wave scheduling.
2. Before spawning a wave: check the group's intended file sets are disjoint
   (planner's parallelization map); any overlap → chain those tasks
   serially instead. Disjoint files are what makes concurrent implementers
   safe.
3. Mark every spawned task `(in-progress)` first (orchestrator, sole
   writer) — bookkeeping only, not a tick, no commit yet.
4. Spawn each with: brief + task entry verbatim + spec-dir pointer +
   acceptance commands (always for code tasks) + specs/CONSTITUTION.md
   pointer — the implementer implements and returns a digest; it does
   not test, gate, or prove.
5. Collect digests. A reported deviation → orchestrator **appends** the
   D-### to tech-spec.md immediately (don't wait for the closing audit) —
   append only, never rewrite an existing decision, and never touch
   test.md. A digest that claims a TC is wrong is a signal to re-brief qa
   afterward, not license to edit test.md now. Every D-### opens with
   `- **Context**: / **Decision**: / **Consequences**:` labels (check.py
   warns on any other shape) and, WHERE it touches files, names them by
   literal path — the scope gate greps paths, not descriptions. WHERE a
   D-### supersedes a number or target other docs quote (targets in
   plan.md, thresholds in test.md), grep the sibling docs for the old
   value and reconcile in the same pass — wording drift there is exactly
   what the reviewer exists to catch, and cheaper to prevent.
6. Move to the next batch the same way — no ticks, no commits, no audit at
   a phase boundary — until every task in task.md, across every phase,
   has been implemented.

**Chained tasks gate on landing, not on ticks.** graph.py's per-task
readiness is tick/struck-based — an `(after T###)` dependency counts
satisfied only once the upstream entry is `[x]` or struck — the
conservative mechanical truth. Live execution can never meet it: ticks
stay forbidden until the closing audit (audits happen exactly twice,
above), so a chained task sits `waiting on T001 (unticked)` for the whole
implementation even after its upstream has landed. When the frontier
shows a chained task blocked-on-unticked and the upstream's digest plus
your own scoped re-verification of its acceptance commands prove it
landed, spawn the dependent on that evidence and record the ruling — the
frontier is the mechanical floor, not a veto.

**Rulings, not stalls**: a running plan does not park on the user for
every conflict. An implementer's `blocked:why` digest, a task that
contradicts survey evidence, an ambiguity the spec doesn't answer — rule
on it, append the ruling as a D-### (what was decided, why, what it
costs if wrong), and keep the wave moving. Stop and ask only for: an
irreversible or destructive operation; a security-sensitive action; a
side effect outside the workspace (push, deploy, publish); or a plan
broken enough that every path forward is a guess. Everything else is a
recorded ruling. This is an execution-mode rule: it governs
mid-implementation conflicts on an *approved* plan — the clarify pass's
question rounds and the approve gate are HUMAN gates that wait for an
answer, non-answers included (§ Authoring the spec, D-018).

### Closing audit (once, after every task in task.md is implemented)
7. **Scope diff**: `git diff --name-only` (the whole plan) ⊆ the union of
   every task's intended files + tests — `scripts/audit.py scope
   <spec-dir>` does the grep: every changed file no doc mentions is
   listed as UNMENTIONED for you to adjudicate (renames and generated
   files may be legitimate). Anything unexplained → revert it or record
   it as a deviation.
8. **Cleanliness sweep**: the full diff carries no debug prints, temporary
   log statements, commented-out code, scratch files, or leftover TODOs
   from any task (unless a task's FR explicitly requires logging) —
   `scripts/audit.py clean` lists the suspects in the added lines; you
   adjudicate.
9. **Proof**: every task's FR gets its TC pass condition (test.md) run
   green — `scripts/audit.py proofs <spec-dir> --run` extracts each TC's
   command, runs it, and prints the command + summary line for the audit
   (opt-in: it executes commands embedded in test.md). TCs it lists as
   MANUAL are human-observation cases and stay yours to verify. Every
   green here is **fresh evidence** — run in this session, command and
   output on record; a pass you cannot cite the output for isn't a pass,
   and neither is one from an earlier session on changed code. A rerun
   that flips red→green unexplained is a finding, not noise — flaky ≠
   ignorable: fix the flake or park it with a D-###; a waived flake is a
   lying green.
10. **Regression gate**: the repo's broader check per conventions (full
    suite, impacted subset, or lint/format gates), green.
11. All green per the DoD gates (`gates/dod.md`; `audit.py dod
    <spec-dir>` prints the scorecard) → tick every task `- [x]` with its
    done-note (proof command), recompute burndown, **one commit for the
    entire plan's implementation** (code + docs together, `check.py
    --fix-burndown` for the arithmetic). Use `scripts/tick.py <spec-dir>
    --note 'T### :: <proof>'` per task — it applies the ticks, inserts
    the done-lines, and fixes the burndown mechanically; hand-editing a
    dozen entries has gutted as-built records (entry bodies and
    checkpoint comments must survive byte-identical into the archive).
12. **Rulings report**: surface every D-### (decision, why, cost if
    wrong) in the closing summary and get the user's ack — DoD gates 9–10 (rulings
    surfaced, then sign-off). A
    ruling that dies inside tech-spec.md was a decision made in secret.
    The report also names every irreversible or state-mutating change the
    plan shipped (migrations, backfills, anything hard to roll back) so
    the ack covers them explicitly.
13. Anything fails → nothing is ticked or committed. Use the scope diff to
    localize which task(s) likely caused it, fix the cause (spec, plan, or
    fix rounds — below), then re-run the **entire closing audit from
    step 7** — this gates the whole plan all-or-nothing, not task-by-task
    or phase-by-phase.

The lifecycle commands `/test`, `/review`, and `/ship` enter this one
procedure at its steps — `/test` = 9–10, `/review` = 7–8 plus the DoD
scorecard of step 11, `/ship` = 11–12 plus `Status: done` and, on
request, archive — portions of the ONE audit, never three; a failure in
any portion is a fix round, and the whole procedure re-runs from step 7.

**Fix rounds** (a task that came back wrong — a `blocked:why` digest
mid-execution, or a closing-audit failure traced to one task): capped at
5 per task. Rounds 1–3 re-brief the **same** implementer with the failure
evidence verbatim — it still holds the task's context (on harnesses that
cannot resume an agent, spawn fresh carrying the task entry, its last
digest, and the findings). Rounds 4–5 go to a **fresh** implementer one
capability tier up: the `spec-implementer` def itself runs the cheap
model tier (D-016), so the tier-up is the § Spawn mechanics step 3
fallback — the same brief body + shared protocol run at the **default
model tier** (a generic default-model agent where one exists; see §
Running under omp for why a generic subagent is not automatically one) —
a loop that survives three re-briefs usually means
the implementer cannot see its own problem. Round 3 failing is also the
signal to suspect the plan, not the implementer: re-brief tech for that
area's approach before spending rounds 4–5. At the cap, adjudicate — the finding is wrong (park it with a
D-### ruling), real but isolated (defer it with a D-###), or load-bearing
(the tech-spec is wrong: re-brief tech, then re-plan the affected tasks).
Between rounds, re-verify scoped — that task's acceptance commands and
its FR's TCs only; the full closing audit re-runs once, at the end, from
step 7. Annotate the task entry `(fix <n>/5)` each round — the cap
survives resume only if the count lives in task.md (graph.py surfaces a
task at cap as `at-fix-cap` — adjudication, never another auto-retry).
From round 2 on, the
implementer may write exactly one scratch note, `specs/<name>/notes/
T###.md` (its own task ID only) — what was tried, why it failed, in the
implementer's own words — and the orchestrator re-briefs the next
attempt (same or fresh implementer) with it verbatim. This is the one
named exception to "implementers never touch specs/": one file per task,
never read by check.py, never counted as status, and never any other
spec file.

**Write-contention rule**: implementers never touch anything under
`specs/` — concurrent `[P]` agents would clobber task.md. Agents return a
digest only; the orchestrator is the sole writer of status and the sole
prover of the plan, via the closing audit. Same effort scaling as always: a
one-file task is faster inline than spawned — but it still lands between
the before-audit and the closing audit, not inside an audit of its own.

## Authoring the spec (spec node + clarify loop — intent is human, never generated)

1. `scripts/scaffold.sh <kebab-name>` — templates in place; refuse
   overwrite; registers the spec in `specs/INDEX.md` — and creates
   specs/CONSTITUTION.md on the repo's first scaffold: fill it WITH the
   user (non-negotiable articles; the before-audit gates on them).
2. **Clarify pass (grilling)** — the clarify node, before any wave spawns:
   map the draft's gaps (missing ACs, undefined edge cases, vague FRs,
   open NEEDS CLARIFICATION markers) as a **design tree** — every open
   decision branches into the decisions that hang off it. Work it in
   **rounds**: the **frontier** is every question whose prerequisites are
   already settled — askable now without guessing at an answer you haven't
   heard yet. Ask the *whole* frontier in one batched round, each question
   numbered with why it matters, 2–3 viable options where useful, and a
   recommended answer:

   ```
   ❓ **Q1** — **<question title>**: <body>
   ➡️ <recommended answer>
   ---
   ❓ **Q2** — **<question title>**: <body>
   ➡️ <recommended answer>
   ```

   A question whose answer depends on another still-open question belongs
   to a *later* round, not this one. **Finding facts is never the user's
   job** — "does X already exist / is Y already handled" is a fact, not a
   decision: grep/read the repo yourself (or spawn a scoped surveyor probe
   for anything substantial) instead of asking, and put only genuine
   judgment calls to the user. Don't block the round on a running check —
   only the questions downstream of it wait; ask the rest of the frontier
   now.

   **A round put to the user is a HUMAN gate — an unanswered round is
   not an answer.** Where the harness has an interactive question tool,
   ask through it; but some modes resolve the call without ever waiting
   (ZCode autonomous runs return "user did not provide answers" in under
   a second), and an empty or skipped reply is the same thing. On any
   non-answer, print the round in chat exactly as formatted above and
   **end the turn there**: do not adopt the ➡️ recommendations, do not
   resolve the NEEDS CLARIFICATION markers yourself, do not spawn
   anything. Stopping is safe by construction — open markers keep the
   spec node blocked and graph.py holds the frontier at `clarify`, so
   the run resumes from doc state the moment the user's next message
   carries the answers. The recommended answer exists to make answering
   one glance cheap, not to make the round optional. Proceeding on
   recorded defaults is Execution mode's mid-implementation rule
   (§ Execution mode) and never applies here, at the approve gate, or at
   the closing-audit rulings ack (D-018).

   Each round's answers reshape the tree and push the frontier
   outward; recompute it and ask the next round. The pass ends when the
   frontier is empty — not at a fixed question count, though a tree that
   keeps sprouting new branches instead of closing is a signal to split
   the feature, not to push through more rounds. Every question still
   closes in one of three states — answered (resolved into spec.md),
   explicitly deferred (Scope out), or a named assumption (Assumptions &
   risks) — never left open. Do not spawn the analysis wave until the user
   has confirmed the shared understanding (open markers keep the spec node
   blocked, and graph.py holds the frontier there). An ambiguity caught
   here never reaches a downstream agent.
3. Fill spec.md WITH the user: what/why/business, stories+ACs, FR-###,
   scope in/out. Unresolved ambiguity → `NEEDS CLARIFICATION: <question>`
   inline — collect answers before the task list is written (check.py and
   the graph hold the spec node blocked while any marker stands), never
   guess.
4. Derive research questions from the open technical choices, if any exist
   — apply the researcher gate above before the analysis wave spawns.

## Verification (verify → before-audit → approve)

Run `scripts/check.py <spec-dir>` — the verify node runs it mechanically,
you run it for the judgment calls around it — mechanical checks: 7 files
present (5 contract files + survey.md/research.md as optional inputs), ID
traceability (every FR/US has a task + TC; no dangling IDs), burndown
arithmetic vs checkboxes including the Σ total row, status-bleed
(checkboxes outside task.md), open NEEDS CLARIFICATION, unfilled template
placeholders, vague plan phrases (TBD, "handle edge cases"…), FR→milestone
coverage, cross-phase dependency chains, parallel file overlap, TC shape,
status/INDEX consistency, tech-spec
citation paths vs the repo (any known source
extension, not just .py), survey baseline vs HEAD (staleness), survey.md
evidence reality (every file:symbol:line citation names a real def/class),
verify-command path reality (a pytest path/glob actually matches a
file) — the same two checks the surveyor already ran on itself via
`--survey-only`, re-run here as a backstop in case a single-agent survey
repair (§ Run modes) skipped the self-check — and constitution presence
(escalates from WARN to FAIL once a second spec exists in the repo;
`check.py <spec-dir> --constitution` runs this one check standalone, e.g.
as a CI pre-flight). Fix small failures
directly; substantive ones go back to the responsible agent. For large
specs, spawn the **reviewer** agent first — the adversarial pass on what
scripts can't see (vacuous test cases, over-promised acceptance, wording
drift, both-sides-wrong parity); it returns BLOCK/WARN/NIT findings and
edits nothing. Still human: integration behavior end-to-end.

Optionally, `check.py <spec-dir> --checklist` (re)generates
`specs/<name>/checklist.md` — a plain FR/AC summary for readers who won't
parse task.md's burndown table. It is a derived, regenerate-only view
(never hand-edited, never read by check.py, task.md stays the only status
holder) — the same anti-drift shape as merging the agent defs/briefs
(decisions/007): one representation, not two that can disagree.

**Before-audit (once — the plan's only pre-implementation audit)** runs
when the execution frontier first becomes eligible: verify done, before
Execution mode ever spawns a task. It does not repeat per phase, per
task, or per resumed session. Six gates — full contract in
`gates/before-audit.md`:

1. **Preconditions** — task.md's phase/dependency order internally
   consistent (cross-phase `(after T###)` chains fail check.py
   mechanically; real-dependency judgment is yours).
2. **Fresh baseline** — code-guide verify command + project test command,
   both green before any task spawns.
3. **Clean tree** — `git status --porcelain` empty.
4. **Already-done sweep** — tasks survey shows satisfied get noted, never
   spawned.
5. **Isolated branch/workspace** — cut the branch spec.md names (ask
   before worktrees); never main/master or a user-active branch without
   consent; its starting HEAD anchors the closing audit's scope diff.
6. **Constitution gate** — every specs/CONSTITUTION.md article complied
   with; every implementer payload carries it from here on.

Passing all six, record `Before-audit: passed @ <sha>` in task.md's
header block (`passed @ -` where no git sha exists) — resume and the
closing audit read it, graph.py reads it as the before-audit node's done
signal; a later failure attributes to this plan only from a recorded
green baseline. In a non-git repo the git gates degrade to explicit
SKIPPED notes, never silent passes. Any failure here → fix the cause
(spec, plan, or re-brief) before the execute node spawns anything.

**User approval (the gate into execute)**: with verify green and the
before-audit passed, present the spec-set digest — approach,
phase/task counts, burndown, open WARNs, any D-###s so far — and get an
explicit go-ahead before the first implementer is ever spawned. "An
approved task.md" (§ Run modes) means this sign-off. Record it the
moment it's given — spec.md `Status: approved` (a resumed session reads
it instead of re-asking; check.py fails progress on a still-draft spec,
and the approve node — a HUMAN gate — stays open without it).

## Resuming (recompute the frontier — state lives in the docs)

A fresh session reconstructs all workflow state from the spec dir itself —
never from memory — by computing the frontier:

1. Run `scripts/graph.py <spec-dir>` — the report (or `--state-json`) is
   the state of the union: every node's state and reason, the frontier
   (exactly what is done, what is ready, what is blocked), loop-edge
   status, and task counts, derived from doc state alone. Work what it
   prints: run the ready wave, resolve the named pauses, unblock what the
   blocked reasons name. `scripts/check.py <spec-dir>` failures name the
   node to re-run (single-agent repair runs cover it).
2. Progress rides the same doc state: `Status:` in spec.md gives the
   lifecycle position — draft → approved → active → done, which the graph
   reads as the approve / execute / tick-commit signals; task.md statuses
   are implementation progress, with `(in-progress)` marking the
   interrupted task.
3. `research-gate: gate:undetermined` means the run/skip decision is
   still yours to make — a `not applicable` research.md means the gate
   was deliberately resolved skip (solo analysis wave), not unfinished.
4. A survey-staleness warning means the evidence baseline moved — re-run
   surveyor before trusting any status (delta-scoped: `--emit-spawns
   --repair survey` emits the DELTA RE-SURVEY payload), then diff old vs
   new with `audit.py converge <spec-dir> --repo <path>` (§ Run modes'
   **Converge**) rather than trusting the overwrite silently.
5. An interrupted implementation leaves `(in-progress)` tasks with code
   already on disk but **unticked and uncommitted** — this mode has no
   per-task or per-phase commit to roll back to. Before spawning anything,
   run `git status` / `git diff` to see what's already implemented rather
   than re-doing it (in a non-git workspace the probe doesn't exist:
   skip it with a `SKIPPED (not a git repo)` note and inspect the
   `(in-progress)` tasks' intended files directly instead). The
   before-audit already ran once and does not repeat on resume; resume
   straight into the closing audit if every task in task.md looks
   implemented, or resume spawning only the tasks that aren't.

## During implementation (status lifecycle & scope changes)

Execution mode (§ above) owns the mechanics — waves, the two audits, the
single end-of-plan tick-and-commit. This section covers what it doesn't:
the docs' own lifecycle.

1. **Spec status**: first task of the whole spec spawned → spec.md
   `Status: active`. Done = all ticked, every TC has a passing run,
   `check.py` green → `Status: done`, and update the specs/INDEX.md line
   to match. Then archive the completed set — `scripts/archive.sh <name>`
   moves specs/<name>/ to specs/archive/<date>-<name>/ and repoints INDEX
   (the archive node: ready once tick-commit is done and Status is done;
   the repointing is the archive action itself); the dated archive is the
   as-built record, specs/context/ stays the living view.
2. **Phase boundary**: read plan.md's checkpoint for the phase just
   finished before briefing the next wave — a sanity read, not a gate.
   Running its verify command is allowed and often useful for shaping
   the next briefs, but a red checkpoint is information (note it, fix
   the cause via the responsible implementer), never an audit: nothing
   is un-ticked, unwound, or re-audited at a boundary. The only audits
   are the two Execution mode defines.
3. **Divergence from spec**: append the D-### to tech-spec.md
   (§ Execution mode, step 5 — append-only) and update spec.md if the
   *what* changed. Never implement off-spec silently; dropped tasks get
   struck through in task.md with the D-### that killed them.

**Adding scope later**: re-survey only the delta, append IDs (never
renumber — `check.py --next-ids` prints the next free ones), refresh
burndown + coverage matrix, keep the chain intact.

## Bugfix specs

Same graph, same waves; deltas only in `references/bugfix.md` (bug
narrative + unchanged-behavior FRs, surveyor's bug item, root-cause
section, plan.md's first phase is always the regression, one regression
TC per unchanged FR).

## Rules that bind the orchestrator

- You are the sole status writer: task.md checkboxes and burndown are
  yours to update from agents' proof, never the agents' own.
- You are the sole ID allocator and re-briefer: agents report gaps and
  drift, you decide what changes and who fixes it.
- You are the sole coordinator: wave sequencing and re-briefing are your
  job; agents run independently and never assign each other work — they
  report gaps in their digest, and only you act on it.
- tech-spec.md and test.md are read-only during implementation, except for
  **appending** a D-### to tech-spec.md. Never rewrite an existing
  decision, diagram, or TC to match what got built — that launders "what I
  happened to implement" as if it were the original contract — and never
  touch test.md at all during implementation. A real correction to an
  existing decision or TC is a fresh tech/qa re-brief (§ Run modes) with
  fresh evidence, not an inline edit mid-implementation.

The agent-facing versions of these rules (citations verbatim, symbols over
line numbers, IDs never renumbered, one file per agent, never spawn/commit)
are canonical in `agents/_shared-protocol.md` § Universal
rules — that file, not this one, is what sub-agents actually read.

## Anti-patterns

1. Docs written before surveying → statuses and citations guess. *The
   analysis wave precedes the authoring wave, always.*
2. Sub-agent outputs piped through the conversation → telephone-game drift.
   *Artifacts on disk; digests ≤10 lines (sole named exception: the
   reviewer's ≤20 — its findings list is the deliverable).*
3. Context-free spawn ("go plan it") → duplicate/gapped work. *Brief +
   payload, every time.*
4. Spawning without the shared rules → agents guessing at conventions
   (citation discipline, ID immutability, file ownership) instead of
   following a stated contract. *Prepend `_shared-protocol.md` to every
   spawn — sole exception: the reviewer, whose brief states it needs no
   `_shared-protocol.md` (it runs solo, outside a wave).*
5. Agents assigning work to each other (or spawning agents) → runaway
   trees and dueling edits. *Agents run independently and report gaps in
   their digest only; the orchestrator is the sole spawner and re-briefer.*
6. One agent editing another's file → fights over section ownership.
   *Re-brief the owner instead — ownership is exclusive, by role.*
7. task.md written from plan intent instead of survey status → `todo` for
   built work. *Task-breaker's #1 rule.*
8. qa reading tech-spec → tests that verify the implementation, not the
   promise. *Implementation blindness is required.*
9. Inherited numbers laundered as evidence → stale counts ship. *Re-count
   in survey.*
10. Status bleed into intent files → tracker and spec disagree. *check.py
    fails it.*
11. tech-spec.md/test.md rewritten mid-implementation to match what got
    built → hallucinated "always-was" history, the contract chasing the
    code instead of the reverse. *Append D-### only; a real correction to
    an existing decision or TC goes through a fresh tech/qa re-brief, never
    an inline edit mid-implementation.*
12. Audit re-run per task or per phase → defeats the point of batching it.
    *Before-audit once, when the execution frontier first becomes eligible;
    closing audit once after every task in task.md is implemented —
    nowhere else.*
13. Essay or decision-log comments, and copy-pasted logic, landing in the
    diff → comments state constraints, decisions live in tech-spec
    D-###s, and shared logic lives in one shared home. *Implementer brief
    § Method 2–3; `audit.py clean` flags essay comments (≥120-char
    comment lines) and comment walls (≥8 consecutive) as adjudication
    suspects.*
