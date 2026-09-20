# D-020: Workflow-run efficiency — one probe per wave, a bounded round-1 re-brief, unattended-run guidance

D-019's dialects worked but paid three avoidable costs per run. On
Claude Code every graph fetch was a probe agent (state + emit + final
recompute ≈ 3 agents per wave — agent calls the script cannot avoid,
only minimize). A wave whose agents returned `blocked`/`gap` digests
always ended the run there, parking even the mechanical first fix —
playbook fix-round 1 ("re-brief the same implementer with the failure
evidence verbatim") is exactly reproducible from the digests already in
hand. And nothing told users how to tier, schedule, or pre-approve
workflow runs, so the cheap levers sat unused.

**Decision**: (1) the claude dialect fetches state and payload emission
in ONE probe call (a single shell line runs `--state-json` and
`--emit-spawns`, outputs marker-split on `__SPLIT__`), and the final
summary reuses the last post-wave state — one probe per wave, down from
~three; the zcode dialect keeps its two direct `world.run` calls (local
subprocesses, ~0.2s, no agent involved). (2) Both dialects gained a
bounded re-brief round: a wave that changed no doc state gets exactly
ONE retry for its failed payloads (status `blocked`/`gap`, not yet
retried this run), the failure digest verbatim appended to the ask; if
the retry also changes nothing the run stops `no-change` and names that
rounds 2+ are the orchestrator's. The once-only guard is a per-run
`retriedPaths` list keyed by payload path, so the cap survives without
touching task.md (the `(fix n/5)` annotations remain the orchestrator's
to write). (3) SKILL.md § Dynamic workflow runs documents the cost and
unattended levers: staged tiering on zcode (launch analysis waves with
`subagent_model` on a cheap model, execute waves at the default —
per-role tiering stays impossible on both facades), scheduled/off-peak
runs (wrap the workflow with the harness's scheduler; only run spans
with no gate ahead — post-approve — unattended), and pre-approving the
probe command in Claude permission rules so runs don't pause on
permission prompts mid-wave.

**Why**: the probe merge removes the dominant per-wave agent cost on
the one runtime that pays it; the re-brief round automates only the
round the playbook itself defines as mechanical (same evidence, same
agent, once), keeping every judgment round with the orchestrator; and
the guidance turns existing harness levers into documented practice
instead of tribal knowledge.

**Cost if wrong**: the merged probe couples the two graph.py modes in
one shell line — if graph.py ever rejects running both in one process
chain (it cannot today: separate invocations chained by `&&`), the
split marker surfaces loudly as unparseable state, not silently. The
re-brief round could mask a systematically broken payload by retrying
it every wave — bounded by the per-run once-only guard, and the stop
message names the orchestrator as the next actor. Guidance risk is
drift with harness docs; the section stays phrased on levers (model
override, scheduler, permission rules) rather than exact settings
syntax.
