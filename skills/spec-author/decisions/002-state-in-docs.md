# D-002: State lives in the docs — no step ledger

A fresh session reconstructs pipeline state from specs/<name>/ alone:
which artifacts exist = which stages ran; task.md statuses = progress;
spec.md Status: = lifecycle position; `Before-audit: passed @ <sha>` =
the gate record. No separate progress log, session file, or step ledger.

**Why**: a second state store drifts from the artifacts it describes and
becomes one more thing to reconcile on resume. The docs are already
written; making them authoritative costs nothing extra.

**Cost if wrong**: resume depends on docs being current — mitigated by
check.py (failures name the stage to re-run) and the survey-staleness
warning.
