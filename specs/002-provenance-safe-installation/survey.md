# Survey: provenance-safe-installation

**Created**: 2026-09-21 | **Baseline**: SpecDevKit v2.7.3 @ f212cc8

## Items
```
item S1: "sync has a provenance ledger for commands and skill trees"
  evidence:   tools/sync.sh:105
  status:     PARTIAL
  verify:     python3 tools/tests/test_sync.py
  gap:        same-path master files are skipped by the tree sweep before rsync overwrites them
item S2: "skill installation writes through rsync after a partial collision sweep"
  evidence:   tools/sync.sh:172
  status:     TODO
  verify:     python3 tools/tests/test_sync.py
  gap:        no all-roots preflight or same-path ownership proof
item S3: "optional harness definitions delete by shared prefix"
  evidence:   tools/agent-defs.py:main:157
  status:     TODO
  verify:     python3 tools/tests/test_agent_defs.py
  gap:        prefix matches are unlinked before parsing, rendering, or provenance checks
item S4: "OMP generation already tracks per-skill provenance"
  evidence:   tools/omp-defs.py:main:155
  status:     DONE
  verify:     python3 tools/tests/test_omp_defs.py
item S5: "workflow installation uses a ledger but raw path interpolation"
  evidence:   tools/workflow-defs.py:main:795
  status:     PARTIAL
  verify:     python3 tools/tests/test_workflow_defs.py
  gap:        install-workflow.sh bakes skill paths through unescaped sed replacement
```

## Supporting evidence
- Live optional-harness generation is invoked from `tools/sync.sh:172`
  after the tree-copy phase.
- Generator output is written by `tools/agent-defs.py:main:157`.
- The shared installer test convention uses temporary HOME directories.

## Rules
- Evidence is from f212cc8.
- Tests must never write to the real user HOME.
- An identical file without ledger proof is unowned, not automatically adopted.
