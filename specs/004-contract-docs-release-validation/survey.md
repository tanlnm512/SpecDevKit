# Survey: Contract, documentation, and release validation

**Created**: 2026-09-21 | **Baseline**: SpecDevKit v2.7.3 @ f212cc8

## Items

```text
item S1: "Checker is the canonical static docset gate"
  evidence:   skills/spec-to-prod/scripts/check.py:main:492
  status:     PARTIAL
  verify:     python3 skills/spec-to-prod/tests/test_check.py
  gap:        User-story acceptance-criterion coverage is not enforced as strongly as public claims imply.

item S2: "Workflow definitions are generated from a Python source"
  evidence:   tools/workflow-defs.py:main:795
  status:     PARTIAL
  verify:     python3 tools/workflow-defs.py --check
  gap:        CI does not enforce a clean second generation across all supported outputs.

item S3: "Plugin manifests have a canonical generation boundary"
  evidence:   tools/plugin-manifest.py:main:116
  status:     PARTIAL
  verify:     python3 tools/plugin-manifest.py --check
  gap:        Release version, changelog, and every manifest are not enforced together in CI.

item S4: "Repository has no cross-platform CI workflow"
  evidence:   .github/workflows/ci.yml:missing
  status:     TODO
  verify:     test -f .github/workflows/ci.yml
  gap:        Linux and macOS quality gates are absent.

item S5: "Public entrypoint documents the workflow"
  evidence:   README.md:1
  status:     PARTIAL
  verify:     rg -n 'requirements|migration|supported|trust' README.md skills/spec-to-prod/SKILL.md
  gap:        Runtime dependencies, migration, harness support, and command trust boundaries need one current statement.
```

## Supporting evidence
- `skills/spec-to-prod/scripts/check.py:main:492` owns static traceability results.
- `tools/workflow-defs.py:main:795` owns workflow generation.
- `tools/plugin-manifest.py:main:116` owns manifest synchronization.
- `README.md:1` and `skills/spec-to-prod/SKILL.md:1` are public contract surfaces.

## Rules
- Every cited line was verified against commit `f212cc8`; the missing CI path is an observed absence.
- Status describes current behavior, not target design.
