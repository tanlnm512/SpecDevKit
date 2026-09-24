# Changelog — spec-code-review

Release history. The skill began life 2026-09-23 as the validated
`spec-code-review` dynamic workflow in the SpecDevKit repo (three-stage
review: mechanical gate → specialist panel with triage and independent
confirmation → synthesis), then became a portable sibling skill.


## 0.3.0 — 2026-09-24

The panel's agents, materialized. Each side of the review rubric now
ships as an installable agent brief under `agents/`:
`code-review-correctness`, `code-review-security`, `code-review-quality`
(each carrying the full checklist for its side of the rubric) and
`code-review-fixer` (the fix loop's author role), over the shared
`_panel-protocol.md` (the flagging bar, severity ladder, citation
format, zero-findings rule — the contract every panel member shares).
Harnesses with subagent dispatch (Claude Code, omp, opencode, Factory
Droid, Antigravity) get them as real subagent types from
`tools/sync.sh`, so the inline path dispatches genuine specialists
instead of one agent simulating every lens; SKILL.md's Stage 2 and fix
loop now say exactly that. The three lens briefs are pinned to the
workflow masters by their focus strings — a third representation of
the panel that cannot drift silently (tests/test_workflow_copies.py).

Migration: none required — rerun `tools/sync.sh` to install the new
agent defs alongside the existing skills and workflows.


## 0.2.0 — 2026-09-24

Second dialect, plus the drift guard. `workflows/spec-code-review.js`
ports the full protocol to the Claude Code dynamic-workflow runtime, so
`tools/install-workflow.sh claude` (and `tools/sync.sh`) deliver the
review to Claude Code exactly as the zcode dialect reaches zcode. The
one-shot agent model forced three documented divergences (header of the
file): system prompts ride at the head of each ask; cross-lens dedup
runs as one explicit merge pass instead of a shared triage
conversation; every fixer round embeds the full finding detail instead
of relying on conversation context. Shell work (gate.sh, git) reaches
the runtime only through probe agents returning stdout verbatim, and
the report returns as the run result's `markdown` field.

`tests/test_workflow_copies.py` pins the two masters together — shared
phases, tunables, panel definition, ask anchors, report contract, and
each runtime's structural invariants — the guard the hand-maintained
two-dialect layout demands.

Fix-loop correctness fix, applied to both dialects and to the repo's
own project-scoped copy: the post-fix verification wave no longer
spawns reader verifiers for gate-lens findings — a reader cannot
verify a check name, and the fresh authoritative gate re-run owns
those.

Migration: none required. The zcode dialect's behavior is unchanged;
rerun `tools/install-workflow.sh` (or sync) to pick up the fix and the
new claude dialect.


## 0.1.0 — 2026-09-23

First release. The review protocol of the validated workflow, packaged
for any repo and any coding agent: `scripts/gate.sh` detects and runs
the target repo's own checks (Makefile targets, npm scripts, cargo, go,
pytest/unittest, `bash -n` on the changed shell scripts) and reports a
JSON array callers can branch on; SKILL.md carries the full protocol —
defect-first flagging bar, severity ladder, exclusions, triage,
independent confirmation, the bounded fix loop, and the
merge/fix-first/human recommendation. The zcode workflow
(`workflows/spec-code-review.dwf.ts`) automates the stages on harnesses
that run dynamic workflows; agents without workflow support execute the
stages inline. Validated end-to-end twice in SpecDevKit: the review
pass confirmed 7 findings on a 20-file commit (risk medium), and the
fix loop resolved 7 of 8 tracked findings across 2 rounds with the gate
green and every fix independently verified.

Migration: none required — first release. `tools/sync.sh` installs the
skill tree and the workflow (as the saved zcode workflow
`spec-code-review`); repos that want a gate tuned to their exact CI set
keep a project-scoped workflow copy, which takes precedence there.
