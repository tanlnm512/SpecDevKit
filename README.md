# spec-to-prod

Spec-driven development as a skill suite: an orchestrator (your main
session) plus eight role agents produce an execution-ready, grounded doc
set per feature under `specs/<name>/` — `spec.md`, `plan.md`, `task.md`
(the status holder), `tech-spec.md`, `test.md`, with `survey.md` and
`research.md` as evidence — every artifact mechanically verified by
`scripts/check.py` and scheduled by a **dynamic state graph**
(`scripts/graph.py`), not a fixed stage ladder.

This repo — published on GitHub as **SpecDevKit**
(`tanlnm512/SpecDevKit`) — is a **skillset**, not a single-skill package:
every skill lives at `skills/<name>/`, and one shared, harness-neutral install
pipeline (`tools/sync.sh`) installs every skill it finds there to every
supported coding-agent harness in one pass. `spec-to-prod` is the first
resident skill; § Adding a skill to this repo below is the contract a
second one follows.

The single organizing rule: **the doc state under `specs/<name>/` is the
only state.** Every workflow node's readiness is derived from it; nothing
else (no session log, no step ledger) is consulted.

## How the workflow works

Scheduling is a frontier computation over a graph of sixteen nodes (the
eight role agents plus orchestrator/mechanical nodes: spec, clarify,
research-gate, verify, before-audit, approve, execute, closing-audit,
tick-commit, archive):

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
(spec.md `Status: approved`), the closing-audit judgment (including
rulings), and tick-commit. `graph.py --run` pauses with
`AWAITING HUMAN: <node>` at each and waits; the auto-trigger loop runs
only the mechanical verify node (check.py) itself and hands agent waves
to a configurable `--runner`.

