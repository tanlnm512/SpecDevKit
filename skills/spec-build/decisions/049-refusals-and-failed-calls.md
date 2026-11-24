# D-049: a refusal or a failed call is one of three kinds, named before acting

The kit-wide rules said nothing about how to read a refusal or a
failed call. The project this was learned from paid for the gap three
ways: two of its rules gave a worker opposite orders about one
refusal and the worker stalled; 190 of its 207 reviewer failures were
one unanswered permission prompt retried on every pass; a retry
counter was reset inside its own loop and one task burned 28 launches.
An agent with no rule classifies by mood — fixes what needs waiting,
waits on what needs fixing, and reports verdicts for checks that
never ran.

**Decision**:

1. **The rules text names the three kinds**, and the kind is named
   before acting on it: fix and run again — the refusal is about your
   own output, not final, do not stop on it; wait, then retry — the
   tool itself did not answer, nothing in the work is wrong, retry up
   to three times, then report `blocked: <tool> did not answer:
   <error>` and never turn it into a result; stop and report — a
   refusal by policy, never worked around, its exact text reported.
2. **A failed call is never a failed check.** A check is reported
   only when the agent saw it run; otherwise `not run: <why>` — never
   a failure, a pass or a verdict the agent did not observe. This is
   the honesty line D-042 and D-047 drew for proofs (PENDING and
   ENV-BLOCKED are neither pass nor failure) extended to every call
   an agent makes.
3. **The retry bound (three) lives in the rules text itself, not in
   `rules/agent-limits.md`.** That file states only the numbers an
   engine enforces — the fix cap `graph.py` counts, the developer's
   self-check reruns, the fixer's `fix_rounds`. No engine counts a
   spawn's retries; the count is the agent's own discipline at the
   moment of the failed call, so the bound sits beside the behaviour
   it bounds instead of dressing itself up as an enforced budget.
4. **The orchestrator's mirror is this skill's half**: a spawn that
   did not answer is not a failed implementation — the task's
   acceptance commands did not fail, nothing ran. Release the claim
   (`mark.py release`, reason `blocked: <tool> did not answer:
   <what>` — the `blocked:` prefix files it under the release
   telemetry's blocked category), spawn the task again, count three
   per task, then stop and tell the owner which task, which error,
   how many times. A fix round never opens on a call that did not
   answer or a refusal by policy; the engine's part is only
   `release` clearing the claim so the next emit re-spawns.

**Consequences**: the cost if wrong is the one the gap already
charged — a policy refusal worked around, a prompt nobody answered
retried forever, a verdict reported for a check that never ran. The
bound's honest limit: it is a rule, not an enforced counter — a
miscounting agent is caught by the same-signature watch (D-044) or
the owner reading the transcript, not by the engine; the delivery
pass's live proofs and the resume path's orphan settlement (a
`blocked:` digest → release and rule) stay the backstop.
