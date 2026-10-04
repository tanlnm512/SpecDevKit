# E2 session transcript — spec-to-prod, bugfix pipeline

- date: 2026-10-04 · drill harness (disclosed) · bug: median() returns lower-middle for even-length lists · scratch /tmp/specdev-e2-nSkoLo (branch fix/median-even-mean; C1 293b91a, C2 ce0b5cc, Status done, tree clean)
- note: scaffold.sh takes no bugfix flag — references/bugfix.md deltas applied manually (recorded); drill instrumentation briefly rode early commits and was scope-adjudicated in the as-built record (the DoD scope gate flagged it; resolved by naming, not hiding)

## Verdicts

- C1: pass — spec.md carries the bug narrative (Current/Expected behavior with the [1,2,3,4]→3 repro) + three unchanged-behavior FRs (odd-length, empty-list ValueError, input immutability); check counts 4 FR · 5 TC · PASS
- C2: pass — research.md is exactly `not applicable — no open questions at Stage 0` (byte-exact check True); the researcher was never spawned
- C3: pass — the repro test ran RED inside plan.md's phase 1 (the regression milestone: "the repro runs RED" is the milestone's demoable deliverable) BEFORE any fix work: AssertionError 3 != 2.5, exit 1, with T002 chained (after T001)
- C4: pass — one regression TC per unchanged FR (TC-003/004/005 map FR-002/003/004 1:1; coverage matrix enforced by check.py)
- C5: pass — the delivery pass includes the revert-proof with all three outputs: pre-fix red (3 != 2.5, exit 1) → reverted (git stash): FAILED again → restored: OK, exit 0
- bonus fidelity: a real fix round fired (fix 1/5 on T001+T003 — implementer test-class names diverged from qa's TC commands; code re-briefed, test.md untouched) and audit.py mutate killed 13/13 mutants
