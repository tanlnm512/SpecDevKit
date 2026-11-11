# D-005: The fix loop is bounded, verified, and continuable from a report

With `fix_rounds > 0` an author/fixer fixes confirmed findings in the
working tree (minimal, repo style, never commits, never weakens a test
— pins corrected behavior instead); every attempted fix is verified by
an independent reader (fixed/unfixed/worse); the gate re-runs (failures
become findings the fixer must clear); a fresh-eyes reviewer scans only
the fixer's paths for NEW defects. `fix_from` carries a previous
report's findings JSON into that loop directly, skipping the review
stages — the decision gate becomes two cheap runs: review, present,
ask, then fix from the report.

**Why**: a dynamic workflow cannot pause mid-run to ask the user, so
the ask must live between runs; re-reviewing to fix what was already
found wastes the panel's expensive half. The loop stays bounded
(default 2) because unbounded auto-fixing is how an author loses track
of their own tree.

**Cost if wrong**: unverified fixes ship cosmetic proximity as
resolution; an unbounded loop rewrites the tree while the user is away.
A fix_from run inherits the previous report's coverage — disclosed
under notCovered, never silently reset.