Audits run exactly twice per plan: the **before-audit** once, when the
execution frontier first becomes eligible, and the **closing audit**
once, after every task is implemented. Nothing is ticked or committed in
between.

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
/plugin install spec-to-prod@spec-dev-kit
```

**omp (Oh My Pi)** reads the same `.claude-plugin/marketplace.json` as
its Claude-Code-compatible fallback — no separate `.omp-plugin/` catalog
is published, since the content would be identical:

```
/marketplace add tanlnm512/SpecDevKit
/marketplace install spec-to-prod@spec-dev-kit
```

**zcode** understands the same marketplace.json shape (its own local
plugin state already tracks `anthropics/claude-plugins-official` as a
GitHub-sourced marketplace) — add and install it through zcode's own
plugin/marketplace command.

This repo is private: the installing machine needs git credentials with
access already configured (the same requirement as any private
`git clone`) — there's no separate plugin-specific auth step.

Known cosmetic gap: `_shared-protocol.md` (shared prose every role brief
points at, not a role itself) sits inside `agents/` and gets picked up by
Claude Code's default agent-directory scan alongside the 8 real roles,
surfacing as one extra, inert `spec-to-prod:_shared-protocol` entry —
`claude plugin validate` reports it as a warning, not an error.

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
  installing globally. Run `skills/spec-to-prod/scripts/skill-dir.sh`
  from a workspace to print spec-to-prod's active skill dir — the
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
- **Command router** — a skill's `commands/<name>.md` (only if it ships
  one, installed from `skills/<name>/commands/<name>.md`) →
  `~/.agents/commands/`, `~/.claude/commands/`, `~/.zcode/commands/`
  (omp needs none — `/skill:<name>` auto-registers).

## Usage

Invoke via the router (`/spec-to-prod <verb> <spec-name>`) or naturally
("re-survey the auth spec"). Verbs:

| Verb | Does |
|---|---|
| `scaffold <name>` | `scripts/scaffold.sh <name>`, then draft spec.md with the user (clarify loop: batched frontier rounds of the draft's gaps) |
| `bugfix <name>` | same, with the `references/bugfix.md` deltas (bug narrative, unchanged-behavior FRs, failing repro first) |
| `graph <spec>` | the workflow graph's live picture: `scripts/graph.py specs/<spec>` (`--state-json`, `--mermaid`, `--explain <node>`) |
| `run <spec>` | continue the full pipeline from current doc state: `scripts/graph.py specs/<spec> --run` — waves run, `AWAITING HUMAN` at every judgment node; `--runner` template for real spawns, `--dry-run`, `--max-waves N` |
| `resume <spec>` | the same continuation, worked manually per SKILL.md § Resuming (orchestrator judgment at every step) |
| `survey` `research` `plan` `tech` `qa` `tasks` `review` | single-agent runs of one node (repair/refresh; `check.py` after) |
| `check <spec>` | `scripts/check.py specs/<spec>` and triage the output |
| `converge <spec>` | re-survey, then `scripts/audit.py converge specs/<spec> --repo <path>` (`--repo` defaults to the spec dir's grandparent); append a task per NEW GAP/REGRESSED |
| `implement <spec> [T###]` | the execute node: waves of implementer agents; nothing ticks or commits until the plan-wide closing audit passes |
| `archive <spec>` | after `Status: done`: `scripts/archive.sh <spec>` moves the dir to `specs/archive/<date>-<name>/` and repoints INDEX |

A typical pass: `scaffold` → author spec.md with the user → resolve the
researcher gate → wave 1 (survey ∥ research) → wave 2 (plan ∥ tech ∥ qa)
→ tasks → verify (`check.py` green) → before-audit (six gates, record
`Before-audit: passed @ <sha>` or `@ -` in a non-git repo) → user
approval → execute (implementer waves) → closing audit → one tick +
commit → `archive`.

## Scripts reference

All under `skills/spec-to-prod/scripts/`, run from a workspace root:

| Script | Purpose |
|---|---|
| `scaffold.sh <name> [root]` | create `specs/<name>/` from templates, register in INDEX; refuses overwrite, requires kebab-case |
| `check.py <spec-dir>` | the doc-set validator: 7 files, FR→T→TC traceability, burndown, status-bleed, citation reality, staleness, constitution; `--survey-only`, `--next-ids`, `--constitution`, `--fix-burndown`, `--checklist`, `--repo <path>` |
| `audit.py <sub> <spec-dir>` | closing-audit halves: `scope`, `clean`, `proofs --run`, `dod`, `converge` |
| `graph.py <spec-dir>` | the workflow engine: frontier report, `--state-json`, `--mermaid`, `--explain <node>`, `--emit-spawns` (`--wave-dir <dir>` relocates payloads), `--run [--runner] [--dry-run] [--max-waves N]` |
| `archive.sh <name> [root]` | move a `Status: done` spec to `specs/archive/<date>-<name>/`, repoint INDEX |
| `skill-dir.sh` | print the active skill directory (spawn-payload `skill_dir`) |

**Non-git honesty**: in a non-git repo, git-derived behavior degrades
loudly — explicit `SKIPPED (not a git repo)` notices from audit.py's
scope/clean, check.py's staleness line, and the commit step — never a
silent false all-clear.

## Adding a skill to this repo

A second skill needs no change to `tools/sync.sh` or `tools/omp-defs.py`
— both discover skills structurally, by walking `skills/*/`, never by a
hardcoded name:

1. `skills/<name>/SKILL.md` — required; its frontmatter (`name`,
   `description`) is what every harness's skill loader reads. This alone
   is enough for a pure-instruction skill.
2. `skills/<name>/agents/*.md` — optional. Ship one file per spawnable
   role: Claude-style frontmatter (`name`, `description`, `model`,
   `tools`, optionally `effort`, `disallowedTools`) with the full brief
   as the body — `tools/omp-defs.py` derives the omp-side def from this
   directly at sync time, no edit to the generator needed. A shared,
   non-role file (protocol text every role's brief points at, e.g. this
   skill's `_shared-protocol.md`) is named with a leading `_` so it's
   excluded from both the Claude-agents copy and the omp-defs
   generation. Pick a role-name prefix unique to the skill (`spec-` for
   this one) — it scopes omp-defs.py's stale-file cleanup in the shared
   `~/.omp/agent/agents/` directory, so regenerating one skill's defs
   never deletes another's.
3. `skills/<name>/commands/<name>.md` — optional: a router command
   (`/<name> <verb> …`) if the skill benefits from one — lives inside
   the skill dir so it stays a self-contained plugin root.
4. `skills/<name>/tests/` — expected for anything with its own scripts;
   each skill owns and runs its own suite
   (`skills/spec-to-prod/tests/run.sh` is the existing example). Changes
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
LICENSE
skills/
└── spec-to-prod/           # first resident skill — a self-contained plugin root
    ├── SKILL.md            # the orchestrator's playbook (workflow graph, spawn mechanics, rules)
    ├── .claude-plugin/plugin.json  # this skill's plugin manifest (tools/plugin-manifest.py)
    ├── commands/spec-to-prod.md    # router command — installed by tools/sync.sh, auto-discovered as a plugin
    ├── agents/spec-*.md    # 8 role briefs = harness defs (frontmatter + body) + _shared-protocol.md
    ├── contracts/docset.md # canonical doc-set/ownership/payload contract
    ├── gates/              # before-audit (6 gates) + dod (10-gate scorecard)
    ├── templates/          # the 7 scaffolded doc templates
    ├── scripts/            # scaffold.sh · check.py · audit.py · graph.py · archive.sh · skill-dir.sh · specstate.py
    ├── decisions/          # this skill's own ADRs (D-001…D-012)
    ├── diagrams/           # workflow graph (.mmd + 2 HTML renders)
    ├── references/         # bugfix deltas, mermaid cheatsheet
    ├── evals/              # prepared eval cases
    ├── examples/mini-spec/ # green fixture used by the test suite
    ├── observations/       # living open-items list
    ├── tests/              # this skill's own stdlib unittest suite (bash tests/run.sh)
    └── VERSION · CHANGELOG.md
tools/
├── sync.sh                 # shared installer: every skills/<name>/ → every harness root, SHA-verified
├── omp-defs.py             # shared: Claude-style agents/*.md frontmatter → omp task-agent frontmatter
├── plugin-manifest.py      # shared: generates .claude-plugin/marketplace.json + per-skill plugin.json
└── tests/                  # suite for the shared tooling itself (bash tests/run.sh)
```

A skill owns everything under its own `skills/<name>/` — including
whether it needs `tools/`-shaped subdirectories of its own (spec-to-prod
doesn't: its install tooling is the repo-shared one above).

## Development

From the repo root:

```bash
bash tools/tests/run.sh                                         # shared install-tooling suite
python3 tools/plugin-manifest.py                                # regenerate plugin/marketplace manifests
claude plugin validate ./skills/spec-to-prod                    # sanity-check a skill's plugin manifest
```

From `skills/spec-to-prod/`:

```bash
bash tests/run.sh                                              # full suite
python3 scripts/check.py examples/mini-spec/specs/mini-spec    # fixture green
python3 scripts/graph.py examples/mini-spec/specs/mini-spec --state-json
```

Normative docs: `skills/spec-to-prod/SKILL.md` is that skill's
orchestrator entry point; `contracts/docset.md` is canonical for file
ownership and payloads; `decisions/` records why (read
`decisions/010-graph-dynamic-workflow.md` for the graph refactor).
