# SpecDevKit

Spec-driven development as a skill suite: an orchestrator (your main
session) plus five archetype agents (scout · designer · qa · builder ·
reviewer, lens payloads riding the spawn) drive the frontier loop of
`graph.py` and produce a grounded, execution-ready doc set per feature
under `specs/<name>/` — ONE file by default (`Tier: tiny`, D-037) or
the full seven-file docset (`spec.md`, `plan.md`, `task.md` (the
status holder), `tech-spec.md`, `test.md`, with `survey.md` and
`research.md` as evidence — with FR/NFR → task → test traceability, an
approval freeze, durable tick/delivery evidence, and an
implementation-diff review. Every artifact is mechanically verified by
`scripts/check.py` and scheduled by a **dynamic state graph**
(`scripts/graph.py`), not a fixed stage ladder.

This repo — published on GitHub as **SpecDevKit**
(`tanlnm512/SpecDevKit`) — is a **skillset**, not a single-skill package:
every skill lives at `skills/<name>/`, and one shared, harness-neutral install
pipeline (`tools/sync.sh`) installs every skill it finds there to every
supported coding-agent harness in one pass. The spec pipeline ships as
THREE phase skills: `spec-intent` (pre-spec intake — scout the repo,
grill the user, produce a validated `intent.md`), `spec-shape` (gated
authoring — the docset waves through verify, stopping at the human
approve gate; the shared-core master and the workflow graph's node
table live here), and `spec-execute` (post-approve implementer waves,
the delivery pass, the lifecycle commands). Beside
them: `spec-code-review` — the portable three-stage code review (the
repo's own detected checks as a mechanical gate, then a preflight
scout that maps the codebase and modules, then specialist lenses with
triage and independent confirmation of every finding, then synthesis,
plus an optional author-fix loop ending in a merge recommendation) —
and `spec-brainstorming` — the pre-spec front door (one clarifying
question, a spawned three-lens panel of Visionary / Cynic /
Minimalist, a trade-off matrix, socratic refinement, then a durable
design specification at `brainstorms/<name>.md` that feeds `/spec-idea` as
intent input). § Adding a skill to this repo below is the contract any
further one follows.

The single organizing rule: **the doc state under `specs/<name>/` is the
only state.** Every workflow node's readiness is derived from it; nothing
else (no session log, no step ledger) is consulted.

New-user entry point: `skills/spec-shape/SKILL.md` (the authoring
playbook and the workflow graph's node table); the phase commands are
`/spec-idea`, `/spec-gen`, `/spec-execute`.

## How the workflow works

Scheduling is a frontier computation over a graph of fifteen nodes
(six role-spawn nodes — survey, research, plan, tech, qa, tasks —
plus orchestrator/mechanical nodes: spec, clarify, research-gate,
intent, execute, verify, approve, tick-commit, archive; at `Tier:
tiny` the five authoring nodes are SKIPPED and the spec's own § Tasks
drive execute — D-037):

1. **Compute the frontier** — `python3 scripts/graph.py specs/<name>`
   prints every node's state (`done` / `READY` / `blocked(reason)` /
   `gate:undetermined` / `SKIPPED`) with reasons, derived from doc state
   alone.
2. **Run the ready frontier as one wave** — every ready agent node
   spawns in a single message (surveyor ∥ researcher, then planner ∥
   tech ∥ qa, then task-breaker, then implementer batches). Each agent
   writes its artifact to disk and returns only a short digest.
3. **Recompute and repeat** until the graph completes (archive).

Loop edges are first-class: the clarify loop (open `NEEDS CLARIFICATION`
markers hold the spec), fix rounds capped at 5 per task (`(fix n/5)` in
task.md), re-briefs on gap digests, and converge (survey staleness →
re-survey → `audit.py converge` → appended tasks re-enter execute).

**Human gates are never auto-satisfied** — by any script: clarify, the
researcher run/skip gate (an orchestrator judgment), user approval
(spec.md `Status: approved`), and tick-commit. `graph.py --run` pauses
with `AWAITING HUMAN: <node>` at each and waits; the auto-trigger loop
runs only the mechanical verify node (check.py) itself and hands agent
waves to a configurable `--runner`.

One proof-and-delivery pass runs per plan, after every task is
implemented: proofs, regression, and the review instruments (scope
diff, cleanliness sweep, DoD scorecard, implementation-diff reviewer)
feed the ticks' proof notes — then the implementation commit C1 and
delivery record C2. Nothing is committed before it.

Right-sizing is explicit at two axes: the CONTRACT tier (`Tier: tiny`
— one file with § Tasks inside, the scaffold default; `full` — the
seven-file docset; `migrate.py grow` promotes between them with ids
preserved — D-037) and the effort tier (standard merges the design
wave; large/high-risk changes add NFR triage, threat modeling,
rollback design, and both reviewer modes).

## Harness support

| Harness | Skills | Agent defs | Entry |
|---------|--------|-----------|-------|
| Claude Code | plugin / sync | `~/.claude/agents/` as-is (frontmatter-enforced) | the five `/spec-*` commands (one per skill); `/spec-execute` takes the build/test/review/ship verbs; stages inline or via `graph.py --run` |
| omp | native root / marketplace | `~/.omp/agent/agents/` regenerated (omp dialect) | `/skill:spec-intent`, `/skill:spec-shape`, `/skill:spec-execute` |
| zcode | plugin / sync | none — fallback spawn carries briefs in the payload | the five `/spec-*` commands via `~/.agents/commands/`; stages inline or via `graph.py --run` |
| opencode | `~/.agents/skills/` (compatibility root it scans) | `~/.config/opencode/agents/` regenerated (permission map) | `skill` tool / `@spec-scout`-style archetype names |
| Factory Droid | `~/.agents/skills/` (personal-compatibility root) | `~/.factory/droids/` regenerated (Task subagent_types) | the five `/spec-*` commands via `~/.factory/commands` (gated) |
| Kilo | `~/.config/kilo/skills/` (native config-dir scan; D-040) + `~/.agents/skills/` (compatibility root) | `~/.config/kilo/agent/` regenerated (subagent permission map) | the five `/spec-*` commands via `~/.config/kilo/command/` (gated); stages run inline — no dynamic workflow runtime |
| Antigravity (agy) | this repo as a plugin | committed root `agents/` personas (byte-verbatim) | `agy plugin install` |

ADR-015 records the model: one skill copy at `~/.agents/skills/` feeds
every harness that reads the compatibility root; per-harness work is
confined to agent-def dialects, generated by `tools/omp-defs.py` and
`tools/agent-defs.py` (opencode / droid / kilo / agy), and — where the
harness runs the same frontier loop through the ONE engine,
`graph.py --run` (ADR-035): doc state in, payloads out, a `--runner`
seam per harness, AWAITING HUMAN stops at every judgment gate — no
per-harness workflow dialects exist to install or drift.

## Requirements, platforms, and trust boundaries

One current statement of what this repo needs, where it runs, and what is
safe to run — every claim here tracks a gate: the CI matrix proves the
platform list, `tools/sync.sh` proves the harness list.

- **Runtime**: Python ≥ 3.10, stdlib only — nothing to install — plus
  **bash**: every shell entry point (`tools/*.sh`, the skills'
  `scripts/*.sh`, both `tests/run.sh` suites) is a bash script. git is
  optional: scope, staleness, and commit behavior degrade to explicit
  `SKIPPED (not a git repo)` notices, never a silent all-clear.
- **Platforms**: Linux and macOS — the two platforms the CI matrix
  exercises (both Python suites, compilation, shell syntax,
  generated-artifact drift, representative docset checks). Windows-native
  shells are unsupported.
- **Harnesses**: exactly the seven [Harness support](#harness-support)
  surfaces — what `tools/sync.sh` populates and SHA-verifies; a harness
  whose config home is absent is skipped loudly, never created.

**Migrating existing docsets**: docsets authored under the version-1
lifecycle upgrade in place with the suite's migration utility
(`skills/spec-execute/scripts/migrate.py`): a dry-run previews the added lifecycle
fields, apply is idempotent, and migration only inserts explicit pending
evidence markers — missing evidence never becomes passed evidence; it
stays pending until a human acknowledges it. Archived docsets stay
readable and report a compatibility warning instead.

**Safe commands**: read-only on any docset — `check.py` (without
`--fix-burndown`), `graph.py --state-json|--mermaid|--explain`,
`audit.py scope|clean|converge|archived`, `freeze.py --verify`,
`skill-dir.sh`. Everything else
writes: `scaffold.sh`, `archive.sh`, `tick.py`, `check.py
--fix-burndown`, `freeze.py --record` (docsets); `sync.sh` (harness
homes under `$HOME`); `plugin-manifest.py`,
`omp-defs.py`, `agent-defs.py` (regenerate committed artifacts);
`graph.py --run|--emit-spawns` (spawn agents, write payloads);
`audit.py proofs --run` and `audit.py dod` execute the commands embedded
in test.md — read them first. Agents themselves never commit: the human
gates (approval, tick-commit) are the only path to a
commit, and push/publish stay human/CI gates.

## Install as a plugin

The fastest path — no local checkout needed. This repo is a plugin
marketplace (`.claude-plugin/marketplace.json` at the repo root) with one
plugin entry per skill; each skill's own directory is a self-contained,
independently installable plugin — its `commands/` and `agents/` already
live inside it, at the locations Claude Code's plugin loader scans by
default.

**Claude Code:**

```shell
/plugin marketplace add tanlnm512/SpecDevKit
/plugin install spec-intent@spec-dev-kit
/plugin install spec-shape@spec-dev-kit
/plugin install spec-execute@spec-dev-kit
```

**omp (Oh My Pi)** reads the same `.claude-plugin/marketplace.json` as
its Claude-Code-compatible fallback — no separate `.omp-plugin/` catalog
is published, since the content would be identical:

```
/marketplace add tanlnm512/SpecDevKit
/marketplace install spec-shape@spec-dev-kit
```

**zcode** understands the same marketplace.json shape (its own local
plugin state already tracks `anthropics/claude-plugins-official` as a
GitHub-sourced marketplace) — add and install it through zcode's own
plugin/marketplace command.

**Antigravity (agy)** installs the repo itself as a plugin — the root
`plugin.json` marks it, `skills/` carries the skills, and the committed
root `agents/` provides the five archetype personas:

```shell
agy plugin install /path/to/SpecDevKit   # or the git URL
```

**opencode, Factory Droid, and Kilo** need no install step of their
own: opencode and Droid scan `~/.agents/skills/**/SKILL.md` as a
compatibility root, and Kilo gets BOTH that compatibility copy and
its own native root `~/.config/kilo/skills/` (D-040) — all populated
by `tools/sync.sh`. Their
agent defs (`~/.config/opencode/agents/`, `~/.factory/droids/`,
`~/.config/kilo/agent/`) and Kilo's commands
(`~/.config/kilo/command/`) are generated by the same sync run **only
when the harness's own config home exists** — sync never fabricates a
harness directory; install the harness, re-run sync, and the defs
appear. Kilo has no dynamic workflow runtime: the pipeline stages run
inline per each skill's SKILL.md (the same fallback path opencode and
Droid use), and its "workflows" surface (markdown auto-converted to
commands) is deliberately not targeted.

This repo is private: the installing machine needs git credentials with
access already configured (the same requirement as any private
`git clone`) — there's no separate plugin-specific auth step.

Known cosmetic gap: each spec-suite skill's `_shared-protocol.md`
(shared prose every role brief points at, not a role itself) sits
inside `agents/` and gets picked up by Claude Code's default
agent-directory scan alongside the real roles, surfacing as one extra,
inert `<skill>:_shared-protocol` entry — `claude plugin validate`
reports it as a warning, not an error.

Regenerate the manifests after adding a skill, bumping a skill's
VERSION, or editing a SKILL.md description (derived, regenerate-only —
never hand-edited, same as `tools/omp-defs.py`'s output):

```bash
python3 tools/plugin-manifest.py
```

## Install (manual, vendored copy)

No dependencies to install — Python ≥ 3.10, stdlib only. `tools/sync.sh`
(repo root) installs **every** skill under `skills/*/` into **every**
supported harness root in one pass, then SHA-verifies the result — edits
always land in `skills/<name>/` first; this script is the only thing
that copies out:

- **Skill directory** — `skills/<name>/` → `~/.claude/skills/<name>/`,
  `~/.zcode/skills/<name>/`, `~/.agents/skills/<name>/`, and
  `~/.omp/agent/skills/<name>/` (omp's native, priority-100 root — omp
  sessions load this copy). Project-level equivalents (`.claude/skills/`,
  `.zcode/skills/`, `.agents/skills/`, `.omp/skills/`) are the same
  shape, one level up, for a project that vendors its own copy instead of
  installing globally. Run `skills/spec-shape/scripts/skill-dir.sh`
  from a workspace to print the active skill dir — the
  orchestrator resolves it once per session and carries it in every
  spawn payload.
- **Agent defs** — a skill's `agents/*.md` (excluding `_`-prefixed shared
  prose like `_shared-protocol.md`) → `~/.claude/agents/` as-is, and →
  `~/.omp/agent/agents/` regenerated with omp frontmatter by
  `tools/omp-defs.py` (omp skips `~/.claude/agents`, and its tool
  registry is lowercase, so the Claude frontmatter can't be copied as-is
  — the generator derives omp's `tools:`/`model:`/`thinking-level:` by
  parsing each role's own Claude-side `tools:`/`model:`/`effort:`
  directly; no per-role table to maintain when a new skill's roles use
  the same frontmatter shape). zcode currently gets no agent-def install
  step: SKILL.md documents it as having no user-installable agent types,
  so its roles run through the harness-neutral fallback spawn instead
  (frontmatter-stripped brief body + `_shared-protocol.md` verbatim +
  input payload). A skill with no `agents/` dir (a pure-instruction
  skill) skips this step entirely.
- **Optional-harness agent defs** — where `~/.config/opencode/`,
  `~/.factory/`, or `~/.config/kilo/` exists, `tools/agent-defs.py`
  regenerates the same roles as opencode subagents (a permission map
  derived from each brief's own `tools:`), as Factory droids (Task-tool
  `subagent_type` targets; `model: inherit` always — cost tiers ride
  the Task `complexity` argument, not the def), and as Kilo subagents
  (`mode: subagent` + the same derived permission map, `task` always
  denied — Kilo agents take no `tools:` frontmatter of their own).
  Absent homes are skipped loudly, never created.
- **Droid commands** — where `~/.factory/` exists, the same sync run
  installs the routers and lifecycle wrappers to `~/.factory/commands/`
  (gated on the harness home, never fabricated).
- **Kilo commands** — where `~/.config/kilo/` exists, the same sync run
  installs the routers and lifecycle wrappers to
  `~/.config/kilo/command/` (gated on the harness's global config dir,
  never fabricated — the same shape as the droid block). Kilo reads
  `$1`…`$N`/`$ARGUMENTS` template variables the wrappers already use.
- **The loop engine** — no per-harness workflow dialects ship anymore
  (ADR-035): `graph.py --run` is the one frontier-loop engine, driven
  by any session on any harness through its `--runner` seam; `--dry-run`
  plans a run without executing, `--launch-check` says when automation
  pays. The harness-glue cost (two dialect masters per workflow, parity
  suites, installers) is deleted outright.
- **Antigravity personas** — the repo-root `agents/` dir is a
  committed, regenerate-only byte-verbatim copy of the skills' briefs:
  `agy plugin install` copies the repo wholesale, so the personas ship
  in-tree; sync.sh regenerates and verifies them every run.
- **Commands** — a skill's `commands/<name>.md` router (only if it
  ships one) plus each skill's bare names opted into via its own
  `commands/extra.txt` (ADR-013 — `/spec-idea` claims spec-intent,
  `/spec-gen` claims spec-shape) — five commands total, exactly one
  per skill (spec-execute D-033: its build/test/review/ship ride
  `/spec-execute` as verbs) →
  `~/.agents/commands/`, `~/.claude/commands/`,
  `~/.zcode/commands/` (omp needs none — `/skill:<name>`
  auto-registers); a foreign file at a destination is refused, not
  clobbered (per-root provenance ledger).

