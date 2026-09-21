# Survey: Contract, documentation, and release validation

**Created**: 2026-09-21 | **Baseline**: HEAD `72b6eed`, working tree intentionally ahead of HEAD (uncommitted plan implementation; VERSION 2.8.0). Original survey baseline was SpecDevKit v2.7.3 @ f212cc8; delta re-survey against the working tree.

## Items

```text
item S1: "Checker is the canonical static docset gate"
  evidence:   skills/spec-to-prod/scripts/check.py:main:538
  status:     DONE
  verify:     python3 skills/spec-to-prod/tests/test_check.py
  gap:        none

item S2: "Workflow definitions are generated from a Python source"
  evidence:   tools/workflow-defs.py:main:808
  status:     DONE
  verify:     python3 tools/workflow-defs.py --check
  gap:        none

item S3: "Plugin manifests have a canonical generation boundary"
  evidence:   tools/plugin-manifest.py:main:183
  status:     DONE
  verify:     python3 tools/plugin-manifest.py --check
  gap:        none

item S4: "Repository has no cross-platform CI workflow"
  evidence:   .github/workflows/ci.yml:12
  status:     DONE
  verify:     test -f .github/workflows/ci.yml
  gap:        none

item S5: "Public entrypoint documents the workflow"
  evidence:   README.md:1
  status:     DONE
  verify:     rg -n 'requirements|migration|supported|trust' README.md skills/spec-to-prod/SKILL.md
  gap:        none
```

## Supporting evidence
- `skills/spec-to-prod/scripts/check.py:main:538` owns static traceability results. FR→task/test-case gaps are FAILs (`check.py:709-711`); AC coverage is FAIL — every acceptance criterion needs a TC mapping (`check.py:792-796`); US traceability stays WARN by documented policy (`check.py:784-791`), and the module docstring now states exactly that split (`check.py:5-6`).
- `tools/workflow-defs.py:main:808` owns workflow generation. CI enforces a clean second generation via the generated-artifact drift step (`.github/workflows/ci.yml:35-36`), which delegates to `workflow-defs.py --check` (`tools/drift-check.py:152-153`); the check passes for both committed outputs (`spec-run.dwf.ts`, `spec-run.js`).
- `tools/plugin-manifest.py:main:183` owns manifest synchronization. Version/changelog/manifest alignment is enforced together by `tools/tests/test_release.py:447` (`test_version_changelog_manifest_alignment`) and `:442` (`test_generated_surfaces_match_canonical_sources`); CI runs the whole `tools/tests/test_*.py` suite (`tools/tests/run.sh:14`, wired at `.github/workflows/ci.yml:27-28`) plus the manifest drift gate (`tools/drift-check.py:158-159`).
- `.github/workflows/ci.yml:12` defines the `validate` job on an `ubuntu-latest`/`macos-latest` matrix (`.github/workflows/ci.yml:19`), running both test suites, compileall, `bash -n` over all shell scripts, generated-artifact drift, and a representative docset check (`ci.yml:38`).
- `README.md:80` is the single current statement "Requirements, platforms, and trust boundaries": runtime (Python ≥ 3.10, stdlib + bash, git optional with loud degradation), platforms (Linux/macOS per the CI matrix; Windows-native shells unsupported, `README.md:94`), harnesses (the six `sync.sh` surfaces), and migration via `scripts/migrate.py` (`README.md:100`). `README.md:1` and `skills/spec-to-prod/SKILL.md:1` remain the public contract surfaces.

## Rules
- Delta re-survey from the f212cc8 baseline: every item cited a file in the changed footprint, so all five were re-grepped and re-verified against the working tree; no item was carried over byte-identical.
- `tools/workflow-defs.py` was untouched by this plan's working tree; its drift arrived via intermediate commit `780ad03` and is re-cited as observed.
- Status describes current behavior, not target design.
