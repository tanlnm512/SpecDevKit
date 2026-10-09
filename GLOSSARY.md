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

### Scheduling and state (spec-to-prod)

| Term | Means | Canonical home |
|------|-------|----------------|
| doc-set | the seven files under `specs/<name>/` — the canonical statement of what a spec dir IS | `skills/spec-to-prod/contracts/docset.md` |
| contract file / evidence file | the two doc-set classes: spec / plan / tech-spec / task / test are Contract; survey / research are Evidence | same (files table) |
| status holder | task.md — the only file that carries status (C-01) | `specs/CONSTITUTION.md` |
| frontier | every graph node that is ready and not done; the only scheduler — nothing schedules by stage number | `skills/spec-to-prod/SKILL.md` (workflow graph) |
| wave | one concurrent run of the whole frontier; recompute after each wave | same |
| tick | the mechanical, atomic `- [ ] T###` → `- [x]` promotion with its `done <date> — <proof>` sub-line | `skills/spec-to-prod/scripts/tick.py` |
| freeze | the approval freeze applied to the doc-set before execution | `skills/spec-to-prod/scripts/freeze.py` |
| gate | a check the flow must pass — say mechanical gate (scripts decide: `check.py`, review stage 1) or name the approval gate (verify → approve; the researcher gate); bare "gate" is ambiguous | each skill's SKILL.md |

### Review (spec-code-review)

| Term | Means | Canonical home |
|------|-------|----------------|
| mechanical gate | stage 1: the target repo's own checks (Makefile, npm scripts, cargo, go, pytest/unittest, shell syntax, secret shapes) | `skills/spec-code-review/SKILL.md`, `scripts/gate.sh` |
| finding | a kept review observation with an ID, independently confirmed before it survives triage | `skills/spec-code-review/contracts/panel.md` |
| verdict | a fix-loop verification outcome for one finding | same |
| shared review oracle | `review_orchestrator.py` — the single home of review state, systems, asks, finding IDs, and report assembly | D-014 |
| probe | one thin per-phase agent call by which a workflow dialect fetches JSON from the oracle | D-014 |
| dialect twin | one of a skill's two workflow scripts — `*.dwf.ts` (zcode) and `*.js` (Claude Code); behavior-identical, so every edit lands in both or in the oracle they share | `skills/*/workflows/` |

### Kit plumbing

| Term | Means | Canonical home |
|------|-------|----------------|
| skill dir | `skills/<name>/`, self-contained by packaging (marketplace `source: ./skills/<name>`) | `AGENTS.md` |
| generated surface | any regenerate-only artifact: root `agents/`, `workflows/spec-run.*`, the plugin/marketplace manifests, the `§ Engineering rules` sections | `AGENTS.md` house rules |
| ADR (D-###) | an append-only decision record; every divergence from a doc contract gets its own entry (C-05) | `skills/<name>/decisions/` |
| eval case | an entry in a skill's `evals/cases.md`; every increment names its served case (C-10) | `specs/CONSTITUTION.md` |
| sync | `tools/sync.sh` — the one harness-neutral install pipeline to every machine harness root | `tools/` |
| lifecycle commands | the `/spec-*` verb wrappers — `/spec`, `/spec-plan`, `/spec-build`, `/spec-test`, `/spec-review`, `/spec-ship` | D-029 |

## Terms to avoid

- **The former name** of the suite (pre-2.1.0) — say "the former
  name"; it is redacted repo-wide and never reintroduced (D-014).
- **Bare `/review`, `/plan`, `/build`, `/test`, `/ship`** — retired by
  D-029; they collide with harness modes and built-ins. Use the
  `/spec-*` forms, and say `spec-code-review` for standalone review —
  "review" alone is ambiguous with `/spec-review`.
- **"Stage" for spec-to-prod scheduling** — the pipeline schedules by
  frontier and waves, never by a stage ladder ("Waves, not stages").
  The brainstorming and code-review skills do have real stages; the
  word is theirs.
- **"Copy" for a root `agents/*.md` file** — it is a generated view;
  "copy" invites hand-editing.

## Flagged ambiguities (resolved)

- **"review"** splits three ways (D-029): `/spec-review` is
  spec-to-prod's implementation-diff review node; `spec-code-review`
  is the standalone skill; harness built-ins keep their own names.
- **"agent"** covers four things — say role agent (spawned), brief
  (the markdown), generated view (root `agents/` file), or AGENTS.md
  (the convention file).
- **"workflow"** covers three things — the workflow graph (scheduling
  semantics, spec-to-prod SKILL.md), the workflow twins (scripts
  under `skills/*/workflows/`), and a workflow run (a harness
  executing one). Name which.
- **Byte-identical pairs** (workflow twins, dialect copies) are edited
  in every copy at once or regenerated from source — the recurring
  mistake is editing one copy and shipping drift.
