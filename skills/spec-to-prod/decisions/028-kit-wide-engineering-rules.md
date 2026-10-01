# D-028: Kit-wide engineering rules — one source, injected carriers

Three engineering rules bind across the suite wherever their action
happens — test discipline before adding a test, the
backgrounded-job discipline (never poll a backgrounded job), and
strict code commenting (why not what, no decision logs, no volatile
values). Their canonical text lives ONCE, in the repo-root
`rules/engineering-rules.md` — the browsable, editable file — and
`tools/kit-rules.py` injects it verbatim as the
`## Engineering rules (kit-wide)` section into two carrier views the
kit's spawn channels already load: `agents/_shared-protocol.md`
(embedded byte-verbatim into every spawn payload by `graph.py
build_payload`, reaching implementer, qa, designer(s), planner,
task-breaker, surveyor, researcher — in-session and in both workflow
dialects, reviewer exempt as before) and spec-code-review's
`agents/code-review-fixer.md` (that skill's D-012). Zero
workflow-master edits, zero re-bakes: the payload and brief channels
carry the rules with no new wiring.

**Why this shape**: the delivery decision follows the documented best
practice for short must-follow rules — inline where the agent reads
them before acting, restated at the delegation boundary (subagents do
not inherit skill or parent context; "keep gotchas in SKILL.md where
the agent reads them first"; pointer-to-file is the weaker option
vendor docs reserve for large, on-demand material). The
single-source part follows both prior art — shared prompt constants
composed at build time (OpenAI Agents SDK's RECOMMENDED_PROMPT_PREFIX,
LangChain partial_variables, Google ADK's GlobalInstructionPlugin) —
and this repo's own C-02: one committed source of truth, a tool does
the copying, a mechanical drift check (`drift-check.py`'s kit-rules
category) catches hand edits. Carriers are generated views, exactly
like plugin.json manifests and the root `agents/` personas. A
prompt-parity CI check is not yet standard practice anywhere; the
test suite (`tools/tests/test_kit_rules.py`) and the drift category
together pin injection, anchors, wiring, and scope.

Scope is writers + orchestrators, not reviewers: the panel lenses
and spec-reviewer read, they do not write, and teaching them the
writing rules would blur the review bar (spec-code-review
Principle 8 stands). The reviewer's protocol exemption is unchanged.
spec-brainstorming's lenses carry none of it (that skill's D-005).
The repo's own `specs/CONSTITUTION.md` gains the matching articles
(C-07 test discipline, C-08 commenting, C-09 backgrounded jobs), and
a thin root `AGENTS.md` (the cross-tool agents.md convention) makes
the constitution and the rules source machine-discoverable to any
coding agent working in this repo. The end-user
`templates/constitution.md` is deliberately unchanged: end-user
repos receive the rules through their installed briefs and
protocols, not through a scaffolded constitution they never asked
for.

**Cost if wrong**: a hand edit to a carrier is caught by
`kit-rules.py --check` (drift-check) and by the test suite; a source
edit that does not regenerate leaves carriers stale — same guard
catches it. A rule could over-reach (roles that never run commands
reading the backgrounded-job rule): harmless by construction, the
section's scope line says a rule whose action you never perform
does not apply.
