# D-063: the survey folds into tech, and tasks wait for test.md

Two faults in the authoring order. The survey wave mostly repeated what
intake had already probed: spec-define's grill reads the repo for the
idea's areas before spec.md exists, and the survey analyst then
re-grepped the same areas into a separate survey.md, a whole spawn whose
main consumer was the tech lens one wave later. And the tasks lens was
told to make every task own the tests that prove it (D-062) while its
node did not wait for qa and its payload never named test.md: at
Effort: standard one architect wrote task.md in the same spawn as plan
and tech, before the tester could finish. Test cases landed with no
owning task, and the proofs of those cases read PENDING at delivery
(spec-build D-042).

**Decision**:

1. **The survey node and survey.md are retired.** The tech lens grounds
   first: tech-spec.md gains `## Code state` — one item per requirement
   (evidence pasted verbatim, DONE/PARTIAL/TODO status, verify command,
   gap) plus supporting evidence — and the doc's header carries the
   `**Baseline**: <version> @ <sha>` survey.md owned. The survey lens's
   evidence rules move into the tech lens; every "cite only survey.md"
   rule now reads "cite only tech-spec.md § Code state". The tech node is
   done when tech-spec.md is filled and `check.py --code-state-only`
   (the renamed self-check) exits 0. The analyst keeps the intent,
   research, and constitution lenses.
2. **New order**: spec → tech (after research resolves) → plan; qa is
   ready on spec alone, beside them; tasks waits for tech, plan, and qa;
   verify waits for all four. At Effort: standard one merged architect
   spawn authors tech then plan; tasks is always its own spawn.
3. **The tester reads spec.md only.** It no longer reads code state to
   mark regression guards; it writes a case for every requirement.
4. **The tasks lens owns TC assignment.** Each TC gets a `Proves:
   TC-###` sub-line on the task that writes its test, or — when § Code
   state reads its requirement DONE — a `- TC-### — …` line under
   task.md's `## Regression guards`. `check.py` FAILs a case with
   neither (WARN once the contract is frozen, like the other coverage
   shapes) and FAILs an owned id test.md does not define. An
   implementer's acceptance list follows its task's `Proves:` line.
5. **Freshness re-keys on tech-spec.md's Baseline**: the converge loop
   edge runs tech → tasks, `--repair tech` carries the DELTA RE-GROUND
   block, and `audit.py converge` diffs § Code state's items against
   their committed version. The freeze manifest drops survey.md.
6. **Migration**: spec-build's `migrate.py <spec-dir> upgrade` folds an
   existing survey.md into an appended `## Code state` section (title
   dropped, H2s demoted) and deletes it. `check.py` FAILs a docset that
   still holds survey.md and names that command. The kit's own example
   docsets were folded with the same step, then reordered to the
   template's shape.

**Consequences**: one fewer spawn per full-tier spec, and grounding sits
in the document that cites it. Plan now waits on tech, so a large-effort
run takes one more wave. A docset approved before the fold carries its
folded § Code state in tech-spec.md's append zone, which the prefix
freeze does not pin; the next re-approval freezes it again. Archived and
done docsets are never migrated and keep their survey.md as history.
