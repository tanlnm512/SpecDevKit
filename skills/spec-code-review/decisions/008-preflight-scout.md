# D-008: Preflight scout — one read-only map before the panel

After a green gate, before any reviewer, one scout explores the
codebase and the modules the target touches and returns a bounded
RepoMap (modules, conventions, riskAreas). The map rides the reviewer
and final-assessment asks as orientation; triage, confirmers and the
fixer never see it; the scout itself never reports findings.

**Why**: each specialist was rediscovering the same codebase context
per lens, and grounding "design fit" differently per reviewer is
exactly the drift the panel exists to prevent — one scout turn
amortizes discovery into a shared map every lens starts from. Project
mode needs it most: thirty files with no diff give a reviewer no
orientation at all.

**Cost if wrong**: a scout that editorializes defects would launder
unverified findings past triage and confirmation — so the map carries
no findings and confirmers never see it; an unbounded map would bloat
every ask — so ≤8/6/6; running it before the gate would burn agent
attention on a mechanically red target — so it sits after the green
gate (D-001 keeps precedence).
