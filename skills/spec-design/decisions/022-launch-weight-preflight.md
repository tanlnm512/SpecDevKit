# D-022: Launch-weight preflight — the spec-run workflow runs only heavy spans

D-019/D-020 made the workflow dialects cheap per wave, but said nothing
about the launch decision. Runs launched on light states dominated the
run history: a spec sitting at a human gate (clarify, an undetermined
research-gate, before-audit, approve, closing-audit, tick-commit) or a
held frontier makes the workflow read state once and stop seconds later
with zero waves — deciding nothing the orchestrator could not have read
off the same one command; on Claude Code even that single fetch costs a
full probe agent. A frontier of exactly one light doc node (survey,
plan, tech, qa, tasks) is a single-agent run the orchestrator can spawn
directly, so the launch buys no fan-out and no loop.

**Decision**: graph.py — the only oracle — gained `--launch-check`, a
pure-read mode printing `{weight, launch_workflow, gate,
frontier_agents, payloads, reason}`. `weight: "wave"` (a multi-payload
wave, or any execute span — implementation is heavy even as one
runnable task, and the recompute loop after each landed task is exactly
what the workflow automates) is the only `launch_workflow: true`.
`gate` answers the gate inline with the user; `single` runs the
single-agent run mode inline (`--emit-spawns` + one spawn); `complete`
archives inline; `held` unblocks inline. Payloads are counted through
the same `frontier_payloads` enumeration `--emit-spawns` writes, so the
advisory can never drift from what a launch would actually spawn. The
dialects' metadata (`whenToUse` / `meta.description`, both regenerated
from tools/workflow-defs.py) and SKILL.md § Dynamic workflow runs carry
the rule; the zcode dialect also dropped its redundant final
`--state-json` fetch (the summary now reuses the last post-wave state,
the same parity the claude dialect already had — D-020). The weight is
the default decision rule, never a refusal: an explicit user ask for
the workflow launches it regardless.

**Why**: the cheapest workflow run is the one never launched — every
few-seconds run in the history paid a launch, a confirmation, and (on
Claude Code) a probe agent to learn something one local python command
already knew. Keeping the rule in graph.py (not in SKILL.md prose
alone) means every harness and every orchestrator reads the same
weight, and the payload count cannot disagree with `--emit-spawns`.

**Cost if wrong**: the `single` cutoff could send a genuinely heavy
lone doc node (a large spec's first survey) inline — acceptable: the
single-agent run mode is the same brief and payload, only the spawner
differs, and an explicit ask still launches the workflow. The execute
always-wave rule could launch for one tiny task — the loop after it
(next tasks, the closing-audit stop) is the workflow's other half, so
the launch still earns itself. If `find_pause` and the dialects' gate
sets ever diverge, the advisory and a real run would disagree about
`gate`; the parity test pins both to the same token set.
