# AGENTS.md

Instructions for AI coding agents working in this repository — the
[AGENTS.md](https://agents.md) convention, auto-read by Claude Code,
Codex, Cursor, Gemini CLI and others. Keep this file thin: commands and
pointers; the documents it names are canonical.

## What this repo is

SpecDevKit — five installable agent skills (`skills/spec-intent/`,
`skills/spec-shape/`, `skills/spec-execute/`, `skills/spec-code-review/`,
`skills/spec-brainstorming/`) plus their shared install/validation
tooling (`tools/`). Python is stdlib-only (C-06); the harness-neutral
core never grows harness-specific code (C-03).

## Commands — run before declaring work done

- Skill suites: `skills/<name>/tests/run.sh` for all five skills
- Tooling suite: `tools/tests/run.sh`
- Generated-surface drift: `python3 tools/drift-check.py` (contract,
  manifests, kit-rules, parity, diagrams, examples, personas)
- Docset contract: `python3 skills/spec-shape/scripts/check.py
  skills/spec-shape/examples/mini-spec/specs/mini-spec`
- Install to machine harness roots + verify: `bash tools/sync.sh`, then
  `bash tools/sync.sh --check`

## House rules

- **Generated surfaces are regenerate-only** — never hand-edit; edit
  the source, regenerate, re-run drift-check:
  - root `agents/` personas ← `skills/*/agents/*.md` via
    `tools/agent-defs.py`
  - `plugin.json` / `marketplace.json` ← `tools/plugin-manifest.py`
  - the `§ Engineering rules` sections in `skills/spec-intent/agents/
    builder.md`, `skills/spec-shape/agents/builder.md`,
    `skills/spec-execute/agents/builder.md`, and
    `skills/spec-code-review/agents/code-review-fixer.md` ←
    `rules/engineering-rules.md` via `tools/kit-rules.py`
    (`tools/sync.sh` also refreshes them before every install)
- **Agent briefs live in `skills/<skill>/agents/`** — root `agents/`
  copies are generated views. The per-harness workflow dialects are
  retired (D-035/D-016): the shared review oracle
  (`scripts/review_orchestrator.py`, D-014) and `graph.py --run` are
  the one executable form each — shared state, systems, asks and
  report assembly live once there, fetched through one probe per
  phase.
- **Skills are self-contained by packaging** — each `skills/<name>/`
  ships alone (marketplace `source: ./skills/<name>`), so content used
  by several skills is duplicated on purpose and pinned by tests.
- **Decisions are append-only ADRs** in each skill's `decisions/`
  (D-###); every divergence from a doc contract gets its own entry
  (C-05).
- **Do not commit or push unless the user explicitly asks.**

## Rules that bind you here

- `rules/engineering-rules.md` — the kit-wide engineering rules,
  canonical text; injected into the agent carriers by
  `tools/kit-rules.py`, never edited in the carriers themselves.
- `GLOSSARY.md` — the kit's shared language: canonical terms, terms
  to avoid, flagged ambiguities. Use its terms in briefs, docs, and
  commits; add a term when a new one stabilizes.
