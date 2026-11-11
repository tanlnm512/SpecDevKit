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
| role agent | a spawned sub-agent with exclusive artifact ownership, named for its job role (`spec-<role>` in the spec suite and discovery, `review-<role>` in spec-review; installed as native subagent types where the harness has them) | `skills/<name>/agents/*.md` |
| brief | an agent-definition markdown file in `skills/<name>/agents/`; its frontmatter-stripped body IS the system prompt | same |
| generated view | a root `agents/*.md` file, regenerated from a skill brief by `tools/agent-defs.py` — never hand-edited | `AGENTS.md` house rules |
| panel | a concurrent wave of role agents, one lens each, over a shared protocol (`protocol/panel-protocol.md`) (spec-discover: Visionary / Cynic / Minimalist; spec-review: correctness / security / quality) | `contracts/panel.md`, `contracts/run.md` |
| payload | the self-contained spawn input — skill_dir, problem restatement, brief body, lens section, protocol text, evidence pack | `skills/spec-discover/contracts/run.md` |
| digest | the only return value a spawned lens or panel agent produces; its grammar is fixed per skill | same |
| evidence pack | the external context gathered before a brainstorm panel spawns | `skills/spec-discover/SKILL.md` (stage 2) |
| idea brief | spec-discover's durable output at `brainstorms/<name>.md` — the chosen direction, problem, personas, MVP cut, risks, and kill criteria, ready to feed `/spec-define`; never a spec and never a design | `skills/spec-discover/templates/idea-brief.md` |

### Scheduling and state (the spec suite: spec-define · spec-design · spec-build)