## Usage

Two invocation surfaces:

### Lifecycle commands (DEFINE → SHIP)

```text
  DEFINE          PLAN           BUILD          VERIFY         REVIEW          SHIP
 ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐
 │ Idea │ ───▶ │ Spec │ ───▶ │ Code │ ───▶ │ Test │ ───▶ │  QA  │ ───▶ │  Go  │
 │Refine│      │  PRD │      │ Impl │      │Debug │      │ Gate │      │ Live │
 └──────┘      └──────┘      └──────┘      └──────┘      └──────┘      └──────┘
  /spec-idea   /spec-gen     /spec-execute build · test · review · ship
```

`/spec-brainstorming` is the optional stage BEFORE this lifecycle:
five rigid stages — one clarifying question, a parallel three-lens
panel (Visionary / Cynic / Minimalist), a trade-off matrix, socratic
refinement — ending in a design specification at
`brainstorms/<name>.md`. It writes nothing under `specs/`; the doc is
pointed at as intent input for `/spec-idea <name>`, not parsed.

| Command | Lands on |
|---|---|
| `/spec-idea <name>` | spec-intent's intake: scout + grill until the question frontier is empty, producing a validated `intent.md` (a bug takes the bugfix deltas) |
| `/spec-gen <spec>` | spec-shape's authoring waves: draft spec.md from the intent, then survey → plan ∥ tech ∥ qa → tasks → verify, to the approve gate |
| `/spec-execute build <spec> [T###]` | spec-execute's implementer waves; nothing ticked or committed |
| `/spec-execute test <spec>` | the proof pass: every TC pass condition green + regression gate |
| `/spec-execute review <spec>` | review instruments: scope diff, cleanliness sweep, implementation-diff review, DoD scorecard |
| `/spec-execute ship <spec>` | tick with proof notes, implementation commit C1 + delivery-record C2, `Status: done`, archive on request |

