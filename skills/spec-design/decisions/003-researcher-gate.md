# D-003: The researcher is conditional — gate at Stage 0

Spawn the researcher only when ≥1 real open question exists (which
library, algorithm, protocol version). Zero real questions → skip the
spawn; orchestrator writes `research.md: not applicable — no open
questions at Stage 0` so resume can tell "skipped on purpose" from
"forgotten".

**Why**: a researcher costs a full spawn (≈15× a solo pass). Most
bugfixes and single-known-pattern changes have nothing genuine to
research; manufacturing questions to justify the wave shape is the named
failure mode this gate prevents.

**Cost if wrong**: a skipped question surfaces at Stage 2 — the tech
agent reports the gap, the orchestrator spawns the researcher then
(single-agent repair run).
