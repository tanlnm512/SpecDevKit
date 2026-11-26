# D-030: keep the entry gate, the happy path and the pointers in SKILL.md; the edge cases live in the contracts, read on demand

SKILL.md stood at 342 lines, and much of the growth was restatement:
the pr-mode CI triage, the stop ask's content, a failed call and
resume retold what `contracts/panel.md`, `contracts/run-sequence.md`
and `gates/recommendation.md` arbitrate, beside the stages every run
executes, and instructions cited decision numbers ("(D-023)",
"D-024") an executing model cannot act on — the number names a record;
it carries no instruction. A body that restates its contracts is read
in full on every invocation to answer questions the run mostly never
asks (kit-hardening plan § 4.1).

**Decision**:

1. **SKILL.md keeps the entry gate, the happy path and the pointers.**
   What every run needs stays in the body: when to use, the targets,
   the principles, the stages' own steps, the run sequence's phase
   order, the launch discipline and how to read the result — and what
   the session itself does at a stop: the red-gate rules, and putting
   the stop ask to the user.
2. **Edge cases live in contracts, read on demand.** A passage that
   restates panel.md, run-sequence.md or gates/recommendation.md is
   deleted and the pointer the file already makes stays. No new
   contract file: every deleted passage already had a home.
3. **No decision numbers in instructions.** An instruction sentence
   loses an inline `D-###` citation and keeps the instruction. The
   number stays only where it is load-bearing — where it names a
   ruling a task must carry. The contract files and the ADRs keep
   every citation.
4. **The live re-record is the acceptance.** The standing evals in
   `evals/cases.md`, re-recorded green, are what proves that a session
   reading the slimmer body still stops at a red gate, hands a stop
   ask to the user and resumes by the contract. It was not run in this
   change; it is the owner's step before release.

**Consequences**: the body read on every invocation is shorter, and an
edge case is read from its contract when it is reached instead of
carried always. The pointer is now the thread from the body to each
deleted passage, and for the pr-mode CI triage it is the general one
("panel.md § The mechanical gate"): a session that skips the contract
at a red CI row meets an `infrastructure` class it has not read about.
The cost if this is wrong is a live eval that misreads a gate row or a
stop ask; the re-record is what shows it. No test pins the pointer
rule, so a later edit can grow the body back without a red suite.
