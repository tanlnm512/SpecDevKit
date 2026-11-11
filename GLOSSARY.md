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
| panel | a concurrent wave of role agents, one lens each, over a shared protocol (`protocol/panel-protocol.md`) (brainstorming: Visionary / Cynic / Minimalist; review: correctness / security / quality) | `contracts/panel.md`, `contracts/run.md` |
| payload | the self-contained spawn input — skill_dir, problem restatement, brief body, lens section, protocol text, evidence pack | `skills/spec-brainstorming/contracts/run.md` |
| digest | the only return value a spawned lens or panel agent produces; its grammar is fixed per skill | same |
| evidence pack | the external context gathered before a brainstorm panel spawns | `skills/spec-brainstorming/SKILL.md` (stage 2) |

### Scheduling and state (the spec suite: spec-intake · spec-author · spec-execute)

| Term | Means | Canonical home |
|------|-------|----------------|
| doc-set | the seven files under `specs/<name>/` at `Tier: full` — the canonical statement of what a spec dir IS; at `Tier: tiny` the doc-set is ONE file (spec.md with § Tasks) | `skills/spec-author/scripts/check.py` (the docset discipline) |
| contract file / evidence file | the two doc-set classes: spec / plan / tech-spec / task / test are Contract; survey / research are Evidence | same (check discipline) |
| contract tier | `**Tier**: tiny \| full` on spec.md — one-file contract vs the seven-file docset (D-037); absent reads full | `skills/spec-author/decisions/037` |
| archetype | one of the five agent briefs — scout · designer · qa · builder · reviewer (panelist in brainstorming); harness def and brief are the same file (D-036) | `skills/spec-*/agents/` (byte-shared across the trio) |
| protocol / `protocol/` dir | a skill's shared prose its briefs point at — lens table, shared or panel protocol — kept in `protocol/`, never `agents/`, so no harness registers it as an agent (D-049) | `skills/*/protocol/` |
| lens | a specialization riding a spawn payload from `protocol/lenses.md` (survey/research on scout; plan/tech/tasks on designer; the three panel angles) — data, not a brief file (D-036) | `skills/*/protocol/lenses.md` |
| primitive | a model-invoked discipline reference an orchestrator composes — grilling, diagnosing, domain-language (D-039) | `skills/spec-intake/references/` (grilling; the monolith's tree is retired) |
| status holder | the one file that carries status: task.md at full tier, spec.md § Tasks at tiny — no other file holds status (C-01, amended by D-037) | `skills/spec-author/decisions/037-thin-floor.md` |
| frontier | every graph node that is ready and not done; the only scheduler — nothing schedules by stage number | `skills/spec-author/SKILL.md` (the generated node table) |
| wave | one concurrent run of the whole frontier; recompute after each wave | same |
| tick | the mechanical, atomic `- [ ] T###` → `- [x]` promotion with its `done <date> — <proof>` sub-line | `skills/spec-execute/scripts/tick.py` |
| freeze | the approval freeze applied to the doc-set before execution; `approvals/approval.md` is its record, required at both tiers for an approved spec; at tiny tier it covers the § Tasks list less its status markers (D-050, D-051, D-052) | `skills/spec-author/scripts/freeze.py` (the parity master) |
| `approvals/review.md` | full tier's record of the contract review — the findings digest, one ruling per BLOCK, and the payload's docset fingerprint (a hash of the frozen manifest plus task.md); `freeze.py --record` refuses a missing or stale one; tiny tier has none | `skills/spec-author/decisions/050-approval-records-and-payload-contracts.md` |
| `(fix n/5)` / `(fixed n/5)` | a task entry's fix-round marker: `(fix n/5)` is an OPEN round (the task is runnable again), `(fixed n/5)` the same round landed; `n` counts failures and 5/5 is the cap | `skills/spec-author/decisions/051-engine-enforces-wave-fix-and-tiny-approval.md` |
| deferred | a runnable task the engine left out of this wave because its files overlap a wave-mate or an `(in-progress)` task; printed `deferred: T### (<why>)`, emitted on a later wave | same |
| `--native-agents` | `graph.py --emit-spawns\|--run` flag for a harness with registered agent types: the payload names the type and omits the brief the type already carries; default payloads embed the brief | same |
| `reviewer-diff.patch` | the implementation-diff review's full diff, written beside its reviewer payload because the reviewer holds no shell; its header lists the untracked files the diff omits | `skills/spec-author/decisions/050-approval-records-and-payload-contracts.md` |
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
| eval case | an entry in a skill's `evals/cases.md`; every increment names its served case (C-10) | `skills/<name>/evals/cases.md` |
| sync | `tools/sync.sh` — the one harness-neutral install pipeline to every machine harness root | `tools/` |
| telemetry | the local append-only run record (`scripts/telemetry.py` → `~/.spec-dev-kit/telemetry/*.jsonl`) — evidence for self-improvement, never status, never contents | `skills/*/scripts/telemetry.py` |
| skill command | one `/spec-*` command per skill, named for it — `/spec-brainstorming`, `/spec-intake`, `/spec-author`, `/spec-execute`, `/spec-code-review`; execute's build/test/review/ship ride its router as verbs (D-033) | D-029, spec-execute D-033, spec-author D-048 |
| lifecycle commands | the three skill commands that carry a spec from idea to delivery, in order: `/spec-intake` → `/spec-author` → `/spec-execute`; `/spec-brainstorming` is the optional step before them and `/spec-code-review` stands outside the lifecycle | `README.md` Usage |

## Terms to avoid

- **The suite's pre-2.1.0 name** — retired and deliberately not
  spelled out anywhere in this repo; refer to it only as "the former
  name" and never reintroduce it (D-014).
- **Bare `/review`, `/plan`, `/build`, `/test`, `/ship`** — retired by
  D-029; they collide with harness modes and built-ins. Use the
  `/spec-*` forms, and say `spec-code-review` for standalone review —
  "review" alone is ambiguous with `/spec-execute review`.
- **`spec-intent`, `spec-shape`, `/spec-idea`, `/spec-gen`** — retired
  aliases (spec-author D-048): the skills are `spec-intake` and
  `spec-author`, and each command is its skill's name.
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
- **Hedged normative verbs in contract text** — "should ideally",
  "try to", "if possible". Acceptance criteria and rule text use
  MUST / MUST NOT / NEVER; if a behavior is genuinely optional, say
  what decides the optionality instead of hedging the verb.

## Flagged ambiguities (resolved)

- **"review"** splits three ways (D-029): `/spec-execute review` is
  spec-execute's implementation-diff review step; `spec-code-review`
  is the standalone skill; harness built-ins keep their own names.
- **"agent"** covers four things — say role agent (spawned), brief
  (the markdown), generated view (root `agents/` file), or AGENTS.md
  (the convention file).
- **"workflow"** covers two things — the workflow graph (scheduling
  semantics, `scripts/contract.py` + the spec-author SKILL.md node
  table) and a workflow run (`graph.py --run` executing one). Name
  which.
- **Byte-identical pairs** (telemetry module copies, lens sections in
  payloads) are edited in every copy at once or regenerated from
  source — the recurring mistake is editing one copy and shipping
  drift.
