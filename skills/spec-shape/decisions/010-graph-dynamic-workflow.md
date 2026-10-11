# D-010: The pipeline becomes a dynamic state-graph workflow

The suite was born as a fixed Stage 0–4 ladder: schedule by stage number,
run the stages in order, resume by mapping artifacts back to stage numbers.
Three decisions had already punched state-derived holes in that ladder —
D-002 made doc state the only state, D-006 made parallel waves the default
shape, D-009 made the clarify pass a frontier computation — but the
pipeline as a whole still scheduled by stage: SKILL.md's stage sections,
the router's "Stage N" verb annotations, the resuming-by-stage-number
table, and a workflow diagram still carrying "up to 5 questions, one at a
time" (contradicting D-009 on its face). Each new loop (fix rounds,
re-briefs, converge) had to be described as an exception to the ladder it
actually invalidates.

**Decision**: scheduling is a dynamic state graph over the doc set, and
the stage ladder is demoted to one non-normative orientation note (the
"typical topological order" a fresh spec's waves usually land in). The
graph: sixteen nodes — six single-agent nodes (research, survey,
plan, tech, qa, tasks), the execute node's implementer waves, and nine
orchestrator/mechanical nodes (spec, clarify, research-gate, verify,
before-audit, approve, closing-audit, tick-commit, archive) — each with
one mechanical done-signal read from doc state alone. A node is *ready* exactly when all
of its inputs are done; the **frontier** is every ready-not-done node;
execution is: run the ready frontier as one wave, recompute, repeat.
Conditional and loop edges are first-class, not exceptions: the researcher
gate (a judgment node no tooling ever decides), fix rounds capped
`(fix <n>/5)` in task.md, re-briefs on gap digests, converge on survey
staleness, and the clarify loop. The human gates — clarify, approve, an
undetermined research-gate, the closing-audit judgment (including
rulings), tick-commit — are never auto-satisfied: `scripts/graph.py --run`
(the auto-trigger loop) pauses `AWAITING HUMAN` at each, and before-audit
pauses the same way, being the orchestrator's six-gate judgment.
`graph.py` (over the shared `specstate.py` parsers) is the mechanical
truth the orchestrator schedules from — report, `--state-json`,
`--mermaid`, `--explain`, `--emit-spawns`, `--run` — while judgment
(gate decisions, brief quality, rulings) stays with the orchestrator and
the user.

**What this generalizes**: D-002's state-in-docs becomes the graph's only
input (the frontier is computed, not remembered); D-006's parallel-by-
default becomes the frontier wave (one message, disjoint files); D-009's
grilling frontier becomes pipeline-wide (the clarify loop, execute's
per-task frontier, and the whole workflow are the same compute-ready →
run → recompute shape). It supersedes stage-normative *wording* in the
active docs — SKILL.md, contracts/docset.md, the agent briefs, both gates
files, templates, the router, the diagrams — not the ADR texts themselves
(001–009 stay as written) and not CHANGELOG history (append-only). Phases
*inside* plan.md/task.md stay: they are the implementation graph, the
task-breaker's and planner's own ordering, not pipeline scheduling.

**Why**: the ladder and the loops had inverted — the graph's real shape
(loop-heavy, state-derived) was being expressed as a linear rule plus a
growing exception list, and every resume, gate, and wave decision
required a human re-derivation the docs then had to re-explain. A
mechanical frontier computation (`graph.py`) makes the state derivable
instead of reconstructed, keeps every scheduling fact greppable to a
single grep-verified vocabulary (`done · READY · blocked ·
gate:undetermined · SKIPPED`), and turns "resuming" from a stage-number
lookup into running one command.

**Cost if wrong**: the documented node model and graph.py's actual
behavior can drift apart — the doc claims a readiness condition the code
doesn't implement, or vice versa. That is mitigated by making graph.py's
`--state-json` the test-facing oracle (frontier-transition unit tests per
node) and by the cross-surface rule that SKILL.md's node table and
graph.py's ready/done conditions must match name-for-name and
condition-for-condition. A second cost is conceptual for readers of older
material: "Stage N" phrasing in history (ADRs, old changelog entries, the
fixture) maps to nodes only through the orientation note.
