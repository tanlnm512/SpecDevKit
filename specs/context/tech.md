# Tech conventions — SpecDevKit

**Baseline**: 0.1.0 @ 98fa893d4018592624c23f8fcf0b7e3855fe3989

## Stack

- Python 3, stdlib-only — no third-party packages anywhere (contract
  C-06); the doc-state engine, gates, and tools are all stdlib scripts.
- Bash for the shell entry points (`scaffold.sh`, `archive.sh`, `gate.sh`,
  `sync.sh`, per-skill `tests/run.sh`), `set -euo pipefail` discipline.
- No build step; scripts run in place from `skills/<name>/scripts/`.

## Commands

- Skill suites: `skills/<name>/tests/run.sh` (all seven).
- Tooling suite: `tools/tests/run.sh`.
- Generated-surface drift: `python3 tools/drift-check.py`.
- Docset gate: `python3 skills/spec-design/scripts/check.py
  <spec-dir> --repo <repo-root>` (add `--survey-only`, `--intent-only`,
  `--fix-burndown`, `--next-ids`, `--checklist` as needed).
- Install + verify: `bash tools/sync.sh` then `bash tools/sync.sh --check`.
- Search with `rg` (ripgrep), never `grep`, in agent work.

## Conventions

- **Doc state is the source of truth** — the seven-file doc-set under
  `specs/<name>/` at `Tier: full`, one file (spec.md § Tasks) at
  `Tier: tiny`; status lives only in the status holder (task.md at full).
- **Byte-shared duplication** — spec-design, spec-build, and spec-define
  ship byte-identical copies of the shared engine scripts (specstate.py,
  check.py, freeze.py, graph.py, index.py, contract.py, telemetry.py —
  `cmp`-verified pairwise across all three skills at the baseline
  commit); edit via the parity masters or all copies at once;
  `tools/tests/test_parity.py` pins it.
- **Regenerate-only surfaces** — root `agents/`, SKILL.md node tables
  (`contract.py`), plugin/marketplace manifests, `§ Engineering rules`
  sections; never hand-edit.
- **Append-only ADRs** — `skills/<name>/decisions/D-###`; every doc
  contract divergence gets its own entry (C-05).
- **Normative text** — MUST / MUST NOT / NEVER in rule and AC text; no
  hedged verbs (GLOSSARY "Terms to avoid").
- **WHEN/IF/THEN phrasing** in FR/AC statements (see
  `specs/loop-ready-docset/spec.md` for the live shape).
- **Commits and pushes only on the user's explicit ask** (AGENTS.md; the
  commit boundary, spec-design ADR-014).
- **Versioning** — `skills/<name>/VERSION` is the source of truth
  (RELEASE.md step 2); SKILL.md frontmatter and the generated manifests
  are kept equal to it mechanically; every skill sits at 0.1.0 at the
  baseline commit.
- **Telemetry** — local append-only run records via
  `scripts/telemetry.py` → `~/.spec-dev-kit/telemetry/*.jsonl`;
  content-free, never status.

## Domain terms worth reusing

- tick, freeze, wave/frontier, doc-set, contract/evidence files, work
  type, payload, digest, brief, lens, role agent — all defined in
  `GLOSSARY.md`; use those terms exactly.

## Gotchas

- `rg -r` is ripgrep's `--replace` flag — a stray `-rn` rewrites matched
  text in the OUTPUT (not the files) and silently corrupts evidence.
- `ls` sorts its operands: listing several dirs alphabetizes the blocks
  regardless of argument order.
- check.py's survey-only mode mechanically verifies every
  `path.ext:symbol:line` citation in survey.md (symbol must be a
  def/class at that file) — cite constants as `file:LINE`, defs as
  `file:def_name:LINE`.
