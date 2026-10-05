# Survey: code-review-workflow-extraction

**Created**: 2026-10-05 | **Baseline**: SpecDevKit main @ 5d01304 + working tree
Phase-A output — code state evidence, pasted verbatim from this session's
commands. Every citation below is from grep/wc/test output in this session.

## Items

```
item S1: "the two workflow dialects are 2114 and 2239 lines"
  evidence:   wc -l skills/spec-code-review/workflows/spec-code-review.dwf.ts skills/spec-code-review/workflows/spec-code-review.js → 2114, 2239
  status:     DONE
  verify:     wc -l skills/spec-code-review/workflows/*
item S2: "the js twin's bulk is shared logic, not agent prose: shell/probe/git helpers run lines 473-760, ask builders 910-1237, main orchestration 1268-2239"
  evidence:   grep -n '^function |^async function |phase("' spec-code-review.js → probe:473, runGate:492, selectProjectFiles:541, shardProjectFiles:574, gitScope:624, nextId:760, parseFindingsMd:772, loadFixFromFindings:831, scoutAsk:910, reviewAsk:955, triageAsk:1011, fixerAsk:1103, findingsMd:1237, main:1268
  status:     DONE
  verify:     grep -n '^async function main' skills/spec-code-review/workflows/spec-code-review.js
item S3: "parity is enforced by 35 string/anchor tests, none of which execute the workflow"
  evidence:   cd skills/spec-code-review && python3 tests/test_workflow_copies.py → "Ran 35 tests in 2.121s OK" (phases literal, ask anchors, tunables — static)
  status:     DONE
  verify:     cd skills/spec-code-review && python3 tests/test_workflow_copies.py
item S4: "the mechanical gate already has a JSON contract the oracle can reuse"
  evidence:   bash skills/spec-code-review/scripts/gate.sh --base HEAD → [{"name": "shell syntax (bash -n, 4 changed files)", "exit_code": 0}, {"name": "secrets (token patterns on the change)", "exit_code": 0}]
  status:     DONE
  verify:     bash skills/spec-code-review/scripts/gate.sh --plan
item S5: "no shared oracle script exists today"
  evidence:   ls skills/spec-code-review/scripts/ → gate.sh, skill-dir.sh (no review_orchestrator.py); test ! -f skills/spec-code-review/scripts/review_orchestrator.py → 0
  status:     TODO
  gap:        target resolution, sharding, finding IDs, fix_from parsing, and report assembly live only inside the two dialect files (S2)
  verify:     test ! -f skills/spec-code-review/scripts/review_orchestrator.py
item S6: "a runtime-execution harness pattern already exists and covers only spec-run"
  evidence:   tools/tests/test_workflow_runtime.py → "Ran 3 tests ... OK"; executes spec-run.js with real graph.py oracle; grep -c spec-code-review → 0
  status:     DONE
  verify:     python3 tools/tests/test_workflow_runtime.py
item S7: "spec-run shows the target architecture at 358/320 lines: one Python oracle, thin generated dialects"
  evidence:   wc -l skills/spec-to-prod/workflows/* → 358 spec-run.dwf.ts, 320 spec-run.js; graph.py is the only oracle (SKILL.md ADR-010/019)
  status:     DONE
  verify:     wc -l skills/spec-to-prod/workflows/*
item S8: "the grader scores this surface worst in the kit: W5 4/15 (size 0/8 at 2239 lines; hand-maintained 4/7)"
  evidence:   python3 tools/grade.py → "workflow:spec-code-review — mechanical 8.53/10 · 2239 lines; W5 Size & generation governance | 4/15"
  status:     TODO
  gap:        size 0/8 needs ≤1200 lines for 4/8 (W5 8/15 → mechanical ≥9.07)
  verify:     python3 tools/grade.py --skip-suites --skip-sync | grep -A6 'workflow:spec-code-review'
```

## Supporting evidence
- The dialects are semantically parallel but syntactically distinct
  (typed facade vs plain JS primitives); raw diff shows 2,891 changed
  lines across the pair — "one master + mechanical transform" codegen is
  not a small step (S2, S3).
- The runtime-execution harness executes plain-JS dialects via Node
  `new Function` with scripted `agent/pipeline/phase/log` primitives and
  a probe that runs real commands (S6) — directly reusable for the
  review workflow's Claude dialect.
- AGENTS.md currently pins the twins as "hand-maintained masters kept in
  parity by each skill's tests" — the governance text must move with
  the architecture (spec FR-006).

## Rules
- Every `file:line` pasted from grep/read in this survey — never from
  memory. Can't find it → `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