| Term | Means | Canonical home |
|------|-------|----------------|
| doc-set | the seven files under `specs/<name>/` at `Tier: full` — the canonical statement of what a spec dir IS; at `Tier: tiny` the doc-set is ONE file (spec.md with § Tasks) | `skills/spec-design/scripts/check.py` (the docset discipline) |
| contract file / evidence file | the two doc-set classes: spec / plan / tech-spec / task / test are Contract; survey / research are Evidence | same (check discipline) |
| contract tier | `**Tier**: tiny \| full` on spec.md — one-file contract vs the seven-file docset (D-037); absent reads full | `skills/spec-design/decisions/037` |
| work type | `**Type**: feature \| bugfix \| hotfix \| refactor \| upgrade` on spec.md (intent.md seeds it); absent reads feature. bugfix adds the red repro and root-cause deltas, hotfix is a bugfix at `Tier: tiny`, refactor and upgrade preserve behavior — stories and ACs optional, a `**Preserves**:` test case required | `skills/spec-design/decisions/056-sdlc-coverage-in-define-and-design.md` |
| `**Depends on**` | optional spec.md header naming the specs this one builds on; check.py refuses a name that is no spec, warns while one is unapproved, and warns when another in-flight spec's `Touches:` overlap this spec's | same |
| `specs/INDEX.md` line | the cross-spec view's one line per spec — `- [<name>](<path>/spec.md) — <status> · <type> · <tier>[ · depends on …]` — rendered by `scripts/index.py`, its only writer; never hand-edited | `skills/spec-design/scripts/index.py` (the parity master) |
| Interfaces & data | the tech-spec.md section naming API shapes, data-model changes, migrations, and compatibility; required at full tier, `none — <reason>` allowed; a user-facing UI adds its `### UX` subsection (flows, empty/error/loading states, accessibility) | `skills/spec-design/decisions/056-sdlc-coverage-in-define-and-design.md` |
| Rollout | plan.md § Delivery's `### Rollout` subsection — exposure, migration order, rollback trigger, post-release check, or `none — <reason>`; it must agree with the tech-spec's rollback column | same |
| archetype | one of the five spec-suite agent briefs (the outward phases add integrator and release-manager, below), each named for its job role — analyst (`spec-analyst`) · architect (`spec-architect`) · tester (`spec-tester`) · developer (`spec-developer`) · auditor (`spec-auditor`); spec-discover's panelist is `spec-panelist`; harness def and brief are the same file (D-036) | `skills/spec-*/agents/` (byte-shared across the trio) |
| protocol / `protocol/` dir | a skill's shared prose its briefs point at — lens table, shared or panel protocol — kept in `protocol/`, never `agents/`, so no harness registers it as an agent (D-049) | `skills/*/protocol/` |
| lens | a specialization riding a spawn payload from `protocol/lenses.md` (survey/research on analyst; plan/tech/tasks on architect; the three panel angles) — data, not a brief file (D-036) | `skills/*/protocol/lenses.md` |
| constitution lens | the analyst lens that proposes `specs/CONSTITUTION.md` articles from the repo's observed conventions (tooling, test style, dependency policy, layering), each cited to evidence; it writes nothing — the user confirms every article. Emitted by `graph.py --emit-spawns --repair constitution` | `skills/spec-design/protocol/lenses.md` |
| primitive | a model-invoked discipline reference an orchestrator composes — grilling, diagnosing, domain-language (D-039) | `skills/spec-define/references/` (grilling; the monolith's tree is retired) |
| status holder | the one file that carries status: task.md at full tier, spec.md § Tasks at tiny — no other file holds status (C-01, amended by D-037) | `skills/spec-design/decisions/037-thin-floor.md` |
| frontier | every graph node that is ready and not done; the only scheduler — nothing schedules by stage number | `skills/spec-design/SKILL.md` (the generated node table) |
| wave | one concurrent run of the whole frontier; recompute after each wave | same |
| tick | the mechanical, atomic `- [ ] T###` → `- [x]` promotion with its `done <date> — <proof>` sub-line | `skills/spec-build/scripts/tick.py` |
| freeze | the approval freeze applied to the doc-set before execution; `approvals/approval.md` is its record, required at both tiers for an approved spec; at tiny tier it covers the § Tasks list less its status markers (D-050, D-051, D-052) | `skills/spec-design/scripts/freeze.py` (the parity master) |
| `**Approved-by**` | a line in `approvals/approval.md` naming one person who signed the approval, written by `freeze.py --record --by "<name>"` (repeatable); optional — a record without it is the session user's yes | `skills/spec-design/scripts/freeze.py` |
| `approvals/review.md` | full tier's record of the contract review — the findings digest, one ruling per BLOCK, and the payload's docset fingerprint (a hash of the frozen manifest plus task.md); `freeze.py --record` refuses a missing or stale one; tiny tier has none | `skills/spec-design/decisions/050-approval-records-and-payload-contracts.md` |
| `(fix n/5)` / `(fixed n/5)` | a task entry's fix-round marker: `(fix n/5)` is an OPEN round (the task is runnable again), `(fixed n/5)` the same round landed; `n` counts failures and 5/5 is the cap | `skills/spec-design/decisions/051-engine-enforces-wave-fix-and-tiny-approval.md` |
| deferred | a runnable task the engine left out of this wave because its files overlap a wave-mate or an `(in-progress)` task; printed `deferred: T### (<why>)`, emitted on a later wave | same |
| `--native-agents` | `graph.py --emit-spawns\|--run` flag for a harness with registered agent types: the payload names the type and omits the brief the type already carries; default payloads embed the brief | same |
| `reviewer-diff.patch` | the implementation-diff review's full diff, written beside its auditor payload because the auditor holds no shell; its header lists the untracked files the diff omits | `skills/spec-design/decisions/050-approval-records-and-payload-contracts.md` |
| gate | a check the flow must pass — say mechanical gate (scripts decide: `check.py`, review stage 1) or name the approval gate (verify → approve; the researcher gate); bare "gate" is ambiguous | each skill's SKILL.md |
| automatic regression gate | delivery-pass step 2: `audit.py regression` runs the repo's own checks (spec-review's `gate.sh`, a pinned byte-identical copy) against the approved base — dod gate 3 reads PASS, FAIL, or NONE; NONE (no repo checks detected) is never a pass | `skills/spec-build/decisions/036-sdlc-rows-in-the-delivery-pass.md` |
| delivery note | `specs/<name>/notes/delivery.md` — the delivery pass's own facts (`Docs impact:`, `Rollback:` rulings, `Behavior preserved:`) that dod gates 11–13 read | same |
| docs impact | the delivery note's `Docs impact:` line — the user-facing docs the diff updates (README, API docs, CHANGELOG, migration notes), or `none — <reason>` | same |
| `specs/BACKLOG.md` | the repo's parked-work list, one date-free line each — `- <spec> — <item> (source: <source>)`; `tick.py --park` and spec-review's `backlog_offer` write it, only on the user's yes | same; `skills/spec-review/decisions/019-dependencies-ci-and-the-backlog.md` |
| `retro.md` | an archived spec's retrospective, assembled by `retro.py` at archive from its own records (tasks, fix rounds, decisions, delivery note, parked lines, telemetry counts) — facts, never prose; its D-### titles roll up to `specs/context/decisions.md` | `skills/spec-build/scripts/retro.py` |

