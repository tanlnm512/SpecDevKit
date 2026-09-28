# D-011: Audits continue past red gates

D-001 (gate first) stands for change reviews: a red gate stops the
run before the panel — mechanical fixes are cheap, reviewers are not,
and a change whose checks fail is not mergeable anyway. This decision
scopes the one exception: a **project audit does not stop at a red
gate**. Each failing check becomes a high-severity gate finding
(lens `gate`, status verified, evidence = the check's tail) carried
into the report beside the panel's findings, and the reviewers still
read the code.

**Why**: an audit's deliverable is the full list of what is wrong
with the codebase as it stands — a failing test suite is not a blocker
of that list, it is one of its most important entries. Stopping the
audit at a red gate reports exactly one class of defect and drops the
rest; the fix_from path already models the better shape (a red
pre-fix gate enters tracked as gate findings the fixer must clear).
Live case: the 441-file audit that prompted this ran on a repo whose
pytest was red (19 failed, 2 errors, 2334 passed) — under the old
rule the entire audit would have collapsed to "fix these first".

**Cost if wrong**: reviewers on a red tree may report symptoms of the
known failures — triage sees the gate findings and drops duplicates;
and a genuinely broken build can make some static reads misleading —
the report's mechanical-gate section names the failing checks, so the
reader weighs panel findings against a red floor. Change reviews keep
the hard stop, so no merge recommendation is ever issued over a red
gate.
