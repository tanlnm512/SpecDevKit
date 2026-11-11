# D-035: The tiny tier's delivery pass, and archive only what was delivered

A review that ran the real scripts on the delivered tiny example and
the mini-spec found the delivery path weaker than the graph:

- `audit.py` read only task.md, test.md, tech-spec.md, and plan.md. On a
  `Tier: tiny` spec `proofs --run` ran 0 commands and passed, dod gate 4
  read `FAIL 0/0 ticked` on a fully ticked spec, and `scope` flagged files
  that spec.md § Tasks lists under `Touches:`.
- A failed proof kept the last 100 characters of stdout and dropped
  stderr, while § Fix rounds demands "the failing command and its output
  verbatim".
- `archive.sh` checked only `Status: done`: a spec with no `Delivered:`
  record was archived while the graph said `archive blocked`, the INDEX
  still read `draft`, and the move was left uncommitted with no step
  naming it.
- Nothing said what C1 and C2 stage, so `git add -A` would commit
  `spawns/` payloads and the auditor's diff patch. After C2 the run
  ended without naming a next step, and spec-review was never mentioned.
- Running proofs left `__pycache__/` files that scope and hygiene then
  flagged. `mutate` flipped lines the diff never touched. A frozen
  survey's line drift raised WARNs that dod said must be "fixed or
  ruled", though the freeze forbids fixing them.

**Decision**:

1. **At `Tier: tiny`, spec.md is the docset for every audit
   subcommand.** The proofs are each § Tasks entry's `Accept:` commands,
   labelled by task id. An Accept line saying the command "exits
   nonzero" passes only on a nonzero exit. `scope` checks changed files
   against spec.md. Completeness, coverage, and `archived` read § Tasks
   through specstate's parsers (`tiny_task_text`, `task_entries`).
   `converge` reports n/a.
2. **A failed proof prints its exit code and the last 40 lines of
   combined stdout and stderr.** The orchestrator pastes that block into
   `notes/T###.md`, which the fix payload embeds. audit.py does not
   write the note itself, because choosing the task and round is the
   orchestrator's job.
3. **Archive requires delivery.** `archive.sh` refuses without a
   `Delivered: commit @ <sha|->` record (in task.md, or in spec.md at
   tiny). It sets the INDEX line's status word to `done`, drops
   `spawns/`, and prints the follow-up commit for the user to approve.
   `audit.py archived` fails an archived spec that has no delivery record.
4. **Staging is by path.** C1 carries code, tests, and the ticked task
   list. C2 carries the delivery record, `Status: done`, the INDEX line,
   and `notes/` (the evidence behind `(fixed n/5)`), plus `approvals/`
   if it is not yet committed. `spawns/` is never committed: it is
   regenerable and gets deleted after C2.
5. **Delivery names spec-review.** Step 3 adds `/spec-review branch`
   for changes touching auth, persistence, or migrations, or when the
   user asks. A new step 8 ends the run by naming the next steps: push
   and PR (both the user's), an optional `/spec-review`, and archive.
6. **Instrument hygiene.** Scope, clean, and mutate skip tool-cache
   paths (`__pycache__`, `.pytest_cache`, `*.pyc`, and similar), and
   clean skips binary untracked files. `mutate` only mutates sites on
   lines the diff added or changed. dod gate 5 counts frozen-survey
   drift WARNs as expected and already ruled.

**Consequences**: the Accept grammar gains one more reading ("exits
nonzero") in audit.py only, and graph.py and check.py are unchanged.
The regression gate stays MANUAL, and the spec-review step is advice,
not a gate (a later wave may automate both). `migrate.py` now accepts
`approved` docsets, because task.md sits outside the freeze.
