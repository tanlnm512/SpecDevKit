# GLOSSARY — the kit's shared language

One term, one meaning. Use these words exactly in briefs, SKILL.md
bodies, contracts, docs, and commit messages; when a new term
stabilizes, add it here instead of redefining it inline. Each entry
names its canonical home — this file routes, it does not arbitrate;
on any conflict the canonical file wins.

## Terms

### Orchestration

| Term | Means | Canonical home |
|------|-------|----------------|
| orchestrator | the main agent session running a skill's pipeline; owns statuses, synthesis, and spawn discipline — never a role agent's artifact | each skill's SKILL.md rules |
| role agent | a spawned sub-agent with exclusive artifact ownership (`spec-<role>`; installed as native subagent types where the harness has them) | `skills/<name>/agents/*.md` |
| brief | an agent-definition markdown file in `skills/<name>/agents/`; its frontmatter-stripped body IS the system prompt | same |
| generated view | a root `agents/*.md` file, regenerated from a skill brief by `tools/agent-defs.py` — never hand-edited | `AGENTS.md` house rules |
| panel | a concurrent wave of role agents, one lens each, over a shared protocol prepend (brainstorming: Visionary / Cynic / Minimalist; review: correctness / security / quality) | `contracts/panel.md`, `contracts/run.md` |
| payload | the self-contained spawn input — skill_dir, problem restatement, brief body, protocol prepend, evidence pack | `skills/spec-brainstorming/contracts/run.md` |
| digest | the only return value a spawned lens or panel agent produces; its grammar is fixed per skill | same |
| evidence pack | the external context gathered before a brainstorm panel spawns | `skills/spec-brainstorming/SKILL.md` (stage 2) |

### Scheduling and state (the spec suite: spec-intent · spec-shape · spec-execute)

