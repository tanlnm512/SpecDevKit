# D-004: Definition of Done is conjunctive — never a score

Ten binary gates (gates/dod.md), all must pass; nothing averaged, no
partial credit. A feature at 92% is 0% shippable. `audit.py dod` prints
the scorecard; the closing audit owns the verdict.

**Why**: a score invites shipping at 92. Binary artifact-backed gates
keep the metric honest — the numerator's quality is itself gated (gate 8
kills vacuous TCs that would make gate 1 mean nothing).

**Cost if wrong**: none accepted — WARNs may be parked, but only with a
signed D-### ruling, never swept.