### Outward phases (spec-ship · spec-release)

| Term | Means | Canonical home |
|------|-------|----------------|
| outward action | any step that leaves the workspace — push, PR create or edit, posted comment, tag push, GitHub release; runs only on the user's explicit yes to a shown preview, never forced, never merging, never deploying | `skills/spec-ship/gates/outward-actions.md`, `skills/spec-release/gates/cut.md` |
| `Shipped:` record | `Shipped: PR <url>` in the status holder beside `Delivered:` — written by `/spec-ship` once the PR exists; task.md's header at full tier, spec.md § Evidence at tiny | `skills/spec-ship/decisions/002-shipped-record-beside-delivered.md` |
| `Released:` record | `Released: <tag> @ <sha>` in each included spec's status holder, written in a record commit right after the tagged release commit | `skills/spec-release/decisions/002-released-record-placement.md` |
| `notes/ship.md` | `specs/<name>/notes/ship.md` — evidence no task covers (CI output, review comments) that `/spec-ship` writes for `/spec-build` fix rounds; a change outside the approved contract routes to `/spec-design` | `skills/spec-ship/SKILL.md` |
| post-release check | the human-run checklist `/spec-release verify` prints; its outcome lands beside `Released:` as `Post-release check: <tag> pass\|fail <date> — <note>`; a failure routes to `/spec-define <name>` as a hotfix | `skills/spec-release/SKILL.md` |
| integrator | the `spec-integrator` agent — drafts PR wording and classifies review comments for `/spec-ship`; holds no shell and takes no outward action | `skills/spec-ship/agents/integrator.md` |
| release manager | the `spec-release-manager` agent — tightens changelog and release-notes wording from recorded facts for `/spec-release`; writes nothing | `skills/spec-release/agents/release-manager.md` |

### Review (spec-review)

| Term | Means | Canonical home |
|------|-------|----------------|
| mechanical gate | stage 1: the target repo's own checks (Makefile, npm scripts, cargo, go, pytest/unittest, shell syntax, secret shapes) | `skills/spec-review/SKILL.md`, `scripts/gate.sh` |
| finding | a kept review observation with an ID, independently confirmed before it survives triage | `skills/spec-review/contracts/panel.md` |
| verdict | a fix-loop verification outcome for one finding | same |
| shared review oracle | `review_orchestrator.py` — the single home of review state, systems, asks, finding IDs, and report assembly | D-014 |
| probe | one thin per-phase call by which any caller fetches JSON from the oracle (scope, gate, shard, ask, report) | D-014 |
| dialect twin | (retired, D-035) the per-harness workflow scripts deleted with the one-engine move — history only; the shared oracle is the one executable form | `skills/spec-review/decisions/016` |

### Kit plumbing

