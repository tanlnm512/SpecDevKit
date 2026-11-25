# D-025: a failed call is not a round

The kit told the fixer never to weaken a test (D-005, D-012) and told
the orchestrator how fix rounds are counted (D-005's bound, D-022's
rounds that are not rounds), but nothing said how to read a refusal or
a failed call. The project this was learned from paid for that twice:
two of its rules gave a worker opposite orders about one refusal and
the worker stalled, and 190 of its 207 reviewer failures were the same
unanswered permission prompt retried on every pass — a tool that did
not answer read as a verdict.

**Decision** (the kit-wide rule "Refusals and failed calls"
`rules/engineering-rules.md`, adopted kit-wide alongside this record;
the fixer brief receives it through `tools/kit-rules.py`, so the
wording cannot fork — D-012's channel; this record adapts it to the
run's stage vocabulary):

1. **`contracts/run-sequence.md` gains § A failed call is not a
   round**: a fixer, reviewer or verifier spawn that returned nothing
   usable (a rate limit, a timeout, a lost session, a permission
   prompt nobody answered) opens no fix round and changes no finding's
   status; the orchestrator runs the same stage again, counts these
   retries against a bound of three per stage, and at the bound stops
   and tells the owner which stage, which error and how many times. A
   refusal by policy is final: report it, never work around it. A gate
   or ask that refuses because of what an agent produced is not
   final: fix what it names and run it again — the report row's
   `conclusion` below the derived floor is the standing example
   (D-021).
2. **SKILL.md § Run sequence points at the section** in one sentence.
3. **No engine change**: the oracle (`review_orchestrator.py`) holds
   no per-stage retry state — checked, and none added. The counting
   lives with the driving session, which already owns the stage loop,
   the `run-save` checkpoints and the `status: error` stop; a bound of
   three is a rule for that loop, not oracle state, and the checkpoint
   already makes the re-run exact (`run-resume` returns `next`).

**Consequences**: an outage or an unanswered prompt no longer burns a
fix round, flips a finding's status, or stalls the run on
contradictory orders — after three tries the run stops and the owner
learns which stage, which error, how many times. The cost if wrong is
a flaky spawn masked as an outage and retried past a real failure: the
bound caps that at three tries per stage, and a refusal by policy
(permission, hook, scope) is never retried at all — it is reported and
stops.
