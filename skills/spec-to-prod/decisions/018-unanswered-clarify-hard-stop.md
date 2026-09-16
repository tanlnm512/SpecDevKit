# D-018: An unanswered clarify round is a hard stop, not a defaults fallback

The clarify pass's question rounds are now explicitly HUMAN gates with a
defined non-answer protocol. When a round put to the user comes back
without answers — an autonomous-run harness resolving the question tool
without ever waiting (ZCode returns "user did not provide answers" in
under a second), an empty reply, a skipped dialog — the orchestrator
prints the round in chat (the ❓ format, verbatim) and **ends the turn
there**. It does not adopt the ➡️ recommended answers, does not resolve
the NEEDS CLARIFICATION markers itself, and does not spawn anything.
Open markers keep the spec node blocked and graph.py holds the frontier
at `clarify`, so the stop is resume-clean by construction: the user's
next chat message carries the answers, and the recomputed frontier
moves. SKILL.md's Execution-mode "rulings, not stalls" rule gains the
mirror clause: it governs mid-implementation conflicts on an *approved*
plan only, never the clarify pass, the approve gate, or the
closing-audit rulings ack.

**Why**: the recommended-answer convention (D-009) made every question
cheap to answer — and, on non-interactive harnesses, cheap to
*self-serve*. Observed in the wild (cairn repo, agent-skills-output
spec, 2026-09-16): a ZCode autonomous run called `AskUserQuestion` with
two clarify questions; the harness resolved the call unanswered in 0.3s
with "continue using your best judgment"; the orchestrator adopted both
recommendations as FR rulings and rewrote the NEEDS CLARIFICATION marker
itself — a spec the user never agreed to, laundered through the clarify
loop's own closure rule. That rule ("never left open") was written to
force closure *through the user*, not to authorize self-closure. The
user's ruling on the observed run: when the spec is being broken down,
stop and show the questions/scope — get the answers from the human.

**What's preserved, not overridden**: the tri-state closure rule
(answered / deferred / named assumption), the frontier/round model,
"an ambiguity caught here never reaches a downstream agent", "do not
spawn the analysis wave until the user has confirmed the shared
understanding", and Execution mode's rulings-not-stalls — which keeps
its original momentum purpose inside execution instead of bleeding into
authoring.

**Cost if wrong**: a truly unattended run now parks at `clarify` instead
of producing a defaults-based draft to veto at the approve gate later.
That is the intended trade: an unattended run has nobody to veto at the
approve gate either, so "draft now, veto later" silently becomes "ship
unvetoed". A user who *does* want the recommendations can say so in one
message — the same one-glance cost the recommendations were adopted
for (D-009). Prose-only change: nothing in `check.py`/`graph.py` gates
on it, and the graph's existing behavior (markers hold the spec node)
already enforces the stop mechanically once the orchestrator stops
resolving markers itself.
