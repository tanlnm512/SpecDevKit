# Survey: dynamic-workflow

**Created**: 2026-09-20 | **Baseline**: 2.6.1 @ cd62be8
The survey node's output — the single source of truth for code state. Every citation
in the other four docs must trace to a line here. Evidence is pasted
verbatim from grep/read output in the session that wrote it.

## Items

```
item S1: "workflow engine derives full node/frontier state from doc state as JSON"
  evidence:   skills/spec-to-prod/scripts/graph.py:compute_state:963
  status:     DONE
  verify:     python3 skills/spec-to-prod/scripts/graph.py specs/dynamic-workflow --state-json
  gap:        —

item S2: "human-gate pause set is a named function, reusable as the workflow-stop contract"
  evidence:   skills/spec-to-prod/scripts/graph.py:find_pause:788
  status:     DONE
  verify:     grep -n "def find_pause" skills/spec-to-prod/scripts/graph.py
  gap:        —

item S3: "auto-trigger loop semantics exist verbatim (pause/verify/emit/runner/recompute + 4 stop conditions)"
  evidence:   skills/spec-to-prod/scripts/graph.py:run_loop:877
  status:     DONE
  verify:     grep -n "AWAITING HUMAN\|max-waves\|no doc-state change" skills/spec-to-prod/scripts/graph.py
  gap:        —

item S4: "frontier payloads (incl. per-task implementer files + undetermined-gate researcher prep) are written mechanically"
  evidence:   skills/spec-to-prod/scripts/graph.py:frontier_payloads:668
  status:     DONE
  verify:     python3 skills/spec-to-prod/scripts/graph.py specs/dynamic-workflow --emit-spawns
  gap:        —

item S5: "payload emission prints one parseable '   payload: PATH (role: ROLE, node: NODE)' line per file"
  evidence:   skills/spec-to-prod/scripts/graph.py:write_wave_payloads:744
  status:     DONE
  verify:     python3 skills/spec-to-prod/scripts/graph.py specs/dynamic-workflow --emit-spawns | grep payload
  gap:        —

item S6: "frontier agent nodes map to roles via the AGENT_BRIEFS dict the payload builder keys off"
  evidence:   skills/spec-to-prod/scripts/graph.py:frontier_payloads:668
  status:     DONE
  verify:     grep -n "AGENT_BRIEFS = {" skills/spec-to-prod/scripts/graph.py
  gap:        —

item S7: "per-harness generated dialects have a regenerate-only precedent (omp frontmatter twins, per-skill manifest)"
  evidence:   tools/omp-defs.py:main:155
  status:     DONE
  verify:     python3 tools/omp-defs.py --skill-dir skills/spec-to-prod --out /tmp/omp-defs-check >/dev/null && ls /tmp/omp-defs-check | head -3
  gap:        —

item S8: "sync installs skills/commands/defs per root with provenance ledger; no workflow surface anywhere"
  evidence:   tools/sync.sh (whole-file read this session; SKILLS_ROOTS block at lines 68–73, no workflows step)
  status:     PARTIAL
  verify:     grep -n "workflows" tools/sync.sh || echo "no workflows step (confirmed absent pre-work)"
  gap:        no tools/workflow-defs.py generator, no tools/install-workflow.sh installer, no skills/spec-to-prod/workflows/ dialects, no SKILL.md/README dynamic-workflow docs — the whole FR-001…FR-007 surface

item S9: "VERSION ↔ SKILL.md frontmatter pairing is enforced by the sync verify pass"
  evidence:   tools/sync.sh (verify block, lines 300–310)
  status:     DONE
  verify:     bash tools/sync.sh 2>&1 | grep -q "DRIFT" && echo drift || echo clean
  gap:        —

item S10: "zcode + claude-code dynamic-workflow runtime shapes captured in-session (facade surfaces read directly, not from memory)"
  evidence:   session research 2026-09-20 — zcode: TS, agent()/ask<T>/phase()/world.run/artifact, .zcode/workflows/*.dwf.ts, no import/export/declare; claude: JS, export const meta first statement, agent/pipeline/parallel/phase, schema-validated returns, script has NO fs/shell (agents only), .claude/workflows/, no mid-run user input
  status:     DONE
  verify:     ls skills/spec-to-prod/workflows/ 2>/dev/null || echo "dialects not yet generated (pre-work state)"
  gap:        —
```

## Supporting evidence

- The 16 contractual node names live in graph.py's module-level `NODES`
  list; `--state-json` (via `skills/spec-to-prod/scripts/graph.py:main:1388`)
  prints `{spec_dir, status, git, nodes{name:{state,reason,tasks?}}, edges,
  frontier[], loops, counts}` — the exact oracle both dialects parse.
- Node-state vocabulary `done · READY · blocked · gate:undetermined · SKIPPED`
  (graph.py lines 184–185) — the dialects key off exactly these tokens.
- `--emit-spawns` and `--run` are argparse-exclusive modes
  (`skills/spec-to-prod/scripts/graph.py:emit_spawns:934`); `--run`'s default
  runner is the `print` echo (`PRINT_RUNNER`, graph.py line 206) — the seam
  the dialects replace with a real spawner, without touching graph.py.
- `tools/sync.sh` ships a per-root provenance ledger
  (`.spec-dev-kit-deployed`, lines 99–126) and foreign-file refusal — the
  installer reuses the same discipline rather than inventing a looser one.
- Test convention for HOME-touching tooling: copy the repo to a temp dir,
  point HOME at a fresh temp dir, run with `env=dict(os.environ, HOME=…)`
  (`tools/tests/test_sync.py`, SyncShBase setUp lines 30–40).
- Baseline this session (pre-work): tools/tests/run.sh 10/10 OK;
  skills/spec-to-prod/tests/test_*.py all OK; `git status --porcelain` shows
  only the untracked `specs/` scaffold.

## Rules
- Every `file:line` pasted from grep/read in this survey — never from memory.
  Can't find it → write `unknown — verify`, don't guess.
- Status derives from evidence, not intent. Run every verify command.
- A number in an old doc is a claim, not evidence — re-count it.
