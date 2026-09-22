# Tech baseline — SpecDevKit

**Baseline**: bc5e9de + current working tree (2026-09-22 assurance hardening) · living view — refresh where the
code moved; per-spec surveys carry their own evidence.

## Stack

- Python ≥ 3.10, stdlib only — no runtime dependencies (CONSTITUTION
  C-06); Bash for installers (`sync.sh`, `install-workflow.sh`,
  `scaffold.sh`, …); the two workflow dialects are TypeScript /
  JavaScript emitted as text by `tools/workflow-defs.py` (never compiled
  in this repo).

## Build / test runners

- Tooling suites: `bash tools/tests/run.sh` (unittest per file; prefers
  `uvx python@3.12`, falls back to `python3`).
- Skill script suites: `python3 skills/spec-to-prod/tests/test_<x>.py`
  (check / audit / graph / specstate / tick / git-degradation).
- Spec verification: `python3 skills/spec-to-prod/scripts/check.py
  <spec-dir>`; workflow state: `…/scripts/graph.py <spec-dir>`.
- Approval/evidence integrity: `freeze.py <spec-dir> --record|--verify`
  and `audit.py evidence <spec-dir>`.
- Install + verify: `bash tools/sync.sh` (SHA-verifies every root).
- Manifests: `python3 tools/plugin-manifest.py` after VERSION or
  SKILL.md description changes.

## Conventions

- One skill copy per harness root (D-015); generated dialects are
  regenerate-only with `--check` drift guards (C-02).
- Provenance ledger `.spec-dev-kit-deployed` in every install root:
  foreign files refused, stale-own cleaned (sync.sh,
  install-workflow.sh).
- Tests that touch HOME copy the repo to a temp dir and point HOME at a
  fresh temp dir (tools/tests/test_sync.py convention).
- No harness-specific code inside `skills/spec-to-prod/scripts/` (C-03).
