# D-060: the --run contract amends for headless execute

spec-build D-041 lifts the custom-runner refusal at execute where
`scripts/mark.py` ships beside `graph.py`: the loop claims the wave,
runs it, and lands each implemented task through mark.py. The shared
engine's own contract line changes here, because this copy ships the
amended bytes:

- the old rule — "gates are never auto-satisfied and this loop mutates
  no doc state of its own" — becomes "…mutates no doc state of its own
  EXCEPT through mark.py, the single marker writer" (spec-build D-039);
- where this package ships no mark.py (it does not — mark.py imports
  this package's audit.py, so it is build-only), a custom runner
  meeting execute payloads is still refused with exit 2 before any
  invocation (spec-build D-038). This package also ships no developer
  brief, so it cannot emit execute payloads at all; the refusal is the
  belt under that brace.

Human gates stay absolute in every package: clarify, approve,
research-gate, tick-commit are never auto-satisfied, and the headless
path writes `(implemented)` markers only — ticks and commits stay the
user's.
