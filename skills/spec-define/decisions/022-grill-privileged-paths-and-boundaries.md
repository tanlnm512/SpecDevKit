# D-022 — the grill asks who may use a privileged path, and pins counts and exemptions

An intake recorded security as "none" for a feature whose rules said an
operator submit bypasses a hold. The question that mattered — who may
invoke the bypass, and how the system verifies it from the caller rather
than from a field the caller writes — surfaced only in the second
contract review, after six documents were written. The same intake left
a count's default, whether the first item counts as 1 or 0, and whether
a negative value is valid to later rounds.

**Decision**: references/grilling.md's failure-pattern table gains three
rows. A privileged word (operator, admin, force, override, bypass, skip)
becomes "who may invoke it, verified from the caller"; a count, window,
limit or timeout becomes default, unit, what counts, whether zero or
negative is valid, and whether startup refuses a bad value; a general
rule becomes "which sources, roles or paths are exempt, and what happens
at each edge". Like every row, the facts behind them stay the runner's
job and only the judgment call goes to the frontier.

**Consequences**: a privilege question is asked at intake, where its
answer costs one line in intent.md, not at review, where it costs a
re-draft of every document.
