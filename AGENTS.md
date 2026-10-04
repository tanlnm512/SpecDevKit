# AGENTS.md

Instructions for AI coding agents working in this repository — the
[AGENTS.md](https://agents.md) convention, auto-read by Claude Code,
Codex, Cursor, Gemini CLI and others. Keep this file thin: commands and
pointers; the documents it names are canonical.

## What this repo is

SpecDevKit — three installable agent skills (`skills/spec-to-prod/`,
`skills/spec-code-review/`, `skills/spec-brainstorming/`) plus their
shared install/validation tooling (`tools/`). Python is stdlib-only
(C-06); the harness-neutral core never grows harness-specific code
(C-03).

## Commands — run before declaring work done

- Skill suites: `skills/<name>/tests/run.sh` for all three skills
- Tooling suite: `tools/tests/run.sh`
- Generated-surface drift: `python3 tools/drift-check.py` (workflows,
  manifests, kit-rules, diagrams, examples)
- Docset contract: `python3 skills/spec-to-prod/scripts/check.py
  skills/spec-to-prod/examples/mini-spec/specs/mini-spec`
- Install to machine harness roots + verify: `bash tools/sync.sh`, then
  `bash tools/sync.sh --check`

## House rules

- **Generated surfaces are regenerate-only** — never hand-edit; edit
  the source, regenerate, re-run drift-check:
  - root `agents/` personas ← `skills/*/agents/*.md` via
    `tools/agent-defs.py`
  - `skills/spec-to-prod/workflows/spec-run.*` ← `tools/workflow-defs.py`
  - `plugin.json` / `marketplace.json` ← `tools/plugin-manifest.py`
  - the `§ Engineering rules` sections in `skills/spec-to-prod/agents/
    _shared-protocol.md` and `skills/spec-code-review/agents/
    code-review-fixer.md` ← `rules/engineering-rules.md` via
    `tools/kit-rules.py` (`tools/sync.sh` also refreshes them before
    every install)
- **Agent briefs live in `skills/<skill>/agents/`** — root `agents/`
  copies are generated views. Workflow dialect twins
  (`spec-code-review.*`, `spec-brainstorming.*`) are hand-maintained
  masters kept in parity by each skill's `tests/test_workflow_copies.py`.
- **Skills are self-contained by packaging** — each `skills/<name>/`
  ships alone (marketplace `source: ./skills/<name>`), so content used
  by several skills is duplicated on purpose and pinned by tests.
- **Decisions are append-only ADRs** in each skill's `decisions/`
  (D-###); every divergence from a doc contract gets its own entry
  (C-05).
- **Do not commit or push unless the user explicitly asks.**

## Rules that bind you here

- `specs/CONSTITUTION.md` — articles C-01…C-10: task.md is the sole
  status holder; regenerate-only artifacts; harness-neutral core;
  reuse before writing; append-only decisions; stdlib-only Python;
  test discipline (C-07); comments explain why, not what (C-08);
  never poll a backgrounded job (C-09); every increment names its
  served eval case (C-10).
- `rules/engineering-rules.md` — the kit-wide engineering rules,
  canonical text; injected into the agent carriers by
  `tools/kit-rules.py`, never edited in the carriers themselves.
