# D-060: keep the entry gate, the happy path and the pointers in SKILL.md; the execute edge cases live in a contract, read on demand

SKILL.md stood at 432 lines, and most of the growth was restatement:
the task-marker transition table, the resume path and the fix cap's
three options with their recommendation and same-signature rules sat
in the body beside the steps every run takes, and instructions cited
decision numbers ("(D-043)", "(D-047)") an executing model cannot act
on — the number names a record; it carries no instruction. A body that
restates its contracts is read in full on every invocation to answer
questions the run mostly never asks (kit-hardening plan § 4.1).

**Decision**:

1. **SKILL.md keeps the entry gate, the happy path and the pointers.**
   What every run needs stays in the body: the invocation gate, the
   run command and its per-task waves, how a fix round opens and how
   the round-4 `Model:` line is honored, and the delivery pass's
   numbered summary.
2. **Edge cases live in contracts, read on demand.** The execute edge
   cases are `contracts/execution.md`: the task-marker table
   (§ Task markers), § Resume, and the fix cap's adjudication — the
   three options with their consequences, the same-signature rule and
   the recommendation rule. Every sentence moved verbatim; SKILL.md
   § Fix rounds ends with the one pointer to the file.
3. **No decision numbers in instructions.** An instruction sentence
   loses an inline `D-###` citation and keeps the instruction. The
   number stays only where it is load-bearing — where it names a
   ruling a task must carry ("append the D-### to tech-spec.md"). The
   contract files and the ADRs keep every citation.
4. **The live re-record is the acceptance.** The standing evals in
   `evals/cases.md`, re-recorded green, are what proves that a session
   reading the slimmer body still resumes, settles a blocked task and
   adjudicates the cap by the contract. It was not run in this change;
   it is the owner's step before release.

**Consequences**: the body read on every invocation is shorter, and an
edge case is read when it is reached instead of carried always. The
pointer is now the only thread from the body to an edge case: a
session that does not open `contracts/execution.md` at the fix cap
holds the stop marker and none of the options, and the pointer names
the cap while the same-signature rule fires a round or two before it —
a session that stops at the pointer when `mark.py fail` reports a
repeat reads that rule late. The cost if this is wrong is a live eval
that improvises an edge case from memory; the re-record is what shows
it. No test pins the pointer rule, so a later edit can grow the body
back without a red suite.
