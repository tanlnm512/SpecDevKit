# D-001: Audits batch exactly twice per plan

The before-audit runs once at Stage 4; the closing audit runs once after
every task across every phase is implemented. Nothing is audited, ticked,
or committed per task or per phase in between.

**Why**: per-task gating (BMAD-style per-story QA) defeats the parallel
wave shape — implementers would serialize on a gate — and re-introduces
the telephone game by piping proof through conversation. Batching makes
the plan all-or-nothing: one scope diff, one cleanliness sweep, one proof
run, one commit.

**Cost if wrong**: a bad task contaminates the single commit; recovery is
a fix round + full closing-audit re-run from step 7. Accepted — fix
rounds (capped 5/task) localize causes first.

**Rejected**: per-phase audit gates; feature-flag red-green per task;
per-task TDD enforced on implementers (implementers don't test or gate;
the orchestrator proves).
