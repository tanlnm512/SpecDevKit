# D-019: Dynamic-workflow dialects — the frontier loop as generated per-harness scripts

Two harnesses now ship script-driven subagent-orchestration runtimes:
zcode dynamic workflows (TypeScript scripts against a fixed facade —
typed actors, literal phases, journaled world commands) and Claude Code
dynamic workflows (plain JavaScript — `agent`/`pipeline`/`phase`
primitives, schema-validated returns, runs as `/<name>` commands).
Meanwhile the pipeline's own loop (D-010) still runs only inside an
orchestrator session: the orchestrator reads the frontier, spawns each
wave by hand, and re-derives everything on resume. The loop's mechanics
were already harness-neutral — `graph.py --state-json` is the oracle,
`--emit-spawns` writes self-contained payloads, `--run`'s pause set names
every human gate — so what was missing was a native instantiation of
exactly that seam, not new logic.

**Decision**: workflow scripts are a third application of D-015's
generated-dialect pattern (omp-defs.py → agent-defs.py → workflow-defs).
`tools/workflow-defs.py` emits two committed regenerate-only artifacts
under `skills/spec-to-prod/workflows/` — `spec-run.dwf.ts` (zcode) and
`spec-run.js` (claude code) — each a thin loop over graph.py: state from
`--state-json`, waves spawned from `--emit-spawns` payload files, and
find_pause's gate set stopping the run `AWAITING HUMAN` (clarify, an
undetermined research-gate, before-audit, approve, the closing-audit
judgment, tick-commit — never auto-satisfied). A rerun after each gate
resumes from doc state, the same resume contract every other surface
already has. Neither dialect implements a single readiness rule.
`tools/install-workflow.sh` installs each dialect to its own harness
root (`~/.zcode/workflows/`, `~/.claude/workflows/`, with `--project`
variants), baking the target root's own skill copy into the installed
file (a runtime `skill_dir` arg overrides the bake) under sync.sh's
provenance-ledger refusal discipline; sync.sh installs and verifies
both, gated on each harness home existing. A harness earns a dialect
when it has a scriptable workflow runtime with subagent spawning,
rerun/resume semantics, and a progress surface — omp's kernel bridge
already covers this via the documented in-process recipe (no file
needed), and Droid missions / Codex have no comparable script runtime
yet, so no dialect is emitted for them.

**Why**: the runtimes give the loop a native surface — phase graph,
rerun-as-command, resumable runs — for zero changes to any gate or
parser; keeping the dialects generated (one template constant each in
the generator, parity-checked by tests) means the loop contract cannot
drift between harnesses, and a harness facade change surfaces as a loud
dialect edit + regenerate, never a silent break. The installer keeps
the "one copy per harness root, self-contained" property D-015
established: each root's workflow points at that root's own skill copy.

**Cost if wrong**: facade drift — a runtime renames primitives or
changes its metadata shape, and the dialect stops loading. Mitigated by
per-dialect invariant tests (forbidden/required tokens, metadata-first
rules), the target runtime named in each file header, and `--check`
catching hand-edits. A baked skill_dir can go stale if the skill moves;
`--check` compares installed copies against the currently resolved
skill_dir, so one installer (or sync) run repairs it. The subtle risk
is expectation drift — a user reading "dynamic workflow" as "the script
decides the gates": the stop vocabulary (`AWAITING HUMAN`, the six gate
names) is byte-shared with graph.py's own `--run` precisely so the two
surfaces teach the same rule.
