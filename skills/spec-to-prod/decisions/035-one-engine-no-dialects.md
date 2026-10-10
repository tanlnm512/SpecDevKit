# D-035 — One engine, no workflow dialects

- **Context**: ADR-019 shipped the frontier loop as generated
  per-harness workflow dialects (zcode `.dwf.ts`, Claude `.js`),
  each a committed regenerate-only artifact of `tools/
  workflow-defs.py`, installed by `tools/install-workflow.sh` and
  pinned by parity suites. The kit's biggest maintenance tax: two
  masters per workflow that must never drift, installers, bake
  steps, and per-harness prose inside a harness-neutral playbook —
  none of it about the specs themselves. Meanwhile `graph.py --run`
  already IS the loop: doc state in, payloads out, a `--runner`
  command-template seam, AWAITING HUMAN pauses, resume from doc
  state — harness-neutral by construction.
- **Decision**: delete the dialects. `skills/*/workflows/`,
  `tools/workflow-defs.py`, `tools/install-workflow.sh`, both
  `test_workflow_copies.py` suites, and `tools/tests/
  test_workflow_defs.py` / `test_workflow_runtime.py` are removed;
  sync.sh, drift-check.py, grade.py (workflow unit type retired),
  the rubric, README and AGENTS.md follow. `graph.py --run` is the
  one engine on every harness, driven by the orchestrator session or
  a scripted wrapper through its runner seam; `--launch-check`
  (D-022) keeps deciding when automation pays. Supersedes D-019's
  dialect split and D-020's facade-specific tier levers (per-run
  tiering still exists wherever the chosen runner supports it — it
  is a property of the runner command, not a kit surface).
- **Consequences**: the harness-glue mass is deleted outright; adding
  a harness (like Kilo, D-033) no longer raises the question of a
  workflow dialect at all. Cost: the facades' one-command launch
  convenience — replaced by `graph.py --run --runner '<spawn cmd>'`
  presets any session or cron can hold. Serves eval cases
  spec-to-prod/e1 (the loop drives the same waves inline or via
  --run; `--state-json` snapshots unchanged) and e4 (resume from doc
  state — unchanged, the docs were always the only state).
