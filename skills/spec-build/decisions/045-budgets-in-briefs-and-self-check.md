# D-045: the briefs carry their budgets; a red acceptance command gets a bounded self-check before it is reported

Two gaps, one decision. The numeric limits the engine holds the
writing agents to — the fix cap (5), the fix loop's round bound
(default 2) — lived in SKILL.md prose and graph.py constants; the
agents themselves never saw the number until they hit it. And a
developer whose acceptance command ran red handed the red straight
through in a `note`, costing an orchestrator round-trip for failures
one more in-session attempt would have cleared.

**Decision** (the pattern is agent-rail's "K1": every limit the rails
enforce on an agent is stated in that agent's prompt with its current
value, from one registry both sides read — after measuring that
`submit-return` was refused 45 times by a limit agents could not see):

1. **`rules/agent-limits.md`** is the canonical budget registry — one
   `## <role>` section per writing carrier. `tools/kit-rules.py`
   injects each role's section into its carrier as the generated
   `## Budgets (kit-enforced)` section (developer: fix cap 5 and the
   self-check count; fixer: the bounded rounds, default 2, and what
   burns none). drift-check's kit-rules category covers both sections;
   `tools/tests/test_kit_rules.py` cross-checks every stated number
   against the engine (graph.py's `FIX_CAP`, panel.md's round default).
2. **Self-check reruns: 2.** The developer's payload contract now says
   a red acceptance command is not a hand-off: fix what it names and
   re-run it, up to the budgeted count; still red after that, report
   it as it stands in the digest's `note` — never hidden, never
   silently widened. The delivery pass stays the one proof authority;
   this only absorbs the cheap in-session retries before it.
3. The doctrine line lives in the registry: a future length cap lands
   as a cut with a marker in the artifact, never a surprise refusal at
   hand-in.

**Consequences**: one more generated section in the two carriers
(regenerate via `tools/kit-rules.py`; sync.sh refreshes before every
install). An agent that knows its budget works to it; a budget that
changes is regenerated everywhere it is stated, and the test fails if
the stated number drifts from the engine's.
