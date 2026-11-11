# AGENTS.md

Instructions for AI coding agents working in this repository — the
[AGENTS.md](https://agents.md) convention, auto-read by Claude Code,
Codex, Cursor, Gemini CLI and others. Keep this file thin: commands and
pointers; the documents it names are canonical.

## What this repo is

SpecDevKit — seven installable agent skills (`skills/spec-discover/`,
`skills/spec-define/`, `skills/spec-design/`, `skills/spec-build/`,
`skills/spec-review/`, `skills/spec-ship/`,
`skills/spec-release/`) plus their shared install/validation
tooling (`tools/`). Python is stdlib-only — no third-party packages
(C-06). The harness-neutral core — `scripts/`, agent briefs,
`protocol/`, templates — never calls a harness API or branches on
which harness runs it; per-harness surface (install layout, agent-def
dialects, manifests) is generated under `tools/` (C-03).

## Commands — run before declaring work done

- Skill suites: `skills/<name>/tests/run.sh` for all seven skills
- Tooling suite: `tools/tests/run.sh`
- Generated-surface drift: `python3 tools/drift-check.py` (contract,
  manifests, kit-rules, parity, diagrams, examples, personas)
- Docset contract: `python3 skills/spec-design/scripts/check.py
  skills/spec-design/examples/mini-spec/specs/mini-spec`
- Install to machine harness roots + verify: `bash tools/sync.sh`, then
  `bash tools/sync.sh --check`

## House rules

- **Generated surfaces are regenerate-only** — never hand-edit; edit
  the source, regenerate, re-run drift-check:
  - root `agents/` personas ← `skills/*/agents/*.md` via
    `tools/agent-defs.py`
  - `plugin.json` / `marketplace.json` ← `tools/plugin-manifest.py`
  - the `§ Engineering rules` sections in
    `skills/spec-build/agents/developer.md` and
    `skills/spec-review/agents/review-fixer.md` ←
    `rules/engineering-rules.md` via `tools/kit-rules.py`
    (`tools/sync.sh` also refreshes them before every install)
- **Agent briefs live in `skills/<skill>/agents/`** (roles only — the
  lens/protocol prose they point at lives in `protocol/`, D-049) — root
  `agents/` copies are generated views. Each skill ships only the archetypes its
  span spawns (intent: analyst · shape: analyst, architect, tester, auditor ·
  execute: developer, auditor · ship: integrator · release:
  release-manager); a brief shipped twice stays
  byte-identical (`tools/tests/test_parity.py`). The per-harness
  workflow dialects are retired (D-035/D-016): the shared review oracle
  (`scripts/review_orchestrator.py`, D-014) and `graph.py --run` are
  the one executable form each — shared state, systems, asks and
  report assembly live once there, fetched through one probe per
  phase.
- **Skills are self-contained by packaging** — each `skills/<name>/`
  ships alone (marketplace `source: ./skills/<name>`), so content used
  by several skills is duplicated on purpose and pinned by tests.
- **Decisions are append-only ADRs** in each skill's `decisions/`
  (D-###); every divergence from a doc contract gets its own entry
  rather than a silent edit (C-05).
- **The commit boundary (ADR-014)** — build ends at the verified
  commit; `/spec-ship` and `/spec-release` act outward (push, PR, tag,
  publish) only on the user's explicit yes to a shown preview; deploy
  stays with humans/CI.
- **Do not commit or push unless the user explicitly asks.**

## Rules that bind you here

- `rules/engineering-rules.md` — the kit-wide engineering rules,
  canonical text; injected into the agent carriers by
  `tools/kit-rules.py`, never edited in the carriers themselves.
- `GLOSSARY.md` — the kit's shared language: canonical terms, terms
  to avoid, flagged ambiguities. Use its terms in briefs, docs, and
  commits; add a term when a new one stabilizes.
