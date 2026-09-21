# Survey: provenance-safe-installation

**Created**: 2026-09-21 | **Baseline**: SpecDevKit v2.7.3 @ 31da94e (delta re-survey; the working tree carries the plan's uncommitted implementation ahead of this HEAD — prior survey baseline f212cc8)

## Items
```
item S1: "sync has a provenance ledger for commands and skill trees"
  evidence:   tools/sync.sh:131
  status:     DONE
  verify:     python3 tools/tests/test_sync.py
item S2: "skill installation writes through rsync after a partial collision sweep"
  evidence:   tools/sync.sh:282
  status:     DONE
  verify:     python3 tools/tests/test_sync.py
item S3: "optional harness definitions delete by shared prefix"
  evidence:   tools/agent-defs.py:main:180
  status:     DONE
  verify:     python3 tools/tests/test_agent_defs.py
item S4: "OMP generation already tracks per-skill provenance"
  evidence:   tools/omp-defs.py:main:158
  status:     DONE
  verify:     python3 tools/tests/test_omp_defs.py
item S5: "workflow installation uses a ledger but raw path interpolation"
  evidence:   tools/workflow-defs.py:main:808
  status:     DONE
  verify:     python3 tools/tests/test_workflow_defs.py
```

## Supporting evidence
- Live optional-harness generation is invoked from `tools/sync.sh:354`
  (preflight renders every generator to scratch) and `tools/sync.sh:490`
  (apply writes the validated plan).
- Generator output is staged by `tools/agent-defs.py:main:180` and
  planned through tools/ownership.py before the first destination write.
- The shared installer test convention uses temporary HOME directories.

## Rules
- Evidence is from the working tree at HEAD 31da94e, which carries the
  plan's uncommitted implementation (delta re-survey; prior baseline f212cc8).
- Tests must never write to the real user HOME.
- An identical file without ledger proof is unowned, not automatically adopted.
