# D-046: a delivered docset is historical — baseline staleness stops failing

The intent gate's fourth refusal family compares intent.md's
`**Baseline**:` commit against the repo's HEAD and FAILs on mismatch
("re-scout before trusting the artifact"). The refusal guards
pre-authoring trust: an intent whose facts predate the code it
describes must be re-probed. But delivery moves HEAD by design — C1
(implementation) and C2 (delivery record) land after every doc was
written, so every delivered docset's intent baseline is "stale" the
moment the run succeeds. Recorded live in the 2026-10-27 eval pass:
after tick-commit, `check.py --intent-only` (and the full check's
intent family) went red on exactly this mismatch and the graph
display cascaded the intent node to blocked — a green pipeline
turning itself red by finishing (spec-execute E5 and E6 transcripts).

**Decision**: `intent_failures` takes a `delivered` flag, computed at
both call sites from the docset's own record (`Delivered: commit @`
in task.md or spec.md, read via `specstate.delivery_state`). When
delivery is recorded, a baseline-vs-HEAD mismatch is a visible SKIPPED
note ("delivery recorded; the docset is historical"), never a FAIL.
Placeholders and open NEEDS CLARIFICATION markers keep failing in
every state — those are defects at any point in the lifecycle; only
the HEAD comparison is moot post-delivery. Survey.md staleness stays
WARN-only, unchanged. The pre-delivery refusal (I3's repair loop) is
untouched: without a Delivered record the mismatch still FAILs.