| Term | Means | Canonical home |
|------|-------|----------------|
| doc-set | the seven files under `specs/<name>/` at `Tier: full` — the canonical statement of what a spec dir IS; at `Tier: tiny` the doc-set is ONE file (spec.md with § Tasks) | `skills/spec-shape/scripts/check.py` (the docset discipline) |
| contract file / evidence file | the two doc-set classes: spec / plan / tech-spec / task / test are Contract; survey / research are Evidence | same (check discipline) |
| contract tier | `**Tier**: tiny \| full` on spec.md — one-file contract vs the seven-file docset (D-037); absent reads full | `skills/spec-shape/decisions/037` |
| archetype | one of the five agent briefs — scout · designer · qa · builder · reviewer (panelist in brainstorming); harness def and brief are the same file (D-036) | `skills/spec-*/agents/` (byte-shared across the trio) |
| lens | a specialization riding a spawn payload from `agents/_lenses.md` (survey/research on scout; plan/tech/tasks on designer; the three panel angles) — data, not a brief file (D-036) | `skills/*/agents/_lenses.md` |
| primitive | a model-invoked discipline reference an orchestrator composes — grilling, diagnosing, domain-language (D-039) | `skills/spec-intent/references/` (grilling; the monolith's tree is retired) |
| status holder | the one file that carries status: task.md at full tier, spec.md § Tasks at tiny (C-01, amended by D-037) | `specs/CONSTITUTION.md` |
| frontier | every graph node that is ready and not done; the only scheduler — nothing schedules by stage number | `skills/spec-shape/SKILL.md` (the generated node table) |
| wave | one concurrent run of the whole frontier; recompute after each wave | same |
| tick | the mechanical, atomic `- [ ] T###` → `- [x]` promotion with its `done <date> — <proof>` sub-line | `skills/spec-execute/scripts/tick.py` |
| freeze | the approval freeze applied to the doc-set before execution | `skills/spec-shape/scripts/freeze.py` (the parity master) |
| gate | a check the flow must pass — say mechanical gate (scripts decide: `check.py`, review stage 1) or name the approval gate (verify → approve; the researcher gate); bare "gate" is ambiguous | each skill's SKILL.md |

### Review (spec-code-review)

| Term | Means | Canonical home |
|------|-------|----------------|
| mechanical gate | stage 1: the target repo's own checks (Makefile, npm scripts, cargo, go, pytest/unittest, shell syntax, secret shapes) | `skills/spec-code-review/SKILL.md`, `scripts/gate.sh` |
| finding | a kept review observation with an ID, independently confirmed before it survives triage | `skills/spec-code-review/contracts/panel.md` |
| verdict | a fix-loop verification outcome for one finding | same |
| shared review oracle | `review_orchestrator.py` — the single home of review state, systems, asks, finding IDs, and report assembly | D-014 |
| probe | one thin per-phase call by which any caller fetches JSON from the oracle (scope, gate, shard, ask, report) | D-014 |
| dialect twin | (retired, D-035) the per-harness workflow scripts deleted with the one-engine move — history only; the shared oracle is the one executable form | `skills/spec-code-review/decisions/016` |

### Kit plumbing

| Term | Means | Canonical home |
|------|-------|----------------|
| skill dir | `skills/<name>/`, self-contained by packaging (marketplace `source: ./skills/<name>`) | `AGENTS.md` |
| generated surface | any regenerate-only artifact: root `agents/`, the SKILL.md node table (`scripts/contract.py`), the plugin/marketplace manifests, the `§ Engineering rules` sections | `AGENTS.md` house rules |
| ADR (D-###) | an append-only decision record; every divergence from a doc contract gets its own entry (C-05) | `skills/<name>/decisions/` |
| eval case | an entry in a skill's `evals/cases.md`; every increment names its served case (C-10) | `specs/CONSTITUTION.md` |
| sync | `tools/sync.sh` — the one harness-neutral install pipeline to every machine harness root | `tools/` |
| telemetry | the local append-only run record (`scripts/telemetry.py` → `~/.spec-dev-kit/telemetry/*.jsonl`) — evidence for self-improvement, never status, never contents | `skills/*/scripts/telemetry.py` |
| lifecycle commands | the `/spec-*` verb wrappers — `/spec-idea`, `/spec-gen`, `/spec-build`, `/spec-test`, `/spec-review`, `/spec-ship` | D-029 |

## Terms to avoid

- **The former name** of the suite (pre-2.1.0) — say "the former
  name"; it is redacted repo-wide and never reintroduced (D-014).
- **Bare `/review`, `/plan`, `/build`, `/test`, `/ship`** — retired by
  D-029; they collide with harness modes and built-ins. Use the
  `/spec-*` forms, and say `spec-code-review` for standalone review —
  "review" alone is ambiguous with `/spec-review`.
- **"Workflow dialect" / "twin"** for current surfaces — retired with
  D-035; the term now names history only. Say "the oracle"
  (spec-code-review) or "`graph.py --run`" (the spec suite's engine,
  shipped by the trio).
- **"Stage" for the spec suite's scheduling** — the pipeline schedules by
  frontier and waves, never by a stage ladder ("Waves, not stages").
  The brainstorming and code-review skills do have real stages; the
  word is theirs.
- **"Copy" for a root `agents/*.md` file** — it is a generated view;
  "copy" invites hand-editing.

## Flagged ambiguities (resolved)

- **"review"** splits three ways (D-029): `/spec-review` is
  spec-execute's implementation-diff review step; `spec-code-review`
  is the standalone skill; harness built-ins keep their own names.
- **"agent"** covers four things — say role agent (spawned), brief
  (the markdown), generated view (root `agents/` file), or AGENTS.md
  (the convention file).
- **"workflow"** covers two things — the workflow graph (scheduling
  semantics, `scripts/contract.py` + the spec-shape SKILL.md node
  table) and a workflow run (`graph.py --run` executing one). Name
  which.
- **Byte-identical pairs** (telemetry module copies, lens sections in
  payloads) are edited in every copy at once or regenerated from
  source — the recurring mistake is editing one copy and shipping
  drift.