| Term | Means | Canonical home |
|------|-------|----------------|
| skill dir | `skills/<name>/`, self-contained by packaging (marketplace `source: ./skills/<name>`) | `AGENTS.md` |
| generated surface | any regenerate-only artifact: root `agents/`, the SKILL.md node table (`scripts/contract.py`), the plugin/marketplace manifests, the `§ Engineering rules` sections | `AGENTS.md` house rules |
| ADR (D-###) | an append-only decision record; every divergence from a doc contract gets its own entry (C-05) | `skills/<name>/decisions/` |
| eval case | an entry in a skill's `evals/cases.md`; every increment names its served case (C-10) | `skills/<name>/evals/cases.md` |
| sync | `tools/sync.sh` — the one harness-neutral install pipeline to every machine harness root | `tools/` |
| telemetry | the local append-only run record (`scripts/telemetry.py` → `~/.spec-dev-kit/telemetry/*.jsonl`) — evidence for self-improvement, never status, never contents | `skills/*/scripts/telemetry.py` |
| skill command | one `/spec-*` command per skill, named for it — `/spec-discover`, `/spec-define`, `/spec-design`, `/spec-build`, `/spec-review`, `/spec-ship`, `/spec-release`; spec-build's implement/test/audit/ship ride its router as verbs (D-033) | D-029, spec-build D-033, spec-design D-048, D-054 |
| skill name / agent name | skills are named after SDLC phases (discover → define → design → build → review → ship → release); agents are named after job roles (analyst, architect, tester, developer, auditor, panelist, review-*, integrator, release-manager) | spec-design D-054 |
| lifecycle commands | the skill commands that carry a spec from idea to release, in order: `/spec-define` → `/spec-design` → `/spec-build`, then the outward phases `/spec-ship` → `/spec-release`; `/spec-discover` is the optional step before them and `/spec-review` stands outside the lifecycle | `README.md` Usage |

## Terms to avoid

- **The suite's pre-2.1.0 name** — retired and deliberately not
  spelled out anywhere in this repo; refer to it only as "the former
  name" and never reintroduce it (D-014).
- **Bare `/review`, `/plan`, `/build`, `/test`, `/ship`** — retired by
  D-029; they collide with harness modes and built-ins. Use the
  `/spec-*` forms, and say `spec-review` for standalone review.
- **Retired skill and command names** — `spec-brainstorming`,
  `spec-intent`, `spec-shape`, `spec-execute`, `spec-code-review`
  (released), `spec-intake`, `spec-author` (never released),
  `/spec-idea`, `/spec-gen` (spec-design D-048, D-054): the skills are
  `spec-discover`, `spec-define`, `spec-design`, `spec-build`,
  `spec-review`, `spec-ship`, and `spec-release`, and each command is its skill's name.
- **Retired agent names** — `spec-scout`, `spec-designer`, `spec-qa`,
  `spec-reviewer`, `spec-builder`, `brainstorm-panelist`,
  `code-review-scout`, `code-review-correctness`,
  `code-review-security`, `code-review-quality`, `code-review-fixer`
  (spec-design D-054): say analyst, architect, tester, auditor,
  developer, `spec-panelist`, and `review-*`.
- **`/spec-build build`, `/spec-build review`** — the verbs are
  `implement` and `audit` (D-054), so "build" stays the phase and
  "review" stays spec-review's word.
- **"Design specification" / "design spec"** for spec-discover's
  output — it is an idea brief; "design" names only the spec-design
  phase (D-054).
- **"Workflow dialect" / "twin"** for current surfaces — retired with
  D-035; the term now names history only. Say "the oracle"
  (spec-review) or "`graph.py --run`" (the spec suite's engine,
  shipped by the trio).
- **"Stage" for the spec suite's scheduling** — the pipeline schedules by
  frontier and waves, never by a stage ladder ("Waves, not stages").
  spec-discover and spec-review do have real stages; the word is
  theirs.
- **"Copy" for a root `agents/*.md` file** — it is a generated view;
  "copy" invites hand-editing.
- **Hedged normative verbs in contract text** — "should ideally",
  "try to", "if possible". Acceptance criteria and rule text use
  MUST / MUST NOT / NEVER; if a behavior is genuinely optional, say
  what decides the optionality instead of hedging the verb.

## Flagged ambiguities (resolved)

- **"review"** splits three ways (D-029, D-054): `/spec-build audit`
  is spec-build's implementation-diff review step, run by the
  auditor; `spec-review` is the standalone skill; harness built-ins
  keep their own names.
- **"ship"** covers two things: `/spec-build ship` is the delivery
  pass (local commits C1/C2, `Delivered:`); `/spec-ship` is the
  PR/integration skill (push, PR, CI, review comments, `Shipped:`).
  Name which.
- **"agent"** covers four things — say role agent (spawned), brief
  (the markdown), generated view (root `agents/` file), or AGENTS.md
  (the convention file).
- **"workflow"** covers two things — the workflow graph (scheduling
  semantics, `scripts/contract.py` + the spec-design SKILL.md node
  table) and a workflow run (`graph.py --run` executing one). Name
  which.
- **Byte-identical pairs** (telemetry module copies, lens sections in
  payloads) are edited in every copy at once or regenerated from
  source — the recurring mistake is editing one copy and shipping
  drift.
