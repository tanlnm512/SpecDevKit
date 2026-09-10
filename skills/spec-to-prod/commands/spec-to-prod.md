---
description: Spec-driven development - scaffold specs/<name>/ and run the multi-agent graph workflow (survey, plan, tech, tasks, tests, implement) with code-grounded evidence
argument-hint: <scaffold|bugfix|survey|research|plan|tech|tasks|qa|review|check|converge|graph|run|implement|archive> <spec-name> [T###]
skills: spec-to-prod
---

Run the spec-to-prod skill (auto-mounted) for this request: $ARGUMENTS

Verb routing ($1 = verb, $2 = spec name):

- `scaffold <name>` → the spec node: `scripts/scaffold.sh <name>`, then draft spec.md; then the clarify loop (grilling: batched rounds over a design tree of the draft's gaps, frontier-first, never asking a fact the repo can answer), then fill spec.md WITH the user
- `bugfix <name>` → the spec node for a bug, per the skill's `references/bugfix.md` deltas: scaffold, draft the bug-narrative spec.md WITH the user (unchanged-behavior FRs included); researcher usually gated off; the plan's first phase is the failing repro
- `graph <spec>` → the workflow graph's live picture, derived from doc state alone: `scripts/graph.py specs/<spec>` — per-node state and reason, the ready frontier, loop-edge status, task counts. `--state-json` for machine-readable output, `--mermaid` for the rendered graph, `--explain <node>` for why one node sits where it does, `--emit-spawns` to write one self-contained payload per frontier agent node (`--wave-dir <dir>` to land them in DIR instead of `spawns/wave-<N>/`)
- `run <spec>` → continue the full pipeline from the spec's current doc state (new or resumed): `scripts/graph.py specs/<spec> --run` — compute the frontier, run the ready wave, recompute, repeat. Pauses `AWAITING HUMAN` at every judgment stop — the five human gates (clarify, an undetermined research-gate, approve, the closing-audit judgment, tick-commit) are never auto-satisfied, and before-audit, the orchestrator's six-gate judgment, pauses the same way — runs the mechanical verify node (check.py) itself, and hands each agent wave to `--runner` (a command template with `{prompt_file}` `{role}` `{spec_dir}` `{skill_dir}`; default `print` echoes invocations — pair with `--dry-run` to plan without payloads' side effects, `--max-waves N` to bound the loop, `--wave-dir <dir>` to land payloads in DIR instead of `spawns/wave-<N>/`)
- `resume <spec>` → the same continuation, worked manually: reconstruct state per the skill's Resuming section (compute the frontier, work what it prints) instead of the `--run` auto-trigger loop — for when the orchestrator wants judgment at every step
- `survey <spec>` → single-agent repair run: surveyor (re-establish code truth)
- `research <spec>` → single-agent run: researcher (external references)
- `plan <spec>` | `tech <spec>` | `qa <spec>` → single-agent run of that authoring-wave agent
- `tasks <spec>` → task-breaker (also the fix for check.py traceability failures)
- `review <spec>` → reviewer agent: read-only BLOCK/WARN/NIT findings
- `check <spec>` → `scripts/check.py specs/<spec>` and triage the output
- `converge <spec>` → re-run surveyor against HEAD, then `scripts/audit.py
  converge specs/<spec> --repo <path>` (`--repo` defaults to the spec
  dir's grandparent) — diffs old vs new survey.md, append a task per
  NEW GAP/REGRESSED item it prints (skill's Run modes § Converge)
- `implement <spec> [T###]` → the execute node: waves of implementer agents, each payload carrying the task entry verbatim + the acceptance-test commands (always for code tasks). With T###, only that task is spawned. Per the skill's batching rules, nothing is ticked or committed until the plan-wide closing audit passes — never per task
- `archive <spec>` → only after Status: done: `scripts/archive.sh <spec>` (moves specs/<spec>/ to specs/archive/<date>-<spec>/, repoints INDEX — the as-built record)
- no verb → treat `$ARGUMENTS` as a feature request (a bug report is the `bugfix` verb); follow the skill's effort scaling (waves at every size; inline only for single-file, zero-unknown work)

Payload rules per the skill's Spawn mechanics; `check.py` after every doc-writing run; `scripts/graph.py specs/<spec>` is the scheduler's mechanical truth — consult it before and after every wave.
