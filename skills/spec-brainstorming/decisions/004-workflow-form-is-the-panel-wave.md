# D-004: The workflow form is the panel wave, nothing more

Where the harness has a workflow runtime (zcode dynamic
workflows, Claude Code workflows), the skill ships a workflow
form scoped to **stage 2 only**: load the briefs from the skill
dir, spawn the three lenses in parallel, return the three
digests verbatim. Stages 1, 3, 4 and 5 never run in a workflow.

**Why**: the workflow runtimes have no user-turn primitive —
stage 1's one question, stage 4's sequential single questions and
stage 5's collision question are user turns, and stage 3's
matrix is judgment over the digests. A workflow that "paused"
for them would fake interactivity: a stop is not a question. The
panel wave is the one mechanical part, and the payload/digest
contract (`contracts/run.md`) is the same for both forms — the
background form earns its keep without touching the contract.

The briefs are read from the skill dir at run time (cat through
the runtime's command seam), never embedded in the dialect
files: one source of truth for the lenses, so a brief edit ships
without a workflow edit. A brief that fails to load degrades to
the inline mission line and is logged — the lens still argues,
from a thinner brief.

**Cost if wrong**: two dialect masters to keep in behavioral
parity (`tests/test_workflow_copies.py` pins the phases, the
payload anchors and the digest grammar across both) — the same
cost spec-code-review already pays for its panel. If the inline
and workflow digests ever diverge in shape, the parity test has
missed an anchor: add the anchor, don't fork the grammar.