`/spec-execute test`, `review`, `ship` are three steps of the ONE
delivery pass,
never three gates. "Prod" means production-READY (ADR-014):
the flow ends at a verified single commit; push/deploy/publish stay
human/CI gates. On omp the entries are `/skill:spec-intent`,
`/skill:spec-shape`, `/skill:spec-execute`.

### Router verbs

`/spec-idea`, `/spec-gen`, `/spec-execute` each take
`<verb> <spec-name>` — single nodes and repair runs (or naturally:
"re-survey the auth spec"):

| Verb | Does |
|---|---|
| `scaffold <name>` | `scripts/scaffold.sh [--tier tiny\|full] <name>` (default tiny — the one-file contract), then draft spec.md with the user (clarify loop: grilling — batched frontier rounds of the draft's gaps) |
| `graph <spec>` | the workflow graph's live picture: `scripts/graph.py specs/<spec>` (`--state-json`, `--mermaid`, `--explain <node>`) |
| `run <spec>` | continue the pipeline from current doc state: `scripts/graph.py specs/<spec> --run --span intent\|shape\|execute\|full` — waves run, `AWAITING HUMAN` at every judgment node; `--runner` template for real spawns, `--dry-run`, `--max-waves N` |
| `resume <spec>` | the same continuation, worked manually per SKILL.md (orchestrator judgment at every step) |
| `survey` `research` `plan` `tech` `qa` `tasks` `review` | single-agent runs of one node (repair/refresh; `check.py` after) |
| `check <spec>` | `scripts/check.py specs/<spec>` and triage the output |
| `freeze <spec>` | after an explicit user yes only: `scripts/freeze.py <spec> --record` writes the approval hash manifest |
| `converge <spec>` | re-survey, then `scripts/audit.py converge specs/<spec> --repo <path>` (`--repo` defaults to the spec dir's grandparent); append a task per NEW GAP/REGRESSED |
| `implement <spec> [T###]` | the execute node: waves of implementer agents; nothing commits until the plan-wide delivery pass proves every task |
| `archive <spec>` | after `Status: done`: `scripts/archive.sh <spec>` moves the dir to `specs/archive/<date>-<name>/` and repoints INDEX |

A typical pass: `scaffold` → author spec.md with the user → resolve the
researcher gate → wave 1 (survey ∥ research) → wave 2 (plan ∥ tech ∥ qa)
→ tasks → verify (`check.py` green) → pre-flight (baseline green on the
spec's branch) → user
approval → approval freeze (`freeze.py --record`) → execute (implementer
waves) → delivery pass (proofs, regression, review instruments) →
ticks → implementation commit C1 →
delivery-record commit C2 → `archive`.

### The engine — graph.py --run (one loop, every harness)

The same loop runs through ONE engine on every harness:
`scripts/graph.py specs/<name> --run [--runner '<template>']` — doc
state in, self-contained payloads out, the runner invoked per payload,
recompute, repeat; it **stops `AWAITING HUMAN` at every judgment
gate**. Same graph, same gates: the engine is the mechanical
wave-runner, the session keeps every judgment. The recommended shape
alternates the two — 

| Step | Surface | What happens |
|---|---|---|
| 1 | session — `/spec-idea <name>`, then `/spec-gen <name>` | intake grills the idea into a validated intent.md; spec-gen drafts spec.md from it (clarify loop) and decides the researcher gate: `skip` → keep the not-applicable marker; `run` → replace research.md with the template and spawn the researcher out-of-band |
| 2 | engine — `graph.py --run --span shape` | survey ∥ research → plan ∥ tech ∥ qa → tasks → verify, then **stops `AWAITING HUMAN: approve`** |
| 3 | session | pre-flight (baseline green on the spec's branch), present the docset, get approval → `Status: approved` + `freeze.py --record` |
| 4 | engine — rerun `--run --span execute` | execute waves hands-off: one implementer per runnable task, one automatic re-brief round carrying the failure digest verbatim (D-020); **stops `AWAITING HUMAN: tick-commit`** |
| 5 | session — `/spec-execute test/review/ship` | the delivery-pass steps: proofs + regression, review instruments, then tick + C1/C2 |

Rules of thumb: the loop stops `AWAITING HUMAN` at every judgment
gate — resolve the gate in-session, rerun, and the loop resumes from
doc state (reruns are cheap; the docs are the only state). Authoring
never runs automated: an unauthored spec reports `held` with the
reason. Small specs (≤3 FRs) are usually faster fully in-session; the
engine earns its keep on execute-heavy plans (`--launch-check` says
when). The default `print` runner echoes invocations (`--dry-run`
with payloads written); wire a real runner (a spawn command, a cron
wrapper for post-approve spans — they park at the tick-commit gate by
design) per harness.

## Scripts reference

The shared core ships in every spec-suite skill's `scripts/`
(byte-identical, mastered at `skills/spec-shape/scripts/`); the
execute-only machinery ships with spec-execute. Run from a workspace
root:

| Script | Purpose |
|---|---|
| `scaffold.sh [--tier tiny\|full] <name> [root]` | create `specs/<name>/` (`tiny`: spec.md only, the default; `full`: the seven templates), register in INDEX; refuses overwrite, requires kebab-case |
| `check.py <spec-dir>` | the doc-set validator: 7 files, FR/NFR→T→TC traceability, parallel-touch overlap, burndown, status-bleed, citation reality, staleness, freeze integrity, constitution; `--survey-only`, `--intent-only`, `--next-ids`, `--constitution`, `--fix-burndown`, `--checklist`, `--repo <path>` |
| `freeze.py <spec-dir>` | approval freeze: `--record` writes the approved-doc hash manifest after explicit sign-off (existing manifests refuse overwrite; `--record --force` represents a fresh approval); `--verify` is read-only |
| `audit.py <sub> <spec-dir>` | review instruments: `scope` (defaults to the approval-freeze SHA), `clean`, `proofs --run`, `mutate` (mutation testing over the changed files), `coverage` (line-coverage floor over the tasks' intended files), `dod`, `converge`; `archived` (no spec-dir) — every archived plan fully closed |
| `graph.py <spec-dir>` | the workflow engine: frontier report, `--state-json`, `--mermaid`, `--explain <node>`, `--emit-spawns` (`--wave-dir <dir>` relocates payloads), `--run [--runner] [--dry-run] [--max-waves N]`, `--span intent\|shape\|execute\|full` |
| `tick.py` | the atomic task tick with its proof note (spec-execute) |
| `migrate.py grow <spec-dir>` | promote a tiny-tier docset to the full seven-file contract, ids preserved (spec-execute) |
| `archive.sh <name> [root]` | move a `Status: done` spec to `specs/archive/<date>-<name>/`, repoint INDEX |
| `skill-dir.sh` | print the active skill directory (spawn-payload `skill_dir`) |

**Non-git honesty**: in a non-git repo, git-derived behavior degrades
loudly — explicit `SKIPPED (not a git repo)` notices from audit.py's
scope/clean, check.py's staleness line, and the commit step — never a
silent false all-clear.

## Adding a skill to this repo

A further skill needs no change to `tools/sync.sh`, `tools/omp-defs.py`,
or `tools/agent-defs.py` — all three discover skills structurally, by
walking `skills/*/`, never by a hardcoded name:

1. `skills/<name>/SKILL.md` — required; its frontmatter (`name`,
   `description`) is what every harness's skill loader reads. This alone
   is enough for a pure-instruction skill.
2. `skills/<name>/agents/*.md` — optional. Ship one file per spawnable
   role: Claude-style frontmatter (`name`, `description`, `model`,
   `tools`, optionally `effort`, `disallowedTools`) with the full brief
   as the body — `tools/omp-defs.py` derives the omp-side def from this
   directly at sync time, and `tools/agent-defs.py` derives the
   opencode/droid/kilo defs and the agy persona copy from the same
   frontmatter.
   A shared, non-role file (protocol text every role's brief points at, e.g. this
   suite's `_shared-protocol.md`) is named with a leading `_` so it's
   excluded from both the Claude-agents copy and the omp-defs
   generation. Pick a role-name prefix unique to the skill (`spec-` for
   this suite) — it scopes omp-defs.py's stale-file cleanup in the shared
   `~/.omp/agent/agents/` directory, so regenerating one skill's defs
   never deletes another's.
3. `skills/<name>/commands/<name>.md` — optional: a router command
   (`/<name> <verb> …`) if the skill benefits from one — lives inside
   the skill dir so it stays a self-contained plugin root.
   Bare-name commands (`/spec-idea`, `/spec-gen`) are an
   explicit per-skill opt-in — a `commands/extra.txt` file in the
   skill (one line of space-separated bare names; ADR-013) — because
   generic names land flat in shared global command roots; the
   skill-named router needs no entry.
4. `skills/<name>/tests/` — expected for anything with its own scripts;
   each skill owns and runs its own suite
   (`skills/spec-shape/tests/run.sh` is the existing example). Changes
   to the shared install tooling itself are covered separately, by
   `tools/tests/`.
5. Run `tools/sync.sh` from anywhere in the repo — it discovers the new
   `skills/<name>/` automatically and installs it alongside every other
   resident skill.
6. Run `tools/plugin-manifest.py` to (re)generate the new skill's
   `.claude-plugin/plugin.json` and refresh the repo-root marketplace
   catalog so `/plugin install <name>@spec-dev-kit` picks it up too.

## Repository layout

```
.claude-plugin/marketplace.json  # plugin-marketplace catalog, one entry per skill (tools/plugin-manifest.py)
plugin.json                     # Antigravity plugin marker — `agy plugin install <repo>` consumes the repo root
agents/                         # agy personas: byte-verbatim brief copies (committed, regenerate-only)
LICENSE
skills/
├── spec-intent/            # phase 1 — pre-spec intake: scout + grill → validated intent.md
├── spec-shape/             # phase 2 — gated authoring: intent → approved docset; the shared-core MASTER
│   │                       #   (graph.py · check.py · contract.py · specstate.py · telemetry.py · freeze.py),
│   │                       #   the workflow node table (scripts/contract.py), and the workflow diagram live here
│   ├── SKILL.md            # the authoring playbook (workflow graph node table, spawn mechanics, rules)
│   ├── .claude-plugin/plugin.json  # this skill's plugin manifest (tools/plugin-manifest.py)
│   ├── commands/           # the /spec-gen router
│   ├── agents/*.md         # 5 archetype briefs = harness defs (frontmatter + body) + _lenses.md lens table + _shared-protocol.md
│   ├── templates/          # 7 scaffolded doc templates + assurance/release records
│   ├── scripts/            # the shared core (master copy) + scaffold.sh · skill-dir.sh
│   ├── decisions/          # this skill's ADRs — including the moved monolith history and the retirement map (D-002)
│   ├── diagrams/           # workflow graph (.mmd + 1 HTML render)
│   ├── examples/mini-spec/ # green fixture used by the test suite
│   └── tests/ · evals/ · VERSION · CHANGELOG.md
├── spec-execute/           # phase 3 — post-approve: implementer waves, delivery pass, tick/commit gates;
│   │                       #   the four lifecycle commands (spec-build…spec-ship) + execute-only machinery
│   │                       #   (tick.py · audit.py · archive.sh · migrate.py)
├── spec-code-review/       # portable three-stage gated code review (same skeleton, own test suite)
└── spec-brainstorming/     # five-stage pre-spec brainstorm panel (own test suite)
tools/
├── sync.sh                 # shared installer: every skills/<name>/ → every harness root, SHA-verified
├── parity.py               # shared: regenerates the shared core from the spec-shape master into every replica
├── omp-defs.py             # shared: Claude-style agents/*.md frontmatter → omp task-agent frontmatter
├── agent-defs.py           # shared: Claude-style agents/*.md frontmatter → opencode / droid / kilo / agy defs
├── plugin-manifest.py      # shared: generates .claude-plugin/marketplace.json + per-skill plugin.json
├── kit-rules.py            # shared: injects rules/engineering-rules.md into the § Engineering rules carriers
├── drift-check.py          # shared: release-validate generated surfaces against their canonical sources
├── evals.py                # shared: list/run/validate the skills' standing eval cases, record results
├── ownership.py            # shared: ownership-plan primitives — classify destinations against the provenance ledger before sync writes
└── tests/                  # suite for the shared tooling itself (bash tests/run.sh)
```

A skill owns everything under its own `skills/<name>/` — including
whether it needs `tools/`-shaped subdirectories of its own (the suite
doesn't: its install tooling is the repo-shared one above).

## Development

Release procedure: [RELEASE.md](RELEASE.md) — the ordered gate checklist
every version ships through.

From the repo root:

```bash
bash tools/tests/run.sh                                         # shared install-tooling suite
python3 tools/plugin-manifest.py                                # regenerate plugin/marketplace manifests
claude plugin validate ./skills/spec-shape                      # sanity-check a skill's plugin manifest
agy plugin validate .                                          # Antigravity plugin shape (skills + agents)
```

From `skills/spec-shape/`:

```bash
bash tests/run.sh                                              # full suite
python3 scripts/check.py examples/mini-spec/specs/mini-spec    # fixture green
python3 scripts/graph.py examples/mini-spec/specs/mini-spec --state-json
```

Normative docs: each skill's `SKILL.md` is its orchestrator entry
point (`spec-shape/SKILL.md` carries the workflow graph's node table);
the docset contract lives in `scripts/check.py` and the scaffold
templates; `decisions/` records why (read
`skills/spec-shape/decisions/010-graph-dynamic-workflow.md` for the
graph refactor and `002-retirement-of-spec-to-prod.md` for the split's
move map).
